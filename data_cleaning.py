"""
data_cleaning.py
Day 2 — Tasks 1, 2, 3

Reads all 10 raw CSVs from data/raw/
Applies cleaning (dates, nulls, duplicates, validation)
Saves cleaned versions to data/processed/

Run: python3 data_cleaning.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR       = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# TASK 1 — Clean nav_history.csv
# ─────────────────────────────────────────────────────────────

def clean_nav_history():
    print("\n>>> TASK 1: Cleaning nav_history.csv")
    df = pd.read_csv(RAW_DIR / "02_nav_history.csv")
    print(f"  Raw rows : {len(df)}")

    # Parse date string → proper datetime object
    df["date"] = pd.to_datetime(df["date"])

    # Sort by fund + date so history is in order
    df = df.sort_values(["amfi_code", "date"]).reset_index(drop=True)

    # Remove exact duplicate rows (same fund, same date)
    before = len(df)
    df = df.drop_duplicates(subset=["amfi_code", "date"])
    print(f"  Duplicates removed : {before - len(df)}")

    # Validate NAV > 0 (impossible for a real fund to have zero/negative NAV)
    bad = df[df["nav"] <= 0]
    if len(bad) > 0:
        print(f"  WARNING: {len(bad)} rows with NAV <= 0 — removing")
        df = df[df["nav"] > 0]
    else:
        print(f"  NAV > 0 check      : all values valid  ✓")

    # Forward-fill missing NAV for market holidays and weekends
    # Method: reindex each fund to a full business-day calendar, then ffill
    filled_parts = []
    for code, group in df.groupby("amfi_code"):
        g = group.set_index("date")[["nav"]]
        full_bday_range = pd.bdate_range(g.index.min(), g.index.max())
        g = g.reindex(full_bday_range)        # NaN inserted for missing days
        g["nav"] = g["nav"].ffill()           # fill with last known NAV
        g.index.name = "date"
        g["amfi_code"] = code
        g = g.reset_index()[["amfi_code", "date", "nav"]]
        filled_parts.append(g)

    df = pd.concat(filled_parts, ignore_index=True)
    df = df.sort_values(["amfi_code", "date"]).reset_index(drop=True)

    # Compute daily return % — core metric used in Sharpe, Beta, VaR later
    # Formula: (today_NAV / yesterday_NAV - 1) * 100
    df["daily_return_pct"] = (
        df.groupby("amfi_code")["nav"]
          .pct_change()
          .mul(100)
          .round(4)
    )

    # Convert date back to string for consistent CSV storage
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    df.to_csv(PROCESSED_DIR / "02_nav_history_clean.csv", index=False)
    print(f"  Rows after forward-fill : {len(df)}")
    print(f"  Saved → data/processed/02_nav_history_clean.csv  ✓")
    return df


# ─────────────────────────────────────────────────────────────
# TASK 2 — Clean investor_transactions.csv
# ─────────────────────────────────────────────────────────────

def clean_investor_transactions():
    print("\n>>> TASK 2: Cleaning investor_transactions.csv")
    df = pd.read_csv(RAW_DIR / "08_investor_transactions.csv")
    print(f"  Raw rows : {len(df)}")

    # Fix date format
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["transaction_date"] = df["transaction_date"].dt.strftime("%Y-%m-%d")

    # Standardise transaction_type — only 3 valid values allowed
    valid_types = {"SIP", "Lumpsum", "Redemption"}
    found_types = df["transaction_type"].value_counts().to_dict()
    print(f"  transaction_type values : {found_types}")

    invalid = df[~df["transaction_type"].isin(valid_types)]
    if len(invalid) > 0:
        print(f"  WARNING: {len(invalid)} rows with unexpected type — removing")
        df = df[df["transaction_type"].isin(valid_types)]
    else:
        print(f"  transaction_type   : SIP / Lumpsum / Redemption only  ✓")

    # Validate amount > 0
    bad_amt = df[df["amount_inr"] <= 0]
    if len(bad_amt) > 0:
        print(f"  WARNING: {len(bad_amt)} rows with amount <= 0 — removing")
        df = df[df["amount_inr"] > 0]
    else:
        print(f"  amount_inr > 0     : all values valid  ✓")

    # Check KYC status enum
    valid_kyc = {"Verified", "Pending"}
    bad_kyc = df[~df["kyc_status"].isin(valid_kyc)]
    if len(bad_kyc) > 0:
        print(f"  WARNING: unexpected KYC values: {bad_kyc['kyc_status'].unique()}")
    else:
        print(f"  kyc_status         : Verified / Pending only  ✓")

    df.to_csv(PROCESSED_DIR / "08_investor_transactions_clean.csv", index=False)
    print(f"  Final rows : {len(df)}")
    print(f"  Saved → data/processed/08_investor_transactions_clean.csv  ✓")
    return df


# ─────────────────────────────────────────────────────────────
# TASK 3 — Clean scheme_performance.csv
# ─────────────────────────────────────────────────────────────

def clean_scheme_performance():
    print("\n>>> TASK 3: Cleaning scheme_performance.csv")
    df = pd.read_csv(RAW_DIR / "07_scheme_performance.csv")
    print(f"  Raw rows : {len(df)}")

    # Validate all numeric return/risk columns
    numeric_cols = [
        "return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
        "benchmark_3yr_pct", "alpha", "beta", "sharpe_ratio",
        "sortino_ratio", "std_dev_ann_pct", "max_drawdown_pct",
        "aum_crore", "expense_ratio_pct"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        n_nulls = df[col].isnull().sum()
        if n_nulls > 0:
            print(f"  WARNING: '{col}' has {n_nulls} non-numeric values — set to NaN")

    # Check expense_ratio in valid SEBI range: 0.1% to 2.5%
    out_of_range = df[(df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5)]
    if len(out_of_range) > 0:
        print(f"  Funds with expense_ratio outside 0.1–2.5% (flagged, not removed):")
        print(out_of_range[["scheme_name", "expense_ratio_pct"]].to_string(index=False))
    else:
        print(f"  expense_ratio_pct  : all within SEBI range 0.1–2.5%  ✓")

    # Flag negative Sharpe ratios
    neg_sharpe = df[df["sharpe_ratio"] < 0]
    if len(neg_sharpe) > 0:
        print(f"  Funds with negative Sharpe ratio (underperformed risk-free rate):")
        print(neg_sharpe[["scheme_name", "sharpe_ratio"]].to_string(index=False))
    else:
        print(f"  Sharpe ratios      : all positive  ✓")

    df.to_csv(PROCESSED_DIR / "07_scheme_performance_clean.csv", index=False)
    print(f"  Final rows : {len(df)}")
    print(f"  Saved → data/processed/07_scheme_performance_clean.csv  ✓")
    return df


# ─────────────────────────────────────────────────────────────
# PASS-THROUGH — remaining 7 CSVs (parse dates, fix minor issues)
# ─────────────────────────────────────────────────────────────

def clean_remaining():
    print("\n>>> Cleaning remaining 7 CSV files...")

    files = [
        ("01_fund_master.csv",          "01_fund_master_clean.csv",          ["launch_date"]),
        ("03_aum_by_fund_house.csv",    "03_aum_by_fund_house_clean.csv",    ["date"]),
        ("04_monthly_sip_inflows.csv",  "04_monthly_sip_inflows_clean.csv",  ["month"]),
        ("05_category_inflows.csv",     "05_category_inflows_clean.csv",     ["month"]),
        ("06_industry_folio_count.csv", "06_industry_folio_count_clean.csv", ["month"]),
        ("09_portfolio_holdings.csv",   "09_portfolio_holdings_clean.csv",   ["portfolio_date"]),
        ("10_benchmark_indices.csv",    "10_benchmark_indices_clean.csv",    ["date"]),
    ]

    for in_file, out_file, date_cols in files:
        df = pd.read_csv(RAW_DIR / in_file)

        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")

        # SIP inflows: first 12 months have no YoY (expected) — fill with 0
        if "yoy_growth_pct" in df.columns:
            n = df["yoy_growth_pct"].isnull().sum()
            df["yoy_growth_pct"] = df["yoy_growth_pct"].fillna(0)
            if n > 0:
                print(f"  {in_file}: filled {n} null yoy_growth_pct with 0")

        df.to_csv(PROCESSED_DIR / out_file, index=False)
        print(f"  {in_file:<35} {len(df)} rows  →  {out_file}  ✓")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("="*60)
    print("  data_cleaning.py — Day 2 Tasks 1, 2, 3")
    print("="*60)

    clean_nav_history()
    clean_investor_transactions()
    clean_scheme_performance()
    clean_remaining()

    count = len(list(PROCESSED_DIR.glob("*.csv")))
    print(f"\n{'='*60}")
    print(f"  Done! {count} clean files saved in data/processed/")
    print(f"  Next: python3 db_loader.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()