"""
Parses the monthly Department of Environment (DoE) monitoring reports (2021-2023)
for four Shitalakhya River stations into canonical clean long-format observations.

Schema:
  year, station_id, station_name, latitude, longitude, month, parameter, value, unit

Inputs:
  data/raw/shitalakhya_monitoring_report_raw.md

Outputs:
  data/raw/shitalakhya_stations.csv
  data/processed/shitalakhya_water_quality.csv
"""

import os
import re
import pandas as pd
import numpy as np

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT    = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
RAW_DATA_DIR = os.path.join(REPO_ROOT, "data", "raw")
PROC_DIR     = os.path.join(REPO_ROOT, "data", "processed")
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROC_DIR, exist_ok=True)

RAW_FILE     = os.path.join(RAW_DATA_DIR, "shitalakhya_monitoring_report_raw.md")
STATIONS_CSV = os.path.join(RAW_DATA_DIR, "shitalakhya_stations.csv")
OUT_CSV      = os.path.join(PROC_DIR, "shitalakhya_water_quality.csv")

STATIONS_META = {
    "PORT_ROAD":         {"name": "Port Road",          "lat": 23.619368, "lon": 90.507349},
    "MAJIRA_DEMRA_GHAT": {"name": "Majira Demra Ghat",  "lat": 23.721544, "lon": 90.500228},
    "MURAPARA_RUPGONJ":  {"name": "Murapara (Rupgonj)", "lat": 23.783145, "lon": 90.517817},
    "GHORASHAL":         {"name": "Ghorashal",          "lat": 23.935991, "lon": 90.616093},
}

PARAM_UNITS = {
    "pH": "pH units", "DO": "mg/L", "BOD": "mg/L", "COD": "mg/L",
    "TDS": "mg/L", "Chloride": "mg/L", "SS": "mg/L", "EC": "µS/cm",
    "Total Alkalinity": "mg/L"
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def identify_station(line_text):
    t = line_text.strip()
    if re.search(r'port\s*road', t, re.I): return "PORT_ROAD"
    if re.search(r'demra', t, re.I): return "MAJIRA_DEMRA_GHAT"
    if re.search(r'murapara|rupgo?nj', t, re.I): return "MURAPARA_RUPGONJ"
    if re.search(r'gorashal|ghorashal', t, re.I): return "GHORASHAL"
    return None

def main():
    stations_df = pd.DataFrame([
        {"station_id": k, "station_name": v["name"], "latitude": v["lat"], "longitude": v["lon"]}
        for k, v in STATIONS_META.items()
    ])
    stations_df.to_csv(STATIONS_CSV, index=False)

    if not os.path.exists(RAW_FILE):
        if os.path.exists(OUT_CSV):
            print(f"Processed dataset already exists: {OUT_CSV}")
            return
        raise FileNotFoundError(f"Raw report not found: {RAW_FILE}")

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        raw_text = f.read()

    records = []
    current_year = None
    current_param = None

    year_pattern  = re.compile(r'(\d{4})\s*report', re.I)
    table_pattern = re.compile(r'Table-\d+[\.\:]\s*Level\s+of\s+([A-Za-z0-9\s]+?)(?:\s*\([^\)]+\))?\s+of\s+Shitalakhya', re.I)

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        y_match = year_pattern.search(line)
        if y_match:
            current_year = int(y_match.group(1))
            continue

        t_match = table_pattern.search(line)
        if t_match:
            param_raw = t_match.group(1).strip()
            if "pH" in param_raw: current_param = "pH"
            elif "DO" in param_raw: current_param = "DO"
            elif "BOD" in param_raw: current_param = "BOD"
            elif "COD" in param_raw: current_param = "COD"
            elif "TDS" in param_raw: current_param = "TDS"
            elif "Chloride" in param_raw: current_param = "Chloride"
            elif "SS" in param_raw: current_param = "SS"
            elif "EC" in param_raw: current_param = "EC"
            elif "Alkalinity" in param_raw: current_param = "Total Alkalinity"
            continue

        st_id = identify_station(line)
        if st_id and current_year and current_param:
            tokens = line.split()
            nums = []
            for tok in tokens:
                clean_tok = tok.replace(',', '').strip()
                try:
                    val = float(clean_tok)
                    nums.append(val)
                except ValueError:
                    pass

            unit_str = PARAM_UNITS.get(current_param, "mg/L")
            meta = STATIONS_META[st_id]

            for m_idx, m_name in enumerate(MONTH_NAMES):
                val_out = nums[m_idx] if m_idx < len(nums) else None
                records.append({
                    "year": current_year,
                    "station_id": st_id,
                    "station_name": meta["name"],
                    "latitude": meta["lat"],
                    "longitude": meta["lon"],
                    "month": m_name,
                    "parameter": current_param,
                    "value": val_out if (val_out is not None and not np.isnan(val_out)) else np.nan,
                    "unit": unit_str
                })

    df_clean = pd.DataFrame(records)
    df_clean_valid = df_clean[df_clean["value"].notna()].copy()
    df_clean_valid.to_csv(OUT_CSV, index=False)

    print("=" * 64)
    print("SHITALAKHYA WATER QUALITY PREPROCESSING COMPLETED")
    print("=" * 64)
    print(f"Output:     {OUT_CSV}")
    print(f"Total Rows: {len(df_clean_valid)}")
    print(f"Years:      {sorted(df_clean_valid['year'].unique())}")
    print(f"Stations:   {df_clean_valid['station_id'].unique()}")
    print(f"Parameters: {df_clean_valid['parameter'].unique()}")

if __name__ == "__main__":
    main()
