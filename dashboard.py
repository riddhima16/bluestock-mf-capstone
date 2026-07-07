"""
dashboard.py  —  Day 5: Bluestock MF Analytics Dashboard
4-page interactive Streamlit dashboard wired to bluestock_mf.db

Pages:
  1. Industry Overview   — KPIs, AUM trends, folio growth
  2. Fund Performance    — risk/return scatter, scorecard, NAV vs benchmark
  3. Investor Analytics  — demographics, geography, transaction patterns
  4. SIP & Market Trends — SIP vs Nifty dual-axis, category heatmap

Run: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ── page config — must be FIRST streamlit call ─────────────────────────
st.set_page_config(
    page_title="Bluestock MF Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── brand colours ───────────────────────────────────────────────────────
BLUE   = "#1565C0"
GREEN  = "#00897B"
AMBER  = "#F9A825"
RED    = "#C62828"
GREY   = "#546E7A"
PALETTE = [BLUE, GREEN, AMBER, RED, "#6A1B9A",
           "#00838F", "#EF6C00", "#2E7D32", "#4527A0", "#AD1457"]

# ── custom CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* hide default top padding */
    .block-container { padding-top: 1.2rem; }

    /* metric cards */
    [data-testid="stMetricValue"] {
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        color: #1565C0 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        color: #546E7A !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.78rem !important;
    }

    /* sidebar */
    [data-testid="stSidebarContent"] {
        background: #f0f4ff;
    }

    /* section headers inside pages */
    .section-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #1565C0;
        border-bottom: 2px solid #1565C0;
        padding-bottom: 4px;
        margin: 18px 0 10px 0;
    }

    /* card divider */
    hr { border: none; border-top: 1px solid #e0e0e0; margin: 12px 0; }
</style>
""", unsafe_allow_html=True)

DB_PATH = Path("data/db/bluestock_mf.db")


# ══════════════════════════════════════════════════════════════════════
# DATA LOADING  (cached — only hits the DB once per session)
# ══════════════════════════════════════════════════════════════════════

@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    d = {}
    tables = [
        "dim_fund", "fact_nav", "fact_performance", "fact_aum",
        "sip_inflows", "category_inflows", "folio_count",
        "fact_transactions", "portfolio_holdings", "benchmark_indices",
    ]
    for t in tables:
        d[t] = pd.read_sql(f"SELECT * FROM {t}", conn)
    conn.close()

    # parse date columns
    d["fact_nav"]["date"]                      = pd.to_datetime(d["fact_nav"]["date"])
    d["fact_aum"]["date"]                      = pd.to_datetime(d["fact_aum"]["date"])
    d["sip_inflows"]["month"]                  = pd.to_datetime(d["sip_inflows"]["month"])
    d["category_inflows"]["month"]             = pd.to_datetime(d["category_inflows"]["month"])
    d["folio_count"]["month"]                  = pd.to_datetime(d["folio_count"]["month"])
    d["fact_transactions"]["transaction_date"] = pd.to_datetime(d["fact_transactions"]["transaction_date"])
    d["benchmark_indices"]["date"]             = pd.to_datetime(d["benchmark_indices"]["date"])

    return d


