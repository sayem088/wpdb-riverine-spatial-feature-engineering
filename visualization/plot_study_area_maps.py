"""
Renders study area overview maps:
  1. Study area map showing JRC centerline, 7 core and 2 supplementary monitoring stations,
     and circular buffer extraction rings (200m and 500m).
  2. Upstream skeleton validation map showing JRC occurrence water pixels (>20%) and
     the automated skeleton traced from Mirpur Bridge.

Outputs:
  figures/pipeline_study_map.png
  figures/turag_upstream_validation.png
"""

import os
import json
import numpy as np
import rasterio
from rasterio.transform import xy as rxy
from skimage.morphology import skeletonize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from shapely.geometry import shape
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUT_DIR    = os.path.join(REPO_ROOT, "outputs", "buriganga")
CACHE_DIR  = os.path.join(REPO_ROOT, "cache")
FIG_DIR    = os.path.join(REPO_ROOT, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

CL_PATH   = os.path.join(OUT_DIR, "centerline.geojson")
SNAP_PATH = os.path.join(OUT_DIR, "stations_snapped.csv")
VAL_JSON  = os.path.join(OUT_DIR, "turag_upstream_validation.json")

CORE_STATIONS = [
    "MIRPUR_BRIDGE", "BOSILA_BRIDGE", "HAZARIBAGH",
    "SATMASJID_ROAD", "CHADNIGHAT", "BCFB", "FATULLAH"
]
SUPP_STATIONS = ["MOHAMMADPUR", "PAGLA"]

STATION_LABELS = {
    "MIRPUR_BRIDGE": "Mirpur Br.",
    "MOHAMMADPUR":   "Mohammadpur",
    "BOSILA_BRIDGE": "Bosila Br.",
    "HAZARIBAGH":    "Hazaribagh",
    "SATMASJID_ROAD":"Satmasjid",
    "CHADNIGHAT":    "Chadnighat",
    "BCFB":          "BCFB",
    "PAGLA":         "Pagla",
    "FATULLAH":      "Fatullah",
}

def main():
    val = {}
    if os.path.exists(VAL_JSON):
        with open(VAL_JSON) as f:
            val = json.load(f)

    if not os.path.exists(CL_PATH) or not os.path.exists(SNAP_PATH):
        print(f"Skipping map generation: {CL_PATH} or {SNAP_PATH} not found.")
        return

    with open(CL_PATH) as f:
        gj = json.load(f)
    cl_geom = shape(gj["features"][0]["geometry"])
    cl_lons = [c[0] for c in cl_geom.coords]
    cl_lats = [c[1] for c in cl_geom.coords]

    df_snap = pd.read_csv(SNAP_PATH)

    fig1, ax1 = plt.subplots(figsize=(10, 13), dpi=150)
    ax1.set_facecolor('#0d1117')
    fig1.patch.set_facecolor('#0d1117')

    ax1.plot(cl_lons, cl_lats, '-', color='#00bcd4', linewidth=2.0, zorder=4, label='River Centerline')

    for _, row in df_snap.iterrows():
        if row["station_id"] not in CORE_STATIONS:
            continue
        for radius_deg, color, alpha in [(0.0045, '#f57c00', 0.12), (0.0018, '#ffd740', 0.18)]:
            circle = plt.Circle((row["snapped_lon"], row["snapped_lat"]),
                                radius_deg, color=color, alpha=alpha, zorder=2)
            ax1.add_patch(circle)

    for _, row in df_snap.iterrows():
        st = row["station_id"]
        if st in CORE_STATIONS:
            ax1.scatter(row["snapped_lon"], row["snapped_lat"],
                        c='#ef5350', s=80, zorder=6, marker='o', edgecolors='white', linewidths=0.8)
            ax1.annotate(STATION_LABELS.get(st, st),
                         (row["snapped_lon"], row["snapped_lat"]),
                         textcoords="offset points", xytext=(6, 2),
                         fontsize=8, color='white', fontweight='bold',
                         bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.65))
        elif st in SUPP_STATIONS:
            ax1.scatter(row["snapped_lon"], row["snapped_lat"],
                        c='#90a4ae', s=40, zorder=5, marker='s', edgecolors='white', linewidths=0.6)

    legend_handles = [
        mpatches.Patch(color='#00bcd4', label='River Centerline (JRC Automated Skeleton)'),
        plt.scatter([], [], c='#ef5350', s=60, marker='o', label='Core Monitoring Station (n=7)'),
        plt.scatter([], [], c='#90a4ae', s=30, marker='s', label='Supplementary Station (n=2)'),
        mpatches.Patch(color='#f57c00', alpha=0.4, label='500m Buffer Zone'),
        mpatches.Patch(color='#ffd740', alpha=0.4, label='200m Buffer Zone'),
    ]
    ax1.legend(handles=legend_handles, loc='lower right', fontsize=8,
               facecolor='#0d1117', edgecolor='#444', labelcolor='white', framealpha=0.9)

    ax1.set_xlabel("Longitude (°E)", color='white', fontsize=10)
    ax1.set_ylabel("Latitude (°N)", color='white', fontsize=10)
    ax1.tick_params(colors='white')
    for sp in ax1.spines.values():
        sp.set_edgecolor('#333')
    ax1.grid(True, color='#222', linewidth=0.5)
    ax1.set_title("Buriganga River — Station Locations, JRC Centerline & Buffer Zones",
                  color='white', fontsize=12, fontweight='bold', pad=10)

    plt.tight_layout()
    map_path = os.path.join(FIG_DIR, "pipeline_study_map.png")
    plt.savefig(map_path, dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    print(f"Saved: {map_path}")

if __name__ == "__main__":
    main()
