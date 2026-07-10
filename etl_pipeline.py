"""
etl_pipeline.py  —  Master ETL Pipeline
Bluestock Fintech | Mutual Fund Analytics Capstone

Runs the complete data pipeline in one command:
    Day 1 → Data Ingestion (live NAV fetch + CSV profiling)
    Day 2 → Data Cleaning + SQLite database load
    Day 3 → Exploratory Data Analysis (17 charts)
    Day 4 → Performance Analytics (CAGR, Sharpe, Alpha/Beta, Scorecard)
    Day 6 → Advanced Analytics (VaR, Cohort, Recommender, HHI)

Usage:
    python3 etl_pipeline.py              # run full pipeline
    python3 etl_pipeline.py --from day2  # start from a specific day

Prerequisites:
    - All 10 provided CSVs must be in data/raw/
    - pip3 install -r requirements.txt
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path


# ── pipeline steps ─────────────────────────────────────────────────────────
PIPELINE = [
    {
        "day":    "Day 1",
        "name":   "Live NAV Fetch",
        "script": "live_nav_fetch.py",
        "desc":   "Fetching live NAV from mfapi.in for 6 mutual fund schemes",
    },
    {
        "day":    "Day 1",
        "name":   "Data Ingestion",
        "script": "data_ingestion.py",
        "desc":   "Loading + profiling all 10 CSV datasets, validating AMFI codes",
    },
    {
        "day":    "Day 2",
        "name":   "Data Cleaning",
        "script": "data_cleaning.py",
        "desc":   "Cleaning all datasets — dates, nulls, duplicates, validation",
    },
    {
        "day":    "Day 2",
        "name":   "Database Loader",
        "script": "db_loader.py",
        "desc":   "Loading cleaned data into SQLite star schema (11 tables)",
    },
    {
        "day":    "Day 3",
        "name":   "EDA Analysis",
        "script": "eda_analysis.py",
        "desc":   "Generating 17 exploratory charts and EDA findings",
    },
    {
        "day":    "Day 4",
        "name":   "Performance Analytics",
        "script": "performance_analytics.py",
        "desc":   "Computing CAGR, Sharpe, Sortino, Alpha/Beta, Drawdown, Scorecard",
    },
    {
        "day":    "Day 4",
        "name":   "Benchmark Comparison",
        "script": "fix_task8.py",
        "desc":   "Benchmark comparison chart vs Nifty 50 and Nifty 100",
    },
    {
        "day":    "Day 6",
        "name":   "Advanced Analytics",
        "script": "advanced_analytics.py",
        "desc":   "VaR/CVaR, Rolling Sharpe, Cohort Analysis, SIP Continuity, Sector HHI",
    },
]

DAY_MAP = {
    "day1": 0, "day2": 2, "day3": 4,
    "day4": 5, "day6": 7,
}


def run_step(step: dict, step_num: int, total: int) -> bool:
    """Run a single pipeline step. Returns True on success."""
    script = step["script"]
    day    = step["day"]
    name   = step["name"]
    desc   = step["desc"]

    if not Path(script).exists():
        print(f"  ⚠  SKIP: {script} not found in project root")
        return True   # non-fatal: skip and continue

    print(f"\n{'='*65}")
    print(f"  [{step_num}/{total}]  {day}  —  {name}")
    print(f"  {desc}")
    print(f"{'='*65}")

    start = time.time()
    result = subprocess.run(
        [sys.executable, script],
        capture_output=False,
        text=True,
    )
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"\n  ✗  FAILED: {script} exited with code {result.returncode}")
        print(f"     Elapsed: {elapsed:.1f}s")
        return False
    else:
        print(f"\n  ✓  Done in {elapsed:.1f}s")
        return True


def check_prerequisites() -> bool:
    """Verify that required CSV files and folders exist before running."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        print(f"  ✗  ERROR: data/raw/ directory not found.")
        print(f"     Create it and place the 10 provided CSV files inside.")
        return False

    csv_files = list(raw_dir.glob("*.csv"))
    if len(csv_files) < 5:
        print(f"  ⚠  WARNING: Only {len(csv_files)} CSV files found in data/raw/")
        print(f"     Expected 10+ CSV files. Live NAV fetch will still run.")

    print(f"  ✓  data/raw/ found with {len(csv_files)} CSV files")
    return True


def print_summary(results: list):
    """Print a clean summary table at the end."""
    print(f"\n{'='*65}")
    print(f"  PIPELINE SUMMARY")
    print(f"{'='*65}")
    all_ok = True
    for step, success in results:
        status = "✓ OK   " if success else "✗ FAILED"
        print(f"  {status}  {step['day']:<8} {step['name']}")
        if not success:
            all_ok = False

    print(f"\n  {'All steps completed successfully!' if all_ok else 'Some steps failed — check output above.'}")
    print(f"{'='*65}\n")

    if all_ok:
        print("  📊 Next steps:")
        print("     streamlit run dashboard.py      ← Launch interactive dashboard")
        print("     python3 recommender.py           ← Get fund recommendations")
        print("     python3 create_report.py         ← Generate final report HTML")
        print("     python3 create_slides.py         ← Generate presentation PPTX\n")


def main():
    parser = argparse.ArgumentParser(
        description="Bluestock MF Analytics — Master ETL Pipeline")
    parser.add_argument(
        "--from", dest="start_from", type=str, default=None,
        choices=["day1","day2","day3","day4","day6"],
        help="Start pipeline from a specific day (e.g. --from day3)")
    parser.add_argument(
        "--only", dest="only_step", type=str, default=None,
        help="Run only one step by script name (e.g. --only db_loader.py)")
    args = parser.parse_args()

    print("\n" + "="*65)
    print("  BLUESTOCK MF ANALYTICS — MASTER ETL PIPELINE")
    print("  Mutual Fund Analytics Capstone · Cohort 2025")
    print("="*65)

    # determine which steps to run
    steps = PIPELINE.copy()
    if args.start_from:
        start_idx = DAY_MAP.get(args.start_from, 0)
        steps = steps[start_idx:]
        print(f"\n  Starting from: {args.start_from.upper()}")
    if args.only_step:
        steps = [s for s in steps if s["script"] == args.only_step]
        if not steps:
            print(f"  ERROR: No step found with script '{args.only_step}'")
            sys.exit(1)

    print(f"\n  Steps to run: {len(steps)}")
    for i, s in enumerate(steps, 1):
        print(f"    {i}. [{s['day']}] {s['name']} ({s['script']})")

    # prerequisites check
    print(f"\n  Checking prerequisites...")
    if not check_prerequisites():
        sys.exit(1)

    # run pipeline
    results = []
    total = len(steps)
    for i, step in enumerate(steps, 1):
        success = run_step(step, i, total)
        results.append((step, success))
        if not success:
            print(f"\n  Pipeline halted at step {i}: {step['script']}")
            print(f"  Tip: Fix the error above and re-run with: python3 etl_pipeline.py --from {step['day'].lower().replace(' ','')}")
            break

    print_summary(results)


if __name__ == "__main__":
    main()