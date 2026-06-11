# Washington Residential Real Estate Dashboard

An interactive Streamlit dashboard for exploring residential real estate conditions across Washington state.

The dashboard turns public housing-market data into practical answers for buyers, sellers, and market researchers:

- Where are prices rising or softening?
- Is supply growing faster than buyer demand?
- Do buyers or sellers currently have more negotiating leverage?
- Which Washington markets deserve closer investigation?

## Features

### Overview

Select a state, county, city, or ZIP market and review:

- median sale price and price per square foot,
- inventory and months of supply,
- days on market and sale-to-list ratio,
- buyer power and current market classification,
- a plain-English market read,
- coordinated price and inventory trends.

### Price Trends

Compare up to five markets using a searchable selector. The comparison includes:

- configurable price and market metrics,
- property-type filtering,
- a multi-market trend chart,
- a dynamic read covering every selected market,
- rankings, period changes, and comparison with the selected-market median.

### Supply / Demand

Understand why market conditions may be changing:

- inventory, new listings, pending sales, and months of supply,
- supply entering the market versus buyer activity,
- days on market, homes sold, sale-to-list ratio, and above-list sales,
- a dynamic assessment of whether supply or demand is gaining leverage.

### Market Power

Evaluate buyer and seller negotiating leverage through:

- a buyer power score and market regime,
- explanations of the indicators driving the score,
- buyer, balanced, and seller reference zones,
- score movement over time,
- peer rankings across Washington markets.

Higher scores indicate more buyer-friendly conditions. Lower scores indicate more seller-friendly conditions.

### County Map

Explore Washington counties geographically and color them by:

- distance from Seattle or another county,
- median price,
- inventory,
- months of supply,
- days on market,
- homes sold.

Distances are straight-line estimates rather than driving distances.

### Opportunity Finder

Screen markets from either side of a transaction.

Buyer rankings favor signals such as:

- lower relative prices,
- softer price growth,
- higher months of supply,
- longer market time,
- inventory growth and weaker sale-to-list pressure.

Seller rankings favor signals such as:

- stronger price growth,
- tighter supply,
- faster sales,
- stronger sale-to-list performance,
- more above-list sales and stronger sales activity.

The finder ranks markets, not individual properties. It is a research tool and does not guarantee a deal, sale price, or investment return.

## Data

The primary dataset comes from the public [Redfin Data Center](https://www.redfin.com/news/data-center/) Housing Market Tracker. Metrics include pricing, inventory, listings, sales, market speed, and competition.

Data is downloaded on demand and cached locally as Parquet files. Cached data is not committed to the repository.

The county map uses public US county GeoJSON boundaries from Plotly's datasets repository.

## Run Locally

Requires Python 3.10 or newer.

```bash
git clone https://github.com/saswat13/wa-residential-real-estate-dashboard.git
cd wa-residential-real-estate-dashboard

python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS or Linux
source .venv/bin/activate
```

Install dependencies and start the dashboard:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local Streamlit URL, usually `http://localhost:8501`.

## Load Market Data

1. Choose a geography in the sidebar.
2. Expand **Data & settings**.
3. Select **Refresh data** for that geography.
4. Wait for the public dataset to download and cache locally.

County data is included in the current local development workflow. State, city, and ZIP data may require their own refresh and can be considerably larger.

## Scoring Notes

Market Power and Opportunity Finder scores are relative indicators, not forecasts.

- Scores depend on the markets, property type, and time period being analyzed.
- Z-score normalization makes markets comparable but means scores can change when the comparison population changes.
- Sparse or low-volume markets can produce volatile monthly values.
- Market-level indicators do not account for property condition, neighborhood differences, financing, taxes, insurance, or transaction costs.

Use the rankings to identify markets for deeper research, then validate decisions with property-level data and qualified local professionals.

## Project Structure

```text
app.py             Streamlit interface, charts, and dashboard logic
data_sources.py    Redfin downloads, normalization, and local caching
market_signals.py  Buyer/seller market scoring
config.py          Public data endpoints and configuration
requirements.txt   Python dependencies
```

## Roadmap

- Mortgage-rate and affordability overlays
- Driving-time and commute analysis
- ZIP and city opportunity drilldowns
- Property-level deal watchlists
- Rent-versus-buy analysis
- Saved markets and change alerts
- Automated data freshness reporting

## Disclaimer

This project is for informational and educational use only. It is not financial, investment, appraisal, legal, or real estate advice.
