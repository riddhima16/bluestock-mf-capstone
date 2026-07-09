"""
recommender.py  —  Day 6: Fund Recommendation Engine

Standalone script. Can be run interactively OR imported as a module.

Usage:
    python3 recommender.py                     # interactive mode
    python3 recommender.py --risk Low          # CLI mode
    from recommender import recommend          # import mode

Logic:
    Input  : investor risk appetite (Low / Moderate / High)
    Process: filter fact_performance by matching risk_grade,
             rank by Sharpe ratio (best risk-adjusted return),
             enrich with CAGR, expense ratio, max drawdown
    Output : top 3 fund recommendations as a formatted table

Risk grade mapping:
    Low      → risk_grade in [Low]
    Moderate → risk_grade in [Moderate, Moderately High]
    High     → risk_grade in [High, Very High]
"""

import sqlite3
import pandas as pd
from pathlib import Path
import sys
import argparse

DB_PATH       = Path("data/db/bluestock_mf.db")
PROCESSED_DIR = Path("data/processed")


# ── load data from DB ─────────────────────────────────────────────────────

def load_performance_data() -> pd.DataFrame:
    """Load fact_performance and join with dim_fund for full context."""
    conn = sqlite3.connect(DB_PATH)
    perf = pd.read_sql("SELECT * FROM fact_performance", conn)
    fund = pd.read_sql("""
        SELECT amfi_code, risk_category, min_sip_amount, fund_manager
        FROM dim_fund
    """, conn)
    conn.close()

    # merge to get risk_category from dim_fund as well
    df = perf.merge(fund, on="amfi_code", how="left")
    return df


def load_scorecard() -> pd.DataFrame:
    """Load composite scorecard if available (Day 4 output)."""
    path = PROCESSED_DIR / "fund_scorecard.csv"
    if path.exists():
        return pd.read_csv(path)[["amfi_code","score_100","rank"]].copy()
    return pd.DataFrame()


# ── risk grade mapping ────────────────────────────────────────────────────

RISK_MAP = {
    "low":      ["Low"],
    "moderate": ["Moderate", "Moderately High"],
    "high":     ["High", "Very High"],
}

RISK_DESCRIPTION = {
    "low":      "Capital preservation. Suitable for short-term goals (1–2 yrs).",
    "moderate": "Balanced growth. Suitable for medium-term goals (3–5 yrs).",
    "high":     "Aggressive growth. Suitable for long-term goals (5+ yrs).",
}


# ── core recommendation function ──────────────────────────────────────────

def recommend(risk_appetite: str, top_n: int = 3) -> pd.DataFrame:
    """
    Recommend top_n funds for a given risk appetite.

    Args:
        risk_appetite: 'Low', 'Moderate', or 'High' (case-insensitive)
        top_n        : number of funds to return (default 3)

    Returns:
        DataFrame with top_n recommended funds and key metrics
    """
    risk_key = risk_appetite.strip().lower()
    if risk_key not in RISK_MAP:
        raise ValueError(f"risk_appetite must be Low, Moderate, or High. Got: {risk_appetite}")

    matched_grades = RISK_MAP[risk_key]

    df = load_performance_data()
    scorecard = load_scorecard()

    # filter by risk grade
    filtered = df[df["risk_grade"].isin(matched_grades)].copy()

    if filtered.empty:
        print(f"  No funds found for risk grade: {matched_grades}")
        return pd.DataFrame()

    # merge scorecard score if available
    if not scorecard.empty:
        filtered = filtered.merge(scorecard, on="amfi_code", how="left")
        # composite rank: 60% Sharpe + 40% composite score (normalised)
        max_sharpe = filtered["sharpe_ratio"].max()
        max_score  = filtered["score_100"].max() if "score_100" in filtered.columns else 1
        filtered["composite"] = (
            0.6 * (filtered["sharpe_ratio"] / max_sharpe) +
            0.4 * (filtered["score_100"].fillna(0) / max_score)
        )
        filtered = filtered.sort_values("composite", ascending=False)
    else:
        filtered = filtered.sort_values("sharpe_ratio", ascending=False)

    # select output columns
    out_cols = {
        "scheme_name":       "Fund Name",
        "fund_house":        "AMC",
        "risk_grade":        "Risk Grade",
        "sharpe_ratio":      "Sharpe Ratio",
        "sortino_ratio":     "Sortino Ratio",
        "return_3yr_pct":    "3yr CAGR %",
        "expense_ratio_pct": "Expense Ratio %",
        "max_drawdown_pct":  "Max Drawdown %",
        "aum_crore":         "AUM (₹ Cr)",
        "min_sip_amount":    "Min SIP (₹)",
        "fund_manager":      "Fund Manager",
    }
    available = [c for c in out_cols if c in filtered.columns]
    result = filtered.head(top_n)[available].copy()
    result = result.rename(columns={c: out_cols[c] for c in available})
    result = result.reset_index(drop=True)
    result.index = result.index + 1   # rank starts at 1
    return result