# ── plotly default layout helper ────────────────────────────────────────
def chart(fig, height=400):
    fig.update_layout(
        height=height,
        template="plotly_white",
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white",
        plot_bgcolor="#f7f9fc",
        font=dict(size=11),
        legend=dict(orientation="h", y=-0.18, font=dict(size=10)),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════
# PAGE 1 — INDUSTRY OVERVIEW
# ══════════════════════════════════════════════════════════════════════

def page_industry(d):
    st.markdown("## 🏦 Industry Overview")
    st.caption("Indian Mutual Fund Industry — Key Metrics & Trends (2022–2026)")

    aum   = d["fact_aum"]
    sip   = d["sip_inflows"].sort_values("month")
    folio = d["folio_count"].sort_values("month")
    fund  = d["dim_fund"]

    # ── KPI row ───────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Industry AUM",    "₹81 Lakh Cr",   "+94% vs 2022")
    k2.metric("SIP Inflow Dec'25","₹31,002 Cr",   "All-time high")
    k3.metric("Total Folios",    "26.12 Cr",       "+97% vs 2022")
    k4.metric("Active SIP A/Cs", "9.35 Cr",        "+90% vs 2022")
    k5.metric("Schemes Tracked", f"{len(fund)}",   "Across 10 AMCs")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── AUM trend (line) + AUM by AMC latest (bar) ────────────────────
    col1, col2 = st.columns([1.4, 1])

    with col1:
        st.markdown('<div class="section-title">AUM Growth by Fund House (2022–2025)</div>',
                    unsafe_allow_html=True)
        aum_yr = aum.copy()
        aum_yr["year"] = aum_yr["date"].dt.year.astype(str)
        aum_yr["house"] = (aum_yr["fund_house"]
                           .str.replace(" Mutual Fund", "", regex=False)
                           .str.replace(" MF", "", regex=False))
        aum_latest = (aum_yr.sort_values("date")
                            .groupby(["house","year"], as_index=False)
                            .last())
        fig = px.line(aum_latest, x="year", y="aum_lakh_crore", color="house",
                      markers=True,
                      labels={"year":"Year","aum_lakh_crore":"AUM (₹ Lakh Cr)","house":"AMC"},
                      color_discrete_sequence=PALETTE)
        fig.update_traces(line=dict(width=2.2), marker=dict(size=6))
        st.plotly_chart(chart(fig, 380), use_container_width=True, config={"displayModeBar":False})

    with col2:
        st.markdown('<div class="section-title">Latest AUM by Fund House</div>',
                    unsafe_allow_html=True)
        latest_date = aum["date"].max()
        latest_aum  = aum[aum["date"] == latest_date].copy()
        latest_aum["house"] = (latest_aum["fund_house"]
                               .str.replace(" Mutual Fund","",regex=False)
                               .str.replace(" MF","",regex=False))
        latest_aum = latest_aum.sort_values("aum_lakh_crore", ascending=True)
        fig2 = px.bar(latest_aum, x="aum_lakh_crore", y="house",
                      orientation="h",
                      labels={"aum_lakh_crore":"AUM (₹ Lakh Cr)","house":""},
                      color="aum_lakh_crore",
                      color_continuous_scale=[[0,GREEN],[1,BLUE]])
        fig2.update_coloraxes(showscale=False)
        st.plotly_chart(chart(fig2, 380), use_container_width=True, config={"displayModeBar":False})

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── SIP trend + Folio growth ──────────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.markdown('<div class="section-title">Monthly SIP Inflows (₹ Crore)</div>',
                    unsafe_allow_html=True)
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=sip["month"], y=sip["sip_inflow_crore"],
            fill="tozeroy", fillcolor="rgba(21,101,192,0.12)",
            line=dict(color=BLUE, width=2.5),
            mode="lines", name="SIP Inflow",
        ))
        peak = sip.loc[sip["sip_inflow_crore"].idxmax()]
        fig3.add_annotation(
            x=peak["month"], y=peak["sip_inflow_crore"],
            text=f"₹{int(peak['sip_inflow_crore']):,} Cr",
            showarrow=True, arrowhead=2, arrowcolor=RED,
            font=dict(color=RED, size=11), bgcolor="white", bordercolor=RED,
        )
        st.plotly_chart(chart(fig3, 340), use_container_width=True, config={"displayModeBar":False})

    with col4:
        st.markdown('<div class="section-title">Total MF Folios Growth (Crore)</div>',
                    unsafe_allow_html=True)
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=folio["month"], y=folio["total_folios_crore"],
            fill="tozeroy", fillcolor="rgba(0,137,123,0.12)",
            line=dict(color=GREEN, width=2.5),
            mode="lines+markers", marker=dict(size=5), name="Total Folios",
        ))
        fig4.add_trace(go.Scatter(
            x=folio["month"], y=folio["equity_folios_crore"],
            line=dict(color=BLUE, width=1.8, dash="dot"),
            mode="lines", name="Equity Folios",
        ))
        st.plotly_chart(chart(fig4, 340), use_container_width=True, config={"displayModeBar":False})


# ══════════════════════════════════════════════════════════════════════
# PAGE 2 — FUND PERFORMANCE
# ══════════════════════════════════════════════════════════════════════

