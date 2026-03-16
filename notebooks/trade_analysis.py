# =============================================================================
# GLOBAL TRADE ANALYSIS — ETL + VISUALISATION PIPELINE
# =============================================================================
# Data Sources : UN Comtrade API, World Bank Development Indicators
# Coverage     : 11 major economies, 5 commodity groups (HS codes), 2013–2023
# =============================================================================


# ── CELL 1: Imports & Config ──────────────────────────────────────────────────

import wbgapi as wb
import pandas as pd
print("Libraries loaded ✅")
print(f"pandas version: {pd.__version__}")

COUNTRIES = {
    'USA': 'United States',
    'GBR': 'United Kingdom',
    'DEU': 'Germany',
    'FRA': 'France',
    'JPN': 'Japan',
    'CAN': 'Canada',
    'ITA': 'Italy',
    'CHN': 'China',
    'IND': 'India',
    'BRA': 'Brazil',
    'ZAF': 'South Africa',
    'MEX': 'Mexico'
}

YEARS = range(2013, 2024)

INDICATORS = {
    'NY.GDP.MKTP.CD':    'gdp_usd',
    'NY.GDP.MKTP.KD.ZG': 'gdp_growth_pct',
    'FP.CPI.TOTL.ZG':    'inflation_pct',
    'SP.POP.TOTL':        'population'
}

print(f"Countries: {len(COUNTRIES)}")
print(f"Years: {min(YEARS)} - {max(YEARS)}")
print(f"Indicators: {len(INDICATORS)}")


# ── CELL 2: Fetch World Bank Indicators ──────────────────────────────────────

print("Fetching World Bank indicators...")
frames = []

for wb_code, col_name in INDICATORS.items():
    print(f"  → Fetching: {col_name} ({wb_code})")
    df = wb.data.DataFrame(
        wb_code,
        economy=list(COUNTRIES.keys()),
        time=YEARS,
        labels=False
    )
    df = df.reset_index().melt(
        id_vars='economy',
        var_name='year',
        value_name=col_name
    )
    df['year'] = df['year'].str.replace('YR', '').astype(int)
    df.rename(columns={'economy': 'country_code'}, inplace=True)
    frames.append(df)
    print(f"     ✅ {len(df)} rows fetched")

print("\nAll indicators fetched!")

wb_df = frames[0]
for df in frames[1:]:
    wb_df = wb_df.merge(df, on=['country_code', 'year'], how='outer')

wb_df = wb_df.sort_values(['country_code', 'year']).reset_index(drop=True)
print(f"Shape: {wb_df.shape}")
print(f"Columns: {list(wb_df.columns)}")
wb_df.head(12)


# ── CELL 3: Clean World Bank Data ─────────────────────────────────────────────

wb_df['gdp_usd']        = wb_df['gdp_usd'].round(2)
wb_df['gdp_growth_pct'] = wb_df['gdp_growth_pct'].round(3)
wb_df['inflation_pct']  = wb_df['inflation_pct'].round(3)
wb_df['population']     = wb_df['population'].round(0).astype('Int64')

print("Missing values per column:")
print(wb_df.isnull().sum())
print(f"\nTotal rows: {len(wb_df)}")


# ── CELL 4: Build Countries Table ─────────────────────────────────────────────

COUNTRY_META = {
    'USA': ('North America',      'High income'),
    'GBR': ('Europe',             'High income'),
    'DEU': ('Europe',             'High income'),
    'FRA': ('Europe',             'High income'),
    'JPN': ('East Asia',          'High income'),
    'CAN': ('North America',      'High income'),
    'ITA': ('Europe',             'High income'),
    'CHN': ('East Asia',          'Upper middle income'),
    'IND': ('South Asia',         'Lower middle income'),
    'BRA': ('Latin America',      'Upper middle income'),
    'ZAF': ('Sub-Saharan Africa', 'Upper middle income'),
    'MEX': ('Latin America',      'Upper middle income'),
}

countries_df = pd.DataFrame([
    {
        'country_code': code,
        'country_name': name,
        'region':       COUNTRY_META[code][0],
        'income_group': COUNTRY_META[code][1]
    }
    for code, name in COUNTRIES.items()
])

print(f"Countries table: {len(countries_df)} rows")
print(countries_df)


# ── CELL 5: Save World Bank CSVs ──────────────────────────────────────────────

wb_df.to_csv('wb_indicators.csv', index=False)
countries_df.to_csv('countries.csv', index=False)
print("✅ wb_indicators.csv saved")
print("✅ countries.csv saved")


