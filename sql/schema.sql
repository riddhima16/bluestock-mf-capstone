-- ============================================================
-- schema.sql
-- Day 2 — Task 4
-- Bluestock Fintech | Mutual Fund Analytics Capstone
--
-- Star Schema Design for bluestock_mf.db (SQLite)
-- 2 Dimension tables + 4 Fact tables + 5 Supporting tables
--
-- Relationships:
--   fact_nav.amfi_code         → dim_fund.amfi_code
--   fact_nav.date              → dim_date.date
--   fact_transactions.amfi_code→ dim_fund.amfi_code
--   fact_performance.amfi_code → dim_fund.amfi_code
--   fact_aum.fund_house        → dim_fund.fund_house (soft)
--   portfolio_holdings.amfi_code → dim_fund.amfi_code
-- ============================================================

PRAGMA foreign_keys = ON;

-- ────────────────────────────────────────────────
-- DIMENSION TABLES
-- ────────────────────────────────────────────────

-- dim_fund: one row per mutual fund scheme
-- Primary key: amfi_code (AMFI-assigned unique 6-digit scheme identifier)
CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code          INTEGER  PRIMARY KEY,
    fund_house         TEXT     NOT NULL,     -- AMC name e.g. SBI Mutual Fund
    scheme_name        TEXT     NOT NULL,     -- Full AMFI scheme name
    category           TEXT,                 -- Equity / Debt / Hybrid
    sub_category       TEXT,                 -- Large Cap / Mid Cap / Liquid etc.
    plan               TEXT,                 -- Regular or Direct
    launch_date        TEXT,                 -- ISO date YYYY-MM-DD
    benchmark          TEXT,                 -- Official benchmark index
    expense_ratio_pct  REAL,                 -- Annual TER in % (0.1 – 2.5)
    exit_load_pct      REAL,                 -- Exit load % (0 for index/liquid)
    min_sip_amount     INTEGER,              -- Minimum SIP in INR
    min_lumpsum_amount INTEGER,              -- Minimum lumpsum in INR
    fund_manager       TEXT,                 -- Primary fund manager name
    risk_category      TEXT,                 -- SEBI: Low/Moderate/High/Very High
    sebi_category_code TEXT                  -- e.g. EC01=LargeCap, DC01=Liquid
);

-- dim_date: one row per calendar day 2022-01-01 to 2026-12-31
-- Generated in Python; used to join time-series facts for easy grouping
CREATE TABLE IF NOT EXISTS dim_date (
    date        TEXT    PRIMARY KEY,  -- ISO format YYYY-MM-DD
    year        INTEGER,
    month       INTEGER,              -- 1–12
    quarter     INTEGER,              -- 1–4
    month_name  TEXT,                 -- January … December
    day_of_week TEXT,                 -- Monday … Sunday
    is_weekday  INTEGER               -- 1 = Mon–Fri, 0 = Sat–Sun
);

-- ────────────────────────────────────────────────
-- FACT TABLES
-- ────────────────────────────────────────────────

-- fact_nav: daily NAV for each of 40 schemes
-- Grain: one row per scheme per business day
CREATE TABLE IF NOT EXISTS fact_nav (
    amfi_code        INTEGER  NOT NULL,
    date             TEXT     NOT NULL,
    nav              REAL     NOT NULL,   -- NAV in INR
    daily_return_pct REAL,               -- (nav_t/nav_t-1 - 1) * 100
    PRIMARY KEY (amfi_code, date),
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code),
    FOREIGN KEY (date)      REFERENCES dim_date(date)
);

