"""
Master execution runner for the Buriganga River analysis pipeline.

Executes sequential data processing, centerline extraction, land cover extraction,
Bonferroni correlation hypothesis testing, and circular buffer sensitivity comparison.
"""

import subprocess
import sys
import os
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    ("01_preprocess_water_quality.py",       "Preprocess Buriganga Water Quality Dataset"),
    ("02_extract_centerline.py",             "Extract JRC GSW Centerline & Snap Stations"),
    ("03_extract_dynamic_world_cover.py",    "Extract Upstream Land Cover Corridors (GEE)"),
    ("04_bonferroni_hypothesis_test.py",     "Multi-Parameter Bonferroni Hypothesis Test"),
    ("05_buffer_sensitivity_comparison.py", "Circular Buffer vs. Corridor Sensitivity"),
]

def main():
    print("=" * 68)
    print("BURIGANGA FLOW-AWARE LAND COVER & SENSITIVITY PIPELINE")
    print("=" * 68)
    print(f"Executing {len(STEPS)} pipeline steps...\n")

    for i, (script, desc) in enumerate(STEPS, 1):
        script_path = os.path.join(SCRIPT_DIR, script)
        print(f"[{i}/{len(STEPS)}] {desc}")
        print(f"       Script: {script}")
        t0 = time.time()

        res = subprocess.run([sys.executable, script_path], text=True)
        elapsed = time.time() - t0

        if res.returncode == 0:
            print(f"       [OK] Completed in {elapsed:.1f}s\n")
        else:
            print(f"       [FAILED] Exit code {res.returncode} in {elapsed:.1f}s")
            sys.exit(res.returncode)

    print("=" * 68)
    print("BURIGANGA PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
    print("=" * 68)

if __name__ == "__main__":
    main()