# ── CELL 6: Comtrade Config ───────────────────────────────────────────────────

import comtradeapicall as ct

COMTRADE_API_KEY = "8bb4e1c3a2844a72ac950cda93bb1e31"

COMMODITIES = {
    '27': 'Mineral fuels & oil',
    '84': 'Machinery & mechanical appliances',
    '85': 'Electrical machinery & equipment',
    '87': 'Vehicles',
    '30': 'Pharmaceuticals'
}

# FIX: Corrected France (250) and Italy (380) — previous values 251 and 381
# were wrong UN numeric codes and would return no data.
COMTRADE_CODES = {
    'USA': '842',
    'GBR': '826',
    'DEU': '276',
    'FRA': '250',   # Fixed: was 251
    'JPN': '392',
    'CAN': '124',
    'ITA': '380',   # Fixed: was 381
    'CHN': '156',
    'IND': '356',
    'BRA': '076',
    'ZAF': '710',
    'MEX': '484'
}

print("✅ API key set")
print(f"Commodities to fetch: {len(COMMODITIES)}")
for code, name in COMMODITIES.items():
    print(f"  {code} → {name}")


# ── CELL 7: Comtrade API Test ─────────────────────────────────────────────────

test = ct.getFinalData(
    subscription_key = COMTRADE_API_KEY,
    typeCode         = 'C',
    freqCode         = 'A',
    clCode           = 'HS',
    reporterCode     = '842',
    period           = '2022',
    partnerCode      = '0',
    partner2Code     = None,
    cmdCode          = '27',
    flowCode         = 'X',
    customsCode      = 'C00',
    motCode          = '0',
    maxRecords       = 5,
    includeDesc      = True
)

if test is not None and len(test) > 0:
    print(f"✅ Test fetch returned: {len(test)} rows")
    print(test[['reporterCode', 'refYear', 'cmdCode', 'primaryValue']].head())
else:
    print("❌ No data returned")
    print(test)


# ── CELL 8: Fetch All Trade Data ──────────────────────────────────────────────

import time

all_rows = []
errors   = []
total    = len(COMTRADE_CODES) * len(COMMODITIES)
count    = 0

print(f"Fetching {total} combinations (12 countries × 5 commodities)...\n")

for iso3, numeric_code in COMTRADE_CODES.items():
    for cmd_code, cmd_name in COMMODITIES.items():
        count += 1
        print(f"[{count}/{total}] {iso3} | {cmd_name}...", end=' ')

        try:
            df = ct.getFinalData(
                subscription_key = COMTRADE_API_KEY,
                typeCode         = 'C',
                freqCode         = 'A',
                clCode           = 'HS',
                reporterCode     = numeric_code,
                period           = '2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023',
                partnerCode      = '0',
                partner2Code     = None,
                cmdCode          = cmd_code,
                flowCode         = 'X,M',
                customsCode      = 'C00',
                motCode          = '0',
                maxRecords       = 500,
                includeDesc      = True
            )

            if df is not None and len(df) > 0:
                df['iso3'] = iso3
                all_rows.append(df)
                print(f"✅ {len(df)} rows")
            else:
                print("⚠️ No data")
                errors.append(f"{iso3} | {cmd_code}")

        except Exception as e:
            print(f"❌ Error: {e}")
            errors.append(f"{iso3} | {cmd_code}")

        time.sleep(1.5)

print(f"\n✅ Done! Successful fetches: {len(all_rows)}")
print(f"⚠️  Empty/failed: {len(errors)}")
if errors:
    print(f"   Failed combinations: {errors}")


# ── CELL 9: Clean Trade Data ──────────────────────────────────────────────────

trade_df = pd.concat(all_rows, ignore_index=True)

print(f"Total rows before cleaning: {len(trade_df)}")
print(f"\nColumns returned by API:")
print(trade_df.columns.tolist())

trade_df = trade_df[[
    'iso3', 'partnerISO', 'cmdCode', 'refYear', 'flowDesc', 'primaryValue', 'netWgt'
]]

trade_df = trade_df.rename(columns={
    'iso3'        : 'reporter_code',
    'partnerISO'  : 'partner_code',
    'cmdCode'     : 'commodity_code',
    'refYear'     : 'year',
    'flowDesc'    : 'trade_flow',
    'primaryValue': 'value_usd',
    'netWgt'      : 'quantity_kg'
})

trade_df = trade_df[trade_df['partner_code'] == 'W00']

trade_df['value_usd']   = trade_df['value_usd'].fillna(0)
trade_df['quantity_kg'] = trade_df['quantity_kg'].fillna(0)

