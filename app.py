import pandas as pd
import plotly.express as px
import streamlit as st
import math
import requests
import plotly.graph_objects as go

from config import FRED_SERIES
from data_sources import (
    load_redfin_cached,
    refresh_redfin_cache,
    load_fred_series,
    detect_date_col,
    detect_region_col,
    parquet_path_for_level,
)
from market_signals import add_market_signal


st.set_page_config(
    page_title="WA Residential Real Estate Dashboard",
    layout="wide",
)

st.title("Washington Residential Real Estate Dashboard")
st.caption("Free-data MVP using Redfin + FRED/Realtor.com-style housing inventory series.")

with st.sidebar:
    st.header("Controls")
    level = st.selectbox("Geography level", ["state", "county", "city", "zip"], index=1)
    max_rows = st.slider("Max rows after filtering", 1000, 200000, 50000, step=1000)
    st.caption("ZIP-level can be large and slower.")



@st.cache_data(ttl=60 * 60 * 6, show_spinner=True)
def get_fred(series_id: str) -> pd.DataFrame:
    return load_fred_series(series_id)


with st.sidebar:
    st.divider()
    st.subheader("Data Cache")

    cache_path = parquet_path_for_level(level)

    if cache_path.exists():
        st.caption(f"Cache found: {cache_path}")
    else:
        st.caption("No local cache found.")

    refresh_clicked = st.button(f"Refresh {level} data")

if refresh_clicked:
    with st.spinner(f"Downloading and caching {level} data. This may take a while..."):
        try:
            refresh_redfin_cache(level)
            st.success(f"Refreshed {level} data.")
            st.cache_data.clear()
        except Exception as exc:
            st.error(f"Refresh failed: {exc}")
            st.stop()


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def get_cached_redfin(level: str) -> pd.DataFrame:
    return load_redfin_cached(level)

@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def get_cached_redfin(level: str) -> pd.DataFrame:
    return load_redfin_cached(level)


def add_derived_metrics(input_df: pd.DataFrame, date_col: str, region_col: str) -> pd.DataFrame:
    out = input_df.copy()

    sort_cols = [region_col]
    if "property_type" in out.columns:
        sort_cols.append("property_type")
    sort_cols.append(date_col)

    out = out.sort_values(sort_cols)

    group_cols = [region_col]
    if "property_type" in out.columns:
        group_cols.append("property_type")

    metrics = [
        "median_sale_price",
        "median_list_price",
        "median_ppsf",
        "homes_sold",
        "inventory",
        "new_listings",
        "pending_sales",
        "months_of_supply",
        "median_dom",
        "avg_sale_to_list",
        "sold_above_list",
        "price_drops",
    ]

    for metric in metrics:
        if metric in out.columns:
            out[metric] = pd.to_numeric(out[metric], errors="coerce")

            out[f"{metric}_mom_calc"] = (
                out.groupby(group_cols)[metric]
                .pct_change(1)
            )

            out[f"{metric}_yoy_calc"] = (
                out.groupby(group_cols)[metric]
                .pct_change(12)
            )

    for col in [
        "months_of_supply",
        "median_dom",
        "avg_sale_to_list",
        "sold_above_list",
        "price_drops",
        "inventory_yoy_calc",
    ]:
        if col not in out.columns:
            out[col] = None

    def zscore(s):
        s = pd.to_numeric(s, errors="coerce")
        std = s.std(skipna=True)
        if std == 0 or pd.isna(std):
            return s * 0
        return (s - s.mean(skipna=True)) / std

    out["seller_power_score"] = (
        -0.30 * zscore(out["months_of_supply"])
        -0.25 * zscore(out["median_dom"])
        +0.20 * zscore(out["avg_sale_to_list"])
        +0.15 * zscore(out["sold_above_list"])
        -0.05 * zscore(out["price_drops"])
        -0.05 * zscore(out["inventory_yoy_calc"])
    )

    out["buyer_power_score"] = -1 * out["seller_power_score"]

    def classify_market(score):
        if pd.isna(score):
            return "Unknown"
        if score >= 0.75:
            return "Seller advantage"
        if score <= -0.75:
            return "Buyer advantage"
        return "Balanced"

    out["market_power"] = out["seller_power_score"].apply(classify_market)

    for col in [
        "median_sale_price_yoy_calc",
        "inventory_yoy_calc",
        "months_of_supply",
        "median_dom",
        "avg_sale_to_list",
    ]:
        if col not in out.columns:
            out[col] = None

    out["opportunity_score"] = (
        0.30 * zscore(out["months_of_supply"])
        +0.25 * zscore(out["median_dom"])
        -0.20 * zscore(out["median_sale_price_yoy_calc"])
        +0.15 * zscore(out["inventory_yoy_calc"])
        -0.10 * zscore(out["avg_sale_to_list"])
    )

    return out