# ── formatted print ───────────────────────────────────────────────────────

def print_recommendation(risk_appetite: str):
    """Print a nicely formatted recommendation to the terminal."""
    risk_key = risk_appetite.strip().lower()

    print("\n" + "=" * 68)
    print(f"  BLUESTOCK FUND RECOMMENDER")
    print("=" * 68)
    print(f"  Risk Appetite : {risk_appetite.capitalize()}")
    print(f"  Profile       : {RISK_DESCRIPTION.get(risk_key, '')}")
    print(f"  Criteria      : Top Sharpe ratio within {RISK_MAP.get(risk_key, [])} grade")
    print("=" * 68)

    result = recommend(risk_appetite, top_n=3)

    if result.empty:
        print("  No recommendations available for this risk profile.")
        return

    for rank, row in result.iterrows():
        print(f"\n  ── Recommendation #{rank} ──────────────────────────────")
        print(f"  Fund      : {row.get('Fund Name','N/A')}")
        print(f"  AMC       : {row.get('AMC','N/A')}")
        print(f"  Risk Grade: {row.get('Risk Grade','N/A')}")
        print(f"  Sharpe    : {row.get('Sharpe Ratio', 'N/A')}")
        print(f"  Sortino   : {row.get('Sortino Ratio', 'N/A')}")
        print(f"  3yr CAGR  : {row.get('3yr CAGR %', 'N/A')}%")
        print(f"  Exp Ratio : {row.get('Expense Ratio %', 'N/A')}%")
        print(f"  Max DD    : {row.get('Max Drawdown %', 'N/A')}%")
        print(f"  AUM       : ₹{row.get('AUM (₹ Cr)', 'N/A'):,} Cr"
              if isinstance(row.get('AUM (₹ Cr)'), (int, float)) else
              f"  AUM       : {row.get('AUM (₹ Cr)', 'N/A')}")
        print(f"  Min SIP   : ₹{row.get('Min SIP (₹)', 500):.0f}/month")
        print(f"  Manager   : {row.get('Fund Manager','N/A')}")

    print("\n" + "=" * 68)
    print("  ⚠  Disclaimer: This is for educational purposes only.")
    print("     Mutual fund investments are subject to market risks.")
    print("     Past performance does not guarantee future returns.")
    print("=" * 68 + "\n")


# ── interactive demo ──────────────────────────────────────────────────────

def run_interactive():
    """Run all three risk profiles for demo / notebook output."""
    print("\nRunning recommendations for all risk profiles...\n")
    for risk in ["Low", "Moderate", "High"]:
        print_recommendation(risk)


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Bluestock Fund Recommender — get top 3 fund suggestions")
    parser.add_argument("--risk", type=str, default=None,
                        choices=["Low","Moderate","High"],
                        help="Investor risk appetite: Low / Moderate / High")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run data_cleaning.py and db_loader.py first.")
        sys.exit(1)

    if args.risk:
        print_recommendation(args.risk)
    else:
        # interactive: ask the user
        print("\n" + "="*50)
        print("  BLUESTOCK FUND RECOMMENDER")
        print("="*50)
        print("\n  Options: Low | Moderate | High")
        try:
            user_input = input("  Enter your risk appetite: ").strip()
            if user_input.lower() not in RISK_MAP:
                print("  Invalid input. Running all three profiles instead.")
                run_interactive()
            else:
                print_recommendation(user_input)
        except (EOFError, KeyboardInterrupt):
            # non-interactive environment (e.g. notebook) — run all
            run_interactive()


if __name__ == "__main__":
    main()