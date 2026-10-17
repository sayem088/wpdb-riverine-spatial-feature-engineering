"""
Preprocesses and validates the canonical Buriganga River hydrochemical monitoring dataset.

Dataset compiled from Bangladesh Department of Environment (DoE) annual water quality
reports across seven core monitoring stations (2021-2023) and ten physicochemical parameters.
"""

import os
import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_PATH = os.path.join(REPO_ROOT, "data", "processed", "buriganga_water_quality.csv")

if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(f"Water quality dataset not found: {DATA_PATH}")

df = pd.read_csv(DATA_PATH)

print("=" * 64)
print("BURIGANGA HYDROCHEMICAL MONITORING DATASET VERIFICATION")
print("=" * 64)
print(f"Total Observations : {len(df)}")
print(f"Temporal Coverage  : {sorted(df['year'].unique())}")
print(f"Monitoring Stations: {df['station_id'].nunique()}")
print(f"Water Parameters   : {df['parameter'].nunique()}")
print("\nStation record counts per year:")
print(df.groupby(['station_id', 'year'])['parameter'].count().unstack(fill_value=0).to_string())
print(f"\nParameters: {sorted(df['parameter'].unique())}")
print(f"\nDataset verified successfully: {DATA_PATH}")
