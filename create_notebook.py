"""
create_notebook.py
Day 3 — Creates EDA_Analysis.ipynb in notebooks/

Run AFTER eda_analysis.py:
    python3 create_notebook.py

This creates a proper Jupyter notebook with all analysis code
split into logical cells with markdown headers.
"""

import json
from pathlib import Path

NOTEBOOKS_DIR = Path("notebooks")
NOTEBOOKS_DIR.mkdir(exist_ok=True)

def md_cell(text):
    return {"cell_type": "markdown", "metadata": {},
            "source": [text]}

def code_cell(code):
    return {"cell_type": "code", "execution_count": None,
            "metadata": {}, "outputs": [], "source": [code]}

cells = [

md_cell("""# Bluestock Fintech — Mutual Fund Analytics Capstone
## Day 3: Exploratory Data Analysis (EDA)
**Analyst:** Data Analyst Intern | Bluestock Fintech  
**Data:** 40 Schemes · 46K NAV rows · 32K Transactions · 10 AMCs  
**Period:** Jan 2022 – Dec 2025"""),

code_cell("""# Setup — imports and database connection
import sqlite3, pandas as pd, numpy as np
import matplotlib.pyplot as plt, matplotlib.ticker as mtick
import seaborn as sns
import plotly.express as px, plotly.graph_objects as go
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

DB_PATH    = Path('data/db/bluestock_mf.db')
CHARTS_DIR = Path('reports/charts')
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({'figure.dpi': 130, 'figure.facecolor': 'white',
                     'axes.facecolor': '#f7f9fc', 'axes.grid': True,
                     'grid.alpha': 0.35, 'font.size': 11})
sns.set_theme(style='whitegrid', palette='husl')

BLUE='#1565C0'; GREEN='#00897B'; AMBER='#F9A825'; RED='#C62828'
PALETTE = ['#1565C0','#00897B','#F9A825','#C62828','#6A1B9A',
           '#00838F','#EF6C00','#2E7D32','#4527A0','#AD1457']
print('Setup complete')"""),

md_cell("## Load Data from SQLite Database"),

code_cell("""conn = sqlite3.connect(DB_PATH)

dim_fund      = pd.read_sql('SELECT * FROM dim_fund', conn)
fact_nav      = pd.read_sql('SELECT * FROM fact_nav', conn)
fact_perf     = pd.read_sql('SELECT * FROM fact_performance', conn)
fact_aum      = pd.read_sql('SELECT * FROM fact_aum', conn)
sip_inflows   = pd.read_sql('SELECT * FROM sip_inflows', conn)
cat_inflows   = pd.read_sql('SELECT * FROM category_inflows', conn)
folio_count   = pd.read_sql('SELECT * FROM folio_count', conn)
transactions  = pd.read_sql('SELECT * FROM fact_transactions', conn)
holdings      = pd.read_sql('SELECT * FROM portfolio_holdings', conn)
benchmarks    = pd.read_sql('SELECT * FROM benchmark_indices', conn)
conn.close()

# Parse dates
fact_nav['date']                       = pd.to_datetime(fact_nav['date'])
fact_aum['date']                       = pd.to_datetime(fact_aum['date'])
sip_inflows['month']                   = pd.to_datetime(sip_inflows['month'])
cat_inflows['month']                   = pd.to_datetime(cat_inflows['month'])
folio_count['month']                   = pd.to_datetime(folio_count['month'])
transactions['transaction_date']       = pd.to_datetime(transactions['transaction_date'])
benchmarks['date']                     = pd.to_datetime(benchmarks['date'])

print(f'fact_nav: {len(fact_nav):,} rows')
print(f'transactions: {len(transactions):,} rows')
print(f'dim_fund: {len(dim_fund)} schemes across {dim_fund.fund_house.nunique()} AMCs')"""),

md_cell("""## Task 1 — NAV Trend Analysis (Plotly)
Daily NAV for top 10 funds 2022–2026. Highlights 2023 bull run and 2024 correction."""),

code_cell("""top10_codes = fact_perf.nlargest(10, 'aum_crore')['amfi_code'].tolist()
nav10 = fact_nav[fact_nav['amfi_code'].isin(top10_codes)].copy()
nav10 = nav10.merge(dim_fund[['amfi_code','fund_house']], on='amfi_code')
nav10['label'] = nav10['fund_house'].str.replace(' Mutual Fund','').str.replace(' MF','')

# 1a: Actual NAV
fig = px.line(nav10, x='date', y='nav', color='label',
    title='Daily NAV — Top 10 Funds by AUM (2022–2026)',
    labels={'date':'Date','nav':'NAV (₹)','label':'Fund House'},
    color_discrete_sequence=px.colors.qualitative.Set1)
fig.add_vrect(x0='2023-04-01', x1='2023-12-31',
    fillcolor='rgba(0,200,100,0.08)', line_width=0,
    annotation_text='2023 Bull Run', annotation_position='top left')
fig.add_vrect(x0='2024-03-01', x1='2024-06-30',
    fillcolor='rgba(200,0,0,0.07)', line_width=0,
    annotation_text='2024 Correction', annotation_position='top left')
fig.update_layout(height=500, template='plotly_white')
fig.write_html(str(CHARTS_DIR / '01a_nav_trends.html'))
fig.show()"""),

code_cell("""# 1b: NAV indexed to 100 (easier to compare growth %)
nav10 = nav10.sort_values(['amfi_code','date'])
nav10['nav_indexed'] = nav10.groupby('amfi_code')['nav'].transform(lambda x: x/x.iloc[0]*100)

fig2 = px.line(nav10, x='date', y='nav_indexed', color='label',
    title='NAV Growth Indexed to 100 (Jan 2022 = 100)',
    labels={'date':'Date','nav_indexed':'Indexed NAV','label':'Fund House'},
    color_discrete_sequence=px.colors.qualitative.Set1)
fig2.add_hline(y=100, line_dash='dot', line_color='grey', annotation_text='Baseline')
fig2.update_layout(height=500, template='plotly_white')
fig2.write_html(str(CHARTS_DIR / '01b_nav_indexed.html'))
fig2.show()"""),

md_cell("## Task 2 — AUM Growth Bar Chart (Seaborn)"),

code_cell("""aum = fact_aum.copy()
aum['year'] = aum['date'].dt.year
aum_yr = aum.sort_values('date').groupby(['fund_house','year'], as_index=False).last()
aum_yr['house'] = aum_yr['fund_house'].str.replace(' Mutual Fund','').str.replace(' MF','')

fig, ax = plt.subplots(figsize=(14, 7))
bar = sns.barplot(data=aum_yr, x='house', y='aum_lakh_crore', hue='year',
                  palette='Blues', ax=ax)
for patch in bar.patches:
    if patch.get_height() > 10:
        patch.set_edgecolor(AMBER); patch.set_linewidth(2.5)
ax.set_title('AUM by Fund House — 2022 to 2025 (₹ Lakh Crore)', pad=15)
ax.set_xlabel('Fund House'); ax.set_ylabel('AUM (₹ Lakh Crore)')
ax.tick_params(axis='x', rotation=35)
ax.annotate('SBI: ₹12.5L Cr\\n(Dec 2025)', xy=(0,12.5), xytext=(1.5,11.2),
    arrowprops=dict(arrowstyle='->', color=RED),
    fontsize=10, color=RED, fontweight='bold')
plt.legend(title='Year', bbox_to_anchor=(1.01,1))
plt.tight_layout()
plt.savefig(CHARTS_DIR/'02_aum_growth.png', bbox_inches='tight', dpi=150)
plt.show()"""),

md_cell("## Task 3 — SIP Inflow Time Series (Plotly)"),

code_cell("""sip = sip_inflows.copy().sort_values('month')
peak = sip.loc[sip['sip_inflow_crore'].idxmax()]

fig = go.Figure()
fig.add_trace(go.Scatter(x=sip['month'], y=sip['sip_inflow_crore'],
    mode='lines+markers', name='SIP Inflow',
    line=dict(color=BLUE, width=2.5),
    fill='tozeroy', fillcolor='rgba(21,101,192,0.1)'))
fig.add_annotation(x=peak['month'], y=peak['sip_inflow_crore'],
    text=f"All-time High<br>₹{int(peak['sip_inflow_crore']):,} Cr<br>(Dec 2025)",
    showarrow=True, arrowhead=2, arrowcolor=RED,
    font=dict(color=RED, size=12), bgcolor='white', bordercolor=RED, borderwidth=1)
fig.update_layout(title='Monthly SIP Inflows — Jan 2022 to Dec 2025',
    xaxis_title='Month', yaxis_title='SIP Inflow (₹ Crore)',
    height=480, template='plotly_white')
fig.write_html(str(CHARTS_DIR/'03a_sip_inflow.html'))
fig.show()"""),

md_cell("## Task 4 — Category Inflow Heatmap (Seaborn)"),

code_cell("""ci = cat_inflows.copy()
ci['month_label'] = ci['month'].dt.strftime('%b %y')
pivot = ci.pivot_table(index='category', columns='month_label',
                        values='net_inflow_crore', aggfunc='sum')
ordered = [pd.Timestamp(m).strftime('%b %y') for m in sorted(ci['month'].unique())]
pivot = pivot.reindex(columns=[c for c in ordered if c in pivot.columns])

fig, ax = plt.subplots(figsize=(16, 6))
sns.heatmap(pivot, annot=True, fmt='.0f', cmap='YlOrRd', linewidths=0.4,
            ax=ax, annot_kws={'size':8},
            cbar_kws={'label':'Net Inflow (₹ Crore)'})
ax.set_title('Category-wise Net Inflows by Month (₹ Crore)', pad=15)
ax.tick_params(axis='x', rotation=45, labelsize=8)
ax.tick_params(axis='y', rotation=0)
plt.tight_layout()
plt.savefig(CHARTS_DIR/'04_category_heatmap.png', bbox_inches='tight', dpi=150)
plt.show()"""),

md_cell("## Task 5 — Investor Demographics"),

code_cell("""sip_tx = transactions[transactions['transaction_type']=='SIP']
age_order = ['18-25','26-35','36-45','46-55','56+']

# Pie — age distribution
age_counts = transactions['age_group'].value_counts().reindex(age_order).dropna()
fig, ax = plt.subplots(figsize=(8,8))
ax.pie(age_counts, labels=age_counts.index, autopct='%1.1f%%',
       colors=PALETTE[:len(age_counts)], startangle=140, pctdistance=0.82,
       wedgeprops=dict(edgecolor='white', linewidth=1.5))
ax.set_title('Investor Distribution by Age Group', fontsize=14, fontweight='bold')
plt.savefig(CHARTS_DIR/'05a_age_distribution.png', bbox_inches='tight', dpi=150)
plt.show()

# Box plot — SIP amount by age
fig, ax = plt.subplots(figsize=(11,6))
sns.boxplot(data=sip_tx, x='age_group', y='amount_inr', order=age_order,
            palette=PALETTE[:5], flierprops=dict(marker='o', markersize=3, alpha=0.4), ax=ax)
ax.set_title('SIP Amount Distribution by Age Group', pad=12)
ax.set_xlabel('Age Group'); ax.set_ylabel('SIP Amount (₹)')
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x,_: f'₹{int(x):,}'))
plt.tight_layout()
plt.savefig(CHARTS_DIR/'05b_sip_boxplot_age.png', bbox_inches='tight', dpi=150)
plt.show()

# Pie — gender
gender_c = transactions['gender'].value_counts()
fig, ax = plt.subplots(figsize=(7,7))
ax.pie(gender_c, labels=gender_c.index, autopct='%1.1f%%',
       colors=[BLUE,'#E91E63'], startangle=90,
       wedgeprops=dict(edgecolor='white', linewidth=2))
ax.set_title('Investor Gender Split', fontsize=14, fontweight='bold')
plt.savefig(CHARTS_DIR/'05c_gender_split.png', bbox_inches='tight', dpi=150)
plt.show()"""),

md_cell("## Task 6 — Geographic Distribution"),

code_cell("""state_sip = (transactions[transactions['transaction_type']=='SIP']
             .groupby('state')['amount_inr'].sum()
             .sort_values(ascending=True).div(1e7))

fig, ax = plt.subplots(figsize=(10,8))
bars = ax.barh(state_sip.index, state_sip.values,
               color=PALETTE[:len(state_sip)], edgecolor='white')
ax.set_title('Total SIP Investment by State (₹ Crore)', pad=12)
ax.set_xlabel('Total SIP Amount (₹ Crore)')
for b in bars:
    ax.text(b.get_width()+0.1, b.get_y()+b.get_height()/2,
            f'₹{b.get_width():.1f} Cr', va='center', fontsize=9)
plt.tight_layout()
plt.savefig(CHARTS_DIR/'06a_sip_by_state.png', bbox_inches='tight', dpi=150)
plt.show()

tier = transactions.groupby('city_tier')['amount_inr'].sum()
fig, ax = plt.subplots(figsize=(7,7))
ax.pie(tier, labels=tier.index, autopct='%1.1f%%', colors=[BLUE,GREEN],
       explode=[0.04,0], startangle=90, wedgeprops=dict(edgecolor='white',linewidth=2))
ax.set_title('T30 vs B30 City Tier — Investment Split', fontsize=13, fontweight='bold')
plt.savefig(CHARTS_DIR/'06b_t30_vs_b30.png', bbox_inches='tight', dpi=150)
plt.show()"""),

md_cell("## Task 7 — Folio Count Growth (Plotly)"),

code_cell("""fc = folio_count.copy().sort_values('month')
fig = go.Figure()
fig.add_trace(go.Scatter(x=fc['month'], y=fc['total_folios_crore'],
    name='Total Folios', mode='lines+markers',
    line=dict(color=BLUE, width=3), marker=dict(size=7)))
fig.add_trace(go.Scatter(x=fc['month'], y=fc['equity_folios_crore'],
    name='Equity Folios', mode='lines',
    line=dict(color=GREEN, width=2, dash='dot')))
for row in [fc.iloc[0], fc.iloc[-1]]:
    fig.add_annotation(x=row['month'], y=row['total_folios_crore'],
        text=f"{row['total_folios_crore']} Cr",
        showarrow=True, arrowhead=2, ax=30, ay=-35,
        font=dict(size=11, color=RED), bgcolor='white',
        bordercolor=RED, borderwidth=1)
fig.update_layout(title='Mutual Fund Folio Count Growth (2022–2025)',
    xaxis_title='Month', yaxis_title='Folios (Crore)',
    height=460, template='plotly_white', legend=dict(orientation='h', y=-0.15))
fig.write_html(str(CHARTS_DIR/'07_folio_count_growth.html'))
fig.show()"""),

md_cell("## Task 8 — NAV Return Correlation Matrix (Seaborn)"),

code_cell("""top10 = fact_perf.nlargest(10,'aum_crore')['amfi_code'].tolist()
dim_fund['label'] = (dim_fund['fund_house'].str.replace(' Mutual Fund','')
                     .str.replace(' MF','') + ' ' + dim_fund['sub_category'].str[:6])
nav10 = fact_nav[fact_nav['amfi_code'].isin(top10)].merge(
    dim_fund[['amfi_code','label']], on='amfi_code')
pivot = nav10.pivot_table(index='date', columns='label',
                           values='daily_return_pct').dropna()
corr = pivot.corr()

fig, ax = plt.subplots(figsize=(11,9))
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f',
            cmap='RdYlGn', center=0, vmin=-0.2, vmax=1.0,
            linewidths=0.5, ax=ax, annot_kws={'size':9},
            cbar_kws={'label':'Pearson Correlation'})
ax.set_title('Daily Return Correlation Matrix — Top 10 Funds', pad=15)
ax.tick_params(axis='x', rotation=40, labelsize=9)
ax.tick_params(axis='y', rotation=0, labelsize=9)
plt.tight_layout()
plt.savefig(CHARTS_DIR/'08_correlation_matrix.png', bbox_inches='tight', dpi=150)
plt.show()"""),

md_cell("## Task 9 — Sector Allocation Donut (Matplotlib)"),

code_cell("""equity_codes = dim_fund[dim_fund['category']=='Equity']['amfi_code'].tolist()
eq = holdings[holdings['amfi_code'].isin(equity_codes)]
sector_w = eq.groupby('sector')['weight_pct'].mean().sort_values(ascending=False)
big = sector_w[sector_w >= 2.0]
other = sector_w[sector_w < 2.0].sum()
if other > 0:
    big = pd.concat([big, pd.Series({'Others': other})])

fig, ax = plt.subplots(figsize=(10,10))
ax.pie(big, labels=big.index, autopct='%1.1f%%',
       colors=PALETTE[:len(big)], startangle=90, pctdistance=0.8,
       wedgeprops=dict(width=0.55, edgecolor='white', linewidth=1.5))
ax.set_title('Sector Allocation — Equity Mutual Funds\\n(Average Portfolio Weight %)',
             fontsize=13, fontweight='bold', pad=20)
plt.savefig(CHARTS_DIR/'09_sector_donut.png', bbox_inches='tight', dpi=150)
plt.show()"""),

md_cell("""## Task 10 — Key EDA Findings

| # | Finding | Insight |
|---|---------|---------|
| 1 | **SIP Growth** | Monthly SIP inflows grew ~125% from Jan 2022 to Dec 2025, reaching ₹31,002 Cr all-time high. |
| 2 | **SBI Dominance** | SBI MF leads with ₹12.5L Cr AUM (Dec 2025), growing 2x from ₹6.05L Cr in 2022. |
| 3 | **Top Performer** | Small Cap funds delivered the highest 3yr CAGR (20–23%), consistently beating benchmarks. |
| 4 | **Folio Doubling** | Total MF folios doubled from 13.26 Cr to 26.12 Cr — reflecting mass retail adoption. |
| 5 | **Equity Inflows** | Equity categories dominate inflows; Small Cap and Mid Cap saw sharpest growth in FY25. |
| 6 | **B30 Rising** | B30 cities (beyond top 30) are growing faster than T30 metros in MF adoption. |
| 7 | **Senior SIPs** | Investors aged 56+ have the highest avg SIP amounts — retirement planning driving activity. |
| 8 | **Expense Ratio** | 14 of 40 schemes have expense ratio < 1%, all Direct plans — cost advantage is significant. |
| 9 | **High Correlation** | Large Cap funds show >0.85 correlation — diversification within large cap is limited. |
| 10 | **Banking Sector** | Banking & Financial Services is the dominant equity sector — reflects Nifty 50 composition bias. |"""),

]

nb = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11.0"},
    },
    "cells": cells
}

out = NOTEBOOKS_DIR / "EDA_Analysis.ipynb"
out.write_text(json.dumps(nb, indent=2))
print(f"Created: {out}")
print("Open with: jupyter notebook  →  navigate to notebooks/EDA_Analysis.ipynb")