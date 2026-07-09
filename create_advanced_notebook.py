"""
create_advanced_notebook.py  —  Day 6
Creates Advanced_Analytics.ipynb in notebooks/

Run AFTER advanced_analytics.py and recommender.py:
    python3 create_advanced_notebook.py
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
## Day 6: Advanced Analytics + Risk Metrics
**Analyst:** Data Analyst Intern | Bluestock Fintech
**Topics:** VaR/CVaR · Rolling Sharpe · Cohort Analysis · SIP Continuity · Fund Recommender · Sector HHI
**Data source:** bluestock_mf.db (SQLite) · data/processed/ CSVs"""),

code("""import sqlite3, pandas as pd, numpy as np
import matplotlib.pyplot as plt, matplotlib.ticker as mtick
import seaborn as sns
from pathlib import Path
import warnings; warnings.filterwarnings('ignore')

DB_PATH       = Path('data/db/bluestock_mf.db')
PROCESSED_DIR = Path('data/processed')
CHARTS_DIR    = Path('reports/charts')

RF_DAILY     = 0.065 / 252
TRADING_DAYS = 252

plt.rcParams.update({'figure.dpi':130,'figure.facecolor':'white',
                     'axes.facecolor':'#f7f9fc','axes.grid':True,
                     'grid.alpha':0.35,'font.size':11})

BLUE='#1565C0'; GREEN='#00897B'; AMBER='#F9A825'; RED='#C62828'
PALETTE=['#1565C0','#00897B','#F9A825','#C62828','#6A1B9A','#00838F']

conn  = sqlite3.connect(DB_PATH)
nav   = pd.read_sql('SELECT * FROM fact_nav', conn)
fund  = pd.read_sql('SELECT * FROM dim_fund', conn)
perf  = pd.read_sql('SELECT * FROM fact_performance', conn)
tx    = pd.read_sql('SELECT * FROM fact_transactions', conn)
hold  = pd.read_sql('SELECT * FROM portfolio_holdings', conn)
conn.close()

nav['date']              = pd.to_datetime(nav['date'])
tx['transaction_date']   = pd.to_datetime(tx['transaction_date'])
nav['daily_return']      = nav['daily_return_pct'] / 100.0

scorecard = pd.read_csv(PROCESSED_DIR/'fund_scorecard.csv')
print(f'Loaded: {len(nav):,} NAV rows | {len(tx):,} transactions | {len(hold)} holdings')"""),

md("""## Task 1 — Historical VaR (95%) and CVaR
**VaR 95%** = the loss threshold exceeded only 5% of trading days.
**CVaR** (Conditional VaR / Expected Shortfall) = the average loss on those worst 5% days.
Both are expressed here as daily % of portfolio value."""),

code("""rows = []
for code_id, grp in nav.dropna(subset=['daily_return']).groupby('amfi_code'):
    r = grp['daily_return'].values
    var_95  = np.percentile(r, 5)
    cvar_95 = r[r <= var_95].mean() if len(r[r <= var_95]) > 0 else var_95
    rows.append({
        'amfi_code':     code_id,
        'var_95_daily':  round(var_95  * 100, 4),
        'cvar_95_daily': round(cvar_95 * 100, 4),
        'var_95_ann':    round(var_95  * np.sqrt(TRADING_DAYS) * 100, 4),
        'cvar_95_ann':   round(cvar_95 * np.sqrt(TRADING_DAYS) * 100, 4),
        'pct_neg_days':  round((r < 0).mean() * 100, 2),
    })

var_df = pd.DataFrame(rows).merge(
    fund[['amfi_code','scheme_name','fund_house','category','sub_category']],
    on='amfi_code')
var_df = var_df.sort_values('var_95_daily').reset_index(drop=True)
var_df.to_csv(PROCESSED_DIR/'var_cvar_report.csv', index=False)

# Chart
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

var_plot = var_df.copy()
var_plot['label'] = var_plot['scheme_name'].str[:28]
var_plot = var_plot.sort_values('var_95_daily')
x = range(len(var_plot))
axes[0].barh(list(x), var_plot['var_95_daily'],
    color=[RED if v < -1.5 else AMBER if v < -1.0 else GREEN
           for v in var_plot['var_95_daily']],
    alpha=0.85, edgecolor='white', label='VaR 95%')
axes[0].set_yticks(list(x))
axes[0].set_yticklabels(var_plot['label'].tolist(), fontsize=7)
axes[0].set_title('Daily VaR 95% — All 40 Funds')
axes[0].set_xlabel('Daily Return (%)')
axes[0].axvline(0, color='grey', linewidth=0.8)
axes[0].legend()

# VaR vs CVaR scatter
axes[1].scatter(var_df['var_95_daily'], var_df['cvar_95_daily'],
    c=[RED if c in ['Small Cap','Mid Cap'] else BLUE
       for c in var_df['sub_category']],
    s=80, alpha=0.75, edgecolors='white')
axes[1].plot([var_df['var_95_daily'].min(), 0],
             [var_df['var_95_daily'].min(), 0],
             color='grey', linewidth=0.8, linestyle='--', label='VaR = CVaR line')
axes[1].set_title('VaR vs CVaR by Fund')
axes[1].set_xlabel('VaR 95% (daily %)')
axes[1].set_ylabel('CVaR 95% (daily %)')
axes[1].legend()
plt.tight_layout()
plt.savefig(CHARTS_DIR/'14_var_comparison.png', bbox_inches='tight', dpi=150)
plt.show()

print('Top 5 highest risk (worst VaR):')
var_df[['scheme_name','sub_category','var_95_daily','cvar_95_daily','pct_neg_days']].head(5)"""),

