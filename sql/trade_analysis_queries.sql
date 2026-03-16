-- =============================================================================
-- GLOBAL TRADE ANALYSIS — SQL QUERY PORTFOLIO
-- =============================================================================
-- Data Sources : UN Comtrade API, World Bank Development Indicators
-- Coverage     : 11 major economies, 5 commodity groups (HS codes), 2013–2023
-- Database     : PostgreSQL 15
-- Author       : Hazeezat Adebayo
-- =============================================================================


-- =============================================================================
-- SECTION 1: SCHEMA
-- =============================================================================

CREATE TABLE countries (
    country_code  VARCHAR(3)   PRIMARY KEY,
    country_name  VARCHAR(100) NOT NULL,
    region        VARCHAR(100),
    income_group  VARCHAR(50)
);

CREATE TABLE commodities (
    commodity_code  VARCHAR(10)  PRIMARY KEY,
    commodity_name  VARCHAR(200) NOT NULL,
    category        VARCHAR(100)
);

CREATE TABLE trade_flows (
    id             SERIAL       PRIMARY KEY,
    reporter_code  VARCHAR(3)   NOT NULL REFERENCES countries(country_code),
    partner_code   VARCHAR(3)   NOT NULL REFERENCES countries(country_code),
    commodity_code VARCHAR(10)  NOT NULL REFERENCES commodities(commodity_code),
    year           SMALLINT     NOT NULL,
    trade_flow     VARCHAR(10)  NOT NULL,
    value_usd      NUMERIC(20,2) NOT NULL,
    quantity_kg    NUMERIC(20,2)
);

CREATE TABLE wb_indicators (
    country_code   VARCHAR(3)  REFERENCES countries(country_code),
    year           SMALLINT    NOT NULL,
    gdp_usd        NUMERIC(20,2),
    gdp_growth_pct NUMERIC(6,3),
    inflation_pct  NUMERIC(6,3),
    population     BIGINT,
    PRIMARY KEY (country_code, year)
);

-- Indexes for faster joins
CREATE INDEX idx_trade_reporter ON trade_flows(reporter_code);
CREATE INDEX idx_trade_partner  ON trade_flows(partner_code);
CREATE INDEX idx_trade_year     ON trade_flows(year);

-- Constraints
ALTER TABLE trade_flows
    ADD CONSTRAINT chk_trade_flow
    CHECK (trade_flow IN ('Export', 'Import'));

ALTER TABLE trade_flows
    ADD CONSTRAINT uq_trade_flow
    UNIQUE (reporter_code, partner_code, commodity_code, year, trade_flow);


-- =============================================================================
-- SECTION 2: DATA VALIDATION
-- =============================================================================

-- Row counts across all tables
SELECT 'countries'    AS table_name, COUNT(*) AS rows FROM countries
UNION ALL
SELECT 'commodities',                COUNT(*)          FROM commodities
UNION ALL
SELECT 'wb_indicators',              COUNT(*)          FROM wb_indicators
UNION ALL
SELECT 'trade_flows',                COUNT(*)          FROM trade_flows;

-- Sample trade values for 2022 (spot-check)
SELECT
    c.country_name,
    t.commodity_code,
    t.year,
    t.trade_flow,
    ROUND(t.value_usd / 1e9, 2) AS value_billion_usd
FROM trade_flows t
JOIN countries c ON t.reporter_code = c.country_code
WHERE t.year = 2022
LIMIT 10;


-- =============================================================================
-- SECTION 3: TRADE VOLUME BY COUNTRY AND YEAR
-- =============================================================================
-- Total, export, and import values per country per year (billions USD).
-- Used as the basis for Chart 1.

SELECT
    c.country_name,
    t.year,
    ROUND(SUM(t.value_usd) / 1e9, 2)                                                       AS total_trade_billion,
    ROUND(SUM(CASE WHEN t.trade_flow = 'Export' THEN t.value_usd ELSE 0 END) / 1e9, 2)    AS exports_billion,
    ROUND(SUM(CASE WHEN t.trade_flow = 'Import' THEN t.value_usd ELSE 0 END) / 1e9, 2)    AS imports_billion
FROM trade_flows t
JOIN countries c ON t.reporter_code = c.country_code
GROUP BY c.country_name, t.year
ORDER BY t.year, total_trade_billion DESC;