try:
    raw_df = get_cached_redfin(level).copy()
except Exception as exc:
    st.error(str(exc))
    st.info(f"Click **Refresh {level} data** in the sidebar first.")
    st.stop()

date_col = detect_date_col(raw_df)
region_col = detect_region_col(raw_df)

if not date_col:
    st.error("No date column found in the loaded dataset.")
    st.dataframe(raw_df.head())
    st.stop()

raw_df[date_col] = pd.to_datetime(raw_df[date_col], errors="coerce")
raw_df = raw_df.dropna(subset=[date_col]).sort_values(date_col)

raw_df = add_derived_metrics(raw_df, date_col, region_col)

with st.sidebar:
    st.divider()
    st.subheader("Time Period")

    period_option = st.selectbox(
        "Data period",
        [
            "Last 12 months",
            "Last 2 years",
            "Last 5 years",
            "All history",
        ],
        index=0,
        key="global_time_period",
    )

latest_available_date = raw_df[date_col].max()

months_lookup = {
    "Last 12 months": 12,
    "Last 2 years": 24,
    "Last 5 years": 60,
}

if period_option == "All history":
    df = raw_df.copy()
else:
    months_back = months_lookup[period_option]
    start_date = latest_available_date - pd.DateOffset(months=months_back)
    df = raw_df[raw_df[date_col] >= start_date].copy()

df = df.tail(max_rows).copy()



numeric_candidates = [
    "median_sale_price",
    "median_list_price",
    "homes_sold",
    "pending_sales",
    "new_listings",
    "inventory",
    "active_listings",
    "months_of_supply",
    "median_dom",
    "avg_sale_to_list",
    "sold_above_list",
    "price_drops",
    "median_ppsf",
]
WA_COUNTIES_GEOJSON_URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"


@st.cache_data(ttl=60 * 60 * 24 * 7)
def get_wa_counties_geojson():
    r = requests.get(WA_COUNTIES_GEOJSON_URL, timeout=60)
    r.raise_for_status()
    geojson = r.json()

    # Keep only Washington counties (state FIPS = 53)
    geojson["features"] = [
        f for f in geojson["features"]
        if f.get("properties", {}).get("STATE") == "53"
    ]
    return geojson


def flatten_coords(coords):
    """
    Recursively flatten Polygon / MultiPolygon coordinate arrays
    into a simple list of [lon, lat] points.
    """
    points = []

    if not coords:
        return points

    if isinstance(coords[0], (float, int)):
        # Single coordinate pair [lon, lat]
        return [coords]

    for item in coords:
        points.extend(flatten_coords(item))

    return points


def approx_feature_centroid(feature):
    """
    Cheap approximate centroid from all polygon points.
    Good enough for county-distance visualization.
    """
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [])
    pts = flatten_coords(coords)

    if not pts:
        return None, None

    lons = [p[0] for p in pts if len(p) >= 2]
    lats = [p[1] for p in pts if len(p) >= 2]

    if not lons or not lats:
        return None, None

    return sum(lats) / len(lats), sum(lons) / len(lons)


def haversine_miles(lat1, lon1, lat2, lon2):
    """
    Straight-line distance in miles.
    """
    if any(pd.isna(v) for v in [lat1, lon1, lat2, lon2]):
        return None

    r = 3958.8  # Earth radius in miles

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r * c


@st.cache_data(ttl=60 * 60 * 24 * 7)
def build_wa_county_centroids():
    geojson = get_wa_counties_geojson()

    rows = []
    for feature in geojson["features"]:
        props = feature.get("properties", {})
        county_name = props.get("NAME")

        lat, lon = approx_feature_centroid(feature)

        rows.append(
            {
                "county_name": county_name,
                "centroid_lat": lat,
                "centroid_lon": lon,
            }
        )

    return pd.DataFrame(rows)

