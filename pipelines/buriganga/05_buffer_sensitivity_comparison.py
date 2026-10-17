"""
Quantifies buffer radius sensitivity and classification discordance between
isotropic circular buffers (200m and 500m) versus non-water flow corridors.

Classification rule:
  f_{built, nw} >= 0.70 -> "industrial_built"
  otherwise             -> "mixed_land"

Demonstrates that naive circular buffers misclassify stations with high open water
coverage (e.g., Hazaribagh at 62.1% water), whereas non-water flow corridors
correctly identify industrial/built infrastructure.

Inputs:
  outputs/buriganga/land_cover_distance_resolved.csv
  outputs/buriganga/stations_snapped.csv

Outputs:
  outputs/buriganga/h2_classification_comparison.csv
  outputs/buriganga/h2_per_station.csv
"""

import ee
import os
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_DIR    = os.path.join(REPO_ROOT, "outputs", "buriganga")
LC_CSV     = os.path.join(OUT_DIR, "land_cover_distance_resolved.csv")
SNAP_CSV   = os.path.join(OUT_DIR, "stations_snapped.csv")

GEE_PROJECT     = "sundarban-489216"
CORRIDOR_KM     = 1.0
BUILT_THRESHOLD = 0.70

CORE_STATIONS = [
    "MIRPUR_BRIDGE", "BOSILA_BRIDGE", "HAZARIBAGH",
    "SATMASJID_ROAD", "CHADNIGHAT", "BCFB", "FATULLAH"
]

def main():
    print("Initializing Google Earth Engine...")
    ee.Initialize(project=GEE_PROJECT)

    df_lc   = pd.read_csv(LC_CSV)
    df_snap = pd.read_csv(SNAP_CSV)

    print("\nEvaluating Flow-Aware Corridor Classification (1km upstream)...")
    corridor_classes = {}
    for st in CORE_STATIONS:
        sub = df_lc[(df_lc["station_id"] == st) & (df_lc["upstream_distance_m"] <= CORRIDOR_KM * 1000)]
        if sub.empty:
            corridor_classes[st] = "no_data"
            continue

        total_px = sub.drop_duplicates("upstream_distance_m")["total_pixels"].sum()
        water_px = sub[sub["land_cover_class"] == "water"]["pixel_count"].sum()
        built_px = sub[sub["land_cover_class"] == "built"]["pixel_count"].sum()
        nw_px    = total_px - water_px

        built_frac = built_px / nw_px if nw_px > 0 else 0
        label = "industrial_built" if built_frac >= BUILT_THRESHOLD else "mixed_land"
        corridor_classes[st] = label
        print(f"  {st:16s}: non_water={nw_px:5.0f} px, built={built_frac*100:5.1f}% -> {label}")

    dw = (ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
            .filterDate("2021-01-01", "2023-12-31").select("label").mode())

    buffer_classes = {200: {}, 500: {}}
    for radius in [200, 500]:
        print(f"\nEvaluating Circular Buffer ({radius}m radius)...")
        for _, row in df_snap.iterrows():
            st = row["station_id"]
            if st not in CORE_STATIONS:
                continue
            pt = ee.Geometry.Point([row["snapped_lon"], row["snapped_lat"]])
            buf = pt.buffer(radius)
            try:
                hist = dw.reduceRegion(
                    reducer=ee.Reducer.frequencyHistogram(),
                    geometry=buf, scale=10, maxPixels=1e6
                ).getInfo().get("label", {})
                total_px   = sum(hist.values())
                water_px   = hist.get("0", 0)
                built_px   = hist.get("6", 0)
                nw_px      = total_px - water_px
                built_frac = built_px / nw_px if nw_px > 0 else 0
                label      = "industrial_built" if built_frac >= BUILT_THRESHOLD else "mixed_land"
                buffer_classes[radius][st] = label
                print(f"  {st:16s}: non_water={nw_px:5.0f} px, built={built_frac*100:5.1f}% -> {label}")
            except Exception as ex:
                print(f"  {st:16s}: GEE error: {ex}")
                buffer_classes[radius][st] = "error"

    per_station = []
    for st in CORE_STATIONS:
        per_station.append({
            "station_id": st,
            "corridor_class": corridor_classes.get(st, "no_data"),
            "buffer_200m_class": buffer_classes[200].get(st, "no_data"),
            "buffer_500m_class": buffer_classes[500].get(st, "no_data"),
        })

    df_ps = pd.DataFrame(per_station)
    print("\nPer-Station Categorical Comparison:")
    print(df_ps.to_string(index=False))

    xtab_path = os.path.join(OUT_DIR, "h2_classification_comparison.csv")
    ps_path   = os.path.join(OUT_DIR, "h2_per_station.csv")

    df_xtab = df_ps.groupby(["corridor_class", "buffer_200m_class"]).size().reset_index(name="count")
    df_xtab.to_csv(xtab_path, index=False)
    df_ps.to_csv(ps_path, index=False)
    print(f"\nSaved outputs:\n  {xtab_path}\n  {ps_path}")

if __name__ == "__main__":
    main()
