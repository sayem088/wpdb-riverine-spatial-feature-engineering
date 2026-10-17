"""
Evaluates multi-parameter correlations between directional upstream built exposure
and measured in-stream water quality across Buriganga monitoring stations.

Hypothesis Testing Protocol:
  - Model: Linear upstream distance decay (E_i = SUM_k (1 - d_k / 5.0 km) * f_{built, nw}(k))
  - Simultaneous evaluation of 10 water quality parameters from Bangladesh DoE reports.
  - Multiple comparisons control: Bonferroni correction (alpha = 0.05 / 10 = 0.0050).

Inputs:
  data/processed/buriganga_water_quality.csv
  outputs/buriganga/land_cover_distance_resolved.csv

Outputs:
  outputs/buriganga/h1_bonferroni_results.csv
  outputs/buriganga/h1_report.txt
"""

import os
import pandas as pd
import numpy as np
from scipy.stats import pearsonr

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_DIR    = os.path.join(REPO_ROOT, "outputs", "buriganga")
DATA_DIR   = os.path.join(REPO_ROOT, "data", "processed")

WQ_CSV  = os.path.join(DATA_DIR, "buriganga_water_quality.csv")
LC_CSV  = os.path.join(OUT_DIR,  "land_cover_distance_resolved.csv")
OUT_CSV = os.path.join(OUT_DIR,  "h1_bonferroni_results.csv")
OUT_TXT = os.path.join(OUT_DIR,  "h1_report.txt")

CORE_STATIONS = [
    "MIRPUR_BRIDGE", "BOSILA_BRIDGE", "HAZARIBAGH",
    "SATMASJID_ROAD", "CHADNIGHAT", "BCFB", "FATULLAH"
]

ALL_PARAMS = [
    "BOD", "COD", "DO", "pH", "TDS", "EC",
    "SS", "Turbidity", "Chloride", "Total Alkalinity"
]

ALPHA_RAW = 0.05
ALPHA_BONFERRONI = ALPHA_RAW / len(ALL_PARAMS)

def main():
    print("Loading data for hypothesis testing...")
    df_wq = pd.read_csv(WQ_CSV)
    df_lc = pd.read_csv(LC_CSV)

    wq_core = df_wq[df_wq["station_id"].isin(CORE_STATIONS) & df_wq["value"].notna()]
    wq_means = wq_core.groupby(["station_id", "parameter"])["value"].mean().unstack()

    df_built = df_lc[df_lc["land_cover_class"] == "built"].copy()

    def linear_exposure(station_id):
        sub = df_built[df_built["station_id"] == station_id]
        if sub.empty:
            return 0.0
        d_km = sub["upstream_distance_m"] / 1000.0
        weights = np.maximum(0.0, 1.0 - d_km / 5.0)
        return float(np.sum(weights * sub["fraction_of_nonwater"]))

    exposures = {st: linear_exposure(st) for st in CORE_STATIONS}

    lines = [
        "=" * 72,
        "BURIGANGA MULTI-PARAMETER BONFERRONI HYPOTHESIS TEST",
        "=" * 72,
        "Exposure Model: Linear Upstream Distance Decay (1 - d/5.0 km)",
        f"Sample Size:    {len(CORE_STATIONS)} Core Monitoring Stations",
        f"Parameters:     {len(ALL_PARAMS)} Evaluated Simultaneously",
        f"Significance:   alpha_raw = {ALPHA_RAW:.2f}, alpha_bonferroni = {ALPHA_BONFERRONI:.4f}",
        "=" * 72,
        "",
        "STATION EXPOSURE SCORES (Linear 5km Non-Water Normalized):"
    ]

    for st, exp in exposures.items():
        lines.append(f"  {st:20s}: {exp:.6f}")

    lines.extend(["", "=" * 72, "PARAMETER CORRELATION RESULTS", "=" * 72])

    results = []
    for param in ALL_PARAMS:
        if param not in wq_means.columns:
            continue
        xs, ys = [], []
        for st in CORE_STATIONS:
            if st in wq_means.index and not np.isnan(wq_means.loc[st, param]):
                xs.append(exposures[st])
                ys.append(wq_means.loc[st, param])
        if len(xs) < 3:
            continue
        r, p = pearsonr(xs, ys)
        results.append({
            "parameter": param,
            "n_stations": len(xs),
            "pearson_r": round(r, 6),
            "r_squared": round(r**2, 6),
            "p_value": round(p, 6),
            "sig_uncorrected": p < ALPHA_RAW,
            "sig_bonferroni": p < ALPHA_BONFERRONI,
        })

    df_res = pd.DataFrame(results)
    lines.append(df_res.to_string(index=False))

    report = "\n".join(lines)
    print(report)

    df_res.to_csv(OUT_CSV, index=False)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nSaved results: {OUT_CSV}")

if __name__ == "__main__":
    main()