def add_derived_metrics(input_df: pd.DataFrame, date_col: str, region_col: str) -> pd.DataFrame:
    out = input_df.copy()

    sort_cols = [region_col]
    if "property_type" in out.columns:
        sort_cols.append("property_type")
    sort_cols.append(date_col)

    out = out.sort_values(sort_cols)

    group_cols = [region_col]
    if "property_type" in out.columns:
        group_cols.append("property_type")

    metrics = [
        "median_sale_price",
        "median_list_price",
        "median_ppsf",
        "homes_sold",
        "inventory",
        "new_listings",
        "pending_sales",
        "months_of_supply",
        "median_dom",
        "avg_sale_to_list",
        "sold_above_list",
        "price_drops",
    ]

    for metric in metrics:
        if metric in out.columns:
            out[metric] = pd.to_numeric(out[metric], errors="coerce")

            out[f"{metric}_mom_calc"] = (
                out.groupby(group_cols)[metric]
                .pct_change(1)
            )

            out[f"{metric}_yoy_calc"] = (
                out.groupby(group_cols)[metric]
                .pct_change(12)
            )

    # Buyer/seller power score.
    # Higher = seller has more power.
    # Lower = buyer has more power.
    for col in [
        "months_of_supply",
        "median_dom",
        "avg_sale_to_list",
        "sold_above_list",
        "price_drops",
        "inventory_yoy_calc",
    ]:
        if col not in out.columns:
            out[col] = None

    def zscore(s):
        s = pd.to_numeric(s, errors="coerce")
        if s.std(skipna=True) == 0 or pd.isna(s.std(skipna=True)):
            return s * 0
        return (s - s.mean(skipna=True)) / s.std(skipna=True)

    out["seller_power_score"] = (
        -0.30 * zscore(out["months_of_supply"])
        -0.25 * zscore(out["median_dom"])
        +0.20 * zscore(out["avg_sale_to_list"])
        +0.15 * zscore(out["sold_above_list"])
        -0.05 * zscore(out["price_drops"])
        -0.05 * zscore(out["inventory_yoy_calc"])
    )

    out["buyer_power_score"] = -1 * out["seller_power_score"]

    def classify_market(score):
        if pd.isna(score):
            return "Unknown"
        if score >= 0.75:
            return "Seller advantage"
        if score <= -0.75:
            return "Buyer advantage"
        return "Balanced"

    out["market_power"] = out["seller_power_score"].apply(classify_market)

    # Opportunity score.
    # Higher = more interesting for a buyer.
    # Crude but useful starting point.
    for col in [
    "median_sale_price_yoy_calc",
    "inventory_yoy_calc",
    "months_of_supply",
    "median_dom",
    "avg_sale_to_list",
]:
        if col not in out.columns:
            out[col] = None
    out["opportunity_score"] = (
        0.30 * zscore(out["months_of_supply"])
        +0.25 * zscore(out["median_dom"])
        -0.20 * zscore(out["median_sale_price_yoy_calc"])
        +0.15 * zscore(out["inventory_yoy_calc"])
        -0.10 * zscore(out["avg_sale_to_list"])
    )

    return out

available_metrics = [c for c in numeric_candidates if c in df.columns]

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Market Pulse",
        "Price Trends",
        "Supply / Demand",
        "Buyer vs Seller Power",
        "County Map",
        "Opportunity Finder",
    ]
)

def calculate_period_change(history_df: pd.DataFrame, metric: str, date_col: str):
    """
    Calculates percentage change from first available value in selected period
    to latest available value in selected period.
    """
    if history_df.empty or metric not in history_df.columns:
        return None

    temp = history_df[[date_col, metric]].copy()
    temp[metric] = pd.to_numeric(temp[metric], errors="coerce")
    temp = temp.dropna(subset=[date_col, metric]).sort_values(date_col)

    if len(temp) < 2:
        return None

    first_value = temp.iloc[0][metric]
    latest_value = temp.iloc[-1][metric]

    if pd.isna(first_value) or first_value == 0:
        return None

    return (latest_value - first_value) / first_value


