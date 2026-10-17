"""
Extracts distance-resolved upstream land cover for Buriganga monitoring stations
using Google Earth Engine (Sentinel-2 Dynamic World 2021-2023 modal composite).

For each station, the river centerline is segmented into 50 x 100m bins up to
5,000m upstream. A 600m-wide corridor (300m buffer on each side) is extracted.

Normalization: Terrestrial fractions are computed strictly relative to non-water
pixel area to prevent aquatic dilution artifacts.

Inputs:
  outputs/buriganga/centerline.geojson
  outputs/buriganga/stations_snapped.csv

Outputs:
  outputs/buriganga/land_cover_distance_resolved.csv
  outputs/buriganga/land_cover_summary.csv
"""

import ee
import json
import os
import pandas as pd
import numpy as np
from shapely.geometry import shape
from geopy.distance import geodesic

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_DIR    = os.path.join(REPO_ROOT, "outputs", "buriganga")
CL_PATH    = os.path.join(OUT_DIR, "centerline.geojson")
SNAP_PATH  = os.path.join(OUT_DIR, "stations_snapped.csv")
OUT_CSV    = os.path.join(OUT_DIR, "land_cover_distance_resolved.csv")

GEE_PROJECT     = "sundarban-489216"
BIN_SIZE_M      = 100
MAX_UPSTREAM_M  = 5000
CORRIDOR_M      = 300
MIN_NONWATER_PX = 10

DW_CLASSES = {
    0: "water", 1: "trees", 2: "grass", 3: "flooded_vegetation",
    4: "crops", 5: "shrub_and_scrub", 6: "built", 7: "bare", 8: "snow_and_ice"
}

CORE_STATIONS = [
    "MIRPUR_BRIDGE", "BOSILA_BRIDGE", "HAZARIBAGH",
    "SATMASJID_ROAD", "CHADNIGHAT", "BCFB", "FATULLAH"
]

def main():
    print("Initializing Google Earth Engine...")
    ee.Initialize(project=GEE_PROJECT)

    with open(CL_PATH) as f:
        gj = json.load(f)
    centerline = shape(gj["features"][0]["geometry"])
    cl_coords = list(centerline.coords)

    cum_m = [0.0]
    for i in range(1, len(cl_coords)):
        a = (cl_coords[i-1][1], cl_coords[i-1][0])
        b = (cl_coords[i][1],   cl_coords[i][0])
        cum_m.append(cum_m[-1] + geodesic(a, b).meters)
    total_cl_m = cum_m[-1]
    print(f"Centerline total length: {total_cl_m:.0f}m")

    df_snap = pd.read_csv(SNAP_PATH).sort_values("along_channel_m").reset_index(drop=True)

    def get_upstream_segment(station_along_m, bin_start_m, bin_end_m):
        snap = df_snap[df_snap["along_channel_m"] == station_along_m]
        if snap.empty:
            idx = (df_snap["along_channel_m"] - station_along_m).abs().idxmin()
            snap = df_snap.iloc[[idx]]
        frac = float(snap["along_channel_frac"].values[0])
        st_cl_m = frac * total_cl_m
        start_cl = max(0.0, st_cl_m - bin_end_m)
        end_cl   = st_cl_m - bin_start_m
        if end_cl <= 0:
            return []
        seg = [cl_coords[i] for i, d in enumerate(cum_m) if start_cl <= d <= end_cl]
        if len(seg) < 2:
            for i in range(len(cum_m) - 1):
                if cum_m[i] <= end_cl and cum_m[i+1] >= start_cl:
                    return [cl_coords[i], cl_coords[i+1]]
        return seg

    dw = (ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
            .filterDate("2021-01-01", "2023-12-31")
            .select("label").mode())

    all_records = []
    n_bins = MAX_UPSTREAM_M // BIN_SIZE_M

    for _, row in df_snap.iterrows():
        st_id = row["station_id"]
        st_along = row["along_channel_m"]

        if st_id not in CORE_STATIONS:
            continue

        print(f"\nProcessing {st_id} (along_channel={st_along:.0f}m)...")
        station_records = []

        for b in range(n_bins):
            bin_start = b * BIN_SIZE_M
            bin_end   = (b + 1) * BIN_SIZE_M
            bin_mid   = (bin_start + bin_end) / 2

            seg = get_upstream_segment(st_along, bin_start, bin_end)
            if len(seg) < 2:
                continue

            ee_line = ee.Geometry.LineString([[lon, lat] for lon, lat in seg])
            ee_corridor = ee_line.buffer(CORRIDOR_M)

            try:
                hist = dw.reduceRegion(
                    reducer=ee.Reducer.frequencyHistogram(),
                    geometry=ee_corridor, scale=10, maxPixels=1e6
                ).getInfo().get("label", {})

                if not hist:
                    continue

                total_px    = sum(hist.values())
                water_px    = hist.get("0", 0)
                nonwater_px = total_px - water_px

                for cls_str, px in hist.items():
                    cls_idx  = int(float(cls_str))
                    cls_name = DW_CLASSES.get(cls_idx, "unknown")
                    frac     = px / total_px if total_px > 0 else 0
                    if cls_name != "water" and nonwater_px > 0:
                        frac_nw = px / nonwater_px
                    elif cls_name == "water":
                        frac_nw = water_px / total_px if total_px > 0 else 0
                    else:
                        frac_nw = 0.0

                    station_records.append({
                        "station_id":           st_id,
                        "upstream_distance_m":  bin_mid,
                        "bin_start_m":          bin_start,
                        "bin_end_m":            bin_end,
                        "land_cover_class":     cls_name,
                        "pixel_count":          int(px),
                        "total_pixels":         int(total_px),
                        "non_water_pixels":     int(nonwater_px),
                        "fraction":             round(frac, 4),
                        "fraction_of_nonwater": round(min(frac_nw, 1.0), 4)
                    })
            except Exception as ex:
                print(f"  {st_id} bin {bin_mid:.0f}m: GEE error: {ex}")

        if station_records:
            all_records.extend(station_records)

    df_lc = pd.DataFrame(all_records)
    df_lc.to_csv(OUT_CSV, index=False)
    print(f"\nSaved: {OUT_CSV} ({len(df_lc)} rows)")

    pivot = (df_lc.groupby(["station_id","land_cover_class"])["fraction_of_nonwater"]
             .mean().unstack(fill_value=0).round(4))
    summary_path = os.path.join(OUT_DIR, "land_cover_summary.csv")
    pivot.to_csv(summary_path)
    print(f"Summary saved: {summary_path}")

if __name__ == "__main__":
    main()
