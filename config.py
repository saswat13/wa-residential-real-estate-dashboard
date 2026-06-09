# Redfin public data endpoints can change. If the app fails, first check
# Redfin Data Center download URLs and update these constants.

REDFIN_STATE_MARKET_TRACKER_URL = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/state_market_tracker.tsv000.gz"
REDFIN_COUNTY_MARKET_TRACKER_URL = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/county_market_tracker.tsv000.gz"
REDFIN_CITY_MARKET_TRACKER_URL = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/city_market_tracker.tsv000.gz"
REDFIN_ZIP_MARKET_TRACKER_URL = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/zip_code_market_tracker.tsv000.gz"

FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="

# Add more later.
FRED_SERIES = {
    "King County - Total Listing Count": "TOTLISCOU53033",
}