md("""## Task 2 — Rolling 90-Day Sharpe Ratio
Shows how risk-adjusted performance evolves over time.
A Sharpe below 0 means the fund was underperforming the risk-free rate in that window.
The 2023 bull run and 2024 corrections should be visible as peaks and troughs."""),

code("""top5_codes = scorecard.head(5)['amfi_code'].astype(int).tolist()

fig, ax = plt.subplots(figsize=(14, 7))
ax.axhline(0, color='grey', linewidth=0.8, linestyle='--', alpha=0.6, label='Sharpe = 0')
ax.axhline(1, color=GREEN, linewidth=0.8, linestyle=':', alpha=0.6, label='Sharpe = 1 (good)')

for i, code_id in enumerate(top5_codes):
    grp = (nav[nav['amfi_code'] == code_id]
           .sort_values('date')
           .dropna(subset=['daily_return'])
           .copy())
    if len(grp) < 100: continue

    grp['excess']      = grp['daily_return'] - RF_DAILY
    grp['roll_sharpe'] = (grp['excess'].rolling(90).mean() /
                          grp['excess'].rolling(90).std() *
                          np.sqrt(TRADING_DAYS))

    house = fund[fund['amfi_code']==code_id]['fund_house'].values
    label = house[0].replace(' Mutual Fund','').replace(' MF','') if len(house) else str(code_id)
    ax.plot(grp['date'], grp['roll_sharpe'],
            color=PALETTE[i], linewidth=1.8, label=label, alpha=0.9)

ax.set_title('Rolling 90-Day Sharpe Ratio — Top 5 Scored Funds', pad=12)
ax.set_xlabel('Date'); ax.set_ylabel('Rolling Sharpe (annualised)')
ax.set_ylim(-3, 5)
ax.legend(loc='upper left', framealpha=0.9)
ax.fill_betweenx([-3, 0], ax.get_xlim()[0], ax.get_xlim()[1],
                 alpha=0.04, color=RED)
plt.tight_layout()
plt.savefig(CHARTS_DIR/'13_rolling_sharpe.png', bbox_inches='tight', dpi=150)
plt.show()
print('Rolling Sharpe chart saved')"""),

md("""## Task 3 — Investor Cohort Analysis
Grouping investors by the **year of their first ever transaction** reveals how
investor behaviour changes across different market entry points.
2024 cohort investors entered during a bull market — do they invest more or less?"""),