def page_performance(d):
    st.markdown("## 📈 Fund Performance & Risk")

    perf  = d["fact_performance"].copy()
    nav   = d["fact_nav"].copy()
    bench = d["benchmark_indices"].copy()
    fund  = d["dim_fund"].copy()

    # ── sidebar filters ───────────────────────────────────────────────
    st.sidebar.markdown("### Filters — Performance")
    houses     = ["All"] + sorted(perf["fund_house"].unique().tolist())
    categories = ["All"] + sorted(perf["category"].dropna().unique().tolist())
    plans      = ["All"] + sorted(perf["plan"].dropna().unique().tolist())

    sel_house = st.sidebar.selectbox("Fund House",   houses)
    sel_cat   = st.sidebar.selectbox("Category",     categories)
    sel_plan  = st.sidebar.selectbox("Plan",         plans)

    fp = perf.copy()
    if sel_house != "All": fp = fp[fp["fund_house"] == sel_house]
    if sel_cat   != "All": fp = fp[fp["category"]   == sel_cat]
    if sel_plan  != "All": fp = fp[fp["plan"]        == sel_plan]

    st.caption(f"Showing {len(fp)} of {len(perf)} funds  |  "
               f"Filters: {sel_house} · {sel_cat} · {sel_plan}")

    if fp.empty:
        st.warning("No funds match current filters — adjust sidebar selections.")
        return

    # ── Risk vs Return scatter ────────────────────────────────────────
    st.markdown('<div class="section-title">Risk vs Return (bubble size = AUM)</div>',
                unsafe_allow_html=True)

    fp["short_name"] = fp["scheme_name"].str[:35]
    fp_plot = fp.dropna(subset=["return_3yr_pct","std_dev_ann_pct","aum_crore"])
    fig = px.scatter(
        fp_plot,
        x="return_3yr_pct", y="std_dev_ann_pct",
        size="aum_crore", color="category",
        hover_name="short_name",
        hover_data={"return_3yr_pct":":.2f",
                    "std_dev_ann_pct":":.2f",
                    "sharpe_ratio":":.3f",
                    "aum_crore":":,"},
        labels={"return_3yr_pct":"3-Year CAGR (%)",
                "std_dev_ann_pct":"Annualised Std Dev (%)",
                "category":"Category"},
        color_discrete_sequence=PALETTE,
        size_max=50,
    )
    fig.update_layout(height=420, template="plotly_white",
                      margin=dict(l=10,r=10,t=30,b=10))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Scorecard table + NAV chart ───────────────────────────────────
    col1, col2 = st.columns([1, 1.3])

    with col1:
        st.markdown('<div class="section-title">Fund Scorecard (Sortable)</div>',
                    unsafe_allow_html=True)
        table_cols = ["scheme_name","category","return_3yr_pct",
                      "sharpe_ratio","max_drawdown_pct","expense_ratio_pct","morningstar_rating"]
        display_df = fp[table_cols].copy()
        display_df.columns = ["Scheme","Category","3yr CAGR%",
                               "Sharpe","Max DD%","Exp Ratio%","★"]
        display_df["Scheme"] = display_df["Scheme"].str[:32]
        display_df = display_df.sort_values("3yr CAGR%", ascending=False)
        st.dataframe(
            display_df.style
                .background_gradient(subset=["3yr CAGR%","Sharpe"], cmap="Greens")
                .background_gradient(subset=["Max DD%"], cmap="Reds_r")
                .format({"3yr CAGR%":"{:.2f}",
                         "Sharpe":"{:.3f}",
                         "Max DD%":"{:.2f}",
                         "Exp Ratio%":"{:.2f}"}),
            use_container_width=True,
            height=400,
        )

    with col2:
        st.markdown('<div class="section-title">NAV History vs Benchmark</div>',
                    unsafe_allow_html=True)
        fund_options = fp["scheme_name"].tolist()
        selected_fund = st.selectbox("Select fund:", fund_options, key="nav_fund")
        sel_code = fp[fp["scheme_name"] == selected_fund]["amfi_code"].values[0]

        fund_nav = nav[nav["amfi_code"] == sel_code].sort_values("date").copy()
        if len(fund_nav) > 0:
            # index to 100
            fund_nav["indexed"] = fund_nav["nav"] / fund_nav["nav"].iloc[0] * 100

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=fund_nav["date"], y=fund_nav["indexed"],
                name=selected_fund[:25],
                line=dict(color=BLUE, width=2.5), mode="lines",
            ))

            # add Nifty50 benchmark
            n50 = bench[bench["index_name"] == "NIFTY50"].sort_values("date")
            n50 = n50[n50["date"] >= fund_nav["date"].min()]
            if len(n50) > 0:
                n50_idx = n50["close_value"] / n50["close_value"].iloc[0] * 100
                fig2.add_trace(go.Scatter(
                    x=n50["date"], y=n50_idx,
                    name="Nifty 50",
                    line=dict(color=GREY, width=1.8, dash="dash"),
                    mode="lines",
                ))
            fig2.add_hline(y=100, line_color=GREY, line_dash="dot",
                           line_width=1, opacity=0.5)
            fig2.update_layout(
                height=400, template="plotly_white",
                margin=dict(l=10,r=10,t=30,b=10),
                legend=dict(orientation="h", y=-0.2),
                xaxis_title="Date",
                yaxis_title="Indexed (Start = 100)",
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})


