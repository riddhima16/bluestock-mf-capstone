"""
performance_analytics.py  —  Day 4: Fund Performance Analytics

Computes from scratch using NAV history in bluestock_mf.db:
  Task 1 : Daily returns validation + distribution chart
  Task 2 : CAGR (1yr, 3yr, available period)
  Task 3 : Sharpe Ratio  (Rf = 6.5%)
  Task 4 : Sortino Ratio (downside std only)
  Task 5 : Alpha & Beta  (OLS vs Nifty 100)
  Task 6 : Maximum Drawdown
  Task 7 : Fund Scorecard 0-100
  Task 8 : Benchmark comparison chart + tracking error

Outputs (all saved automatically):
  data/processed/returns_computed.csv
  data/processed/cagr_report.csv
  data/processed/alpha_beta.csv
  data/processed/fund_scorecard.csv
  reports/charts/10_return_distribution.png
  reports/charts/11_fund_scorecard_heatmap.png
  reports/charts/12_benchmark_comparison.png

Run:  python3 performance_analytics.py
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
from scipy import stats
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
RF_ANNUAL    = 0.065          # RBI repo rate proxy
RF_DAILY     = RF_ANNUAL / 252
TRADING_DAYS = 252

# ── matplotlib style ──────────────────────────────────────────────────────
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


def savefig(name: str):
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
    nav   = pd.read_sql("SELECT * FROM fact_nav",           conn)
    fund  = pd.read_sql("SELECT * FROM dim_fund",           conn)
    bench = pd.read_sql("SELECT * FROM benchmark_indices",  conn)
    conn.close()

    nav["date"]   = pd.to_datetime(nav["date"])
    bench["date"] = pd.to_datetime(bench["date"])

    # daily_return_pct stored as %; convert to decimal for all math
    nav["daily_return"] = nav["daily_return_pct"] / 100.0

    print(f"  NAV rows   : {len(nav):,}")
    print(f"  Funds      : {nav['amfi_code'].nunique()}")
    print(f"  Date range : {nav['date'].min().date()} to {nav['date'].max().date()}")
    return nav, fund, bench


# ════════════════════════════════════════════════════════════════════════
# TASK 1 — Daily Return Validation
# ════════════════════════════════════════════════════════════════════════

def task1_validate_returns(nav, fund):
    print("\n>>> TASK 1: Daily return distribution validation")
    r = nav.dropna(subset=["daily_return"])

    print(f"  Mean  : {r['daily_return'].mean()*100:.4f}%")
    print(f"  Std   : {r['daily_return'].std()*100:.4f}%")
    print(f"  Min   : {r['daily_return'].min()*100:.4f}%")
    print(f"  Max   : {r['daily_return'].max()*100:.4f}%")

    extreme = r[r["daily_return"].abs() > 0.15]
    if len(extreme) > 0:
        print(f"  WARNING: {len(extreme)} extreme returns >15% found")
    else:
        print(f"  Extreme check (>15%/day): none found  ✓")

    # Chart — histogram + box plot side by side
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].hist(r["daily_return"] * 100, bins=120,
                 color=BLUE, alpha=0.75, edgecolor="white")
    axes[0].axvline(0, color=RED, linewidth=1.5, linestyle="--", label="Zero")
    axes[0].set_title("Daily Return Distribution — All 40 Funds")
    axes[0].set_xlabel("Daily Return (%)")
    axes[0].set_ylabel("Frequency")
    axes[0].legend()

    merged = r.merge(fund[["amfi_code","fund_house"]], on="amfi_code")
    merged["house"] = (merged["fund_house"]
                       .str.replace(" Mutual Fund","",regex=False)
                       .str.replace(" MF","",regex=False))
    sns.boxplot(data=merged, x="house", y="daily_return",
                palette="husl", ax=axes[1],
                flierprops=dict(marker=".", markersize=2, alpha=0.3))
    axes[1].set_title("Daily Return Spread by Fund House")
    axes[1].set_xlabel("Fund House")
    axes[1].set_ylabel("Daily Return (decimal)")
    axes[1].tick_params(axis="x", rotation=40)

    plt.tight_layout()
    savefig("10_return_distribution")

    r.to_csv(PROCESSED_DIR / "returns_computed.csv", index=False)
    print(f"  Saved: data/processed/returns_computed.csv")
    return r


# ════════════════════════════════════════════════════════════════════════
# TASK 2 — CAGR
# ════════════════════════════════════════════════════════════════════════

def task2_cagr(nav, fund):
    print("\n>>> TASK 2: CAGR (1yr, 3yr, full available period)")
    end_date   = nav["date"].max()
    start_1yr  = end_date - pd.DateOffset(years=1)
    start_3yr  = end_date - pd.DateOffset(years=3)
    start_all  = nav["date"].min()

    rows = []
    for code, grp in nav.groupby("amfi_code"):
        grp      = grp.sort_values("date")
        nav_end  = grp["nav"].iloc[-1]
        date_end = grp["date"].iloc[-1]

        def cagr_for(target_start):
            sub = grp[grp["date"] >= target_start]
            if len(sub) < 5:
                return np.nan
            n_start = sub["nav"].iloc[0]
            n_end   = nav_end
            n_yrs   = (date_end - sub["date"].iloc[0]).days / 365.25
            if n_yrs < 0.25 or n_start <= 0:
                return np.nan
            return round(((n_end / n_start) ** (1 / n_yrs) - 1) * 100, 4)

        rows.append({
            "amfi_code":      code,
            "cagr_1yr_pct":   cagr_for(start_1yr),
            "cagr_3yr_pct":   cagr_for(start_3yr),
            "cagr_avail_pct": cagr_for(start_all),
        })

    df = pd.DataFrame(rows)
    df = df.merge(fund[["amfi_code","scheme_name","fund_house",
                         "category","sub_category","plan"]], on="amfi_code")
    df = df.sort_values("cagr_3yr_pct", ascending=False).reset_index(drop=True)

    print(f"\n  Top 10 by 3yr CAGR:")
    print(f"  {'Scheme':<44} {'1yr':>7} {'3yr':>7}")
    print(f"  {'-'*60}")
    for _, row in df.head(10).iterrows():
        nm = str(row["scheme_name"])[:42]
        print(f"  {nm:<44} {row['cagr_1yr_pct']:>6.2f}% {row['cagr_3yr_pct']:>6.2f}%")

    df.to_csv(PROCESSED_DIR / "cagr_report.csv", index=False)
    print(f"\n  Saved: data/processed/cagr_report.csv")
    return df


# ════════════════════════════════════════════════════════════════════════
# TASK 3 + 4 — Sharpe and Sortino
# ════════════════════════════════════════════════════════════════════════

def task3_4_sharpe_sortino(nav):
    print("\n>>> TASK 3 & 4: Sharpe and Sortino ratios")
    rows = []
    for code, grp in nav.dropna(subset=["daily_return"]).groupby("amfi_code"):
        r = grp["daily_return"].values
        excess    = r - RF_DAILY
        mean_exc  = excess.mean()
        std_r     = r.std()
        sharpe    = (mean_exc / std_r * np.sqrt(TRADING_DAYS)
                     if std_r > 0 else np.nan)
        down      = r[r < 0]
        down_std  = down.std() if len(down) > 1 else np.nan
        sortino   = (mean_exc / down_std * np.sqrt(TRADING_DAYS)
                     if down_std and down_std > 0 else np.nan)
        rows.append({
            "amfi_code":     code,
            "sharpe_ratio":  round(sharpe,  4),
            "sortino_ratio": round(sortino, 4),
            "std_dev_ann":   round(std_r * np.sqrt(TRADING_DAYS) * 100, 4),
        })

    df = pd.DataFrame(rows)
    print(f"\n  Top 5 by Sharpe:")
    for _, row in df.nlargest(5,"sharpe_ratio").iterrows():
        print(f"  code={row['amfi_code']}  "
              f"Sharpe={row['sharpe_ratio']:.4f}  "
              f"Sortino={row['sortino_ratio']:.4f}")
    return df


# ════════════════════════════════════════════════════════════════════════
# TASK 5 — Alpha & Beta (OLS vs Nifty 100)
# ════════════════════════════════════════════════════════════════════════

def task5_alpha_beta(nav, bench, fund):
    print("\n>>> TASK 5: Alpha & Beta (OLS regression vs Nifty 100)")

    # Try NIFTY100 first, fallback to NIFTY50
    b = bench[bench["index_name"] == "NIFTY100"].sort_values("date").copy()
    if len(b) == 0:
        b = bench[bench["index_name"] == "NIFTY50"].sort_values("date").copy()
        print("  Using NIFTY50 as benchmark fallback")

    b["bench_return"] = b["close_value"].pct_change()
    b = b.dropna(subset=["bench_return"])[["date","bench_return"]]

    rows = []
    for code, grp in nav.dropna(subset=["daily_return"]).groupby("amfi_code"):
        merged = grp[["date","daily_return"]].merge(b, on="date", how="inner")
        if len(merged) < 60:
            continue
        slope, intercept, r_val, p_val, _ = stats.linregress(
            merged["bench_return"].values,
            merged["daily_return"].values
        )
        rows.append({
            "amfi_code":     code,
            "alpha_ann_pct": round(intercept * TRADING_DAYS * 100, 4),
            "beta":          round(slope, 4),
            "r_squared":     round(r_val**2, 4),
            "p_value":       round(p_val, 6),
            "obs":           len(merged),
        })

    df = pd.DataFrame(rows)
    df = df.merge(fund[["amfi_code","scheme_name","fund_house","category"]],
                  on="amfi_code")
    df = df.sort_values("alpha_ann_pct", ascending=False).reset_index(drop=True)

    print(f"\n  Top 5 by Alpha (annualised %):")
    print(f"  {'Scheme':<44} {'Alpha%':>8} {'Beta':>6} {'R²':>6}")
    print(f"  {'-'*68}")
    for _, row in df.head(5).iterrows():
        nm = str(row["scheme_name"])[:42]
        print(f"  {nm:<44} {row['alpha_ann_pct']:>7.2f}%"
              f" {row['beta']:>6.3f} {row['r_squared']:>6.3f}")

    df.to_csv(PROCESSED_DIR / "alpha_beta.csv", index=False)
    print(f"\n  Saved: data/processed/alpha_beta.csv")
    return df


# ════════════════════════════════════════════════════════════════════════
# TASK 6 — Maximum Drawdown
# ════════════════════════════════════════════════════════════════════════

def task6_max_drawdown(nav):
    print("\n>>> TASK 6: Maximum Drawdown")
    rows = []
    for code, grp in nav.groupby("amfi_code"):
        grp = grp.sort_values("date").copy()
        grp["running_max"] = grp["nav"].cummax()
        grp["drawdown"]    = grp["nav"] / grp["running_max"] - 1
        max_dd     = grp["drawdown"].min()
        end_idx    = grp["drawdown"].idxmin()
        dd_end     = grp.loc[end_idx, "date"]
        peak_sub   = grp[grp["date"] <= dd_end]
        start_idx  = peak_sub["nav"].idxmax()
        dd_start   = grp.loc[start_idx, "date"]
        rows.append({
            "amfi_code":        code,
            "max_drawdown_pct": round(max_dd * 100, 4),
            "drawdown_start":   str(dd_start.date()),
            "drawdown_end":     str(dd_end.date()),
            "drawdown_days":    (dd_end - dd_start).days,
        })

    df = pd.DataFrame(rows).sort_values("max_drawdown_pct")
    print(f"\n  5 Worst drawdowns:")
    print(f"  {'code':>10} {'Max DD%':>9} {'Start':>12} {'End':>12} {'Days':>6}")
    print(f"  {'-'*54}")
    for _, row in df.head(5).iterrows():
        print(f"  {row['amfi_code']:>10} {row['max_drawdown_pct']:>8.2f}%"
              f" {row['drawdown_start']:>12} {row['drawdown_end']:>12}"
              f" {row['drawdown_days']:>6}")
    return df


# ════════════════════════════════════════════════════════════════════════
# TASK 7 — Fund Scorecard
# ════════════════════════════════════════════════════════════════════════

def task7_scorecard(cagr_df, sharpe_df, alpha_df, mdd_df, fund):
    print("\n>>> TASK 7: Fund Scorecard (composite 0-100)")

    sc = fund[["amfi_code","scheme_name","fund_house",
               "category","sub_category","plan","expense_ratio_pct"]].copy()
    sc = sc.merge(cagr_df[["amfi_code","cagr_3yr_pct"]],   on="amfi_code", how="left")
    sc = sc.merge(sharpe_df[["amfi_code","sharpe_ratio"]],  on="amfi_code", how="left")
    sc = sc.merge(alpha_df[["amfi_code","alpha_ann_pct"]],  on="amfi_code", how="left")
    sc = sc.merge(mdd_df[["amfi_code","max_drawdown_pct"]], on="amfi_code", how="left")

    # Rank: higher = better (inverse for cost/drawdown)
    sc["r3"]  = sc["cagr_3yr_pct"].rank(ascending=True)
    sc["rs"]  = sc["sharpe_ratio"].rank(ascending=True)
    sc["ra"]  = sc["alpha_ann_pct"].rank(ascending=True)
    sc["re"]  = sc["expense_ratio_pct"].rank(ascending=False)  # lower cost = better
    sc["rm"]  = sc["max_drawdown_pct"].rank(ascending=False)   # less negative = better

    sc["raw"] = 0.30*sc["r3"] + 0.25*sc["rs"] + 0.20*sc["ra"] + 0.15*sc["re"] + 0.10*sc["rm"]
    rng = sc["raw"].max() - sc["raw"].min()
    sc["score_100"] = ((sc["raw"] - sc["raw"].min()) / rng * 100).round(1)
    sc = sc.sort_values("score_100", ascending=False).reset_index(drop=True)
    sc["rank"] = range(1, len(sc)+1)

    print(f"\n  Top 10 composite scorecard:")
    print(f"  {'#':>3} {'Scheme':<40} {'Score':>6} {'3yr%':>6} {'Sharpe':>7}")
    print(f"  {'-'*67}")
    for _, row in sc.head(10).iterrows():
        nm = str(row["scheme_name"])[:38]
        print(f"  {int(row['rank']):>3} {nm:<40}"
              f" {row['score_100']:>6.1f} {row['cagr_3yr_pct']:>6.2f}"
              f" {row['sharpe_ratio']:>7.3f}")

    # Scorecard heatmap — top 15
    top15 = sc.head(15).copy()
    top15["label"] = top15["scheme_name"].str[:32]
    heat_cols  = ["cagr_3yr_pct","sharpe_ratio","alpha_ann_pct",
                  "expense_ratio_pct","max_drawdown_pct","score_100"]
    heat_data  = top15.set_index("label")[heat_cols]
    heat_norm  = (heat_data - heat_data.min()) / (heat_data.max() - heat_data.min())

    fig, ax = plt.subplots(figsize=(13, 8))
    sns.heatmap(heat_norm, annot=heat_data.round(2), fmt="g",
                cmap="RdYlGn", linewidths=0.5, ax=ax,
                annot_kws={"size": 8},
                cbar_kws={"label": "Normalised Score"})
    ax.set_title("Fund Scorecard Heatmap — Top 15 Funds", pad=15)
    ax.tick_params(axis="x", rotation=25, labelsize=9)
    ax.tick_params(axis="y", rotation=0,  labelsize=8)
    plt.tight_layout()
    savefig("11_fund_scorecard_heatmap")

    out_cols = ["rank","amfi_code","scheme_name","fund_house","category",
                "plan","score_100","cagr_3yr_pct","sharpe_ratio",
                "alpha_ann_pct","max_drawdown_pct","expense_ratio_pct"]
    sc[[c for c in out_cols if c in sc.columns]].to_csv(
        PROCESSED_DIR / "fund_scorecard.csv", index=False)
    print(f"\n  Saved: data/processed/fund_scorecard.csv")
    return sc


# ════════════════════════════════════════════════════════════════════════
# TASK 8 — Benchmark Comparison + Tracking Error
# ════════════════════════════════════════════════════════════════════════

def task8_benchmark(nav, bench, fund, scorecard):
    print("\n>>> TASK 8: Benchmark comparison chart + tracking error")

    top5 = scorecard.head(5)["amfi_code"].tolist()
    end  = nav["date"].max()
    s3   = end - pd.DateOffset(years=3)

    nav3 = nav[(nav["date"] >= s3) & nav["amfi_code"].isin(top5)].copy()

    b50  = (bench[bench["index_name"] == "NIFTY50"]
            .sort_values("date").copy())
    b100 = (bench[bench["index_name"].isin(["NIFTY100","NIFTY 100"])]
            .sort_values("date").copy())
    b50  = b50[b50["date"] >= s3]
    b100 = b100[b100["date"] >= s3]

    def idx100(s):
        return s / s.iloc[0] * 100

    fig, ax = plt.subplots(figsize=(14, 7))

    if len(b50) > 0:
        ax.plot(b50["date"], idx100(b50["close_value"].values),
                color="grey",  linewidth=2.2, linestyle="--",
                label="Nifty 50", alpha=0.85, zorder=2)
    if len(b100) > 0:
        ax.plot(b100["date"], idx100(b100["close_value"].values),
                color="black", linewidth=2.2, linestyle=":",
                label="Nifty 100", alpha=0.85, zorder=2)

    tracking_errors = []
    for i, code in enumerate(top5):
        fd = nav3[nav3["amfi_code"] == code].sort_values("date")
        if len(fd) < 10:
            continue
        house = (fund[fund["amfi_code"]==code]["fund_house"]
                 .values[0].replace(" Mutual Fund","").replace(" MF",""))
        ax.plot(fd["date"], idx100(fd["nav"].values),
                color=PALETTE[i], linewidth=2, label=house,
                alpha=0.9, zorder=3)

        # Tracking error vs Nifty 50
        if len(b50) > 0:
            fr = fd[["date","daily_return"]].dropna()
            br = b50[["date"]].copy()
            br["bench_r"] = b50["close_value"].pct_change().values
            br = br.dropna()
            m  = fr.merge(br, on="date", how="inner")
            if len(m) > 20:
                te = (m["daily_return"] - m["bench_r"]).std() * np.sqrt(TRADING_DAYS) * 100
                tracking_errors.append({"fund": house, "tracking_error_pct": round(te,3)})

    ax.axhline(100, color="grey", linewidth=0.8, alpha=0.5)
    ax.set_title("Top 5 Scored Funds vs Nifty 50 & Nifty 100 — 3 Year Performance\n"
                 "(Indexed to 100 at start date)",
                 fontsize=12, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Indexed Performance (Start = 100)")
    ax.legend(loc="upper left", framealpha=0.9)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f"{x:.0f}"))
    plt.tight_layout()
    savefig("12_benchmark_comparison")

    if tracking_errors:
        print(f"\n  Annualised Tracking Error vs Nifty 50:")
        for row in tracking_errors:
            print(f"    {row['fund']:<32} {row['tracking_error_pct']:.2f}%")


# ════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 65)
    print("  performance_analytics.py — Day 4")
    print("=" * 65)

    nav, fund, bench = load_data()
    returns_df = task1_validate_returns(nav, fund)
    cagr_df    = task2_cagr(nav, fund)
    sharpe_df  = task3_4_sharpe_sortino(nav)
    alpha_df   = task5_alpha_beta(nav, bench, fund)
    mdd_df     = task6_max_drawdown(nav)
    scorecard  = task7_scorecard(cagr_df, sharpe_df, alpha_df, mdd_df, fund)
    task8_benchmark(nav, bench, fund, scorecard)

    print(f"\n{'='*65}")
    print(f"  All Day 4 deliverables saved!")
    print(f"  CSVs   → data/processed/")
    print(f"  Charts → reports/charts/")
    print(f"\n  Next: python3 create_performance_notebook.py")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()