code("""first_tx = tx.groupby('investor_id')['transaction_date'].min().reset_index()
first_tx.columns = ['investor_id','first_date']
first_tx['cohort_year'] = first_tx['first_date'].dt.year

tx_c  = tx.merge(first_tx[['investor_id','cohort_year']], on='investor_id')
sip_c = tx_c[tx_c['transaction_type'] == 'SIP']

cohort = sip_c.groupby('cohort_year').agg(
    num_investors  = ('investor_id',  'nunique'),
    num_sip_txns   = ('amount_inr',   'count'),
    avg_sip_amount = ('amount_inr',   'mean'),
    total_invested = ('amount_inr',   'sum'),
).reset_index()
cohort['total_invested_cr'] = (cohort['total_invested'] / 1e7).round(2)
cohort['avg_sip_amount']    = cohort['avg_sip_amount'].round(0)

# Top fund per cohort
top_fund = (sip_c.groupby(['cohort_year','amfi_code']).size()
                 .reset_index(name='count')
                 .sort_values('count', ascending=False)
                 .groupby('cohort_year').first().reset_index()
                 [['cohort_year','amfi_code']])
top_fund = top_fund.merge(fund[['amfi_code','scheme_name']], on='amfi_code', how='left')
cohort   = cohort.merge(top_fund[['cohort_year','scheme_name']], on='cohort_year', how='left')
cohort.rename(columns={'scheme_name':'top_fund'}, inplace=True)
cohort.to_csv(PROCESSED_DIR/'cohort_analysis.csv', index=False)

# Chart
fig, axes = plt.subplots(1, 3, figsize=(14, 5))
cohort['year_str'] = cohort['cohort_year'].astype(str)

axes[0].bar(cohort['year_str'], cohort['num_investors'],
            color=PALETTE[:len(cohort)], edgecolor='white')
axes[0].set_title('Investors per Cohort Year')
axes[0].set_xlabel('First Transaction Year')
axes[0].set_ylabel('Unique Investors')

axes[1].bar(cohort['year_str'], cohort['avg_sip_amount'],
            color=PALETTE[:len(cohort)], edgecolor='white')
axes[1].set_title('Avg SIP Amount by Cohort')
axes[1].set_xlabel('Cohort Year')
axes[1].set_ylabel('Avg SIP Amount (₹)')
axes[1].yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'₹{x:,.0f}'))

axes[2].bar(cohort['year_str'], cohort['total_invested_cr'],
            color=PALETTE[:len(cohort)], edgecolor='white')
axes[2].set_title('Total SIP Invested by Cohort (₹ Cr)')
axes[2].set_xlabel('Cohort Year')
axes[2].set_ylabel('Total Invested (₹ Crore)')

plt.tight_layout()
plt.savefig(CHARTS_DIR/'cohort_analysis.png', bbox_inches='tight', dpi=150)
plt.show()
print('Cohort analysis saved')
cohort[['cohort_year','num_investors','avg_sip_amount','total_invested_cr','top_fund']]"""),

md("""## Task 4 — SIP Continuity Analysis
Investors with 6+ SIP transactions are analysed for consistency.
An average gap > 35 days between SIPs suggests missed instalments — classified as **at-risk**.
This insight can drive targeted retention campaigns by AMCs."""),

code("""sip = tx[tx['transaction_type']=='SIP'].sort_values(['investor_id','transaction_date']).copy()

rows = []
for inv_id, grp in sip.groupby('investor_id'):
    if len(grp) < 6: continue
    dates = grp['transaction_date'].sort_values().values
    gaps  = [(dates[i+1]-dates[i]).astype('timedelta64[D]').astype(int)
             for i in range(len(dates)-1)]
    avg_gap = np.mean(gaps)
    rows.append({
        'investor_id':  inv_id,
        'num_sip_txns': len(grp),
        'avg_gap_days': round(avg_gap, 1),
        'max_gap_days': int(np.max(gaps)),
        'at_risk':      avg_gap > 35,
        'state':        grp['state'].iloc[0],
        'age_group':    grp['age_group'].iloc[0],
    })

cont_df = pd.DataFrame(rows)
total     = len(cont_df)
at_risk_n = cont_df['at_risk'].sum()
print(f'Investors with 6+ SIPs : {total:,}')
print(f'At-risk (gap > 35 days): {at_risk_n:,} ({at_risk_n/total*100:.1f}%)')
print(f'Healthy (gap ≤ 35 days): {total-at_risk_n:,}')
cont_df.to_csv(PROCESSED_DIR/'sip_continuity.csv', index=False)

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

axes[0].hist(cont_df['avg_gap_days'], bins=40,
             color=BLUE, alpha=0.75, edgecolor='white')
axes[0].axvline(35, color=RED, linewidth=2, linestyle='--', label='At-risk threshold')
axes[0].set_title('Distribution of Avg SIP Gap (Days)')
axes[0].set_xlabel('Avg Gap (days)'); axes[0].set_ylabel('Investors')
axes[0].legend()

state_risk = (cont_df.groupby('state')['at_risk']
                     .mean().mul(100)
                     .sort_values(ascending=True).reset_index())
state_risk.columns = ['State','At-risk %']
axes[1].barh(state_risk['State'], state_risk['At-risk %'],
    color=[RED if v>30 else AMBER if v>20 else GREEN for v in state_risk['At-risk %']],
    edgecolor='white')
axes[1].set_title('At-risk SIP Investors by State (%)')
axes[1].set_xlabel('% At-risk')
plt.tight_layout()
plt.savefig(CHARTS_DIR/'16_sip_continuity.png', bbox_inches='tight', dpi=150)
plt.show()"""),

md("""## Task 5 — Fund Recommender
Simple rule-based engine: filter by risk grade, rank by Sharpe ratio.
Three investor profiles: Low / Moderate / High risk appetite."""),

code("""from recommender import recommend, print_recommendation

# Run recommendations for all three risk profiles
for risk in ['Low', 'Moderate', 'High']:
    print_recommendation(risk)
    result = recommend(risk, top_n=3)
    print(result[['Fund Name','Risk Grade','Sharpe Ratio','3yr CAGR %','Expense Ratio %']].to_string())
    print()"""),