with tab1:
    st.subheader("Market Pulse")
    st.caption("What is happening right now?")

    latest_date = df[date_col].max()
    latest = df[df[date_col] == latest_date].copy()
    latest[region_col] = latest[region_col].astype(str)

    search_placeholder = {
    "county": "Example: King, Pierce, Snohomish",
    "city": "Example: Bellevue, Seattle, Redmond",
    "zip": "Example: 98052, 98004, 98101",
    "state": "Example: Washington",
    }.get(level, "Search market")

    search_text = st.text_input(
        f"Search {level}",
        placeholder=search_placeholder,
        key="market_pulse_search",
    ).strip()

    if search_text:
        search_results = latest[
            latest[region_col].str.contains(search_text, case=False, na=False)
        ].copy()
    else:
        search_results = latest.copy()

    if search_results.empty:
        st.warning(f"No matching {level} found. Try a broader search.")
    else:
        market_options = sorted(search_results[region_col].dropna().unique().tolist())

        selected_market = st.selectbox(
            "Select market",
            market_options,
            key=f"market_pulse_market_{search_text}_{level}",
        )

        market_latest_all_types = search_results[
            search_results[region_col] == selected_market
        ].copy()

        if "property_type" in market_latest_all_types.columns:
            property_types = sorted(
                market_latest_all_types["property_type"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            default_property_index = (
                property_types.index("All Residential")
                if "All Residential" in property_types
                else 0
            )

            selected_property_type = st.selectbox(
                "Select property type",
                property_types,
                index=default_property_index,
                key=f"market_pulse_property_{selected_market}_{search_text}_{level}",
            )

            market_latest = market_latest_all_types[
                market_latest_all_types["property_type"].astype(str) == selected_property_type
            ].copy()
        else:
            selected_property_type = None
            market_latest = market_latest_all_types.copy()

        if market_latest.empty:
            st.warning("No data found for selected market and property type.")
        else:
            row = market_latest.iloc[0]

            title = f"{selected_market}"
            if selected_property_type:
                title += f" — {selected_property_type}"

            st.divider()
            st.subheader(title)
            
            market_history = df[df[region_col].astype(str) == selected_market].copy()

            if selected_property_type and "property_type" in market_history.columns:
                market_history = market_history[
                    market_history["property_type"].astype(str) == selected_property_type
                ].copy()

            price_period_change = calculate_period_change(
                market_history,
                "median_sale_price",
                date_col,
            )

            ppsf_period_change = calculate_period_change(
                market_history,
                "median_ppsf",
                date_col,
            )

            inventory_period_change = calculate_period_change(
                market_history,
                "inventory",
                date_col,
            )

            c1, c2, c3, c4 = st.columns(4)

            current_price = row.get("median_sale_price")
            price_yoy = row.get("median_sale_price_yoy_calc")
            price_mom = row.get("median_sale_price_mom_calc")
            market_power = row.get("market_power")

            if pd.notna(current_price):
                c1.metric(
                    "Median Sale Price",
                    f"${current_price:,.0f}",
                    f"{price_yoy:.1%} YoY" if pd.notna(price_yoy) else None,
                )

                if price_period_change is not None:
                    c1.caption(f"{price_period_change:.1%} change over selected period")
            else:
                c1.metric("Median Sale Price", "N/A")

            if "median_ppsf" in row.index and pd.notna(row["median_ppsf"]):
                c2.metric(
                    "Median Price / Sqft",
                    f"${row['median_ppsf']:,.0f}",
                    f"{row['median_ppsf_yoy_calc']:.1%} YoY"
                    if "median_ppsf_yoy_calc" in row.index and pd.notna(row["median_ppsf_yoy_calc"])
                    else None,
                )

                if ppsf_period_change is not None:
                    c2.caption(f"{ppsf_period_change:.1%} change over selected period")
            else:
                c2.metric("Median Price / Sqft", "N/A")

            if "inventory" in row.index and pd.notna(row["inventory"]):
                c3.metric(
                    "Inventory",
                    f"{row['inventory']:,.0f}",
                    f"{row['inventory_yoy_calc']:.1%} YoY"
                    if "inventory_yoy_calc" in row.index and pd.notna(row["inventory_yoy_calc"])
                    else None,
                )

                if inventory_period_change is not None:
                    c3.caption(f"{inventory_period_change:.1%} change over selected period")
            else:
                c3.metric("Inventory", "N/A")   

            if "months_of_supply" in row.index and pd.notna(row["months_of_supply"]):
                c4.metric("Months of Supply", f"{row['months_of_supply']:.1f}")
            else:
                c4.metric("Months of Supply", "N/A")

            c5, c6, c7, c8 = st.columns(4)

            if "median_dom" in row.index and pd.notna(row["median_dom"]):
                c5.metric("Median Days on Market", f"{row['median_dom']:,.0f}")
            else:
                c5.metric("Median Days on Market", "N/A")

            if "avg_sale_to_list" in row.index and pd.notna(row["avg_sale_to_list"]):
                c6.metric("Sale-to-List Ratio", f"{row['avg_sale_to_list']:.2%}")
            else:
                c6.metric("Sale-to-List Ratio", "N/A")

            if "buyer_power_score" in row.index and pd.notna(row["buyer_power_score"]):
                c7.metric("Buyer Power Score", f"{row['buyer_power_score']:.2f}")
            else:
                c7.metric("Buyer Power Score", "N/A")

            c8.metric("Market Power", market_power if pd.notna(market_power) else "Unknown")

            st.divider()
            st.subheader("Quick Read")

            quick_read_parts = []

            # YoY price read
            if pd.notna(price_yoy):
                if price_yoy > 0.03:
                    quick_read_parts.append(
                        f"Prices are up {price_yoy:.1%} versus last year."
                    )
                elif price_yoy < -0.03:
                    quick_read_parts.append(
                        f"Prices are down {price_yoy:.1%} versus last year."
                    )
                else:
                    quick_read_parts.append(
                        f"Prices are roughly flat versus last year ({price_yoy:.1%})."
                    )

            # Selected-period price read
            if price_period_change is not None:
                if price_period_change > 0.05:
                    quick_read_parts.append(
                        f"Across the selected time period, prices are up {price_period_change:.1%}."
                    )
                elif price_period_change < -0.05:
                    quick_read_parts.append(
                        f"Across the selected time period, prices are down {price_period_change:.1%}."
                    )
                else:
                    quick_read_parts.append(
                        f"Across the selected time period, prices are mostly flat ({price_period_change:.1%})."
                    )

            # Inventory read
            inventory_yoy = row.get("inventory_yoy_calc")

            if pd.notna(inventory_yoy):
                if inventory_yoy > 0.10:
                    quick_read_parts.append(
                        f"Inventory is up {inventory_yoy:.1%} YoY, which usually improves buyer leverage."
                    )
                elif inventory_yoy < -0.10:
                    quick_read_parts.append(
                        f"Inventory is down {inventory_yoy:.1%} YoY, which usually supports seller leverage."
                    )

            if inventory_period_change is not None:
                if inventory_period_change > 0.10:
                    quick_read_parts.append(
                        f"Inventory has also increased {inventory_period_change:.1%} over the selected period."
                    )
                elif inventory_period_change < -0.10:
                    quick_read_parts.append(
                        f"Inventory has decreased {inventory_period_change:.1%} over the selected period."
                    )

            # Months of supply read
            if "months_of_supply" in row.index and pd.notna(row["months_of_supply"]):
                mos = row["months_of_supply"]

                if mos >= 4:
                    quick_read_parts.append(
                        f"Months of supply is {mos:.1f}, which points to a looser, more buyer-friendly market."
                    )
                elif mos <= 2:
                    quick_read_parts.append(
                        f"Months of supply is {mos:.1f}, which points to a tight, seller-friendly market."
                    )
                else:
                    quick_read_parts.append(
                        f"Months of supply is {mos:.1f}, which looks relatively balanced."
                    )

            # Market power read
            if pd.notna(market_power):
                quick_read_parts.append(
                    f"Current dashboard classification: {market_power}."
                )

            if quick_read_parts:
                st.write(" ".join(quick_read_parts))
            else:
                st.write("Not enough clean data to generate a useful read.")
                        
            st.divider()
            st.subheader("Trend Line")

            
            
            trend_metric_options = [
                c for c in [
                    "median_sale_price",
                    "median_sale_price_yoy_calc",
                    "median_ppsf",
                    "inventory",
                    "months_of_supply",
                    "median_dom",
                    "buyer_power_score",
                    "seller_power_score",
                    "opportunity_score",
                ]
                if c in market_history.columns
            ]

            selected_trend_metric = st.selectbox(
                "Trend metric",
                trend_metric_options,
                index=0,
                key=f"market_pulse_trend_{selected_market}_{selected_property_type}_{level}",
            )

            market_history[selected_trend_metric] = pd.to_numeric(
                market_history[selected_trend_metric],
                errors="coerce",
            )

            fig = px.line(
                market_history.sort_values(date_col),
                x=date_col,
                y=selected_trend_metric,
                title=f"{selected_trend_metric.replace('_', ' ').title()} — {title}",
            )

            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Selected latest row"):
                show_cols = [
                    region_col,
                    "property_type",
                    date_col,
                    "median_sale_price",
                    "median_sale_price_yoy_calc",
                    "median_sale_price_mom_calc",
                    "median_ppsf",
                    "inventory",
                    "inventory_yoy_calc",
                    "months_of_supply",
                    "median_dom",
                    "avg_sale_to_list",
                    "buyer_power_score",
                    "seller_power_score",
                    "market_power",
                    "opportunity_score",
                ]

                show_cols = [c for c in show_cols if c in market_latest.columns]

                st.dataframe(
                    market_latest[show_cols],
                    use_container_width=True,
                )
with tab2:
    st.subheader("Price Trends")

    if not available_metrics:
        st.warning("Expected Redfin metric columns were not found.")
    else:
        metric = st.selectbox(
            "Metric",
            available_metrics,
            index=available_metrics.index("median_sale_price")
            if "median_sale_price" in available_metrics
            else 0,
            key="price_metric",
        )

        all_markets = sorted(df[region_col].dropna().astype(str).unique().tolist())

        if "price_selected_markets_persistent" not in st.session_state:
            st.session_state.price_selected_markets_persistent = []

            price_search_placeholder = {
                "county": "Example: King, Pierce, Snohomish",
                "city": "Example: Seattle, Bellevue, Redmond",
                 "zip": "Example: 98052, 98004, 98101",
                 "state": "Example: Washington",
    }.get(level, "Search market")

            
        price_search_placeholder = {
                "county": "Example: King, Pierce, Snohomish",
                "city": "Example: Seattle, Bellevue, Redmond",
                "zip": "Example: 98052, 98004, 98101",
                "state": "Example: Washington",
                }.get(level, "Search market")

        market_search = st.text_input(
            "Search market to add",
            placeholder=price_search_placeholder,
            key="price_market_search",
        ).strip()
        if market_search:
            search_matches = [
                m for m in all_markets
                if market_search.lower() in m.lower()
            ]
        else:
            search_matches = []

        market_to_add = st.selectbox(
            "Matching markets",
            [""] + search_matches,
            key=f"price_market_to_add_{level}_{market_search}",
        )

        c_add, c_clear = st.columns([1, 1])

        with c_add:
            if st.button("Add market", key="price_add_market"):
                if (
                    market_to_add
                    and market_to_add not in st.session_state.price_selected_markets_persistent
                ):
                    st.session_state.price_selected_markets_persistent.append(market_to_add)

        with c_clear:
            if st.button("Clear markets", key="price_clear_markets"):
                st.session_state.price_selected_markets_persistent = []

        selected_markets = st.session_state.price_selected_markets_persistent

        if selected_markets:
            selected_markets_after_removal = st.multiselect(
                "Markets currently in chart",
                selected_markets,
                default=selected_markets,
                key="price_markets_currently_in_chart",
            )

            st.session_state.price_selected_markets_persistent = selected_markets_after_removal
            selected_markets = selected_markets_after_removal

        if not selected_markets:
            st.info("Search and add at least one market to display a trend.")
        else:
            plot_df = df[df[region_col].astype(str).isin(selected_markets)].copy()

            selected_property_type = None

            if "property_type" in plot_df.columns:
                property_types = sorted(
                    plot_df["property_type"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                if "All Residential" in property_types:
                    selected_property_type = "All Residential"
                    plot_df = plot_df[
                        plot_df["property_type"].astype(str) == selected_property_type
                    ].copy()
                    st.caption("Using property type: All Residential")
                elif property_types:
                    selected_property_type = st.selectbox(
                        "Property type",
                        property_types,
                        index=0,
                        key=f"price_property_type_{level}_{len(selected_markets)}",
                    )

                    plot_df = plot_df[
                        plot_df["property_type"].astype(str) == selected_property_type
                    ].copy()
                else:
                    st.warning("No property type values found for selected markets.")

            if plot_df.empty:
                st.warning("No data available for the selected markets after filtering.")
            else:
                plot_df[metric] = pd.to_numeric(plot_df[metric], errors="coerce")

                fig = px.line(
                    plot_df.sort_values(date_col),
                    x=date_col,
                    y=metric,
                    color=region_col,
                    title=(
                        f"{metric.replace('_', ' ').title()}"
                        + (f" — {selected_property_type}" if selected_property_type else "")
                    ),
                )

                st.plotly_chart(fig, use_container_width=True)

                st.divider()
                st.subheader("Selected Latest Rows")

                latest_selected = plot_df[
                    plot_df[date_col] == plot_df[date_col].max()
                ].copy()

                show_cols = [
                    region_col,
                    "property_type",
                    date_col,
                    "median_sale_price",
                    "median_list_price",
                    "homes_sold",
                    "inventory",
                    "months_of_supply",
                    "median_dom",
                    "avg_sale_to_list",
                    "sold_above_list",
                ]

                show_cols = [c for c in show_cols if c in latest_selected.columns]

                st.dataframe(
                    latest_selected[show_cols].sort_values(region_col),
                    use_container_width=True,
                )
with tab3:
    st.subheader("Inventory and Market Speed")

    inv_metrics = [c for c in ["inventory", "active_listings", "months_of_supply", "median_dom", "new_listings"] if c in df.columns]

    if not inv_metrics:
        st.warning("Inventory / days-on-market columns not found.")
    else:
        metric = st.selectbox("Inventory / speed metric", inv_metrics)
        regions = sorted(df[region_col].dropna().astype(str).unique().tolist())
        selected = st.multiselect(
            "Markets",
            regions,
            default=regions[: min(8, len(regions))],
            key="inventory_regions",
        )

        plot_df = df[df[region_col].astype(str).isin(selected)].copy()
        plot_df[metric] = pd.to_numeric(plot_df[metric], errors="coerce")

        fig = px.line(
            plot_df,
            x=date_col,
            y=metric,
            color=region_col,
            title=metric.replace("_", " ").title(),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("FRED example: King County total listing count")

    try:
        fred_df = get_fred(FRED_SERIES["King County - Total Listing Count"])
        fig = px.line(
            fred_df,
            x="date",
            y="value",
            title="King County Total Listing Count",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(f"Could not load FRED series: {exc}")

with tab4:
    st.subheader("Buyer vs Seller Signal")

    signal_df = add_market_signal(df)
    latest_signal = signal_df[signal_df[date_col] == signal_df[date_col].max()].copy()

    st.write(
        "Higher score means more buyer-friendly. Lower score means more seller-friendly. "
        "This is a first-pass model, not a final truth."
    )

    view_cols = [
        region_col,
        date_col,
        "buyer_market_score",
        "market_regime",
        "months_of_supply",
        "median_dom",
        "inventory_yoy",
        "median_sale_price_yoy",
        "homes_sold_yoy",
        "avg_sale_to_list",
        "sold_above_list",
    ]
    view_cols = [c for c in view_cols if c in latest_signal.columns]

    st.dataframe(
        latest_signal[view_cols]
        .sort_values("buyer_market_score", ascending=False)
        .head(200),
        use_container_width=True,
    )

    regions = sorted(signal_df[region_col].dropna().astype(str).unique().tolist())
    selected = st.multiselect(
        "Markets for signal trend",
        regions,
        default=regions[: min(8, len(regions))],
        key="signal_regions",
    )

    plot_df = signal_df[signal_df[region_col].astype(str).isin(selected)].copy()
    fig = px.line(
        plot_df,
        x=date_col,
        y="buyer_market_score",
        color=region_col,
        title="Buyer Market Score Over Time",
    )
    st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.subheader("Washington County Map")

    if level != "county":
        st.info("This map currently works only in county mode. Switch Geography level to 'county'.")
    else:
        map_df = df.copy()

        # Property type filter for the map
        if "property_type" in map_df.columns:
            property_types = sorted(
                map_df["property_type"].dropna().astype(str).unique().tolist()
            )

            selected_map_property_type = st.selectbox(
                "Property type for map",
                property_types,
                index=property_types.index("All Residential")
                if "All Residential" in property_types
                else 0,
                key="map_property_type",
            )

            map_df = map_df[
                map_df["property_type"].astype(str) == selected_map_property_type
            ].copy()
        else:
            selected_map_property_type = None

        latest_date_map = map_df[date_col].max()
        latest_map = map_df[map_df[date_col] == latest_date_map].copy()

        # Clean county name for joining with geojson
        latest_map["county_name"] = (
            latest_map[region_col]
            .astype(str)
            .str.replace(", WA", "", regex=False)
            .str.replace(" County", "", regex=False)
            .str.strip()
        )

        county_centroids = build_wa_county_centroids()
        latest_map = latest_map.merge(county_centroids, on="county_name", how="left")

        # Anchor selection: Seattle or a county
        county_options = sorted(latest_map[region_col].dropna().astype(str).unique().tolist())
        default_anchor_index = county_options.index("King County, WA") if "King County, WA" in county_options else 0

        anchor_choice = st.selectbox(
            "Distance reference point",
            ["Seattle"] + county_options,
            index=default_anchor_index + 1 if county_options else 0,
            key="map_anchor_choice",
        )

        if anchor_choice == "Seattle":
            anchor_lat = 47.6062
            anchor_lon = -122.3321
            anchor_label = "Seattle"
        else:
            anchor_key = (
                anchor_choice.replace(", WA", "")
                .replace(" County", "")
                .strip()
            )

            anchor_row = county_centroids[county_centroids["county_name"] == anchor_key]

            if anchor_row.empty:
                st.warning("Could not find centroid for selected anchor county.")
                st.stop()

            anchor_lat = anchor_row.iloc[0]["centroid_lat"]
            anchor_lon = anchor_row.iloc[0]["centroid_lon"]
            anchor_label = anchor_choice

        latest_map["distance_miles"] = latest_map.apply(
            lambda row: haversine_miles(
                anchor_lat,
                anchor_lon,
                row["centroid_lat"],
                row["centroid_lon"],
            ),
            axis=1,
        )

        color_metric_options = [
            c for c in [
                "distance_miles",
                "median_sale_price",
                "median_list_price",
                "inventory",
                "months_of_supply",
                "median_dom",
                "homes_sold",
            ]
            if c in latest_map.columns
        ]

        selected_color_metric = st.selectbox(
            "Color counties by",
            color_metric_options,
            index=0,
            key="map_color_metric",
        )

        geojson = get_wa_counties_geojson()

        fig = go.Figure()

        fig.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=latest_map["county_name"],
                z=pd.to_numeric(latest_map[selected_color_metric], errors="coerce"),
                featureidkey="properties.NAME",
                colorbar_title=selected_color_metric,
                marker_line_color="white",
                marker_line_width=0.8,
                customdata=latest_map[
                    [
                        region_col,
                        "distance_miles",
                        "median_sale_price",
                        "inventory",
                        "months_of_supply",
                    ]
                ].fillna("N/A"),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Distance: %{customdata[1]:.1f} miles<br>"
                    "Median sale price: %{customdata[2]}<br>"
                    "Inventory: %{customdata[3]}<br>"
                    "Months of supply: %{customdata[4]}<br>"
                    "<extra></extra>"
                ),
            )
        )

        # Anchor marker
        fig.add_trace(
            go.Scattergeo(
                lon=[anchor_lon],
                lat=[anchor_lat],
                text=[anchor_label],
                mode="markers+text",
                textposition="top center",
                marker=dict(size=10, symbol="star"),
                name="Reference point",
            )
        )

        fig.update_geos(
            fitbounds="locations",
            visible=False,
            scope="usa",
        )

        fig.update_layout(
            title=(
                f"Washington counties — {selected_color_metric.replace('_', ' ').title()} "
                f"(reference: {anchor_label})"
            ),
            height=700,
            margin=dict(l=10, r=10, t=60, b=10),
        )

        st.plotly_chart(fig, use_container_width=True)

        st.caption("Distance is straight-line miles, not driving distance.")

        st.divider()
        st.subheader("County Distance Table")

        table_cols = [
            region_col,
            "distance_miles",
            "median_sale_price",
            "inventory",
            "months_of_supply",
            "median_dom",
            "homes_sold",
        ]
        table_cols = [c for c in table_cols if c in latest_map.columns]

        distance_table = latest_map[table_cols].copy()
        if "distance_miles" in distance_table.columns:
            distance_table = distance_table.sort_values("distance_miles")

        st.dataframe(distance_table, use_container_width=True)

with tab6:
    st.subheader("Raw Data")
    st.write(f"Detected date column: `{date_col}`")
    st.write(f"Detected market column: `{region_col}`")
    st.dataframe(df.head(1000), use_container_width=True)