trade_df['year']        = trade_df['year'].astype(int)
trade_df['value_usd']   = trade_df['value_usd'].astype(float).round(2)
trade_df['quantity_kg'] = trade_df['quantity_kg'].astype(float).round(2)

dupe_cols = ['reporter_code', 'partner_code', 'commodity_code', 'year', 'trade_flow']
before    = len(trade_df)
trade_df  = trade_df.drop_duplicates(subset=dupe_cols)
after     = len(trade_df)
print(f"Duplicates removed: {before - after}")
print(f"Rows after dedup:   {after}")

# Replace 0 quantity_kg with NULL (more honest — quantity often unreported)
trade_df['quantity_kg'] = trade_df['quantity_kg'].replace(0, None)

print(f"\nMissing values:")
print(trade_df.isnull().sum())
print(f"\nTrade flow values:")
print(trade_df['trade_flow'].value_counts())
print(f"\nYears covered: {sorted(trade_df['year'].unique())}")
print(f"\nCountries covered: {sorted(trade_df['reporter_code'].unique())}")
trade_df.head(6)


# ── CELL 10: Add World Row + Save CSVs ────────────────────────────────────────

world_row = pd.DataFrame([{
    'country_code': 'W00',
    'country_name': 'World',
    'region':       'Global',
    'income_group': 'Aggregate'
}])
countries_df = pd.concat([countries_df, world_row], ignore_index=True)
countries_df.to_csv('countries.csv', index=False)
print(f"✅ countries.csv updated → {len(countries_df)} rows (includes World)")

trade_df.to_csv('trade_flows_cleaned.csv', index=False)
print(f"✅ trade_flows_cleaned.csv saved → {len(trade_df)} rows")

commodities_df = pd.DataFrame([
    {'commodity_code': '27', 'commodity_name': 'Mineral fuels, mineral oils and products', 'category': 'Energy'},
    {'commodity_code': '84', 'commodity_name': 'Machinery and mechanical appliances',      'category': 'Industrial'},
    {'commodity_code': '85', 'commodity_name': 'Electrical machinery and equipment',       'category': 'Industrial'},
    {'commodity_code': '87', 'commodity_name': 'Vehicles and transport equipment',         'category': 'Transport'},
    {'commodity_code': '30', 'commodity_name': 'Pharmaceutical products',                  'category': 'Healthcare'},
])
commodities_df.to_csv('commodities.csv', index=False)
print(f"✅ commodities.csv saved → {len(commodities_df)} rows")
print(commodities_df)


# ── CELL 11: Load into PostgreSQL ─────────────────────────────────────────────

import psycopg2
from psycopg2.extras import execute_values
import numpy as np

conn = psycopg2.connect(
    host     = 'localhost',
    dbname   = 'trade_analysis',
    user     = 'postgres',
    password = '1234',
    port     = 5432
)
cur = conn.cursor()
print("✅ Connected to trade_analysis database")

def clean_row(row):
    """Replace NaN/None with None for psycopg2 compatibility."""
    return [None if (v is None or (isinstance(v, float) and np.isnan(v))) else v for v in row]

# Load countries
countries_data = [clean_row(row) for row in countries_df.values.tolist()]
execute_values(cur,
    "INSERT INTO countries (country_code, country_name, region, income_group) VALUES %s ON CONFLICT DO NOTHING",
    countries_data
)
print(f"✅ countries loaded → {len(countries_data)} rows")

# Load commodities
commodities_data = [clean_row(row) for row in commodities_df.values.tolist()]
execute_values(cur,
    "INSERT INTO commodities (commodity_code, commodity_name, category) VALUES %s ON CONFLICT DO NOTHING",
    commodities_data
)
print(f"✅ commodities loaded → {len(commodities_data)} rows")

# Load World Bank indicators
wb_data = [clean_row(row) for row in wb_df[['country_code', 'year', 'gdp_usd', 'gdp_growth_pct', 'inflation_pct', 'population']].values.tolist()]
execute_values(cur,
    "INSERT INTO wb_indicators (country_code, year, gdp_usd, gdp_growth_pct, inflation_pct, population) VALUES %s ON CONFLICT DO NOTHING",
    wb_data
)
print(f"✅ wb_indicators loaded → {len(wb_data)} rows")

# Load trade flows
trade_data = [clean_row(row) for row in trade_df[['reporter_code', 'partner_code', 'commodity_code', 'year', 'trade_flow', 'value_usd', 'quantity_kg']].values.tolist()]
execute_values(cur,
    "INSERT INTO trade_flows (reporter_code, partner_code, commodity_code, year, trade_flow, value_usd, quantity_kg) VALUES %s ON CONFLICT DO NOTHING",
    trade_data
)
print(f"✅ trade_flows loaded → {len(trade_data)} rows")

