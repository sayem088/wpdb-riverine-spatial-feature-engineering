"""
Renders Figure 4 for the IEEE CSDE 2026 paper:
Google Earth Engine satellite overlay at Hazaribagh and Satmasjid Road monitoring stations
on the Buriganga River. Displays JRC Global Surface Water permanent water mask and
Dynamic World land cover composite with circular Euclidean buffers (200m and 500m).

Outputs:
  figures/fig4_gee_satellite_overlay.png (300 DPI)
  figures/fig4_gee_satellite_overlay.pdf (Vector TrueType embedded)
"""

import os
import io
import zipfile
import json
import numpy as np
import rasterio
from rasterio.transform import xy as rxy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from shapely.geometry import shape

# Configure TrueType font embedding for IEEE publication standards
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype']  = 42
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
CACHE_DIR  = os.path.join(REPO_ROOT, "cache")
OUT_DIR    = os.path.join(REPO_ROOT, "outputs", "buriganga")
FIG_DIR    = os.path.join(REPO_ROOT, "figures")
CL_PATH    = os.path.join(OUT_DIR, "centerline.geojson")
PNG_OUT    = os.path.join(FIG_DIR, "fig4_gee_satellite_overlay.png")
PDF_OUT    = os.path.join(FIG_DIR, "fig4_gee_satellite_overlay.pdf")

STATIONS = {
    "HAZARIBAGH":     (23.726392, 90.357232),
    "SATMASJID_ROAD": (23.708389, 90.365099),
}

def load_raster_bytes(tif_path):
    with rasterio.open(tif_path) as src:
        arr = src.read(1)
        bounds = src.bounds
        transform = src.transform
    return arr, bounds, transform

DW_COLOR_MAP = {
    0: (31/255, 119/255, 180/255),
    1: (44/255, 160/255, 44/255),
    2: (152/255, 223/255, 138/255),
    3: (31/255, 119/255, 180/255),
    4: (255/255, 187/255, 120/255),
    5: (188/255, 189/255, 34/255),
    6: (214/255, 39/255, 40/255),
    7: (199/255, 199/255, 199/255),
    8: (255/255, 255/255, 255/255)
}

def render_rgb_composite(dw_arr, jrc_arr):
    h, w = dw_arr.shape
    rgb = np.ones((h, w, 3), dtype=np.float32) * 0.94
    for r in range(h):
        for c in range(w):
            lbl = dw_arr[r, c]
            if lbl in DW_COLOR_MAP:
                rgb[r, c] = DW_COLOR_MAP[lbl]
            if jrc_arr[r, c] == 1:
                rgb[r, c] = (24/255, 100/255, 171/255)
    return rgb

