# Global Trade Analysis (2013–2023)

An end-to-end data analysis project exploring global trade patterns across 11 major economies using real-world data from the UN Comtrade API and World Bank Development Indicators.

Built with Python, PostgreSQL, and matplotlib — from raw API data to a structured relational database and publication-quality visualisations.

---

## Key Findings

- **The US trade deficit grew from -$618B (2013) to -$800B+ (2022–2023)** — the largest and most persistent deficit in the dataset, driven by machinery, electrical equipment, and vehicles.
- **Mexico's total trade volume approached Japan's by 2022** (~$705B vs ~$924B) despite having a fraction of Japan's GDP, reflecting deep manufacturing integration with the US.
- **COVID-19 caused a sharp trade contraction in 2020 across all economies**, with the US dropping from $2,178B (2018) to $1,889B — followed by a strong recovery peaking at $2,795B in 2022.
- **Export specialisation varies dramatically by economy**: the US exports broadly across all 5 commodity groups; Japan dominates in vehicles; Brazil and Canada are heavily concentrated in mineral fuels.

---

## Charts

### Chart 1 — Total Trade Volume by Country (2013–2023)
![Total Trade Volume](charts/chart1_trade_over_time.png)

### Chart 2 — Trade Balance by Country (2013–2023)
![Trade Balance](charts/chart2_trade_balance.png)

> United Kingdom excluded due to data anomalies in Comtrade reporting

### Chart 3 — Total Exports by Commodity and Country (2013–2023)
![Export Commodities](charts/chart3_export_commodities.png)

---

## Database Schema

Built in PostgreSQL with 4 normalised tables, foreign key constraints, indexes, and data integrity checks.

| Table | Rows | Description |
|---|---|---|
| `countries` | 13 | Country metadata — region, income group |
| `commodities` | 5 | HS commodity codes and categories |
| `trade_flows` | 957 | Export/import values by country, commodity, year |
| `wb_indicators` | 132 | GDP, growth, inflation, population per country/year |

---

## Project Structure

```
global-trade-analysis/
├── data/
│   ├── countries.csv
│   ├── commodities.csv
│   ├── wb_indicators.csv
│   └── trade_flows_cleaned.csv
├── charts/
│   ├── chart1_trade_over_time.png
│   ├── chart2_trade_balance.png
│   └── chart3_export_commodities.png
├── sql/
│   └── trade_analysis_queries.sql
├── notebooks/
│   └── trade_analysis.py
└── README.md
```

---

## SQL Highlights

The `sql/trade_analysis_queries.sql` file demonstrates:

- Aggregations with `GROUP BY` and `CASE WHEN` for export/import splits
- Trade balance calculation (exports minus imports) with surplus/deficit classification
- Year-on-year growth using CTEs and `LAG()` window functions
- Export ranking with `RANK() OVER (PARTITION BY country)`
- Multi-table joins across trade flows and macroeconomic indicators
- Trade openness ratio (trade as % of GDP) using `NULLIF` for safe division

---

## Skills Demonstrated

- API data ingestion (UN Comtrade, World Bank)
- Data cleaning and transformation (Python, pandas)
- Relational database design (PostgreSQL, foreign keys, constraints)
- SQL analytics and window functions
- Data visualisation and storytelling (matplotlib)

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3 | ETL pipeline, data cleaning, visualisation |
| pandas | Data manipulation and transformation |
| wbgapi | World Bank indicators API |
| comtradeapicall | UN Comtrade trade flows API |
| psycopg2 | PostgreSQL data loading |
| SQLAlchemy | Database querying for visualisation |
| matplotlib | Chart production |
| PostgreSQL 15 | Relational database storage |

---

## Data Sources

- **UN Comtrade** — bilateral trade flows by HS commodity code (2-digit), annual, 2013–2023
- **World Bank Development Indicators** — GDP, GDP growth, inflation, population

---

## Known Limitations

- India returned 0 trade flow rows from the Comtrade API — documented but excluded from analysis
- China, Germany, France, and Canada have incomplete year coverage due to the Comtrade 500-row API cap — excluded from time-series charts
- United Kingdom trade balance shows anomalous spikes in 2017, 2019, and 2020 — excluded from Chart 2