conn.commit()
cur.close()
conn.close()
print("\n🎉 All data loaded and committed to PostgreSQL!")


# ── CELL 12: Connect for Visualisation ───────────────────────────────────────

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from sqlalchemy import create_engine

engine = create_engine('postgresql://postgres:1234@localhost:5432/trade_analysis')
print("✅ Connected to trade_analysis")

# Coverage check
complete = pd.read_sql("""
    SELECT 
        c.country_name,
        COUNT(DISTINCT t.year) AS years_present,
        MIN(t.year)            AS first_year,
        MAX(t.year)            AS last_year
    FROM trade_flows t
    JOIN countries c ON t.reporter_code = c.country_code
    WHERE c.country_name != 'World'
    GROUP BY c.country_name
    ORDER BY years_present DESC, c.country_name
""", engine)
print(complete.to_string(index=False))


# ── CELL 13: Chart 1 — Total Trade Volume ────────────────────────────────────

query1 = """
    SELECT 
        c.country_name,
        t.year,
        ROUND(SUM(t.value_usd) / 1e9, 2) AS total_trade_billion
    FROM trade_flows t
    JOIN countries c ON t.reporter_code = c.country_code
    WHERE c.country_name != 'World'
    GROUP BY c.country_name, t.year
    ORDER BY c.country_name, t.year
"""
df_trade = pd.read_sql(query1, engine)
print(f"✅ Rows fetched: {len(df_trade)}")

fig, ax = plt.subplots(figsize=(14, 7))

full_coverage = ['United States', 'Japan', 'Mexico', 'Brazil',
                 'Italy', 'South Africa', 'United Kingdom']
highlight     = ['United States', 'Japan', 'Mexico', 'Brazil']
colors        = {
    'United States': '#457b9d',
    'Japan':         '#e9c46a',
    'Mexico':        '#e63946',
    'Brazil':        '#2a9d8f'
}

for country, group in df_trade.groupby('country_name'):
    if country not in full_coverage:
        continue
    if country in highlight:
        ax.plot(group['year'], group['total_trade_billion'],
                label=country, color=colors[country],
                linewidth=2.5, marker='o', markersize=4)
    else:
        ax.plot(group['year'], group['total_trade_billion'],
                color='#cccccc', linewidth=1.2, alpha=0.6)

# FIX: Draw COVID line first, then get ylim — ensures annotation is positioned correctly
ax.axvline(x=2020, color='#999999', linestyle='--', linewidth=1.2)
ax.set_xlim(2013, 2023)
ymin, ymax = ax.get_ylim()
ax.text(2020.1, ymax * 0.92, 'COVID-19\n(2020)',
        fontsize=9, color='#666666', va='top')

ax.set_title('Total Trade Volume by Country (2013–2023)',
             fontsize=15, fontweight='bold', pad=15)
