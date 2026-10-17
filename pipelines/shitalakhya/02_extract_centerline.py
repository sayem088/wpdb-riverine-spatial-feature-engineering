"""
Constructs the river centerline for the Shitalakhya River network using JRC Global
Surface Water occurrence data, and snaps monitoring stations to the flowpath.

Stations (South to North / Downstream to Upstream):
  - Port Road         (23.619368, 90.507349)
  - Majira Demra Ghat (23.721544, 90.500228)
  - Murapara (Rupgonj)(23.783145, 90.517817)
  - Ghorashal         (23.935991, 90.616093)

Inputs:
  JRC/GSW1_4/GlobalSurfaceWater occurrence band (via Google Earth Engine or local cache)

Outputs:
  outputs/shitalakhya/centerline_shitalakhya.geojson
  outputs/shitalakhya/stations_shitalakhya_snapped.csv
"""

import ee
import json
import os
import requests
import zipfile
import io
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import xy as rxy
from skimage.morphology import skeletonize
import networkx as nx
from shapely.geometry import LineString, mapping
from geopy.distance import geodesic

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_DIR    = os.path.join(REPO_ROOT, "outputs", "shitalakhya")
CACHE_DIR  = os.path.join(REPO_ROOT, "cache")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

CENTERLINE_PATH = os.path.join(OUT_DIR, "centerline_shitalakhya.geojson")
SNAPPED_PATH    = os.path.join(OUT_DIR, "stations_shitalakhya_snapped.csv")
TIF_PATH        = os.path.join(CACHE_DIR, "jrc_shitalakhya.tif")

GEE_PROJECT = "sundarban-489216"

STATIONS = {
    "PORT_ROAD":         (23.619368, 90.507349),
    "MAJIRA_DEMRA_GHAT": (23.721544, 90.500228),
    "MURAPARA_RUPGONJ":  (23.783145, 90.517817),
    "GHORASHAL":         (23.935991, 90.616093),
}

STATION_ORDER = ["PORT_ROAD", "MAJIRA_DEMRA_GHAT", "MURAPARA_RUPGONJ", "GHORASHAL"]

def download_jrc_tif(ee_image, region, path, name):
    if os.path.exists(path):
        print(f"  [CACHED] {os.path.basename(path)}")
        return
    url = ee_image.getDownloadURL({
        'name': name, 'crs': 'EPSG:4326', 'scale': 30, 'region': region
    })
    resp = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(resp.content))
    tif_file = [f for f in z.namelist() if f.endswith('.tif')][0]
    with open(path, 'wb') as f:
        f.write(z.read(tif_file))
    print(f"  Downloaded: {os.path.basename(path)}")

def build_skeleton_graph(tif_path):
    with rasterio.open(tif_path) as src:
        arr = src.read(1)
        transform = src.transform
        nodata = src.nodata
    binary = (arr != nodata) & (arr > 0) if nodata is not None else arr > 0
    skel = skeletonize(binary)
    skel_pixels = np.argwhere(skel)
    G = nx.Graph()
    skel_set = set(map(tuple, skel_pixels))
    for (r, c) in skel_pixels:
        G.add_node((r, c))
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nb = (r + dr, c + dc)
                if nb in skel_set:
                    G.add_edge((r, c), nb, weight=np.sqrt(dr**2 + dc**2))
    return G, transform, binary

def nearest_node(G_nodes_arr, transform, lat, lon):
    col, row = ~transform * (lon, lat)
    r, c = int(round(row)), int(round(col))
    dists = np.sqrt((G_nodes_arr[:, 0] - r)**2 + (G_nodes_arr[:, 1] - c)**2)
    idx = dists.argmin()
    node = tuple(G_nodes_arr[idx])
    lon_n, lat_n = rxy(transform, node[0], node[1], offset='center')
    dist_m = geodesic((lat, lon), (lat_n, lon_n)).meters
    return node, dist_m

def main():
    if not os.path.exists(TIF_PATH):
        print("Initializing Google Earth Engine...")
        ee.Initialize(project=GEE_PROJECT)
        jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")

        lats_s = [v[0] for v in STATIONS.values()]
        lons_s = [v[1] for v in STATIONS.values()]
        region = ee.Geometry.Rectangle(
            [min(lons_s)-0.040, min(lats_s)-0.040, max(lons_s)+0.040, max(lats_s)+0.040]
        )
        print("\nDownloading JRC Shitalakhya corridor mask (>10%)...")
        download_jrc_tif(jrc.gt(10).selfMask().clip(region), region, TIF_PATH, "jrc_shitalakhya")
    else:
        print("Using cached JRC Shitalakhya GeoTIFF mask.")

    print("\nBuilding Shitalakhya skeleton graph...")
    G, transform, _ = build_skeleton_graph(TIF_PATH)
    nodes_arr = np.array(list(G.nodes()))

    station_nodes = {}
    station_snaps = []
    for st in STATION_ORDER:
        lat, lon = STATIONS[st]
        n, dist_m = nearest_node(nodes_arr, transform, lat, lon)
        station_nodes[st] = n
        lon_n, lat_n = rxy(transform, n[0], n[1], offset='center')
        station_snaps.append({
            "station_id": st,
            "lat_orig": lat, "lon_orig": lon,
            "lat_snapped": lat_n, "lon_snapped": lon_n,
            "snap_distance_m": dist_m
        })

    path_nodes = []
    for i in range(len(STATION_ORDER) - 1):
        st1, st2 = STATION_ORDER[i], STATION_ORDER[i+1]
        n1, n2 = station_nodes[st1], station_nodes[st2]
        seg = nx.shortest_path(G, n1, n2)
        path_nodes.extend(seg[1:] if path_nodes else seg)

    cl_coords = []
    for (r, c) in path_nodes:
        lon_v, lat_v = rxy(transform, r, c, offset="center")
        cl_coords.append((lon_v, lat_v))

    line_geom = LineString(cl_coords)
    geojson_out = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Shitalakhya Centerline"},
            "geometry": mapping(line_geom)
        }]
    }

    with open(CENTERLINE_PATH, "w") as f:
        json.dump(geojson_out, f, indent=2)
    print(f"Saved Shitalakhya centerline to {CENTERLINE_PATH}")

    cum_dist = [0.0]
    for i in range(1, len(cl_coords)):
        a = (cl_coords[i-1][1], cl_coords[i-1][0])
        b = (cl_coords[i][1], cl_coords[i][0])
        cum_dist.append(cum_dist[-1] + geodesic(a, b).meters)

    total_length_m = cum_dist[-1]
    df_snaps = pd.DataFrame(station_snaps)

    along_channel_m = []
    along_channel_frac = []
    for row in df_snaps.itertuples():
        st_coord = (row.lat_snapped, row.lon_snapped)
        min_d = float('inf')
        best_m = 0.0
        for idx, pt in enumerate(cl_coords):
            d = geodesic(st_coord, (pt[1], pt[0])).meters
            if d < min_d:
                min_d = d
                best_m = cum_dist[idx]
        along_channel_m.append(best_m)
        along_channel_frac.append(best_m / total_length_m if total_length_m > 0 else 0)

    df_snaps["along_channel_m"] = along_channel_m
    df_snaps["along_channel_frac"] = along_channel_frac
    df_snaps.to_csv(SNAPPED_PATH, index=False)
    print(f"Saved snapped stations to {SNAPPED_PATH}")
    print(df_snaps[["station_id", "snap_distance_m", "along_channel_m"]].to_string())

if __name__ == "__main__":
    main()
