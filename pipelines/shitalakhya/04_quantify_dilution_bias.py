"""
Quantifies Water-Pixel Dilution Bias (WPDB) across Shitalakhya River stations
and validates the mathematical scaling identity:
  \Delta f_{built} = -f_{water} * f_{built, non-water}

Evaluates multi-year hydrochemical correlations with directional linear exposure.

Inputs:
  outputs/shitalakhya/land_cover_shitalakhya_resolved.csv
  data/processed/shitalakhya_water_quality.csv

Outputs:
  outputs/shitalakhya/shitalakhya_bias_summary.csv
  outputs/shitalakhya/shitalakhya_hydrochemical_correlations.csv
"""

import os
import pandas as pd
import numpy as np
from scipy.stats import pearsonr

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_DIR    = os.path.join(REPO_ROOT, "outputs", "shitalakhya")
DATA_DIR   = os.path.join(REPO_ROOT, "data", "processed")

IN_CSV   = os.path.join(OUT_DIR, "land_cover_shitalakhya_resolved.csv")
WQ_CSV   = os.path.join(DATA_DIR, "shitalakhya_water_quality.csv")
OUT_CSV  = os.path.join(OUT_DIR, "shitalakhya_bias_summary.csv")
CORR_CSV = os.path.join(OUT_DIR, "shitalakhya_hydrochemical_correlations.csv")

def main():
    if not os.path.exists(IN_CSV):
        raise FileNotFoundError(f"Input file not found: {IN_CSV}")

    df = pd.read_csv(IN_CSV)
    stations = df["station_id"].unique()
    summary_records = []

    print("=" * 64)
    print("SHITALAKHYA WATER-PIXEL DILUTION BIAS QUANTIFICATION")
    print("=" * 64)

    for st in stations:
        sub = df[df["station_id"] == st]
        built_sub = sub[sub["land_cover_class"] == "built"]

        total_px    = built_sub["total_pixels"].sum()
        water_px    = built_sub["water_pixels"].sum()
        built_px    = built_sub["pixel_count"].sum()
        nonwater_px = total_px - water_px

        f_water    = water_px / total_px if total_px > 0 else 0.0
        f_naive    = built_px / total_px if total_px > 0 else 0.0
        f_nonwater = built_px / nonwater_px if nonwater_px > 0 else 0.0
        delta_bias = f_naive - f_nonwater

        # Analytical Identity Verification: \Delta f = - f_{water} * f_{nonwater}
        predicted_bias = -f_water * f_nonwater
        identity_diff  = abs(delta_bias - predicted_bias)

        d_km = built_sub["upstream_distance_m"] / 1000.0
        weights = np.maximum(0.0, 1.0 - d_km / 5.0)
        exposure = float(np.sum(weights * built_sub["fraction_of_nonwater"]))

        summary_records.append({
            "station_id": st,
            "total_pixels": total_px,
            "water_pixels": water_px,
            "built_pixels": built_px,
            "non_water_pixels": nonwater_px,
            "water_fraction_pct": f_water * 100.0,
            "naive_built_pct": f_naive * 100.0,
            "nonwater_built_pct": f_nonwater * 100.0,
            "dilution_bias_pct": delta_bias * 100.0,
            "identity_error_pct": identity_diff * 100.0,
            "linear_exposure_5km": exposure
        })

    df_summary = pd.DataFrame(summary_records)
    df_summary.to_csv(OUT_CSV, index=False)

    print("\nStation-Level Bias Quantification:")
    print(df_summary[[
        "station_id", "water_fraction_pct", "naive_built_pct",
        "nonwater_built_pct", "dilution_bias_pct", "linear_exposure_5km"
    ]].to_string(index=False))

    mean_water    = df_summary["water_fraction_pct"].mean()
    mean_naive    = df_summary["naive_built_pct"].mean()
    mean_nonwater = df_summary["nonwater_built_pct"].mean()
    mean_bias     = df_summary["dilution_bias_pct"].mean()
    std_bias      = df_summary["dilution_bias_pct"].std()

    print("\nShitalakhya Network Summary Statistics:")
    print(f"  Mean Water Fraction (f_water)            : {mean_water:.2f}%")
    print(f"  Mean Naive Built Cover (f_naive)         : {mean_naive:.2f}%")
    print(f"  Mean Non-Water Built Cover (f_nw)        : {mean_nonwater:.2f}%")
    print(f"  Mean Dilution Bias (Delta f_built)       : {mean_bias:.2f}% (std = {std_bias:.2f}%)")
    print(f"  Max Numerical Identity Residual          : {df_summary['identity_error_pct'].max():.2e}%")

    if os.path.exists(WQ_CSV):
        print("\n" + "=" * 64)
        print("HYDROCHEMICAL CORRELATION DIAGNOSTICS (2021-2023 Panel)")
        print("=" * 64)
        df_wq = pd.read_csv(WQ_CSV)
        wq_means = df_wq.groupby(["station_id", "parameter"])["value"].mean().unstack()

        corr_results = []
        alpha_bonferroni = 0.05 / 9.0
        exp_map = df_summary.set_index("station_id")["linear_exposure_5km"].to_dict()

        for param in sorted(wq_means.columns):
            xs, ys = [], []
            for st in df_summary["station_id"]:
                if st in wq_means.index and not np.isnan(wq_means.loc[st, param]):
                    xs.append(exp_map[st])
                    ys.append(wq_means.loc[st, param])
            if len(xs) >= 3:
                r, p = pearsonr(xs, ys)
                corr_results.append({
                    "parameter": param,
                    "n_stations": len(xs),
                    "pearson_r": round(r, 4),
                    "p_value": round(p, 4),
                    "sig_bonferroni": p < alpha_bonferroni
                })
                status = f"Sig (p<{alpha_bonferroni:.4f})" if p < alpha_bonferroni else "Not Sig"
                print(f"  {param:18s}: n={len(xs)}, r = {r:+.4f}, p = {p:.4f} --> {status}")

        pd.DataFrame(corr_results).to_csv(CORR_CSV, index=False)
        print(f"\nSaved correlation results: {CORR_CSV}")

if __name__ == "__main__":
    main()