-- =============================================================================
-- SECTION 4: TRADE BALANCE BY COUNTRY AND YEAR
-- =============================================================================
-- Exports minus imports per country per year, with surplus/deficit flag.
-- Used as the basis for Chart 2 (UK excluded due to data anomalies).

SELECT
    c.country_name,
    c.income_group,
    t.year,
    ROUND(
        SUM(CASE WHEN t.trade_flow = 'Export' THEN  t.value_usd
                 WHEN t.trade_flow = 'Import' THEN -t.value_usd
            END) / 1e9, 2
    ) AS trade_balance_billion,
    CASE
        WHEN SUM(CASE WHEN t.trade_flow = 'Export' THEN  t.value_usd
                      WHEN t.trade_flow = 'Import' THEN -t.value_usd
                 END) > 0 THEN 'Surplus'
        ELSE 'Deficit'
    END AS balance_status
FROM trade_flows t
JOIN countries c ON t.reporter_code = c.country_code
GROUP BY c.country_name, c.income_group, t.year
ORDER BY t.year, trade_balance_billion DESC;


-- =============================================================================
-- SECTION 5: YEAR-ON-YEAR TRADE GROWTH
-- =============================================================================
-- Uses a CTE + LAG() window function to calculate YoY % change in total trade.
-- NULL in first year of each country is expected (no prior year to compare).

WITH yearly_trade AS (
    SELECT
        c.country_name,
        t.year,
        ROUND(SUM(t.value_usd) / 1e9, 2) AS total_trade_billion
    FROM trade_flows t
    JOIN countries c ON t.reporter_code = c.country_code
    GROUP BY c.country_name, t.year
),
growth_calc AS (
    SELECT
        country_name,
        year,
        total_trade_billion,
        LAG(total_trade_billion) OVER (PARTITION BY country_name ORDER BY year) AS prev_year_billion
    FROM yearly_trade
)
SELECT
    country_name,
    year,
    total_trade_billion,
    prev_year_billion,
    ROUND(
        (total_trade_billion - prev_year_billion)
        / prev_year_billion * 100
    , 2) AS yoy_growth_pct
FROM growth_calc
ORDER BY country_name, year;


-- =============================================================================
-- SECTION 6: TOP 3 EXPORTS BY COUNTRY (2013–2023 CUMULATIVE)
-- =============================================================================
-- Uses RANK() OVER (PARTITION BY country) to find each country's top exports.
-- Used as the basis for Chart 3.

WITH commodity_ranks AS (
    SELECT
        c.country_name,
        cm.commodity_name,
        cm.category,
        ROUND(SUM(t.value_usd) / 1e9, 2) AS total_export_billion,
        RANK() OVER (
            PARTITION BY c.country_name
            ORDER BY SUM(t.value_usd) DESC
        ) AS rank
    FROM trade_flows t
    JOIN countries   c  ON t.reporter_code  = c.country_code
    JOIN commodities cm ON t.commodity_code = cm.commodity_code
    WHERE t.trade_flow = 'Export'
    GROUP BY c.country_name, cm.commodity_name, cm.category
)
SELECT
    country_name,
    rank,
    commodity_name,
    category,
    total_export_billion
FROM commodity_ranks
WHERE rank <= 3
ORDER BY country_name, rank;


-- =============================================================================
-- SECTION 7: TRADE OPENNESS — TRADE AS % OF GDP
-- =============================================================================
-- Joins trade_flows with wb_indicators to compute trade openness ratio.
-- Note: trade openness = (exports + imports) / GDP × 100.

SELECT
    c.country_name,
    c.region,
    t.year,
    ROUND(SUM(t.value_usd) / 1e9, 2)             AS total_trade_billion,
    ROUND(w.gdp_usd / 1e9, 2)                     AS gdp_billion,
    ROUND(SUM(t.value_usd) / NULLIF(w.gdp_usd, 0) * 100, 2)  AS trade_openness_pct,
    w.gdp_growth_pct,
    w.inflation_pct
FROM trade_flows t
JOIN countries     c ON t.reporter_code = c.country_code
JOIN wb_indicators w ON t.reporter_code = w.country_code
                    AND t.year           = w.year
GROUP BY c.country_name, c.region, t.year, w.gdp_usd, w.gdp_growth_pct, w.inflation_pct
ORDER BY t.year, trade_openness_pct DESC;


-- =============================================================================
-- END OF FILE
-- =============================================================================