def main():
    jrc_h_path = os.path.join(CACHE_DIR, "hazaribagh_jrc.tif")
    dw_h_path  = os.path.join(CACHE_DIR, "hazaribagh_dw.tif")
    jrc_s_path = os.path.join(CACHE_DIR, "satmasjid_road_jrc.tif")
    dw_s_path  = os.path.join(CACHE_DIR, "satmasjid_road_dw.tif")

    jrc_arr_h, bounds_h, _ = load_raster_bytes(jrc_h_path)
    dw_arr_h, _, _         = load_raster_bytes(dw_h_path)
    jrc_arr_s, bounds_s, _ = load_raster_bytes(jrc_s_path)
    dw_arr_s, _, _         = load_raster_bytes(dw_s_path)

    with open(CL_PATH) as f:
        gj = json.load(f)
    cl_geom = shape(gj["features"][0]["geometry"])
    cl_lons = [c[0] for c in cl_geom.coords]
    cl_lats = [c[1] for c in cl_geom.coords]

    rgb_h = render_rgb_composite(dw_arr_h, jrc_arr_h)
    rgb_s = render_rgb_composite(dw_arr_s, jrc_arr_s)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7), dpi=300)

    m_to_deg_lat = 1.0 / 110750.0
    m_to_deg_lon = 1.0 / 101900.0

    def add_station_panel(ax, rgb, bounds, st_lat, st_lon, st_name, stats, panel_letter):
        extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
        ax.imshow(rgb, extent=extent, origin='upper', aspect='equal')
        ax.plot(cl_lons, cl_lats, color='#00e5ff', linewidth=2.5, linestyle='-', zorder=5)

        theta = np.linspace(0, 2*np.pi, 200)
        x200 = st_lon + (200.0 * m_to_deg_lon) * np.cos(theta)
        y200 = st_lat + (200.0 * m_to_deg_lat) * np.sin(theta)
        ax.plot(x200, y200, color='#ffff00', linewidth=2.2, linestyle='--', zorder=6)

        x500 = st_lon + (500.0 * m_to_deg_lon) * np.cos(theta)
        y500 = st_lat + (500.0 * m_to_deg_lat) * np.sin(theta)
        ax.plot(x500, y500, color='#ff6d00', linewidth=2.2, linestyle='-.', zorder=6)

        ax.scatter([st_lon], [st_lat], color='#00ff00', s=140, edgecolors='black', linewidth=1.8, zorder=10)

        zoom_lon = 650.0 * m_to_deg_lon
        zoom_lat = 650.0 * m_to_deg_lat
        ax.set_xlim(st_lon - zoom_lon, st_lon + zoom_lon)
        ax.set_ylim(st_lat - zoom_lat, st_lat + zoom_lat)

        ax.set_title(f"({panel_letter}) {st_name} Station (Buriganga River)", fontsize=13, fontweight='bold', pad=10)
        ax.set_xlabel("Longitude (°E)", fontsize=10)
        ax.set_ylabel("Latitude (°N)", fontsize=10)
        ax.tick_params(labelsize=9)
        ax.grid(color='#cccccc', linestyle=':', linewidth=0.6, alpha=0.7)

        info_text = (
            f"Spatial Distortion Metrics:\n"
            f"• Open Water ($f_{{water}}$): {stats['water']:.1f}%\n"
            f"• Naive Built ($f_{{built,naive}}$): {stats['naive']:.1f}%\n"
            f"• True Non-Water Built ($f_{{built,nw}}$): {stats['nw']:.1f}%\n"
            f"• Dilution Bias ($\\Delta f_{{built}}$): {stats['delta']:.2f} pp\n"
            f"• Identity Predicted: {stats['pred']:.2f} pp"
        )
        ax.text(0.03, 0.04, info_text, transform=ax.transAxes, fontsize=9.5,
                verticalalignment='bottom', horizontalalignment='left',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.92, edgecolor='#333333', linewidth=1.2),
                zorder=12)

    h_lat, h_lon = STATIONS["HAZARIBAGH"]
    s_lat, s_lon = STATIONS["SATMASJID_ROAD"]

    add_station_panel(ax1, rgb_h, bounds_h, h_lat, h_lon, "Hazaribagh",
                      {'water': 62.10, 'naive': 33.66, 'nw': 88.80, 'delta': -55.14, 'pred': -55.14}, "a")
    add_station_panel(ax2, rgb_s, bounds_s, s_lat, s_lon, "Satmasjid Road",
                      {'water': 63.93, 'naive': 31.78, 'nw': 88.12, 'delta': -56.34, 'pred': -56.34}, "b")

    legend_elements = [
        Patch(facecolor=(24/255, 100/255, 171/255), edgecolor='none', label='JRC Open Water'),
        Patch(facecolor=(214/255, 39/255, 40/255), edgecolor='none', label='Dynamic World Built-up'),
        Patch(facecolor=(44/255, 160/255, 44/255), edgecolor='none', label='Vegetation / Trees'),
        Patch(facecolor=(255/255, 187/255, 120/255), edgecolor='none', label='Crops / Bare Soil'),
        Line2D([0], [0], color='#00e5ff', lw=2.5, label='River Centerline (1D)'),
        Line2D([0], [0], color='#ffff00', lw=2.2, linestyle='--', label='200m Circular Buffer'),
        Line2D([0], [0], color='#ff6d00', lw=2.2, linestyle='-.', label='500m Circular Buffer'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#00ff00', markeredgecolor='k', markersize=10, label='Monitoring Station Node')
    ]

    fig.legend(handles=legend_elements, loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.05),
               fontsize=9.5, frameon=True, facecolor='white', edgecolor='#bbbbbb')

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(PNG_OUT, dpi=300, bbox_inches='tight')
    plt.savefig(PDF_OUT, bbox_inches='tight')
    print(f"Figure 4 generated successfully:\n  {PNG_OUT}\n  {PDF_OUT}")

if __name__ == "__main__":
    main()
