"""
fix_task8.py  —  Fixes the benchmark comparison chart (Task 8)

The original idx100 lambda passed .values (numpy array) then called .iloc[0]
which is pandas-only. This standalone script re-runs Task 8 correctly.

Run: python3 fix_task8.py
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

DB_PATH    = Path("data/db/bluestock_mf.db")
CHARTS_DIR = Path("reports/charts")
PROCESSED  = Path("data/processed")

TRADING_DAYS = 252
PALETTE = ["#1565C0","#00897B","#F9A825","#C62828","#6A1B9A","#00838F","#EF6C00","#2E7D32"]

plt.rcParams.update({"figure.dpi":150,"figure.facecolor":"white",
                     "axes.facecolor":"#f7f9fc","axes.grid":True,
                     "grid.alpha":0.35,"font.size":11})

# ── load ──────────────────────────────────────────────────────────────
conn  = sqlite3.connect(DB_PATH)
nav   = pd.read_sql("SELECT * FROM fact_nav", conn)
bench = pd.read_sql("SELECT * FROM benchmark_indices", conn)
fund  = pd.read_sql("SELECT * FROM dim_fund", conn)
conn.close()

nav["date"]           = pd.to_datetime(nav["date"])
bench["date"]         = pd.to_datetime(bench["date"])
nav["daily_return"]   = nav["daily_return_pct"] / 100.0

# ── check what benchmark index names we actually have ─────────────────
print("Benchmark index names in database:")
print(bench["index_name"].value_counts().to_string())
print(f"\nBench date range: {bench['date'].min().date()} to {bench['date'].max().date()}")
print(f"NAV  date range : {nav['date'].min().date()} to {nav['date'].max().date()}")

# ── load scorecard to get top 5 funds ────────────────────────────────
scorecard = pd.read_csv(PROCESSED / "fund_scorecard.csv")
top5      = scorecard.head(5)["amfi_code"].astype(int).tolist()
print(f"\nTop 5 scored funds: {top5}")

# ── 3-year window ─────────────────────────────────────────────────────
end_date = nav["date"].max()
start_3yr = end_date - pd.DateOffset(years=3)
nav3 = nav[(nav["date"] >= start_3yr) & nav["amfi_code"].isin(top5)].copy()

# ── get benchmark series — use whatever names exist ───────────────────
all_names = bench["index_name"].unique()
print(f"\nAvailable benchmark names: {all_names}")

# Pick Nifty 50 and Nifty 100 regardless of exact string
def get_bench(keywords):
    for name in all_names:
        if any(k.lower() in name.lower() for k in keywords):
            df = bench[bench["index_name"] == name].sort_values("date")
            return df[df["date"] >= start_3yr].copy()
    return pd.DataFrame()

b50  = get_bench(["nifty50","nifty 50","nifty_50","^nsei"])
b100 = get_bench(["nifty100","nifty 100","nifty_100"])

print(f"Nifty 50  rows in 3yr window : {len(b50)}")
print(f"Nifty 100 rows in 3yr window : {len(b100)}")

# ── FIX: index to 100 — works on both Series and numpy arrays ─────────
def idx100(series_or_arr):
    """Index a series/array to 100 at the first element."""
    if isinstance(series_or_arr, np.ndarray):
        return series_or_arr / series_or_arr[0] * 100
    else:
        return series_or_arr / series_or_arr.iloc[0] * 100

# ── build chart ───────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7))

if len(b50) > 0:
    b50_sorted = b50.sort_values("date")
    ax.plot(b50_sorted["date"], idx100(b50_sorted["close_value"].values),
            color="grey", linewidth=2.2, linestyle="--",
            label="Nifty 50", alpha=0.85, zorder=2)

if len(b100) > 0:
    b100_sorted = b100.sort_values("date")
    ax.plot(b100_sorted["date"], idx100(b100_sorted["close_value"].values),
            color="black", linewidth=2.2, linestyle=":",
            label="Nifty 100", alpha=0.85, zorder=2)

tracking_errors = []
for i, code in enumerate(top5):
    fd = nav3[nav3["amfi_code"] == code].sort_values("date")
    if len(fd) < 10:
        print(f"  Skipping code {code} — too few rows")
        continue

    house = (fund[fund["amfi_code"] == code]["fund_house"]
             .values[0]
             .replace(" Mutual Fund","")
             .replace(" MF",""))

    ax.plot(fd["date"], idx100(fd["nav"].values),
            color=PALETTE[i], linewidth=2.2,
            label=house, alpha=0.9, zorder=3)

    # Tracking error vs Nifty 50
    if len(b50) > 0:
        fr = fd[["date","daily_return"]].dropna().copy()
        b50s = b50.sort_values("date").copy()
        b50s["bench_r"] = b50s["close_value"].pct_change()
        b50s = b50s[["date","bench_r"]].dropna()
        m = fr.merge(b50s, on="date", how="inner")
        if len(m) > 20:
            te = (m["daily_return"] - m["bench_r"]).std() * np.sqrt(TRADING_DAYS) * 100
            tracking_errors.append({"Fund": house,
                                     "Tracking Error % (ann)": round(te, 3)})

ax.axhline(100, color="grey", linewidth=0.8, alpha=0.5)
ax.set_title("Top 5 Scored Funds vs Nifty 50 & Nifty 100 — 3 Year Performance\n"
             "(All series indexed to 100 at start date)",
             fontsize=12, fontweight="bold")
ax.set_xlabel("Date")
ax.set_ylabel("Indexed Performance (Start = 100)")
ax.legend(loc="upper left", framealpha=0.9)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:.0f}"))
plt.tight_layout()

out_path = CHARTS_DIR / "12_benchmark_comparison.png"
plt.savefig(out_path, bbox_inches="tight", dpi=150, facecolor="white")
plt.close()
print(f"\nSaved: {out_path}")

# ── tracking error table ──────────────────────────────────────────────
if tracking_errors:
    print("\nAnnualised Tracking Error vs Nifty 50:")
    te_df = pd.DataFrame(tracking_errors)
    print(te_df.to_string(index=False))
else:
    print("\nNo tracking error computed (no overlapping dates with benchmark)")

print("\nTask 8 complete!")
print("\nNow run: python3 create_performance_notebook.py")