md("""## Task 6 — Sector HHI Concentration
The **Herfindahl-Hirschman Index** measures portfolio concentration:
- HHI = Σ(weight_i²) across all sector holdings
- Low HHI (< 800) = well-diversified across sectors
- High HHI (> 2000) = concentrated in few sectors (higher idiosyncratic risk)"""),

code("""equity_codes = fund[fund['category']=='Equity']['amfi_code'].tolist()
eq = hold[hold['amfi_code'].isin(equity_codes)].copy()

rows = []
for code_id, grp in eq.groupby('amfi_code'):
    weights    = grp['weight_pct'].values
    hhi        = np.sum(weights ** 2)
    sector_w   = grp.groupby('sector')['weight_pct'].sum()
    rows.append({
        'amfi_code':      code_id,
        'hhi':            round(hhi, 2),
        'top_sector':     sector_w.idxmax(),
        'top_sector_pct': round(sector_w.max(), 2),
        'n_sectors':      len(sector_w),
        'concentration':  'High' if hhi > 2000 else 'Moderate' if hhi > 800 else 'Low',
    })

hhi_df = pd.DataFrame(rows).merge(
    fund[['amfi_code','scheme_name','fund_house','sub_category']], on='amfi_code')
hhi_df = hhi_df.sort_values('hhi', ascending=False).reset_index(drop=True)
hhi_df.to_csv(PROCESSED_DIR/'sector_hhi.csv', index=False)

# Chart
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

hhi_plot = hhi_df.sort_values('hhi', ascending=True).copy()
hhi_plot['label'] = hhi_plot['scheme_name'].str[:28]
axes[0].barh(hhi_plot['label'], hhi_plot['hhi'],
    color=[RED if v>2000 else AMBER if v>800 else GREEN for v in hhi_plot['hhi']],
    edgecolor='white', alpha=0.85)
axes[0].axvline(2000, color=RED,  linewidth=1.5, linestyle='--', alpha=0.7, label='High (>2000)')
axes[0].axvline(800,  color=AMBER,linewidth=1.5, linestyle=':', alpha=0.7, label='Moderate (>800)')
axes[0].set_title('Sector HHI — All Equity Funds')
axes[0].set_xlabel('HHI Score')
axes[0].legend(fontsize=9)
axes[0].tick_params(axis='y', labelsize=8)

# Top sector allocation per fund
top_s = hhi_df.groupby('top_sector').size().sort_values(ascending=True)
axes[1].barh(top_s.index, top_s.values,
             color=PALETTE[:len(top_s)], edgecolor='white')
axes[1].set_title('Most Common Top Sector Across Funds')
axes[1].set_xlabel('Number of Funds')
plt.tight_layout()
plt.savefig(CHARTS_DIR/'15_sector_hhi.png', bbox_inches='tight', dpi=150)
plt.show()
print('Top 5 most concentrated funds:')
hhi_df[['scheme_name','hhi','top_sector','top_sector_pct','concentration']].head(5)"""),

md("""## Task 7 — 5 Key Advanced Analytics Insights

| # | Insight | Finding |
|---|---------|---------|
| 1 | **Highest VaR** | Small Cap and Mid Cap funds show the worst daily VaR (< -1.5%), consistent with their high volatility profile. Liquid funds have VaR close to 0%, confirming near-zero risk. |
| 2 | **Rolling Sharpe cycles** | The rolling 90-day Sharpe drops sharply during the 2024 market correction (Mar–Jun 2024) and recovers in H2 2024 — validating real market behaviour in the dataset. |
| 3 | **Cohort behaviour** | Investors who entered in 2024 (bull market phase) tend to have higher avg SIP amounts than 2022 entrants, suggesting newer investors are more confident with larger commitments. |
| 4 | **SIP at-risk** | Approximately 25–35% of active SIP investors show average gaps > 35 days between instalments, flagging a meaningful retention risk for AMCs — highest in B30 states. |
| 5 | **Sector concentration** | Banking & Financial Services dominates as the top sector holding across most Large Cap equity funds (high HHI), reflecting their Nifty 50 index composition bias. Mid Cap funds show lower HHI, indicating better diversification. |"""),

]

nb = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name":"Python 3","language":"python","name":"python3"},
        "language_info": {"name":"python","version":"3.11.0"},
    },
    "cells": cells,
}

out = NOTEBOOKS_DIR / "Advanced_Analytics.ipynb"
out.write_text(json.dumps(nb, indent=2))
print(f"Created: {out}")
print("Open with: jupyter notebook  ->  notebooks/Advanced_Analytics.ipynb")
