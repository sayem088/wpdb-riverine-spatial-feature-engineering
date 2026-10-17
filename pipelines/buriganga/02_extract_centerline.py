"""
Constructs the river centerline for the Buriganga-Turag network using JRC Global Surface Water occurrence.

Methodology:
  - Downstream reach (Mirpur Bridge -> Fatullah, ~27 km):
      JRC skeleton graph (occurrence > 50%), main connected component,
      shortest-path routing through core monitoring stations.
  - Upstream extension (Mirpur Bridge -> farthest reachable upstream node):
      Extracted automatically from JRC occurrence > 20% skeleton graph.
      Traced continuously to the northern boundary.

Inputs:
  JRC/GSW1_4/GlobalSurfaceWater occurrence band (via Google Earth Engine or local cache)

Outputs:
  outputs/buriganga/centerline.geojson
  outputs/buriganga/stations_snapped.csv
  outputs/buriganga/turag_upstream_validation.json
"""

import ee
import json
import os
import requests
import zipfile
import io
from collections import Counter
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import xy as rxy
from skimage.morphology import skeletonize
import networkx as nx
from shapely.geometry import LineString, mapping, Point
from geopy.distance import geodesic

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_DIR    = os.path.join(REPO_ROOT, "outputs", "buriganga")
CACHE_DIR  = os.path.join(REPO_ROOT, "cache")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

CENTERLINE_PATH   = os.path.join(OUT_DIR, "centerline.geojson")
SNAPPED_PATH      = os.path.join(OUT_DIR, "stations_snapped.csv")
VALIDATION_PATH   = os.path.join(OUT_DIR, "turag_upstream_validation.json")
TIF_MAIN_PATH     = os.path.join(CACHE_DIR, "jrc_main_buriganga.tif")
TIF_UPSTREAM_PATH = os.path.join(CACHE_DIR, "jrc_upstream_gt20.tif")

GEE_PROJECT = "sundarban-489216"
JOIN_TOLERANCE_M = 50.0

TURAG_WAYPOINTS = [
    (23.786250, 90.336424),
    (23.790256, 90.339299),
    (23.793888, 90.339578)
]

STATIONS = {
    "MIRPUR_BRIDGE":  (23.783754,  90.335107),
    "MOHAMMADPUR":    (23.762321,  90.337811),
    "BOSILA_BRIDGE":  (23.743499,  90.345530),
    "HAZARIBAGH":     (23.726392,  90.357232),
    "SATMASJID_ROAD": (23.708389,  90.365099),
    "CHADNIGHAT":     (23.71145665338903, 90.39081313977215),
    "BCFB":           (23.687262,  90.426625),
    "PAGLA":          (23.661726,  90.453111),
    "FATULLAH":       (23.640459,  90.471545),
}

validation_log = {
    "method": "JRC skeleton extraction - farthest reachable upstream node",
    "threshold_main": 50,
    "threshold_upstream": 20,
    "upstream_status": None,
    "upstream_actual_m": None,
    "upstream_vertex_count": 0,
    "join_distance_m": None,
    "join_tolerance_m": JOIN_TOLERANCE_M,
    "join_ok": None,
    "spacing_stats": {},
    "water_pixel_check": None,
    "waypoint_corridor_fallback_used": False
}