# ══════════════════════════════════════════════════════════════════════
# PAGE 3 — INVESTOR ANALYTICS
# ══════════════════════════════════════════════════════════════════════

def page_investor(d):
    st.markdown("## 👥 Investor Analytics")

    tx = d["fact_transactions"].copy()

    # ── sidebar filters ───────────────────────────────────────────────
    st.sidebar.markdown("### Filters — Investors")
    states     = ["All"] + sorted(tx["state"].unique().tolist())
    age_groups = ["All"] + ["18-25","26-35","36-45","46-55","56+"]
    tiers      = ["All"] + sorted(tx["city_tier"].unique().tolist())

    sel_state = st.sidebar.selectbox("State",     states,     key="inv_state")
    sel_age   = st.sidebar.selectbox("Age Group", age_groups, key="inv_age")
    sel_tier  = st.sidebar.selectbox("City Tier", tiers,      key="inv_tier")

    ft = tx.copy()
    if sel_state != "All": ft = ft[ft["state"]     == sel_state]
    if sel_age   != "All": ft = ft[ft["age_group"] == sel_age]
    if sel_tier  != "All": ft = ft[ft["city_tier"] == sel_tier]

    # KPI row
    sip_tx  = ft[ft["transaction_type"] == "SIP"]
    lump_tx = ft[ft["transaction_type"] == "Lumpsum"]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Transactions", f"{len(ft):,}")
    k2.metric("Total Invested",     f"₹{ft['amount_inr'].sum()/1e7:.1f} Cr")
    k3.metric("Avg SIP Amount",     f"₹{sip_tx['amount_inr'].mean():,.0f}" if len(sip_tx) else "N/A")
    k4.metric("Avg Lumpsum",        f"₹{lump_tx['amount_inr'].mean():,.0f}" if len(lump_tx) else "N/A")

    st.markdown("<hr>", unsafe_allow_html=True)

    if ft.empty:
        st.warning("No data matches current filters.")
        return

    # ── Row 1: State bar + transaction type donut ─────────────────────
    col1, col2 = st.columns([1.4, 1])

    with col1:
        st.markdown('<div class="section-title">Investment by State (₹ Crore)</div>',
                    unsafe_allow_html=True)
        state_grp = (ft.groupby("state")["amount_inr"]
                       .sum().div(1e7)
                       .sort_values(ascending=True)
                       .reset_index())
        state_grp.columns = ["State","Amount (₹ Cr)"]
        fig = px.bar(state_grp, x="Amount (₹ Cr)", y="State",
                     orientation="h",
                     color="Amount (₹ Cr)",
                     color_continuous_scale=[[0,GREEN],[1,BLUE]])
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(chart(fig, 360), use_container_width=True, config={"displayModeBar":False})

    with col2:
        st.markdown('<div class="section-title">Transaction Type Split</div>',
                    unsafe_allow_html=True)
        tx_type = ft.groupby("transaction_type")["amount_inr"].sum().reset_index()
        fig2 = px.pie(tx_type, names="transaction_type", values="amount_inr",
                      hole=0.5, color_discrete_sequence=[BLUE, GREEN, AMBER])
        fig2.update_traces(textposition="outside", textinfo="percent+label")
        st.plotly_chart(chart(fig2, 360), use_container_width=True, config={"displayModeBar":False})

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Row 2: Age group SIP + Gender + T30/B30 ──────────────────────
    col3, col4, col5 = st.columns(3)

    with col3:
        st.markdown('<div class="section-title">Avg SIP by Age Group</div>',
                    unsafe_allow_html=True)
        age_order = ["18-25","26-35","36-45","46-55","56+"]
        age_sip = (sip_tx.groupby("age_group")["amount_inr"]
                         .mean().reindex(age_order).reset_index())
        age_sip.columns = ["Age Group","Avg SIP (₹)"]
        fig3 = px.bar(age_sip, x="Age Group", y="Avg SIP (₹)",
                      color="Avg SIP (₹)", color_continuous_scale=[[0,GREEN],[1,BLUE]])
        fig3.update_coloraxes(showscale=False)
        st.plotly_chart(chart(fig3, 300), use_container_width=True, config={"displayModeBar":False})

    with col4:
        st.markdown('<div class="section-title">Gender Split</div>',
                    unsafe_allow_html=True)
        gender = ft["gender"].value_counts().reset_index()
        gender.columns = ["Gender","Count"]
        fig4 = px.pie(gender, names="Gender", values="Count",
                      hole=0.45, color_discrete_sequence=[BLUE,"#E91E63"])
        fig4.update_traces(textinfo="percent+label")
        st.plotly_chart(chart(fig4, 300), use_container_width=True, config={"displayModeBar":False})

    with col5:
        st.markdown('<div class="section-title">T30 vs B30 Cities</div>',
                    unsafe_allow_html=True)
        tier = ft.groupby("city_tier")["amount_inr"].sum().reset_index()
        tier.columns = ["Tier","Amount"]
        fig5 = px.pie(tier, names="Tier", values="Amount",
                      hole=0.45, color_discrete_sequence=[BLUE, GREEN])
        fig5.update_traces(textinfo="percent+label")
        st.plotly_chart(chart(fig5, 300), use_container_width=True, config={"displayModeBar":False})

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Row 3: Monthly transaction volume ────────────────────────────
    st.markdown('<div class="section-title">Monthly Transaction Volume</div>',
                unsafe_allow_html=True)
    ft["month"] = ft["transaction_date"].dt.to_period("M").dt.to_timestamp()
    monthly = (ft.groupby(["month","transaction_type"])["amount_inr"]
                 .sum().div(1e7).reset_index())
    monthly.columns = ["Month","Type","Amount (₹ Cr)"]
    fig6 = px.line(monthly, x="Month", y="Amount (₹ Cr)", color="Type",
                   markers=False,
                   color_discrete_map={"SIP":BLUE,"Lumpsum":GREEN,"Redemption":RED})
    fig6.update_traces(line=dict(width=2))
    st.plotly_chart(chart(fig6, 320), use_container_width=True, config={"displayModeBar":False})


