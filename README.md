# Washington Residential Real Estate Dashboard

Free-data MVP for tracking Washington residential housing markets.

## Main goal

Understand:
- price trends,
- inventory trends,
- days on market,
- sale-to-list pressure,
- whether a county/region looks like a buyer's market, seller's market, or balanced market.

## Data sources

This starter uses free/public sources:

1. Redfin Data Center / Housing Market Tracker  
   Useful for sale price, inventory, days on market, sale-to-list, homes sold, and supply/demand metrics.

2. FRED / Realtor.com housing inventory series  
   Useful for county-level listing count, median listing price, median days on market, price reductions, etc.

## Setup

```bash
cd wa_residential_real_estate_dashboard

python -m venv .venv
source .venv/bin/activate      # mac/linux
# .venv\Scripts\activate     # windows

pip install -r requirements.txt
streamlit run app.py
```

## Dashboard tabs

1. Overview
2. Price Trends
3. Inventory / Days on Market
4. Buyer vs Seller Signal
5. Raw Data

## Buyer vs Seller Signal

Higher score = more buyer-friendly.

The starter score uses:

- months of supply: higher = buyers have more leverage
- median days on market: higher = buyers have more leverage
- inventory year-over-year: higher = buyers have more leverage
- sale price year-over-year: lower = buyers have more leverage
- homes sold year-over-year: lower = weaker demand, more buyer-friendly

This is not perfect. It is intentionally transparent so you can tune it later.

## Next useful additions

- Mortgage rate overlay
- County-to-county comparison
- ZIP-code drilldown
- Affordability index
- Rent-vs-buy calculator
- Price cut tracker
- Alert: "King County shifted toward buyer market"
- Deal watchlist by city/ZIP
