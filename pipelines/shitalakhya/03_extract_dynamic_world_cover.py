"""
Extracts distance-resolved upstream land cover for Shitalakhya monitoring stations
using Google Earth Engine (Sentinel-2 Dynamic World 2021-2023 modal composite).

Utilizes ee.FeatureCollection.reduceRegions for parallel batch reduction across
upstream corridor segments (50 x 100m bins up to 5,000m, 600m total corridor width).

Inputs:
  outputs/shitalakhya/centerline_shitalakhya.geojson
  outputs/shitalakhya/stations_shitalakhya_snapped.csv

Outputs:
  outputs/shitalakhya/land_cover_shitalakhya_resolved.csv
"""

import ee
import json
import os
import pandas as pd
import numpy as np
from shapely.geometry import shape, LineString
from geopy.distance import geodesic

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_DIR    = os.path.join(REPO_ROOT, "outputs", "shitalakhya")
CL_PATH    = os.path.join(OUT_DIR, "centerline_shitalakhya.geojson")
SNAP_PATH  = os.path.join(OUT_DIR, "stations_shitalakhya_snapped.csv")
OUT_CSV    = os.path.join(OUT_DIR, "land_cover_shitalakhya_resolved.csv")

GEE_PROJECT     = "sundarban-489216"
BIN_SIZE_M      = 100
MAX_UPSTREAM_M  = 5000
CORRIDOR_M      = 300
MIN_NONWATER_PX = 10

DW_CLASSES = {
    0: "water", 1: "trees", 2: "grass", 3: "flooded_vegetation",
    4: "crops", 5: "shrub_and_scrub", 6: "built", 7: "bare", 8: "snow_and_ice"
}

STATIONS = ["PORT_ROAD", "MAJIRA_DEMRA_GHAT", "MURAPARA_RUPGONJ", "GHORASHAL"]

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

    df_snap = pd.read_csv(SNAP_PATH).sort_values("along_channel_m").reset_index(drop=True)

    def get_upstream_segment(st_along_m, bin_start_m, bin_end_m):
        start_cl = max(0.0, st_along_m - bin_end_m)
        end_cl   = st_along_m - bin_start_m
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

    features = []
    n_bins = int(MAX_UPSTREAM_M / BIN_SIZE_M)

    for station_id in STATIONS:
        snap_row = df_snap[df_snap["station_id"] == station_id]
        if snap_row.empty:
            continue
        st_along_m = float(snap_row["along_channel_m"].values[0])

        for b in range(n_bins):
            bin_start = b * BIN_SIZE_M
            bin_end   = (b + 1) * BIN_SIZE_M
            seg_coords = get_upstream_segment(st_along_m, bin_start, bin_end)

            if len(seg_coords) < 2:
                continue

            line = LineString(seg_coords)
            ee_geom = ee.Geometry.LineString(list(line.coords)).buffer(CORRIDOR_M)

            features.append(ee.Feature(ee_geom, {
                "feat_id": f"{station_id}_{b}",
                "station_id": station_id,
                "bin_index": b,
                "bin_start_m": bin_start,
                "bin_end_m": bin_end,
                "upstream_distance_m": (bin_start + bin_end) / 2.0
            }))

    fc = ee.FeatureCollection(features)
    print(f"Batch reducing {len(features)} corridor bin geometries on GEE...")

    reduced_fc = dw.reduceRegions(
        collection=fc,
        reducer=ee.Reducer.frequencyHistogram().setOutputs(["histogram"]),
        scale=10
    )

    info = reduced_fc.getInfo()
    all_records = []

    for feat in info["features"]:
        props = feat["properties"]
        station_id    = props["station_id"]
        upstream_dist = props["upstream_distance_m"]
        bin_start     = props["bin_start_m"]
        bin_end       = props["bin_end_m"]

        counts = props.get("histogram", {})
        if not counts:
            continue

        px_counts = {cls_name: 0 for cls_name in DW_CLASSES.values()}
        for k_str, val in counts.items():
            k_int = int(k_str)
            if k_int in DW_CLASSES:
                px_counts[DW_CLASSES[k_int]] = int(val)

        total_px    = sum(px_counts.values())
        water_px    = px_counts["water"]
        nonwater_px = total_px - water_px

        for cls_name, p_cnt in px_counts.items():
            frac_naive    = p_cnt / total_px if total_px > 0 else 0.0
            frac_nonwater = p_cnt / nonwater_px if nonwater_px >= MIN_NONWATER_PX else 0.0
            all_records.append({
                "station_id": station_id,
                "upstream_distance_m": upstream_dist,
                "bin_start_m": bin_start,
                "bin_end_m": bin_end,
                "land_cover_class": cls_name,
                "pixel_count": p_cnt,
                "total_pixels": total_px,
                "water_pixels": water_px,
                "non_water_pixels": nonwater_px,
                "fraction": frac_naive,
                "fraction_of_nonwater": frac_nonwater
            })

    df_out = pd.DataFrame(all_records)
    df_out.to_csv(OUT_CSV, index=False)
    print(f"Saved {len(df_out)} land cover records to {OUT_CSV}")

if __name__ == "__main__":
    main()
