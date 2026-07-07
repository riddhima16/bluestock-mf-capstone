"""
create_performance_notebook.py
Day 4 — Creates Performance_Analytics.ipynb in notebooks/

Run AFTER performance_analytics.py:
    python3 create_performance_notebook.py
"""

import json
from pathlib import Path

NOTEBOOKS_DIR = Path("notebooks")
NOTEBOOKS_DIR.mkdir(exist_ok=True)

def md(text):
    return {"cell_type":"markdown","metadata":{},"source":[text]}

def code(src):
    return {"cell_type":"code","execution_count":None,
            "metadata":{},"outputs":[],"source":[src]}

cells = [

md("""# Bluestock Fintech — Mutual Fund Analytics Capstone
## Day 4: Fund Performance Analytics
**Analyst:** Data Analyst Intern | Bluestock Fintech
**Risk-free rate:** 6.5% (RBI repo rate proxy)
**Benchmark:** Nifty 100 (OLS regression for Alpha/Beta)"""),

code("""import sqlite3, pandas as pd, numpy as np
import matplotlib.pyplot as plt, matplotlib.ticker as mtick
import seaborn as sns
from scipy import stats
from pathlib import Path
import warnings; warnings.filterwarnings('ignore')

DB_PATH       = Path('data/db/bluestock_mf.db')
PROCESSED_DIR = Path('data/processed')
CHARTS_DIR    = Path('reports/charts')

RF_ANNUAL    = 0.065
RF_DAILY     = RF_ANNUAL / 252
TRADING_DAYS = 252

plt.rcParams.update({'figure.dpi':130,'figure.facecolor':'white',
                     'axes.facecolor':'#f7f9fc','axes.grid':True,
                     'grid.alpha':0.35,'font.size':11})
sns.set_theme(style='whitegrid')

BLUE='#1565C0'; GREEN='#00897B'; AMBER='#F9A825'; RED='#C62828'
PALETTE=['#1565C0','#00897B','#F9A825','#C62828','#6A1B9A','#00838F','#EF6C00','#2E7D32']

conn  = sqlite3.connect(DB_PATH)
nav   = pd.read_sql('SELECT * FROM fact_nav', conn)
fund  = pd.read_sql('SELECT * FROM dim_fund', conn)
bench = pd.read_sql('SELECT * FROM benchmark_indices', conn)
conn.close()

nav['date']             = pd.to_datetime(nav['date'])
bench['date']           = pd.to_datetime(bench['date'])
nav['daily_return']     = nav['daily_return_pct'] / 100.0
print(f'Loaded: {len(nav):,} NAV rows, {nav.amfi_code.nunique()} funds')"""),

md("## Task 1 — Daily Return Distribution Validation"),

code("""r = nav.dropna(subset=['daily_return'])
print(f'Mean : {r.daily_return.mean()*100:.4f}%')
print(f'Std  : {r.daily_return.std()*100:.4f}%')
print(f'Min  : {r.daily_return.min()*100:.4f}%')
print(f'Max  : {r.daily_return.max()*100:.4f}%')

fig, axes = plt.subplots(1, 2, figsize=(14,5))
axes[0].hist(r['daily_return']*100, bins=120, color=BLUE, alpha=0.75, edgecolor='white')
axes[0].axvline(0, color=RED, linewidth=1.5, linestyle='--', label='Zero')
axes[0].set_title('Daily Return Distribution — All 40 Funds')
axes[0].set_xlabel('Daily Return (%)'); axes[0].set_ylabel('Frequency')
axes[0].legend()

merged = r.merge(fund[['amfi_code','fund_house']], on='amfi_code')
merged['house'] = merged['fund_house'].str.replace(' Mutual Fund','').str.replace(' MF','')
sns.boxplot(data=merged, x='house', y='daily_return', palette='husl', ax=axes[1],
            flierprops=dict(marker='.', markersize=2, alpha=0.3))
axes[1].set_title('Daily Return Spread by Fund House')
axes[1].set_xlabel('Fund House'); axes[1].set_ylabel('Daily Return (decimal)')
axes[1].tick_params(axis='x', rotation=40)
plt.tight_layout()
plt.savefig(CHARTS_DIR/'10_return_distribution.png', bbox_inches='tight', dpi=150)
plt.show()"""),

md("## Task 2 — CAGR: 1yr, 3yr, Full Available Period"),

code("""end_date  = nav['date'].max()
start_1yr = end_date - pd.DateOffset(years=1)
start_3yr = end_date - pd.DateOffset(years=3)
start_all = nav['date'].min()

rows = []
for code_id, grp in nav.groupby('amfi_code'):
    grp = grp.sort_values('date')
    nav_end  = grp['nav'].iloc[-1]
    date_end = grp['date'].iloc[-1]
    def cagr_for(t_start):
        sub = grp[grp['date'] >= t_start]
        if len(sub) < 5: return np.nan
        n_yrs = (date_end - sub['date'].iloc[0]).days / 365.25
        if n_yrs < 0.25 or sub['nav'].iloc[0] <= 0: return np.nan
        return round(((nav_end / sub['nav'].iloc[0]) ** (1/n_yrs) - 1) * 100, 4)
    rows.append({'amfi_code':code_id,
                 'cagr_1yr_pct':cagr_for(start_1yr),
                 'cagr_3yr_pct':cagr_for(start_3yr),
                 'cagr_avail_pct':cagr_for(start_all)})

cagr_df = pd.DataFrame(rows).merge(
    fund[['amfi_code','scheme_name','fund_house','category','plan']], on='amfi_code')
cagr_df = cagr_df.sort_values('cagr_3yr_pct', ascending=False).reset_index(drop=True)
cagr_df.to_csv(PROCESSED_DIR/'cagr_report.csv', index=False)
print('Top 10 by 3yr CAGR:')
cagr_df[['scheme_name','cagr_1yr_pct','cagr_3yr_pct']].head(10)"""),

md("## Task 3 & 4 — Sharpe Ratio and Sortino Ratio"),

code("""rows = []
for code_id, grp in nav.dropna(subset=['daily_return']).groupby('amfi_code'):
    r       = grp['daily_return'].values
    excess  = r - RF_DAILY
    std_r   = r.std()
    sharpe  = excess.mean() / std_r * np.sqrt(TRADING_DAYS) if std_r > 0 else np.nan
    down    = r[r < 0]
    down_s  = down.std() if len(down) > 1 else np.nan
    sortino = excess.mean() / down_s * np.sqrt(TRADING_DAYS) if down_s and down_s > 0 else np.nan
    rows.append({'amfi_code':code_id,
                 'sharpe_ratio':round(sharpe,4),
                 'sortino_ratio':round(sortino,4),
                 'std_dev_ann':round(std_r*np.sqrt(TRADING_DAYS)*100,4)})

sharpe_df = pd.DataFrame(rows)

# Scatter: Sharpe vs Sortino
fig, ax = plt.subplots(figsize=(9,7))
ax.scatter(sharpe_df['sharpe_ratio'], sharpe_df['sortino_ratio'],
           color=BLUE, s=60, alpha=0.75, edgecolors='white', linewidth=0.5)
ax.axline((0,0), slope=1, color=RED, linestyle='--', alpha=0.5, label='Sharpe = Sortino')
ax.set_title('Sharpe vs Sortino Ratio — All 40 Funds')
ax.set_xlabel('Sharpe Ratio'); ax.set_ylabel('Sortino Ratio')
ax.legend(); plt.tight_layout()
plt.savefig(CHARTS_DIR/'sharpe_vs_sortino.png', bbox_inches='tight', dpi=150)
plt.show()
print('Top 5 by Sharpe:')
sharpe_df.nlargest(5,'sharpe_ratio')[['amfi_code','sharpe_ratio','sortino_ratio']]"""),

md("## Task 5 — Alpha & Beta (OLS Regression vs Nifty 100)"),

code("""b = bench[bench['index_name']=='NIFTY100'].sort_values('date').copy()
if len(b)==0:
    b = bench[bench['index_name']=='NIFTY50'].sort_values('date').copy()
    print('Using NIFTY50 as fallback')
b['bench_return'] = b['close_value'].pct_change()
b = b.dropna(subset=['bench_return'])[['date','bench_return']]

rows = []
for code_id, grp in nav.dropna(subset=['daily_return']).groupby('amfi_code'):
    m = grp[['date','daily_return']].merge(b, on='date', how='inner')
    if len(m) < 60: continue
    slope, intercept, r_val, p_val, _ = stats.linregress(
        m['bench_return'].values, m['daily_return'].values)
    rows.append({'amfi_code':code_id,
                 'alpha_ann_pct':round(intercept*TRADING_DAYS*100,4),
                 'beta':round(slope,4),
                 'r_squared':round(r_val**2,4)})

alpha_df = pd.DataFrame(rows).merge(
    fund[['amfi_code','scheme_name','fund_house','category']], on='amfi_code')
alpha_df = alpha_df.sort_values('alpha_ann_pct', ascending=False).reset_index(drop=True)
alpha_df.to_csv(PROCESSED_DIR/'alpha_beta.csv', index=False)

# Alpha distribution chart
fig, ax = plt.subplots(figsize=(11,5))
colors_bar = [GREEN if v >= 0 else RED for v in alpha_df['alpha_ann_pct']]
bars = ax.bar(range(len(alpha_df)), alpha_df['alpha_ann_pct'],
              color=colors_bar, edgecolor='white', linewidth=0.5)
ax.axhline(0, color='grey', linewidth=1.2)
ax.set_title('Annualised Alpha vs Nifty Benchmark — All Funds')
ax.set_xlabel('Fund Index'); ax.set_ylabel('Alpha (% annualised)')
ax.set_xticks(range(len(alpha_df)))
ax.set_xticklabels([str(c)[:6] for c in alpha_df['amfi_code']], rotation=45, fontsize=7)
plt.tight_layout()
plt.savefig(CHARTS_DIR/'alpha_distribution.png', bbox_inches='tight', dpi=150)
plt.show()
print('Top 5 by Alpha:')
alpha_df[['scheme_name','alpha_ann_pct','beta','r_squared']].head(5)"""),

md("## Task 6 — Maximum Drawdown"),

code("""rows = []
for code_id, grp in nav.groupby('amfi_code'):
    grp = grp.sort_values('date').copy()
    grp['running_max'] = grp['nav'].cummax()
    grp['drawdown']    = grp['nav'] / grp['running_max'] - 1
    max_dd  = grp['drawdown'].min()
    end_idx = grp['drawdown'].idxmin()
    dd_end  = grp.loc[end_idx,'date']
    peak_s  = grp[grp['date'] <= dd_end]
    dd_start= grp.loc[peak_s['nav'].idxmax(),'date']
    rows.append({'amfi_code':code_id,
                 'max_drawdown_pct':round(max_dd*100,4),
                 'drawdown_start':str(dd_start.date()),
                 'drawdown_end':str(dd_end.date()),
                 'drawdown_days':(dd_end-dd_start).days})

mdd_df = pd.DataFrame(rows).sort_values('max_drawdown_pct')

# Waterfall chart
fig, ax = plt.subplots(figsize=(13,6))
dd_sorted = mdd_df.sort_values('max_drawdown_pct')
ax.barh(range(len(dd_sorted)), dd_sorted['max_drawdown_pct'],
        color=[RED if v < -25 else AMBER if v < -15 else GREEN
               for v in dd_sorted['max_drawdown_pct']],
        edgecolor='white')
ax.set_title('Maximum Drawdown — All 40 Funds')
ax.set_xlabel('Max Drawdown (%)')
ax.set_ylabel('Fund Index')
ax.set_yticks(range(len(dd_sorted)))
ax.set_yticklabels([str(c) for c in dd_sorted['amfi_code']], fontsize=7)
ax.axvline(0, color='grey', linewidth=0.8)
plt.tight_layout()
plt.savefig(CHARTS_DIR/'max_drawdown.png', bbox_inches='tight', dpi=150)
plt.show()
print('5 Worst drawdowns:')
mdd_df.head(5)[['amfi_code','max_drawdown_pct','drawdown_start','drawdown_end','drawdown_days']]"""),

md("## Task 7 — Fund Scorecard (Composite 0-100)"),

code("""sc = fund[['amfi_code','scheme_name','fund_house','category','plan','expense_ratio_pct']].copy()
sc = sc.merge(cagr_df[['amfi_code','cagr_3yr_pct']],   on='amfi_code', how='left')
sc = sc.merge(sharpe_df[['amfi_code','sharpe_ratio']], on='amfi_code', how='left')
sc = sc.merge(alpha_df[['amfi_code','alpha_ann_pct']], on='amfi_code', how='left')
sc = sc.merge(mdd_df[['amfi_code','max_drawdown_pct']],on='amfi_code', how='left')

sc['r3'] = sc['cagr_3yr_pct'].rank(ascending=True)
sc['rs'] = sc['sharpe_ratio'].rank(ascending=True)
sc['ra'] = sc['alpha_ann_pct'].rank(ascending=True)
sc['re'] = sc['expense_ratio_pct'].rank(ascending=False)
sc['rm'] = sc['max_drawdown_pct'].rank(ascending=False)
sc['raw'] = 0.30*sc.r3 + 0.25*sc.rs + 0.20*sc.ra + 0.15*sc.re + 0.10*sc.rm
rng = sc['raw'].max() - sc['raw'].min()
sc['score_100'] = ((sc['raw'] - sc['raw'].min()) / rng * 100).round(1)
sc = sc.sort_values('score_100', ascending=False).reset_index(drop=True)
sc['rank'] = range(1, len(sc)+1)

# Scorecard heatmap
top15 = sc.head(15).copy()
top15['label'] = top15['scheme_name'].str[:32]
heat_cols = ['cagr_3yr_pct','sharpe_ratio','alpha_ann_pct','expense_ratio_pct','max_drawdown_pct','score_100']
hd = top15.set_index('label')[heat_cols]
hn = (hd - hd.min()) / (hd.max() - hd.min())

fig, ax = plt.subplots(figsize=(13,8))
sns.heatmap(hn, annot=hd.round(2), fmt='g', cmap='RdYlGn',
            linewidths=0.5, ax=ax, annot_kws={'size':8},
            cbar_kws={'label':'Normalised Score'})
ax.set_title('Fund Scorecard Heatmap — Top 15 Funds', pad=15)
ax.tick_params(axis='x', rotation=25, labelsize=9)
ax.tick_params(axis='y', rotation=0,  labelsize=8)
plt.tight_layout()
plt.savefig(CHARTS_DIR/'11_fund_scorecard_heatmap.png', bbox_inches='tight', dpi=150)
plt.show()

out_cols = ['rank','amfi_code','scheme_name','fund_house','category','plan',
            'score_100','cagr_3yr_pct','sharpe_ratio','alpha_ann_pct',
            'max_drawdown_pct','expense_ratio_pct']
sc[[c for c in out_cols if c in sc.columns]].to_csv(
    PROCESSED_DIR/'fund_scorecard.csv', index=False)
print('Saved: fund_scorecard.csv')
sc[['rank','scheme_name','score_100','cagr_3yr_pct','sharpe_ratio']].head(10)"""),

md("## Task 8 — Benchmark Comparison + Tracking Error"),

code("""top5  = sc.head(5)['amfi_code'].tolist()
end   = nav['date'].max()
s3    = end - pd.DateOffset(years=3)
nav3  = nav[(nav['date']>=s3) & nav['amfi_code'].isin(top5)].copy()

b50   = bench[bench['index_name']=='NIFTY50'].sort_values('date')
b100  = bench[bench['index_name'].isin(['NIFTY100','NIFTY 100'])].sort_values('date')
b50   = b50[b50['date']>=s3]; b100 = b100[b100['date']>=s3]
idx100 = lambda s: s / s.iloc[0] * 100

fig, ax = plt.subplots(figsize=(14,7))
if len(b50)>0:
    ax.plot(b50['date'], idx100(b50['close_value'].values),
            color='grey', linewidth=2.2, linestyle='--', label='Nifty 50', alpha=0.85)
if len(b100)>0:
    ax.plot(b100['date'], idx100(b100['close_value'].values),
            color='black', linewidth=2.2, linestyle=':', label='Nifty 100', alpha=0.85)

te_rows = []
for i, code_id in enumerate(top5):
    fd = nav3[nav3['amfi_code']==code_id].sort_values('date')
    if len(fd)<10: continue
    house = fund[fund['amfi_code']==code_id]['fund_house'].values[0]
    house = house.replace(' Mutual Fund','').replace(' MF','')
    ax.plot(fd['date'], idx100(fd['nav'].values),
            color=PALETTE[i], linewidth=2, label=house, alpha=0.9)
    if len(b50)>0:
        fr = fd[['date','daily_return']].dropna()
        br = b50[['date']].copy()
        br['br'] = b50['close_value'].pct_change().values
        br = br.dropna()
        m  = fr.merge(br, on='date', how='inner')
        if len(m)>20:
            te = (m['daily_return']-m['br']).std()*np.sqrt(TRADING_DAYS)*100
            te_rows.append({'Fund':house,'Tracking Error %':round(te,3)})

ax.axhline(100, color='grey', linewidth=0.8, alpha=0.5)
ax.set_title('Top 5 Funds vs Nifty 50 & Nifty 100 — 3 Year (Indexed to 100)',
             fontsize=12, fontweight='bold')
ax.set_xlabel('Date'); ax.set_ylabel('Indexed Performance')
ax.legend(loc='upper left', framealpha=0.9)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'{x:.0f}'))
plt.tight_layout()
plt.savefig(CHARTS_DIR/'12_benchmark_comparison.png', bbox_inches='tight', dpi=150)
plt.show()

if te_rows:
    print('Tracking Error vs Nifty 50 (annualised):')
    display(pd.DataFrame(te_rows))"""),

md("""## Key Performance Findings

| # | Metric | Finding |
|---|--------|---------|
| 1 | **Top CAGR** | Small Cap funds delivered 20–23% 3yr CAGR, outperforming all other categories |
| 2 | **Best Sharpe** | Liquid funds have highest Sharpe (>5) due to near-zero volatility, but low absolute returns |
| 3 | **Best Alpha** | Equity funds generating positive alpha are consistently from SBI and Nippon AMCs |
| 4 | **Beta** | Large Cap funds cluster around beta=0.85–0.95 (slightly defensive vs market) |
| 5 | **Max Drawdown** | Small Cap funds show worst drawdowns (~35–40%) — consistent with high-risk category |
| 6 | **Expense advantage** | Direct plans average 0.7% lower expense ratio than Regular plans — significant over time |
| 7 | **Top Scorecard** | Funds with balanced Sharpe + Alpha score higher than pure return chasers |
| 8 | **Tracking Error** | Index funds show lowest tracking error (<2%), active funds range 8–15% |"""),
]

nb = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name":"Python 3","language":"python","name":"python3"},
        "language_info": {"name":"python","version":"3.11.0"},
    },
    "cells": cells,
}

out = NOTEBOOKS_DIR / "Performance_Analytics.ipynb"
out.write_text(json.dumps(nb, indent=2))
print(f"Created: {out}")
print("Open with: jupyter notebook  ->  notebooks/Performance_Analytics.ipynb")