ax.set_xlabel('Year', fontsize=11)
ax.set_ylabel('Trade Value (USD Billion)', fontsize=11)
ax.legend(loc='upper left', fontsize=9)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}B'))
ax.set_xticks(range(2013, 2024))
ax.grid(axis='y', alpha=0.3)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
plt.savefig('chart1_trade_over_time.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ chart1_trade_over_time.png saved")


# ── CELL 14: Chart 2 — Trade Balance ─────────────────────────────────────────

query2 = """
    SELECT 
        c.country_name,
        t.year,
        ROUND(SUM(CASE WHEN t.trade_flow = 'Export' THEN  t.value_usd
                       WHEN t.trade_flow = 'Import' THEN -t.value_usd
                  END) / 1e9, 2) AS trade_balance_billion
    FROM trade_flows t
    JOIN countries c ON t.reporter_code = c.country_code
    WHERE c.country_name IN ('United States', 'Japan', 'Mexico',
                             'Brazil', 'Italy', 'South Africa')
    GROUP BY c.country_name, t.year
    ORDER BY c.country_name, t.year
"""
df_balance = pd.read_sql(query2, engine)
print(f"✅ Rows fetched: {len(df_balance)}")

fig, ax = plt.subplots(figsize=(14, 7))

highlight      = ['United States', 'Japan', 'Mexico', 'Brazil']
colors_balance = {
    'United States': '#457b9d',
    'Japan':         '#e9c46a',
    'Mexico':        '#e63946',
    'Brazil':        '#2a9d8f',
    'Italy':         '#cccccc',
    'South Africa':  '#cccccc'
}

for country, group in df_balance.groupby('country_name'):
    if country in highlight:
        ax.plot(group['year'], group['trade_balance_billion'],
                label=country, color=colors_balance[country],
                linewidth=2.5, marker='o', markersize=4)
    else:
        ax.plot(group['year'], group['trade_balance_billion'],
                color='#cccccc', linewidth=1.2, alpha=0.6)

ax.axhline(y=0, color='black', linewidth=1, linestyle='-')
ax.text(2013.1,  20, 'SURPLUS', fontsize=8, color='#2a9d8f', fontweight='bold')
ax.text(2013.1, -50, 'DEFICIT', fontsize=8, color='#e63946', fontweight='bold')

# FIX: Same COVID annotation fix as Chart 1
ax.axvline(x=2020, color='#999999', linestyle='--', linewidth=1.2)
ax.set_xlim(2013, 2023)
ymin, ymax = ax.get_ylim()
ax.text(2020.1, ymax * 0.92, 'COVID-19\n(2020)',
        fontsize=9, color='#666666', va='top')

ax.text(0.01, -0.10,
        '* United Kingdom excluded due to data anomalies in Comtrade reporting',
        transform=ax.transAxes, fontsize=8, color='#999999')

ax.set_title('Trade Balance by Country (2013–2023)',
             fontsize=15, fontweight='bold', pad=15)
ax.set_xlabel('Year', fontsize=11)
ax.set_ylabel('Trade Balance (USD Billion)', fontsize=11)
ax.legend(loc='lower left', fontsize=9)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}B'))
ax.set_xticks(range(2013, 2024))
ax.grid(axis='y', alpha=0.3)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
plt.savefig('chart2_trade_balance.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ chart2_trade_balance.png saved")


# ── CELL 15: Chart 3 — Export Commodities ────────────────────────────────────

query3 = """
    SELECT 
        c.country_name,
        cm.commodity_name,
        cm.category,
        ROUND(SUM(t.value_usd) / 1e9, 2) AS total_export_billion
    FROM trade_flows t
    JOIN countries   c  ON t.reporter_code  = c.country_code
    JOIN commodities cm ON t.commodity_code = cm.commodity_code
    WHERE t.trade_flow = 'Export'
      AND c.country_name IN ('United States', 'Japan', 'Mexico',
                             'Brazil', 'Italy', 'South Africa')
    GROUP BY c.country_name, cm.commodity_name, cm.category
    ORDER BY c.country_name, total_export_billion DESC
"""
df_commodities = pd.read_sql(query3, engine)
print(f"✅ Rows fetched: {len(df_commodities)}")

df_pivot = df_commodities.pivot(
    index='country_name',
    columns='commodity_name',
    values='total_export_billion'
).fillna(0)

# FIX: Map column names explicitly by commodity_name rather than assuming
# alphabetical order — avoids wrong colours if column order changes
name_map = {
    'Electrical machinery and equipment':       'Electrical\nMachinery',
    'Machinery and mechanical appliances':      'Machinery &\nAppliances',
    'Mineral fuels, mineral oils and products': 'Mineral\nFuels',
    'Pharmaceutical products':                  'Pharma-\nceuticals',
    'Vehicles and transport equipment':         'Vehicles'
}
df_pivot = df_pivot.rename(columns=name_map)

# Colour assigned by short name — stable regardless of column order
color_map = {
    'Electrical\nMachinery':  '#e63946',
    'Machinery &\nAppliances':'#457b9d',
    'Mineral\nFuels':         '#e9c46a',
    'Pharma-\nceuticals':     '#2a9d8f',
    'Vehicles':               '#f4a261'
}
plot_colors = [color_map[col] for col in df_pivot.columns]

fig, ax = plt.subplots(figsize=(14, 7))

df_pivot.plot(
    kind='bar',
    ax=ax,
    color=plot_colors,
    width=0.75,
    edgecolor='white',
    linewidth=0.5
)

ax.set_title('Total Exports by Commodity and Country (2013–2023)',
             fontsize=15, fontweight='bold', pad=15)
ax.set_xlabel('Country', fontsize=11)
ax.set_ylabel('Total Export Value (USD Billion)', fontsize=11)
ax.legend(title='Commodity', bbox_to_anchor=(1.01, 1),
          loc='upper left', fontsize=9)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}B'))
ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha='right', fontsize=10)
ax.grid(axis='y', alpha=0.3)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
plt.savefig('chart3_export_commodities.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ chart3_export_commodities.png saved")