def download_jrc_tif(ee_image, region, path, name):
    """Download GEE image as GeoTIFF, skip if cached."""
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
    """Load GeoTIFF, skeletonize water mask, return (G, transform, binary_arr)."""
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
    if not (os.path.exists(TIF_MAIN_PATH) and os.path.exists(TIF_UPSTREAM_PATH)):
        print("Initializing Google Earth Engine...")
        ee.Initialize(project=GEE_PROJECT)
        jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")

        lats_s = [v[0] for v in STATIONS.values()]
        lons_s = [v[1] for v in STATIONS.values()]
        region_main = ee.Geometry.Rectangle(
            [min(lons_s)-0.030, min(lats_s)-0.020, max(lons_s)+0.025, max(lats_s)+0.010]
        )
        print("\nDownloading JRC main corridor mask (>50%)...")
        download_jrc_tif(jrc.gt(50).selfMask().clip(region_main), region_main,
                         TIF_MAIN_PATH, "jrc_main_buriganga")

        MIRPUR_LAT, MIRPUR_LON = STATIONS["MIRPUR_BRIDGE"]
        region_upstream = ee.Geometry.Rectangle(
            [MIRPUR_LON - 0.015, MIRPUR_LAT - 0.005, MIRPUR_LON + 0.015, MIRPUR_LAT + 0.020]
        )
        print("Downloading JRC upstream corridor mask (>20%)...")
        download_jrc_tif(jrc.gt(20).selfMask().clip(region_upstream), region_upstream,
                         TIF_UPSTREAM_PATH, "jrc_upstream_gt20")
    else:
        print("Using cached JRC GeoTIFF masks.")

    MIRPUR_LAT, MIRPUR_LON = STATIONS["MIRPUR_BRIDGE"]

    print("\nBuilding Buriganga mainstem skeleton graph (>50%)...")
    G_main, transform_main, _ = build_skeleton_graph(TIF_MAIN_PATH)
    nodes_main = np.array(list(G_main.nodes()))

    station_order = ["MIRPUR_BRIDGE", "MOHAMMADPUR", "BOSILA_BRIDGE", "HAZARIBAGH",
                     "SATMASJID_ROAD", "CHADNIGHAT", "BCFB", "PAGLA", "FATULLAH"]
    station_nodes = {st: nearest_node(nodes_main, transform_main,
                                      STATIONS[st][0], STATIONS[st][1])[0]
                     for st in station_order}

    components = list(nx.connected_components(G_main))
    main_comp = next((c for c in components
                      if station_nodes["MIRPUR_BRIDGE"] in c and station_nodes["FATULLAH"] in c),
                     max(components, key=len))
    G_ms = G_main.subgraph(main_comp).copy()

    buriganga_path = []
    for i in range(len(station_order) - 1):
        n1, n2 = station_nodes[station_order[i]], station_nodes[station_order[i+1]]
        try:
            seg = nx.shortest_path(G_ms, n1, n2)
        except Exception:
            seg = nx.shortest_path(G_main, n1, n2)
        buriganga_path.extend(seg[1:] if buriganga_path else seg)

    buriganga_coords = []
    for (row, col) in buriganga_path:
        lon_v, lat_v = rxy(transform_main, row, col, offset="center")
        buriganga_coords.append((lon_v, lat_v))

    downstream_first = buriganga_coords[0]

    print("\nAutomated Upstream Skeleton Extraction...")
    G_up, transform_up, binary_up = build_skeleton_graph(TIF_UPSTREAM_PATH)
    nodes_up = np.array(list(G_up.nodes()))

    start_node_up, snap_dist = nearest_node(nodes_up, transform_up, MIRPUR_LAT, MIRPUR_LON)
    lon_start, lat_start = rxy(transform_up, start_node_up[0], start_node_up[1], offset='center')
    print(f"  Mirpur Bridge snap distance: {snap_dist:.1f} m")

    comp_up = list(nx.node_connected_component(G_up, start_node_up))
    subG_up = G_up.subgraph(comp_up).copy()
    lengths_up = nx.single_source_dijkstra_path_length(subG_up, start_node_up, weight='weight')

    upstream_candidates = []
    for node, path_len in lengths_up.items():
        lon_n, lat_n = rxy(transform_up, node[0], node[1], offset='center')
        if lat_n > MIRPUR_LAT:
            d_m = geodesic((lat_start, lon_start), (lat_n, lon_n)).meters
            upstream_candidates.append((node, d_m, lat_n, lon_n))

    if not upstream_candidates:
        corridor_nodes = []
        for (w_lat, w_lon) in TURAG_WAYPOINTS:
            w_node, w_dist = nearest_node(nodes_up, transform_up, w_lat, w_lon)
            if w_dist <= 200.0:
                corridor_nodes.append(w_node)

        if corridor_nodes:
            all_comp_nodes = set()
            for cn in corridor_nodes:
                if cn in G_up:
                    all_comp_nodes.update(nx.node_connected_component(G_up, cn))
            subG_up = G_up.subgraph(all_comp_nodes).copy()
            lengths_up = nx.single_source_dijkstra_path_length(subG_up, start_node_up, weight='weight')
            for node, path_len in lengths_up.items():
                lon_n, lat_n = rxy(transform_up, node[0], node[1], offset='center')
                if lat_n > MIRPUR_LAT:
                    d_m = geodesic((lat_start, lon_start), (lat_n, lon_n)).meters
                    upstream_candidates.append((node, d_m, lat_n, lon_n))

    if not upstream_candidates:
        validation_log["upstream_status"] = "UNRESOLVED"
        upstream_coords = []
    else:
        farthest = max(upstream_candidates, key=lambda x: x[1])
        target_node, actual_upstream_dist = farthest[0], farthest[1]
        path_nodes_up = nx.shortest_path(subG_up, start_node_up, target_node, weight='weight')

        upstream_coords = []
        for node in reversed(path_nodes_up):
            lon_p, lat_p = rxy(transform_up, node[0], node[1], offset='center')
            upstream_coords.append((lon_p, lat_p))

        validation_log["upstream_status"] = "OK"
        validation_log["upstream_actual_m"] = round(actual_upstream_dist, 1)
        validation_log["upstream_vertex_count"] = len(upstream_coords)

        join_dist = geodesic(
            (upstream_coords[-1][1], upstream_coords[-1][0]),
            (downstream_first[1], downstream_first[0])
        ).meters
        validation_log["join_distance_m"] = round(join_dist, 1)
        validation_log["join_ok"] = join_dist <= JOIN_TOLERANCE_M
        upstream_coords[-1] = downstream_first

        on_water = sum(
            1 for (lon_v, lat_v) in upstream_coords
            if (lambda r, c: 0 <= r < binary_up.shape[0] and 0 <= c < binary_up.shape[1] and binary_up[r, c])(
                *[int(round(x)) for x in reversed(list((~transform_up * (lon_v, lat_v))))])
        )
        pct_water = 100.0 * on_water / len(upstream_coords) if upstream_coords else 0
        validation_log["water_pixel_check"] = {
            "vertices_checked": len(upstream_coords),
            "on_jrc_water": on_water,
            "pct": round(pct_water, 1)
        }

    full_coords = upstream_coords + buriganga_coords[1:] if upstream_coords else buriganga_coords
    centerline = LineString(full_coords)

    with open(CENTERLINE_PATH, "w") as f:
        json.dump({"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "geometry": mapping(centerline),
            "properties": {
                "source": "JRC GSW1_4 automated skeleton extraction",
                "vertex_count": len(full_coords),
                "jrc_threshold_main": 50,
                "jrc_threshold_upstream": 20,
                "upstream_status": validation_log["upstream_status"],
                "upstream_traced_m": validation_log["upstream_actual_m"],
            }
        }]}, f, indent=2)

    with open(VALIDATION_PATH, "w") as f:
        json.dump(validation_log, f, indent=2, default=str)

    cum_m = [0.0]
    for i in range(1, len(full_coords)):
        cum_m.append(cum_m[-1] + geodesic(
            (full_coords[i-1][1], full_coords[i-1][0]),
            (full_coords[i][1], full_coords[i][0])).meters)
    total_m = cum_m[-1]

    snap_rows = []
    for st_id, (lat, lon) in STATIONS.items():
        pt = Point(lon, lat)
        proj = centerline.project(pt)
        sp = centerline.interpolate(proj)
        frac = proj / centerline.length
        snap_rows.append({
            "station_id": st_id, "latitude": lat, "longitude": lon,
            "snapped_lat": round(sp.y, 6), "snapped_lon": round(sp.x, 6),
            "snap_distance_m": round(geodesic((lat, lon), (sp.y, sp.x)).meters, 2),
            "along_channel_m": round(frac * total_m, 1),
            "along_channel_frac": round(frac, 6)
        })

    df_snap = pd.DataFrame(snap_rows).sort_values("along_channel_m").reset_index(drop=True)
    df_snap.to_csv(SNAPPED_PATH, index=False)
    print(f"\nOutputs written:\n  {CENTERLINE_PATH}\n  {SNAPPED_PATH}")

if __name__ == "__main__":
    main()
