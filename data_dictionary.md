# Data Dictionary
## Bluestock Fintech — Mutual Fund Analytics Capstone

**Project:** Mutual Fund Analytics Platform  
**Source:** AMFI India, mfapi.in, NSE/BSE Public Data  
**Database:** `data/db/bluestock_mf.db` (SQLite)  
**Last Updated:** Day 2 — Data Cleaning & DB Load

---

## Table of Contents
1. [dim_fund](#dim_fund)
2. [dim_date](#dim_date)
3. [fact_nav](#fact_nav)
4. [fact_transactions](#fact_transactions)
5. [fact_performance](#fact_performance)
6. [fact_aum](#fact_aum)
7. [sip_inflows](#sip_inflows)
8. [category_inflows](#category_inflows)
9. [folio_count](#folio_count)
10. [portfolio_holdings](#portfolio_holdings)
11. [benchmark_indices](#benchmark_indices)

---

## dim_fund
**Source:** `01_fund_master.csv`  
**Rows:** 40  
**Description:** Master reference table for all 40 mutual fund schemes. One row per scheme.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `amfi_code` | INTEGER (PK) | Unique AMFI-assigned 6-digit scheme identifier | `119551` |
| `fund_house` | TEXT | Asset Management Company (AMC) name | `SBI Mutual Fund` |
| `scheme_name` | TEXT | Full official AMFI scheme name | `SBI Bluechip Fund - Regular Plan` |
| `category` | TEXT | Broad fund category | `Equity` / `Debt` / `Hybrid` |
| `sub_category` | TEXT | SEBI-defined sub-category | `Large Cap` / `Mid Cap` / `Liquid` |
| `plan` | TEXT | Plan type | `Regular` / `Direct` |
| `launch_date` | TEXT | Fund launch date (YYYY-MM-DD) | `2006-02-14` |
| `benchmark` | TEXT | Official benchmark index for comparison | `NIFTY 100 TRI` |
| `expense_ratio_pct` | REAL | Annual Total Expense Ratio (%) — fee charged to investors | `1.54` |
| `exit_load_pct` | REAL | Exit load % charged on early redemption | `1.0` |
| `min_sip_amount` | INTEGER | Minimum SIP investment in INR | `500` |
| `min_lumpsum_amount` | INTEGER | Minimum one-time investment in INR | `1000` |
| `fund_manager` | TEXT | Primary fund manager name | `Sohini Andani` |
| `risk_category` | TEXT | SEBI risk label | `Low` / `Moderate` / `High` / `Very High` |
| `sebi_category_code` | TEXT | Internal SEBI code | `EC01` (LargeCap), `EC03` (SmallCap) |

---

## dim_date
**Source:** Generated in Python (2022-01-01 to 2026-12-31)  
**Rows:** ~1,827  
**Description:** Date dimension table. Enables easy grouping by year, month, quarter without string parsing.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `date` | TEXT (PK) | Calendar date in ISO format YYYY-MM-DD | `2024-06-15` |
| `year` | INTEGER | Calendar year | `2024` |
| `month` | INTEGER | Month number 1–12 | `6` |
| `quarter` | INTEGER | Quarter number 1–4 | `2` |
| `month_name` | TEXT | Full month name | `June` |
| `day_of_week` | TEXT | Full day name | `Saturday` |
| `is_weekday` | INTEGER | 1 = Mon–Fri, 0 = Sat–Sun | `0` |

---

## fact_nav
**Source:** `02_nav_history.csv` (cleaned + forward-filled)  
**Rows:** ~47,000+ (after forward-filling market holidays)  
**Description:** Daily NAV history for all 40 schemes from Jan 2022 to May 2026. One row per scheme per business day.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `amfi_code` | INTEGER (FK) | References `dim_fund.amfi_code` | `119551` |
| `date` | TEXT (FK) | References `dim_date.date` | `2024-06-15` |
| `nav` | REAL | Net Asset Value in INR on that date | `72.4856` |
| `daily_return_pct` | REAL | (nav_t / nav_t-1 - 1) × 100 | `0.3421` |

**Notes:**
- Missing NAVs (market holidays, weekends) are forward-filled with the last known NAV
- Composite primary key: `(amfi_code, date)`
- `daily_return_pct` is NULL for the first row of each scheme (no prior day)

---

## fact_transactions
**Source:** `08_investor_transactions.csv`  
**Rows:** ~32,778  
**Description:** Individual investor transactions (SIP, Lumpsum, Redemption) across 5,000 investors in 12 states.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `investor_id` | TEXT | Unique investor identifier | `INV003054` |
| `transaction_date` | TEXT | Date of transaction (YYYY-MM-DD) | `2024-01-01` |
| `amfi_code` | INTEGER (FK) | Fund in which transaction occurred | `119092` |
| `transaction_type` | TEXT | Type of transaction | `SIP` / `Lumpsum` / `Redemption` |
| `amount_inr` | INTEGER | Transaction amount in Indian Rupees | `1834` |
| `state` | TEXT | Investor's state | `Telangana` |
| `city` | TEXT | Investor's city | `Hyderabad` |
| `city_tier` | TEXT | AMFI classification | `T30` (Top 30) / `B30` (Beyond Top 30) |
| `age_group` | TEXT | Investor age bracket | `18-25` / `26-35` / `36-45` / `46-55` / `56+` |
| `gender` | TEXT | Investor gender | `Male` / `Female` |
| `annual_income_lakh` | REAL | Annual income in lakh INR | `77.1` |
| `payment_mode` | TEXT | Payment method | `UPI` / `Net Banking` / `Mandate` / `Cheque` |
| `kyc_status` | TEXT | KYC verification status | `Verified` / `Pending` |

---

## fact_performance
**Source:** `07_scheme_performance.csv`  
**Rows:** 40  
**Description:** Pre-computed risk-return metrics for each scheme as of the report date (Dec 2025).

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `amfi_code` | INTEGER (PK, FK) | References `dim_fund.amfi_code` | `119551` |
| `scheme_name` | TEXT | Scheme name | `SBI Bluechip Fund - Regular` |
| `fund_house` | TEXT | AMC name | `SBI Mutual Fund` |
| `category` | TEXT | Equity / Debt / Hybrid | `Equity` |
| `plan` | TEXT | Regular / Direct | `Regular` |
| `return_1yr_pct` | REAL | 1-year absolute return % | `12.42` |
| `return_3yr_pct` | REAL | 3-year CAGR % | `12.36` |
| `return_5yr_pct` | REAL | 5-year CAGR % | `14.45` |
| `benchmark_3yr_pct` | REAL | Benchmark index 3yr CAGR % | `11.49` |
| `alpha` | REAL | Excess return above benchmark (return_3yr - benchmark_3yr) | `0.87` |
| `beta` | REAL | Market sensitivity — 1.0 means moves exactly with market | `0.89` |
| `sharpe_ratio` | REAL | (Return - Risk-free rate) / Std Dev — higher is better | `0.88` |
| `sortino_ratio` | REAL | Like Sharpe but only penalises downside volatility | `1.29` |
| `std_dev_ann_pct` | REAL | Annualised volatility % | `14.0` |
| `max_drawdown_pct` | REAL | Worst peak-to-trough decline — negative value | `-21.70` |
| `aum_crore` | INTEGER | Assets under management in crore INR | `14288` |
| `expense_ratio_pct` | REAL | Annual TER % | `1.54` |
| `morningstar_rating` | INTEGER | 1–5 star rating | `4` |
| `risk_grade` | TEXT | Risk label for fund | `Moderate` |

---

## fact_aum
**Source:** `03_aum_by_fund_house.csv`  
**Rows:** 90  
**Description:** Quarterly AUM figures for the 10 fund houses from 2022 to 2025. Sourced from AMFI quarterly reports.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `date` | TEXT | Quarter end date (YYYY-MM-DD) | `2022-03-31` |
| `fund_house` | TEXT | AMC name | `SBI Mutual Fund` |
| `aum_lakh_crore` | REAL | AUM in lakh crore INR | `6.05` |
| `aum_crore` | INTEGER | AUM in crore INR | `605000` |
| `num_schemes` | INTEGER | Number of active schemes | `186` |

---

## sip_inflows
**Source:** `04_monthly_sip_inflows.csv`  
**Rows:** 48  
**Description:** Industry-wide monthly SIP statistics from Jan 2022 to Dec 2025. Real figures from AMFI Monthly Notes.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `month` | TEXT (PK) | Month in YYYY-MM-DD format | `2025-12-01` |
| `sip_inflow_crore` | INTEGER | Total SIP inflows in crore INR | `31002` |
| `active_sip_accounts_crore` | REAL | Active SIP accounts in crore | `9.35` |
| `new_sip_accounts_lakh` | REAL | New SIP registrations that month (lakh) | `52.3` |
| `sip_aum_lakh_crore` | REAL | Total SIP AUM in lakh crore | `13.0` |
| `yoy_growth_pct` | REAL | YoY growth % in SIP inflows (0 for first 12 months) | `18.5` |

---

## category_inflows
**Source:** `05_category_inflows.csv`  
**Rows:** 144  
**Description:** Net inflows by fund category per month (FY 2024-25 data).

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `month` | TEXT | Month in YYYY-MM-DD format | `2024-04-01` |
| `category` | TEXT | Fund category | `Large Cap` / `Mid Cap` / `Small Cap` |
| `net_inflow_crore` | REAL | Net inflows into that category in crore INR | `3897.0` |

---

## folio_count
**Source:** `06_industry_folio_count.csv`  
**Rows:** 21  
**Description:** Total MF investor accounts (folios) over time, segmented by fund type.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `month` | TEXT (PK) | Month in YYYY-MM-DD format | `2025-12-01` |
| `total_folios_crore` | REAL | Total MF folios in crore | `26.12` |
| `equity_folios_crore` | REAL | Equity fund folios | `19.45` |
| `debt_folios_crore` | REAL | Debt fund folios | `2.10` |
| `hybrid_folios_crore` | REAL | Hybrid fund folios | `1.30` |
| `others_folios_crore` | REAL | Other category folios | `3.27` |

---

## portfolio_holdings
**Source:** `09_portfolio_holdings.csv`  
**Rows:** 322  
**Description:** Top stock holdings per equity fund as of Dec 2025.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `amfi_code` | INTEGER (FK) | References `dim_fund.amfi_code` | `119551` |
| `stock_symbol` | TEXT | NSE ticker symbol | `HDFCBANK` |
| `stock_name` | TEXT | Company full name | `HDFC Bank Ltd` |
| `sector` | TEXT | GICS sector classification | `Banking` |
| `weight_pct` | REAL | % of fund portfolio in this stock | `11.19` |
| `market_value_cr` | REAL | Market value of holding in crore INR | `88.97` |
| `current_price_inr` | REAL | Stock price as of portfolio date | `1074.65` |
| `portfolio_date` | TEXT | Holdings snapshot date | `2025-12-31` |

---

## benchmark_indices
**Source:** `10_benchmark_indices.csv`  
**Rows:** 8,050  
**Description:** Daily closing values for benchmark indices (Nifty 50, Nifty 100, BSE SmallCap etc.) from Jan 2022 to May 2026.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `date` | TEXT | Trading date (YYYY-MM-DD) | `2022-01-03` |
| `index_name` | TEXT | Index name | `NIFTY50` / `NIFTY100` / `BSESmallCap` |
| `close_value` | REAL | Index closing value on that date | `17492.79` |

---

## Key Relationships (Star Schema)

```
dim_fund ──────────┬──── fact_nav
    (amfi_code)    ├──── fact_transactions
                   ├──── fact_performance
                   └──── portfolio_holdings

dim_date ──────────┬──── fact_nav  (via date)
    (date)         └──── (use SUBSTR on transaction_date for joins)
```

---

## Data Quality Notes

| Issue | Table | Column | Resolution |
|-------|-------|--------|------------|
| 12 null values (first 12 months) | sip_inflows | yoy_growth_pct | Filled with 0 (no prior year to compare) |
| Missing NAV for market holidays | fact_nav | nav | Forward-filled with previous trading day NAV |
| All other tables | — | — | Zero nulls, zero duplicates |

---

*Generated: Day 2 — Bluestock Fintech MF Analytics Capstone*