-- fact_transactions: individual investor SIP/Lumpsum/Redemption events
-- Grain: one row per transaction (~32,000 rows)
CREATE TABLE IF NOT EXISTS fact_transactions (
    investor_id          TEXT,
    transaction_date     TEXT,
    amfi_code            INTEGER,
    transaction_type     TEXT,    -- SIP / Lumpsum / Redemption
    amount_inr           INTEGER,
    state                TEXT,
    city                 TEXT,
    city_tier            TEXT,    -- T30 (Top 30 cities) or B30 (Beyond Top 30)
    age_group            TEXT,    -- 18-25 / 26-35 / 36-45 / 46-55 / 56+
    gender               TEXT,
    annual_income_lakh   REAL,
    payment_mode         TEXT,    -- UPI / Net Banking / Mandate / Cheque
    kyc_status           TEXT,    -- Verified / Pending
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- fact_performance: pre-computed risk-return metrics per scheme
-- Grain: one row per scheme (40 rows)
CREATE TABLE IF NOT EXISTS fact_performance (
    amfi_code          INTEGER  PRIMARY KEY,
    scheme_name        TEXT,
    fund_house         TEXT,
    category           TEXT,
    plan               TEXT,
    return_1yr_pct     REAL,    -- 1-year absolute return %
    return_3yr_pct     REAL,    -- 3-year CAGR %
    return_5yr_pct     REAL,    -- 5-year CAGR %
    benchmark_3yr_pct  REAL,    -- Benchmark 3yr CAGR for comparison
    alpha              REAL,    -- Excess return vs benchmark
    beta               REAL,    -- Market sensitivity (1.0 = same as market)
    sharpe_ratio       REAL,    -- Risk-adjusted return (higher = better)
    sortino_ratio      REAL,    -- Like Sharpe but penalises downside only
    std_dev_ann_pct    REAL,    -- Annualised volatility %
    max_drawdown_pct   REAL,    -- Worst peak-to-trough decline (negative)
    aum_crore          INTEGER, -- Assets under management in crore INR
    expense_ratio_pct  REAL,    -- Annual TER %
    morningstar_rating INTEGER, -- 1–5 stars
    risk_grade         TEXT,    -- Moderate / High / Very High
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- fact_aum: quarterly AUM by fund house (2022–2025)
-- Grain: one row per fund house per quarter
CREATE TABLE IF NOT EXISTS fact_aum (
    date            TEXT,         -- Quarter end date e.g. 2022-03-31
    fund_house      TEXT,
    aum_lakh_crore  REAL,         -- AUM in lakh crore INR
    aum_crore       INTEGER,      -- AUM in crore INR
    num_schemes     INTEGER       -- Number of schemes managed
);

-- ────────────────────────────────────────────────
-- SUPPORTING TABLES
-- ────────────────────────────────────────────────

-- sip_inflows: industry-level monthly SIP data (real AMFI figures)
CREATE TABLE IF NOT EXISTS sip_inflows (
    month                       TEXT  PRIMARY KEY,   -- YYYY-MM-DD
    sip_inflow_crore            INTEGER,
    active_sip_accounts_crore   REAL,
    new_sip_accounts_lakh       REAL,
    sip_aum_lakh_crore          REAL,
    yoy_growth_pct              REAL
);

-- category_inflows: net inflows by fund category per month
CREATE TABLE IF NOT EXISTS category_inflows (
    month             TEXT,
    category          TEXT,
    net_inflow_crore  REAL
);

-- folio_count: total MF folios (investor accounts) over time
CREATE TABLE IF NOT EXISTS folio_count (
    month                TEXT  PRIMARY KEY,   -- YYYY-MM-DD
    total_folios_crore   REAL,
    equity_folios_crore  REAL,
    debt_folios_crore    REAL,
    hybrid_folios_crore  REAL,
    others_folios_crore  REAL
);

-- portfolio_holdings: top equity holdings per fund as of Dec 2025
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    amfi_code          INTEGER,
    stock_symbol       TEXT,
    stock_name         TEXT,
    sector             TEXT,
    weight_pct         REAL,         -- % of portfolio in this stock
    market_value_cr    REAL,         -- Market value in crore INR
    current_price_inr  REAL,
    portfolio_date     TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

-- benchmark_indices: daily closing values for Nifty 50, Nifty 100, etc.
CREATE TABLE IF NOT EXISTS benchmark_indices (
    date         TEXT,
    index_name   TEXT,
    close_value  REAL
);

-- ────────────────────────────────────────────────
-- INDEXES for query performance
-- ────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_nav_date       ON fact_nav(date);
CREATE INDEX IF NOT EXISTS idx_nav_amfi       ON fact_nav(amfi_code);
CREATE INDEX IF NOT EXISTS idx_tx_date        ON fact_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_tx_amfi        ON fact_transactions(amfi_code);
CREATE INDEX IF NOT EXISTS idx_tx_state       ON fact_transactions(state);
CREATE INDEX IF NOT EXISTS idx_bench_date     ON benchmark_indices(date);
CREATE INDEX IF NOT EXISTS idx_bench_name     ON benchmark_indices(index_name);