-- ============================================================
-- queries.sql
-- Day 2 — Task 6
-- Bluestock Fintech | Mutual Fund Analytics Capstone
--
-- 10 Analytical SQL Queries on bluestock_mf.db
-- Run these in DB Browser for SQLite or via Python sqlite3
-- ============================================================


-- ────────────────────────────────────────────────
-- QUERY 1: Top 5 funds by AUM (crore)
-- Business question: Which funds manage the most money?
-- ────────────────────────────────────────────────
SELECT
    scheme_name,
    fund_house,
    category,
    aum_crore,
    expense_ratio_pct,
    sharpe_ratio
FROM fact_performance
ORDER BY aum_crore DESC
LIMIT 5;


-- ────────────────────────────────────────────────
-- QUERY 2: Average NAV per month for each fund house
-- Business question: How has the average fund price trended over time?
-- ────────────────────────────────────────────────
SELECT
    d.year,
    d.month,
    d.month_name,
    f.fund_house,
    ROUND(AVG(n.nav), 2)  AS avg_nav
FROM fact_nav n
JOIN dim_date d ON n.date = d.date
JOIN dim_fund f ON n.amfi_code = f.amfi_code
WHERE d.year >= 2022
GROUP BY d.year, d.month, f.fund_house
ORDER BY d.year, d.month, f.fund_house;


-- ────────────────────────────────────────────────
-- QUERY 3: SIP inflow YoY growth by year
-- Business question: How fast is the SIP habit growing in India?
-- ────────────────────────────────────────────────
SELECT
    SUBSTR(month, 1, 4)            AS year,
    SUM(sip_inflow_crore)          AS total_sip_inflow_crore,
    ROUND(AVG(yoy_growth_pct), 2)  AS avg_yoy_growth_pct,
    ROUND(MAX(sip_inflow_crore))   AS peak_monthly_inflow
FROM sip_inflows
GROUP BY SUBSTR(month, 1, 4)
ORDER BY year;


-- ────────────────────────────────────────────────
-- QUERY 4: Total investment by state
-- Business question: Which states drive the most mutual fund investment?
-- ────────────────────────────────────────────────
SELECT
    state,
    city_tier,
    COUNT(*)                               AS num_transactions,
    ROUND(SUM(amount_inr) / 10000000.0, 2) AS total_invested_crore,
    ROUND(AVG(amount_inr), 0)              AS avg_transaction_inr
FROM fact_transactions
GROUP BY state, city_tier
ORDER BY total_invested_crore DESC;


-- ────────────────────────────────────────────────
-- QUERY 5: Funds with expense ratio below 1%
-- Business question: Which funds offer the most cost-efficient options?
-- ────────────────────────────────────────────────
SELECT
    f.scheme_name,
    f.fund_house,
    f.category,
    f.sub_category,
    f.plan,
    f.expense_ratio_pct,
    p.sharpe_ratio,
    p.return_3yr_pct
FROM dim_fund f
LEFT JOIN fact_performance p ON f.amfi_code = p.amfi_code
WHERE f.expense_ratio_pct < 1.0
ORDER BY f.expense_ratio_pct ASC;


-- ────────────────────────────────────────────────
-- QUERY 6: Top 5 funds by 3-year CAGR
-- Business question: Which funds delivered best long-term returns?
-- ────────────────────────────────────────────────
SELECT
    scheme_name,
    fund_house,
    category,
    return_3yr_pct,
    benchmark_3yr_pct,
    ROUND(return_3yr_pct - benchmark_3yr_pct, 2) AS alpha_vs_benchmark,
    sharpe_ratio,
    risk_grade
FROM fact_performance
ORDER BY return_3yr_pct DESC
LIMIT 5;


-- ────────────────────────────────────────────────
-- QUERY 7: Average SIP amount by investor age group
-- Business question: Which age group invests the most via SIP?
-- ────────────────────────────────────────────────
SELECT
    age_group,
    COUNT(*)                               AS num_sip_transactions,
    ROUND(AVG(amount_inr), 0)              AS avg_sip_amount_inr,
    ROUND(SUM(amount_inr) / 10000000.0, 2) AS total_invested_crore
FROM fact_transactions
WHERE transaction_type = 'SIP'
GROUP BY age_group
ORDER BY avg_sip_amount_inr DESC;


-- ────────────────────────────────────────────────
-- QUERY 8: Transaction breakdown by type
-- Business question: What proportion of activity is SIP vs Lumpsum vs Redemption?
-- ────────────────────────────────────────────────
SELECT
    transaction_type,
    COUNT(*)                                           AS num_transactions,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct_of_total,
    ROUND(SUM(amount_inr) / 10000000.0, 2)            AS total_crore,
    ROUND(AVG(amount_inr), 0)                          AS avg_amount_inr
FROM fact_transactions
GROUP BY transaction_type
ORDER BY num_transactions DESC;


-- ────────────────────────────────────────────────
-- QUERY 9: Top 5 risk-adjusted performers (Sharpe ratio)
-- Business question: Which funds deliver the best return per unit of risk?
-- ────────────────────────────────────────────────
SELECT
    scheme_name,
    fund_house,
    category,
    sharpe_ratio,
    sortino_ratio,
    return_3yr_pct,
    std_dev_ann_pct,
    max_drawdown_pct,
    morningstar_rating
FROM fact_performance
ORDER BY sharpe_ratio DESC
LIMIT 5;


-- ────────────────────────────────────────────────
-- QUERY 10: AUM growth by fund house (2022 vs 2025)
-- Business question: Which AMCs gained or lost market share over 4 years?
-- ────────────────────────────────────────────────
SELECT
    fund_house,
    SUM(CASE WHEN date LIKE '2022%' THEN aum_crore ELSE 0 END) AS aum_2022_crore,
    SUM(CASE WHEN date LIKE '2025%' THEN aum_crore ELSE 0 END) AS aum_2025_crore,
    ROUND(
        (SUM(CASE WHEN date LIKE '2025%' THEN aum_crore ELSE 0 END) -
         SUM(CASE WHEN date LIKE '2022%' THEN aum_crore ELSE 0 END)) * 100.0 /
        NULLIF(SUM(CASE WHEN date LIKE '2022%' THEN aum_crore ELSE 0 END), 0),
    1) AS growth_pct
FROM fact_aum
GROUP BY fund_house
ORDER BY aum_2025_crore DESC;