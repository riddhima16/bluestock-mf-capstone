"""
data_ingestion.py
Day 1 — Tasks 3, 6, 7
"""

import pandas as pd
from pathlib import Path

RAW_DIR     = Path("data/raw")
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

ALL_CSV_FILES = [
    "01_fund_master.csv",
    "02_nav_history.csv",
    "03_aum_by_fund_house.csv",
    "04_monthly_sip_inflows.csv",
    "05_category_inflows.csv",
    "06_industry_folio_count.csv",
    "07_scheme_performance.csv",
    "08_investor_transactions.csv",
    "09_portfolio_holdings.csv",
    "10_benchmark_indices.csv",
]

AMFI_CODE_COL = "amfi_code"


def load_and_profile(filename):
    filepath = RAW_DIR / filename
    if not filepath.exists():
        print(f"\n  WARNING: {filename} not found in data/raw/ — skipping")
        return pd.DataFrame()

    df = pd.read_csv(filepath)
    print(f"\n{'='*60}")
    print(f"  FILE : {filename}")
    print(f"{'='*60}")
    print(f"  Shape : {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"\n  Column types:")
    for col, dtype in df.dtypes.items():
        print(f"    {col:<35} {dtype}")
    print(f"\n  First 3 rows:")
    print(df.head(3).to_string())

    n_dupes      = df.duplicated().sum()
    null_counts  = df.isnull().sum()
    n_nulls      = null_counts.sum()
    print(f"\n  Anomalies:")
    print(f"    Duplicate rows : {n_dupes}")
    print(f"    Total nulls    : {n_nulls}")
    if n_nulls > 0:
        for col, count in null_counts[null_counts > 0].items():
            print(f"      -> '{col}' has {count} null values")
    return df


def explore_fund_master(df):
    if df.empty:
        print("\n  WARNING: fund_master is empty — skipping Task 6.")
        return

    print("\n" + "="*60)
    print("  TASK 6 — Fund Master Exploration")
    print("="*60)

    for col, label in [("fund_house","Fund Houses"), ("category","Categories"),
                        ("sub_category","Sub-categories"), ("risk_category","Risk Grades")]:
        if col in df.columns:
            unique_vals = sorted(df[col].dropna().unique().tolist())
            print(f"\n  {label} ({len(unique_vals)} unique):")
            for val in unique_vals:
                print(f"    * {val}  ({(df[col]==val).sum()} schemes)")
        else:
            print(f"\n  WARNING: column '{col}' not found.")

    if AMFI_CODE_COL in df.columns:
        print(f"\n  AMFI Code sample:")
        print(df[[AMFI_CODE_COL, "scheme_name", "fund_house"]].head(5).to_string(index=False))


def validate_amfi_codes(fund_master, nav_history):
    print("\n" + "="*60)
    print("  TASK 7 — AMFI Code Validation")
    print("="*60)

    if fund_master.empty or nav_history.empty:
        print("  Cannot validate — files missing.")
        return {}

    master_codes = set(fund_master[AMFI_CODE_COL].dropna().unique())
    nav_codes    = set(nav_history[AMFI_CODE_COL].dropna().unique())
    missing      = master_codes - nav_codes

    print(f"\n  Schemes in fund_master   : {len(master_codes)}")
    print(f"  Schemes in nav_history   : {len(nav_codes)}")
    print(f"  Missing from nav_history : {len(missing)}", end="")
    print("  All matched!" if not missing else f"\n  Missing: {sorted(missing)}")

    return {"schemes_in_fund_master": len(master_codes),
            "schemes_in_nav_history": len(nav_codes),
            "missing_from_nav_history": len(missing),
            "missing_codes": sorted(missing)}


def write_quality_report(profiles, validation):
    lines = ["DATA QUALITY SUMMARY - Day 1",
             "Bluestock Fintech | MF Analytics Capstone",
             "="*55, "", "FILE PROFILES:", "-"*40]

    for filename, df in profiles.items():
        if df.empty:
            lines.append(f"  {filename}: MISSING")
        else:
            status = "Clean" if df.duplicated().sum()==0 and df.isnull().sum().sum()==0 else "Issues found"
            lines.append(f"  {filename}: {df.shape[0]}r x {df.shape[1]}c | "
                         f"dupes={df.duplicated().sum()} | nulls={df.isnull().sum().sum()} | {status}")

    lines += ["", "AMFI CODE VALIDATION:", "-"*40]
    if validation:
        for k, v in validation.items():
            lines.append(f"  {k}: {v}")
    else:
        lines.append("  Could not complete validation.")

    report_path = REPORTS_DIR / "data_quality_day1.txt"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Report saved to: {report_path}")


def main():
    print("="*60)
    print("  data_ingestion.py — Day 1 Tasks 3, 6, 7")
    print("="*60)

    loaded = {}
    print("\n>>> TASK 3: Loading all 10 CSV files...")
    for f in ALL_CSV_FILES:
        loaded[f] = load_and_profile(f)

    print("\n>>> TASK 6: Exploring fund master...")
    explore_fund_master(loaded.get("01_fund_master.csv", pd.DataFrame()))

    print("\n>>> TASK 7: Validating AMFI codes...")
    validation = validate_amfi_codes(
        loaded.get("01_fund_master.csv", pd.DataFrame()),
        loaded.get("02_nav_history.csv", pd.DataFrame())
    )
    write_quality_report(loaded, validation)

    print("\n" + "="*60)
    print("  Day 1 complete! Now run: git add . && git commit")
    print("="*60)


if __name__ == "__main__":
    main()