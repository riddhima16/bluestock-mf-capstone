"""
advanced_analytics.py  —  Day 6: Advanced Analytics + Risk Metrics

Tasks:
  1. Historical VaR (95%) + CVaR for all 40 funds
  2. Rolling 90-day Sharpe for 5 key funds + chart
  3. Investor cohort analysis (by first transaction year)
  4. SIP continuity analysis — flag at-risk investors
  5. Sector HHI concentration per equity fund
  (Task 5 recommender is in recommender.py)

Outputs:
  data/processed/var_cvar_report.csv
  data/processed/cohort_analysis.csv
  data/processed/sip_continuity.csv
  data/processed/sector_hhi.csv
  reports/charts/13_rolling_sharpe.png
  reports/charts/14_var_comparison.png
  reports/charts/15_sector_hhi.png

Run: python3 advanced_analytics.py
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ── paths ────────────────────────────────────────────────────────────────
DB_PATH       = Path("data/db/bluestock_mf.db")
PROCESSED_DIR = Path("data/processed")
CHARTS_DIR    = Path("reports/charts")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# ── constants ─────────────────────────────────────────────────────────────
RF_DAILY     = 0.065 / 252
TRADING_DAYS = 252

# ── style ─────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.dpi": 150, "figure.facecolor": "white",
    "axes.facecolor": "#f7f9fc", "axes.grid": True,
    "grid.alpha": 0.35, "font.size": 11,
    "axes.titlesize": 13, "axes.titleweight": "bold",
})
BLUE    = "#1565C0"
GREEN   = "#00897B"
AMBER   = "#F9A825"
RED     = "#C62828"
PALETTE = ["#1565C0","#00897B","#F9A825","#C62828",
           "#6A1B9A","#00838F","#EF6C00","#2E7D32"]

def savefig(name):
    path = CHARTS_DIR / f"{name}.png"
    plt.savefig(path, bbox_inches="tight", dpi=150, facecolor="white")
    plt.close()
    print(f"  Saved: {name}.png")


# ════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ════════════════════════════════════════════════════════════════════════

def load_data():
    print("\n>>> Loading data from database...")
    conn = sqlite3.connect(DB_PATH)
    nav   = pd.read_sql("SELECT * FROM fact_nav",            conn)
    fund  = pd.read_sql("SELECT * FROM dim_fund",            conn)
    perf  = pd.read_sql("SELECT * FROM fact_performance",    conn)
    tx    = pd.read_sql("SELECT * FROM fact_transactions",   conn)
    hold  = pd.read_sql("SELECT * FROM portfolio_holdings",  conn)
    conn.close()

    nav["date"]                      = pd.to_datetime(nav["date"])
    tx["transaction_date"]           = pd.to_datetime(tx["transaction_date"])

    # convert % to decimal for all calculations
    nav["daily_return"] = nav["daily_return_pct"] / 100.0

    # load scorecard for top fund selection
    sc_path = PROCESSED_DIR / "fund_scorecard.csv"
    scorecard = pd.read_csv(sc_path) if sc_path.exists() else pd.DataFrame()

    print(f"  NAV rows      : {len(nav):,}")
    print(f"  Funds         : {nav['amfi_code'].nunique()}")
    print(f"  Transactions  : {len(tx):,}")
    print(f"  Holdings rows : {len(hold):,}")
    return nav, fund, perf, tx, hold, scorecard


# ════════════════════════════════════════════════════════════════════════
# TASK 1 — Historical VaR (95%) + CVaR
# ════════════════════════════════════════════════════════════════════════

def task1_var_cvar(nav, fund):
    print("\n>>> TASK 1: Historical VaR (95%) and CVaR for all 40 funds")

    rows = []
    for code, grp in nav.dropna(subset=["daily_return"]).groupby("amfi_code"):
        r = grp["daily_return"].values

        # VaR: 5th percentile → worst loss exceeded only 5% of days
        var_95  = np.percentile(r, 5)

        # CVaR (Expected Shortfall): mean of returns BELOW VaR threshold
        cvar_95 = r[r <= var_95].mean() if len(r[r <= var_95]) > 0 else var_95

        # Annualise (approximate, for comparison)
        var_ann  = var_95  * np.sqrt(TRADING_DAYS) * 100   # as %
        cvar_ann = cvar_95 * np.sqrt(TRADING_DAYS) * 100   # as %

        rows.append({
            "amfi_code":      code,
            "var_95_daily":   round(var_95  * 100, 4),   # daily %
            "cvar_95_daily":  round(cvar_95 * 100, 4),   # daily %
            "var_95_ann":     round(var_ann,  4),          # annualised %
            "cvar_95_ann":    round(cvar_ann, 4),          # annualised %
            "n_days":         len(r),
            "pct_neg_days":   round((r < 0).mean() * 100, 2),
        })

    df = pd.DataFrame(rows)
    df = df.merge(fund[["amfi_code","scheme_name","fund_house","category",
                         "sub_category"]], on="amfi_code")
    df = df.sort_values("var_95_daily").reset_index(drop=True)

    print(f"\n  Top 5 highest VaR (most risky) — daily %:")
    print(f"  {'Scheme':<44} {'VaR 95%':>9} {'CVaR 95%':>10} {'Neg Days':>10}")
    print(f"  {'-'*76}")
    for _, row in df.head(5).iterrows():
        nm = str(row["scheme_name"])[:42]
        print(f"  {nm:<44} {row['var_95_daily']:>8.3f}%"
              f" {row['cvar_95_daily']:>9.3f}% {row['pct_neg_days']:>9.1f}%")

    print(f"\n  Top 5 lowest VaR (least risky) — daily %:")
    print(f"  {'Scheme':<44} {'VaR 95%':>9} {'CVaR 95%':>10}")
    print(f"  {'-'*66}")
    for _, row in df.tail(5).iterrows():
        nm = str(row["scheme_name"])[:42]
        print(f"  {nm:<44} {row['var_95_daily']:>8.3f}% {row['cvar_95_daily']:>9.3f}%")

    # VaR comparison bar chart
    df_plot = df.copy()
    df_plot["label"] = df_plot["scheme_name"].str[:28]
    df_plot = df_plot.sort_values("var_95_daily")

    fig, ax = plt.subplots(figsize=(14, 8))
    x = range(len(df_plot))
    ax.barh(x, df_plot["var_95_daily"],
            color=[RED if v < -1.5 else AMBER if v < -1.0 else GREEN
                   for v in df_plot["var_95_daily"]],
            alpha=0.85, edgecolor="white", label="VaR 95%")
    ax.barh(x, df_plot["cvar_95_daily"],
            color="none", edgecolor=RED, linewidth=1.2,
            linestyle="--", label="CVaR 95% (outline)")
    ax.set_yticks(list(x))
    ax.set_yticklabels(df_plot["label"].tolist(), fontsize=8)
    ax.set_xlabel("Daily Return (%)")
    ax.set_title("Historical VaR 95% and CVaR — All 40 Funds\n"
                 "(Red = High Risk, Green = Low Risk)", pad=12)
    ax.axvline(0, color="grey", linewidth=0.8)
    ax.legend(loc="lower right")
    plt.tight_layout()
    savefig("14_var_comparison")

    df.to_csv(PROCESSED_DIR / "var_cvar_report.csv", index=False)
    print(f"\n  Saved: data/processed/var_cvar_report.csv")
    return df


# ════════════════════════════════════════════════════════════════════════
# TASK 2 — Rolling 90-Day Sharpe Ratio
# ════════════════════════════════════════════════════════════════════════

def task2_rolling_sharpe(nav, fund, scorecard):
    print("\n>>> TASK 2: Rolling 90-day Sharpe ratio")

    # pick 5 funds — top 5 from scorecard or top 5 by AUM
    if len(scorecard) >= 5:
        top5_codes = scorecard.head(5)["amfi_code"].astype(int).tolist()
    else:
        # fallback: hardcode 5 representative funds
        top5_codes = [119551, 119598, 120503, 148567, 120843]

    top5_codes = [c for c in top5_codes
                  if c in nav["amfi_code"].values][:5]

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.axhline(0, color="grey", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.axhline(1, color=GREEN, linewidth=0.8, linestyle=":", alpha=0.5,
               label="Sharpe = 1 (good)")

    for i, code in enumerate(top5_codes):
        grp = (nav[nav["amfi_code"] == code]
               .sort_values("date")
               .dropna(subset=["daily_return"])
               .copy())
        if len(grp) < 100:
            continue

        grp["excess"] = grp["daily_return"] - RF_DAILY
        grp["roll_sharpe"] = (
            grp["excess"].rolling(90).mean() /
            grp["excess"].rolling(90).std() *
            np.sqrt(TRADING_DAYS)
        )

        # get fund label
        house = fund[fund["amfi_code"] == code]["fund_house"].values
        label = house[0].replace(" Mutual Fund","").replace(" MF","") if len(house) else str(code)

        ax.plot(grp["date"], grp["roll_sharpe"],
                color=PALETTE[i], linewidth=1.8,
                label=label, alpha=0.9)

    ax.set_title("Rolling 90-Day Sharpe Ratio — Top 5 Scored Funds", pad=12)
    ax.set_xlabel("Date")
    ax.set_ylabel("Rolling Sharpe Ratio (annualised)")
    ax.set_ylim(-3, 5)
    ax.legend(loc="upper left", framealpha=0.9)
    ax.fill_between(ax.get_xlim(), 0, 1,
                    alpha=0.04, color=RED, transform=ax.get_xaxis_transform())
    plt.tight_layout()
    savefig("13_rolling_sharpe")
    print(f"  Rolling Sharpe chart saved for {len(top5_codes)} funds")


# ════════════════════════════════════════════════════════════════════════
# TASK 3 — Investor Cohort Analysis
# ════════════════════════════════════════════════════════════════════════

def task3_cohort_analysis(tx, fund):
    print("\n>>> TASK 3: Investor cohort analysis")

    # Find each investor's first transaction date → cohort year
    first_tx = (tx.groupby("investor_id")["transaction_date"]
                  .min().reset_index())
    first_tx.columns = ["investor_id", "first_date"]
    first_tx["cohort_year"] = first_tx["first_date"].dt.year

    tx_c = tx.merge(first_tx[["investor_id","cohort_year"]], on="investor_id")
    sip_c = tx_c[tx_c["transaction_type"] == "SIP"]

    # Per cohort: avg SIP, total invested, unique investors, top fund
    cohort_stats = sip_c.groupby("cohort_year").agg(
        num_investors   = ("investor_id",  "nunique"),
        num_sip_txns    = ("amount_inr",   "count"),
        avg_sip_amount  = ("amount_inr",   "mean"),
        total_invested  = ("amount_inr",   "sum"),
    ).reset_index()
    cohort_stats["avg_sip_amount"]  = cohort_stats["avg_sip_amount"].round(0)
    cohort_stats["total_invested_cr"] = (cohort_stats["total_invested"] / 1e7).round(2)

    # Top fund per cohort
    top_fund_per_cohort = (sip_c.groupby(["cohort_year","amfi_code"])
                                .size().reset_index(name="count")
                                .sort_values("count", ascending=False)
                                .groupby("cohort_year").first()
                                .reset_index()[["cohort_year","amfi_code"]])
    top_fund_per_cohort = top_fund_per_cohort.merge(
        fund[["amfi_code","scheme_name"]], on="amfi_code", how="left")
    top_fund_per_cohort["top_fund"] = top_fund_per_cohort["scheme_name"].str[:40]

    cohort_stats = cohort_stats.merge(
        top_fund_per_cohort[["cohort_year","top_fund"]], on="cohort_year", how="left")

    print(f"\n  Cohort summary:")
    print(f"  {'Year':>6} {'Investors':>10} {'Avg SIP':>10} {'Total Cr':>10} {'Top Fund':<40}")
    print(f"  {'-'*80}")
    for _, row in cohort_stats.iterrows():
        print(f"  {int(row['cohort_year']):>6}"
              f" {int(row['num_investors']):>10}"
              f" {row['avg_sip_amount']:>10,.0f}"
              f" {row['total_invested_cr']:>10.1f}"
              f" {str(row['top_fund']):<40}")

    cohort_stats.to_csv(PROCESSED_DIR / "cohort_analysis.csv", index=False)
    print(f"\n  Saved: data/processed/cohort_analysis.csv")
    return cohort_stats


# ════════════════════════════════════════════════════════════════════════
# TASK 4 — SIP Continuity Analysis
# ════════════════════════════════════════════════════════════════════════

def task4_sip_continuity(tx):
    print("\n>>> TASK 4: SIP continuity analysis")

    sip = (tx[tx["transaction_type"] == "SIP"]
           .sort_values(["investor_id","transaction_date"])
           .copy())

    rows = []
    at_risk_count = 0
    for investor_id, grp in sip.groupby("investor_id"):
        if len(grp) < 6:
            continue   # need at least 6 SIP transactions

        dates = grp["transaction_date"].sort_values().values
        gaps  = [(dates[i+1] - dates[i]).astype("timedelta64[D]").astype(int)
                 for i in range(len(dates) - 1)]
        avg_gap = np.mean(gaps)
        max_gap = np.max(gaps)
        at_risk = avg_gap > 35

        if at_risk:
            at_risk_count += 1

        rows.append({
            "investor_id":   investor_id,
            "num_sip_txns":  len(grp),
            "avg_gap_days":  round(avg_gap, 1),
            "max_gap_days":  int(max_gap),
            "at_risk":       at_risk,
            "state":         grp["state"].iloc[0],
            "age_group":     grp["age_group"].iloc[0],
        })

    df = pd.DataFrame(rows)
    total = len(df)
    at_risk_pct = at_risk_count / total * 100 if total > 0 else 0

    print(f"\n  Investors with 6+ SIP transactions : {total:,}")
    print(f"  At-risk (avg gap > 35 days)         : {at_risk_count:,} ({at_risk_pct:.1f}%)")
    print(f"  Healthy (avg gap ≤ 35 days)         : {total - at_risk_count:,}")

    # Distribution of avg gaps
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].hist(df["avg_gap_days"], bins=40,
                 color=BLUE, alpha=0.75, edgecolor="white")
    axes[0].axvline(35, color=RED, linewidth=2, linestyle="--",
                    label="At-risk threshold (35 days)")
    axes[0].set_title("Distribution of Avg SIP Gap (Days)")
    axes[0].set_xlabel("Avg Gap Between SIP Transactions (days)")
    axes[0].set_ylabel("Number of Investors")
    axes[0].legend()

    # At-risk by state
    state_risk = (df.groupby("state")["at_risk"]
                    .mean().mul(100)
                    .sort_values(ascending=True)
                    .reset_index())
    state_risk.columns = ["State","At-risk %"]
    axes[1].barh(state_risk["State"], state_risk["At-risk %"],
                 color=[RED if v > 30 else AMBER if v > 20 else GREEN
                        for v in state_risk["At-risk %"]],
                 edgecolor="white")
    axes[1].set_title("At-risk SIP Investors by State (%)")
    axes[1].set_xlabel("% At-risk (avg gap > 35 days)")
    axes[1].axvline(at_risk_pct, color=RED, linewidth=1.5, linestyle="--",
                    label=f"Overall avg: {at_risk_pct:.1f}%")
    axes[1].legend()

    plt.tight_layout()
    savefig("16_sip_continuity")

    df.to_csv(PROCESSED_DIR / "sip_continuity.csv", index=False)
    print(f"  Saved: data/processed/sip_continuity.csv")
    return df


# ════════════════════════════════════════════════════════════════════════
# TASK 6 — Sector HHI Concentration
# ════════════════════════════════════════════════════════════════════════

def task6_sector_hhi(holdings, fund):
    print("\n>>> TASK 6: Sector HHI (Herfindahl-Hirschman Index)")

    # Only equity funds
    equity_codes = fund[fund["category"] == "Equity"]["amfi_code"].tolist()
    eq = holdings[holdings["amfi_code"].isin(equity_codes)].copy()

    rows = []
    for code, grp in eq.groupby("amfi_code"):
        weights = grp["weight_pct"].values
        hhi = np.sum(weights ** 2)   # HHI = Σ(w_i²)

        # Sector breakdown
        sector_w = grp.groupby("sector")["weight_pct"].sum()
        top_sector = sector_w.idxmax()
        top_weight = sector_w.max()
        n_sectors  = len(sector_w)

        rows.append({
            "amfi_code":       code,
            "hhi":             round(hhi, 2),
            "top_sector":      top_sector,
            "top_sector_pct":  round(top_weight, 2),
            "n_sectors":       n_sectors,
            "concentration":   "High" if hhi > 2000 else
                               "Moderate" if hhi > 800 else "Low",
        })

    df = pd.DataFrame(rows)
    df = df.merge(fund[["amfi_code","scheme_name","fund_house","sub_category"]],
                  on="amfi_code")
    df = df.sort_values("hhi", ascending=False).reset_index(drop=True)

    print(f"\n  Top 5 most concentrated funds (highest HHI):")
    print(f"  {'Scheme':<44} {'HHI':>7} {'Top Sector':<25} {'Conc.':>10}")
    print(f"  {'-'*90}")
    for _, row in df.head(5).iterrows():
        nm = str(row["scheme_name"])[:42]
        print(f"  {nm:<44} {row['hhi']:>7.1f}"
              f" {str(row['top_sector']):<25} {row['concentration']:>10}")

    # HHI bar chart
    df_plot = df.copy()
    df_plot["label"] = df_plot["scheme_name"].str[:30]
    df_plot = df_plot.sort_values("hhi", ascending=True)

    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.barh(
        df_plot["label"], df_plot["hhi"],
        color=[RED if v > 2000 else AMBER if v > 800 else GREEN
               for v in df_plot["hhi"]],
        edgecolor="white", alpha=0.85,
    )
    ax.axvline(2000, color=RED,   linewidth=1.5, linestyle="--",
               alpha=0.7, label="High concentration (HHI > 2000)")
    ax.axvline(800,  color=AMBER, linewidth=1.5, linestyle=":",
               alpha=0.7, label="Moderate (HHI > 800)")
    ax.set_title("Sector HHI Concentration — All Equity Funds\n"
                 "(Higher = More Concentrated Portfolio)", pad=12)
    ax.set_xlabel("Herfindahl-Hirschman Index (HHI)")
    ax.legend(loc="lower right")
    plt.tight_layout()
    savefig("15_sector_hhi")

    df.to_csv(PROCESSED_DIR / "sector_hhi.csv", index=False)
    print(f"\n  Saved: data/processed/sector_hhi.csv")
    return df


# ════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 65)
    print("  advanced_analytics.py — Day 6")
    print("=" * 65)

    nav, fund, perf, tx, hold, scorecard = load_data()

    var_df      = task1_var_cvar(nav, fund)
    task2_rolling_sharpe(nav, fund, scorecard)
    cohort_df   = task3_cohort_analysis(tx, fund)
    cont_df     = task4_sip_continuity(tx)
    hhi_df      = task6_sector_hhi(hold, fund)

    print(f"\n{'='*65}")
    print(f"  Day 6 complete! All deliverables saved:")
    print(f"    data/processed/var_cvar_report.csv")
    print(f"    data/processed/cohort_analysis.csv")
    print(f"    data/processed/sip_continuity.csv")
    print(f"    data/processed/sector_hhi.csv")
    print(f"    reports/charts/13_rolling_sharpe.png")
    print(f"    reports/charts/14_var_comparison.png")
    print(f"    reports/charts/15_sector_hhi.png")
    print(f"    reports/charts/16_sip_continuity.png")
    print(f"\n  Next: python3 recommender.py")
    print(f"  Then: python3 create_advanced_notebook.py")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()