# ══════════════════════════════════════════════════════════════════════
# PAGE 4 — SIP & MARKET TRENDS
# ══════════════════════════════════════════════════════════════════════

def page_sip_trends(d):
    st.markdown("## 📊 SIP & Market Trends")

    sip   = d["sip_inflows"].sort_values("month")
    ci    = d["category_inflows"].copy()
    bench = d["benchmark_indices"].copy()

    # ── KPI row ───────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    sip_2022  = sip[sip["month"].dt.year == 2022]["sip_inflow_crore"].sum()
    sip_2025  = sip[sip["month"].dt.year == 2025]["sip_inflow_crore"].sum()
    sip_growth = (sip_2025 / sip_2022 - 1) * 100
    k1.metric("SIP Inflows 2022", f"₹{sip_2022/100:.0f}K Cr")
    k2.metric("SIP Inflows 2025", f"₹{sip_2025/100:.0f}K Cr", f"+{sip_growth:.0f}%")
    k3.metric("Peak Month",       "Dec 2025",   "₹31,002 Cr")
    k4.metric("Active SIP A/Cs",  "9.35 Cr",    "Dec 2025")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Dual-axis: SIP bar + Nifty50 line ────────────────────────────
    st.markdown('<div class="section-title">Monthly SIP Inflows vs Nifty 50 Index</div>',
                unsafe_allow_html=True)

    n50 = bench[bench["index_name"] == "NIFTY50"].sort_values("date").copy()
    # aggregate Nifty to monthly (last value per month)
    n50["month"] = n50["date"].dt.to_period("M").dt.to_timestamp()
    n50_monthly  = n50.groupby("month")["close_value"].last().reset_index()

    merged = sip.merge(n50_monthly, on="month", how="inner")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=merged["month"], y=merged["sip_inflow_crore"],
        name="SIP Inflow (₹ Cr)", marker_color=BLUE, opacity=0.8,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=merged["month"], y=merged["close_value"],
        name="Nifty 50", line=dict(color=AMBER, width=2.5),
        mode="lines",
    ), secondary_y=True)
    fig.update_yaxes(title_text="SIP Inflow (₹ Crore)", secondary_y=False)
    fig.update_yaxes(title_text="Nifty 50 Level", secondary_y=True)
    fig.update_layout(height=400, template="plotly_white",
                      margin=dict(l=10,r=10,t=30,b=10),
                      legend=dict(orientation="h", y=-0.18))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Category heatmap + top 5 ──────────────────────────────────────
    col1, col2 = st.columns([1.8, 1])

    with col1:
        st.markdown('<div class="section-title">Category-wise Net Inflows Heatmap</div>',
                    unsafe_allow_html=True)
        ci["month_lbl"] = ci["month"].dt.strftime("%b %y")
        pivot = ci.pivot_table(index="category", columns="month_lbl",
                               values="net_inflow_crore", aggfunc="sum")
        ordered_labels = [pd.Timestamp(m).strftime("%b %y")
                          for m in sorted(ci["month"].unique())]
        pivot = pivot.reindex(columns=[c for c in ordered_labels if c in pivot.columns])

        fig2 = px.imshow(pivot, color_continuous_scale="RdYlGn",
                         aspect="auto",
                         labels={"color":"Net Inflow (₹ Cr)"},
                         text_auto=".0f")
        fig2.update_xaxes(tickangle=45, tickfont=dict(size=8))
        fig2.update_layout(height=380, template="plotly_white",
                           margin=dict(l=10,r=10,t=30,b=10),
                           coloraxis_showscale=True)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})

    with col2:
        st.markdown('<div class="section-title">Top 5 Categories by Total Inflow</div>',
                    unsafe_allow_html=True)
        top_cats = (ci.groupby("category")["net_inflow_crore"]
                      .sum().nlargest(5).sort_values(ascending=True)
                      .reset_index())
        top_cats.columns = ["Category","Net Inflow (₹ Cr)"]
        fig3 = px.bar(top_cats, x="Net Inflow (₹ Cr)", y="Category",
                      orientation="h",
                      color="Net Inflow (₹ Cr)",
                      color_continuous_scale=[[0, GREEN],[1, BLUE]])
        fig3.update_coloraxes(showscale=False)
        for i, row in top_cats.iterrows():
            fig3.add_annotation(
                x=row["Net Inflow (₹ Cr)"],
                y=row["Category"],
                text=f"  ₹{row['Net Inflow (₹ Cr)']:.0f} Cr",
                xanchor="left", showarrow=False,
                font=dict(size=9),
            )
        st.plotly_chart(chart(fig3, 380), use_container_width=True, config={"displayModeBar":False})

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── YoY SIP growth bar ────────────────────────────────────────────
    st.markdown('<div class="section-title">SIP Inflow YoY Growth (%)</div>',
                unsafe_allow_html=True)
    sip_yoy = sip[sip["yoy_growth_pct"] > 0].copy()
    sip_yoy["month_lbl"] = sip_yoy["month"].dt.strftime("%b %y")
    fig4 = px.bar(sip_yoy, x="month_lbl", y="yoy_growth_pct",
                  color="yoy_growth_pct",
                  color_continuous_scale=[[0, AMBER],[0.5, GREEN],[1, BLUE]],
                  labels={"month_lbl":"Month","yoy_growth_pct":"YoY Growth (%)"})
    fig4.update_coloraxes(showscale=False)
    fig4.add_hline(y=0, line_color=GREY, line_dash="dot", opacity=0.5)
    st.plotly_chart(chart(fig4, 300), use_container_width=True, config={"displayModeBar":False})


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR + MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    # Sidebar header
    st.sidebar.markdown(f"""
    <div style='text-align:center; padding:12px 0 8px 0;'>
        <span style='font-size:1.6rem; font-weight:800; color:{BLUE};'>📊 Bluestock</span><br>
        <span style='font-size:0.78rem; color:#666;'>MF Analytics Platform</span>
    </div>
    """, unsafe_allow_html=True)
    st.sidebar.markdown("---")

    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["🏦 Industry Overview",
         "📈 Fund Performance",
         "👥 Investor Analytics",
         "📊 SIP & Market Trends"],
        label_visibility="collapsed",
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Data: AMFI India · mfapi.in · NSE/BSE\n"
                       "Period: Jan 2022 – May 2026\n"
                       "Schemes: 40 across 10 AMCs")

    # Load data (cached)
    if not DB_PATH.exists():
        st.error(f"Database not found at `{DB_PATH}`.\n"
                 "Run `python3 data_cleaning.py` then `python3 db_loader.py` first.")
        return

    d = load_data()

    # Route to page
    if   "Industry"  in page: page_industry(d)
    elif "Fund"      in page: page_performance(d)
    elif "Investor"  in page: page_investor(d)
    elif "SIP"       in page: page_sip_trends(d)


if __name__ == "__main__":
    main()