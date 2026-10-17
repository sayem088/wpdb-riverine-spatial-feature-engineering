"""
Master CLI Entrypoint for the WPDB Riverine Spatial Feature Engineering Framework.

Reproduces all empirical experiments, hypothesis tests, and publication figures
for the IEEE CSDE 2026 conference paper:
"Water Pixel Dilution Bias: A Systematic Measurement Error in Riverine Spatial Feature Engineering"

Usage:
  python run_experiments.py --all
  python run_experiments.py --river buriganga
  python run_experiments.py --river shitalakhya
  python run_experiments.py --figures
"""

import argparse
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

def run_script(script_path, desc):
    print(f"\n>> {desc}")
    print(f"   Executing: {os.path.relpath(script_path, REPO_ROOT)}")
    t0 = time.time()
    res = subprocess.run([sys.executable, script_path], text=True)
    elapsed = time.time() - t0
    if res.returncode == 0:
        print(f"   [SUCCESS] Finished in {elapsed:.1f}s")
    else:
        print(f"   [ERROR] Failed with exit code {res.returncode}")
        sys.exit(res.returncode)

def run_buriganga():
    runner = os.path.join(REPO_ROOT, "pipelines", "buriganga", "run_buriganga.py")
    run_script(runner, "Buriganga River Pipeline (n=7 core stations)")

def run_shitalakhya():
    runner = os.path.join(REPO_ROOT, "pipelines", "shitalakhya", "run_shitalakhya.py")
    run_script(runner, "Shitalakhya River Validation Pipeline (n=4 stations)")

def run_figures():
    fig3 = os.path.join(REPO_ROOT, "visualization", "plot_multi_river_scatter.py")
    fig4 = os.path.join(REPO_ROOT, "visualization", "plot_gee_buffer_overlay.py")
    run_script(fig3, "Generating Figure 3: Multi-River Empirical Scaling")
    run_script(fig4, "Generating Figure 4: GEE Satellite Buffer Overlay")

def main():
    parser = argparse.ArgumentParser(
        description="Reproduce experiments and figures for Water-Pixel Dilution Bias (WPDB)."
    )
    parser.add_argument(
        "--river", choices=["buriganga", "shitalakhya", "both"], default=None,
        help="Execute pipeline for a specific river system."
    )
    parser.add_argument(
        "--figures", action="store_true",
        help="Generate publication-grade figures (Figures 3 and 4)."
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Execute entire suite: Buriganga, Shitalakhya, and all figures."
    )

    args = parser.parse_args()

    # If no arguments provided, display help or default to figures
    if not (args.all or args.river or args.figures):
        parser.print_help()
        print("\nNote: Precomputed results are stored under outputs/. To regenerate figures:")
        print("  python run_experiments.py --figures")
        return

    print("=" * 70)
    print("WATER-PIXEL DILUTION BIAS (WPDB) — EXPERIMENTAL REPRODUCTION SUITE")
    print("IEEE CSDE 2026 | Daffodil International University")
    print("=" * 70)

    if args.all or args.river in ["buriganga", "both"]:
        run_buriganga()

    if args.all or args.river in ["shitalakhya", "both"]:
        run_shitalakhya()

    if args.all or args.figures:
        run_figures()

    print("\n" + "=" * 70)
    print("ALL REQUESTED TASKS COMPLETED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    main()
