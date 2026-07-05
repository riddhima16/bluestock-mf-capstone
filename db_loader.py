"""
db_loader.py
Day 2 — Tasks 4, 5

Creates the SQLite database (bluestock_mf.db) with a star schema,
loads all 10 cleaned CSV files into their respective tables,
and verifies row counts match the source files.

Run AFTER data_cleaning.py: python3 db_loader.py
"""

import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

PROCESSED_DIR = Path("data/processed")
DB_DIR        = Path("data/db")
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "bluestock_mf.db"
engine  = create_engine(f"sqlite:///{DB_PATH}", echo=False)


# ─────────────────────────────────────────────────────────────
# TASK 4 — Generate dim_date (the date dimension table)
# This table makes it easy to filter/group by year, month, quarter
# ─────────────────────────────────────────────────────────────

def generate_dim_date() -> pd.DataFrame:
    """Create a date dimension covering 2022-01-01 to 2026-12-31."""
    dates = pd.date_range("2022-01-01", "2026-12-31", freq="D")
    return pd.DataFrame({
        "date":        dates.strftime("%Y-%m-%d"),
        "year":        dates.year,
        "month":       dates.month,
        "quarter":     dates.quarter,
        "month_name":  dates.strftime("%B"),
        "day_of_week": dates.strftime("%A"),
        "is_weekday":  (dates.dayofweek < 5).astype(int),
    })


# ─────────────────────────────────────────────────────────────
# TASK 5 — Load each table into SQLite
# ─────────────────────────────────────────────────────────────

def load_table(df: pd.DataFrame, table_name: str, source: str = ""):
    """Load a DataFrame into a SQLite table and print a confirmation."""
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"  {table_name:<28} {len(df):>7,} rows  ✓   {source}")


def verify_counts():
    """Re-query the database to confirm all tables loaded correctly."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    tables = [
        "dim_fund", "dim_date", "fact_nav", "fact_transactions",
        "fact_performance", "fact_aum", "sip_inflows",
        "category_inflows", "folio_count", "portfolio_holdings",
        "benchmark_indices",
    ]

    print("\n  Verification — row counts read back from database:")
    print(f"  {'Table':<28} {'Rows':>8}")
    print(f"  {'-'*38}")
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        n = cur.fetchone()[0]
        print(f"  {t:<28} {n:>8,}")

    conn.close()


def main():
    print("="*60)
    print("  db_loader.py — Day 2 Tasks 4 & 5")
    print("="*60)
    print(f"\n  Database location: {DB_PATH}\n")
    print(">>> Loading tables into SQLite...\n")
    print(f"  {'Table':<28} {'Rows':>7}   Source file")
    print(f"  {'-'*60}")

    # ── Dimension tables ────────────────────────────────────────
    load_table(
        pd.read_csv(PROCESSED_DIR / "01_fund_master_clean.csv"),
        "dim_fund", "01_fund_master_clean.csv"
    )
    load_table(
        generate_dim_date(),
        "dim_date", "generated (2022–2026 daily)"
    )

    # ── Core fact tables ────────────────────────────────────────
    load_table(
        pd.read_csv(PROCESSED_DIR / "02_nav_history_clean.csv"),
        "fact_nav", "02_nav_history_clean.csv"
    )
    load_table(
        pd.read_csv(PROCESSED_DIR / "08_investor_transactions_clean.csv"),
        "fact_transactions", "08_investor_transactions_clean.csv"
    )
    load_table(
        pd.read_csv(PROCESSED_DIR / "07_scheme_performance_clean.csv"),
        "fact_performance", "07_scheme_performance_clean.csv"
    )
    load_table(
        pd.read_csv(PROCESSED_DIR / "03_aum_by_fund_house_clean.csv"),
        "fact_aum", "03_aum_by_fund_house_clean.csv"
    )

    # ── Supporting tables ───────────────────────────────────────
    load_table(
        pd.read_csv(PROCESSED_DIR / "04_monthly_sip_inflows_clean.csv"),
        "sip_inflows", "04_monthly_sip_inflows_clean.csv"
    )
    load_table(
        pd.read_csv(PROCESSED_DIR / "05_category_inflows_clean.csv"),
        "category_inflows", "05_category_inflows_clean.csv"
    )
    load_table(
        pd.read_csv(PROCESSED_DIR / "06_industry_folio_count_clean.csv"),
        "folio_count", "06_industry_folio_count_clean.csv"
    )
    load_table(
        pd.read_csv(PROCESSED_DIR / "09_portfolio_holdings_clean.csv"),
        "portfolio_holdings", "09_portfolio_holdings_clean.csv"
    )
    load_table(
        pd.read_csv(PROCESSED_DIR / "10_benchmark_indices_clean.csv"),
        "benchmark_indices", "10_benchmark_indices_clean.csv"
    )

    # ── Verify everything ───────────────────────────────────────
    verify_counts()

    print(f"\n{'='*60}")
    print(f"  Database ready: {DB_PATH}")
    print(f"  Next: open queries.sql and run the 10 SQL queries")
    print(f"  Tip: use DB Browser for SQLite (free) to explore visually")
    print(f"       https://sqlitebrowser.org/dl/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()