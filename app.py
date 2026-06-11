import pandas as pd
import plotly.express as px
import streamlit as st
import math
import requests
import plotly.graph_objects as go
import streamlit.components.v1 as components

from data_sources import (
    load_redfin_cached,
    refresh_redfin_cache,
    detect_date_col,
    detect_region_col,
    parquet_path_for_level,
)
from market_signals import add_market_signal


st.set_page_config(
    page_title="Washington Housing Market",
    page_icon=":material/home_work:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --wa-navy: #123047;
        --wa-evergreen: #28735a;
        --wa-mist: #f3f7f5;
        --wa-slate: #52616b;
        --wa-coral: #d96c5f;
    }
    .stApp { background: #fbfcfb; }
    .block-container { max-width: 1240px; padding-top: 1.6rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { background: #f3f6f5; border-right: 1px solid #e1e8e4; }
    [data-testid="stSidebar"] h2 { color: var(--wa-navy); }
    h1, h2, h3 { color: var(--wa-navy); letter-spacing: -0.02em; }
    .dashboard-header {
        padding: 1.45rem 1.6rem;
        border-radius: 18px;
        color: white;
        background: linear-gradient(120deg, #123047 0%, #1e5260 55%, #28735a 100%);
        box-shadow: 0 12px 30px rgba(18, 48, 71, 0.14);
        margin-bottom: 1.15rem;
    }
    .dashboard-eyebrow { font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; opacity: .76; }
    .dashboard-title { font-size: 2rem; font-weight: 760; line-height: 1.15; margin: .35rem 0; }
    .dashboard-subtitle { font-size: .98rem; opacity: .84; margin: 0; }
    .section-kicker { color: var(--wa-evergreen); font-size: .78rem; font-weight: 750; letter-spacing: .1em; text-transform: uppercase; }
    .market-heading { font-size: 1.55rem; font-weight: 750; color: var(--wa-navy); margin: .2rem 0 0; }
    .market-meta { color: var(--wa-slate); font-size: .9rem; margin-bottom: .8rem; }
    .insight-card {
        border: 1px solid #dfe8e3;
        background: white;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        min-height: 116px;
        box-shadow: 0 4px 16px rgba(18, 48, 71, 0.05);
    }
    .insight-label { color: var(--wa-slate); font-size: .76rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
    .insight-value { color: var(--wa-navy); font-size: 1.7rem; font-weight: 760; margin: .3rem 0 .1rem; }
    .insight-detail { color: var(--wa-slate); font-size: .82rem; }
    .market-badge { display: inline-block; border-radius: 999px; padding: .35rem .7rem; font-size: .8rem; font-weight: 750; }
    .badge-buyer { background: #e6f1f8; color: #246083; }
    .badge-seller { background: #fae9e6; color: #a7493e; }
    .badge-balanced { background: #e5f2eb; color: #25634d; }
    .leverage-panel { background: white; border: 1px solid #dfe8e3; border-radius: 16px; padding: 1.1rem 1.25rem; margin: .4rem 0 1rem; }
    .leverage-title { color: var(--wa-navy); font-size: 1.35rem; font-weight: 760; margin-bottom: .2rem; }
    .leverage-copy { color: var(--wa-slate); font-size: .9rem; margin-bottom: 1rem; }
    .leverage-track { position: relative; height: 14px; border-radius: 999px; background: linear-gradient(90deg, #d96c5f 0%, #f4d6d1 27%, #e7ece9 50%, #d5e7ef 73%, #4f7f96 100%); }
    .leverage-marker { position: absolute; top: -6px; width: 4px; height: 26px; border-radius: 3px; background: #123047; box-shadow: 0 0 0 3px white; }
    .leverage-labels { display: flex; justify-content: space-between; color: var(--wa-slate); font-size: .75rem; font-weight: 650; margin-top: .55rem; }
    .meaning-card { border-radius: 14px; padding: 1rem 1.1rem; min-height: 132px; }
    .meaning-buyer { background: #eef6fa; border: 1px solid #d5e7ef; }
    .meaning-seller { background: #fdf1ef; border: 1px solid #f2d8d3; }
    .meaning-title { color: var(--wa-navy); font-weight: 750; margin-bottom: .35rem; }
    .meaning-copy { color: #46555e; font-size: .9rem; line-height: 1.5; }
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #dfe8e3;
        border-radius: 14px;
        padding: .9rem 1rem;
        box-shadow: 0 4px 16px rgba(18, 48, 71, 0.04);
    }
    [data-testid="stMetricLabel"] { color: var(--wa-slate); }
    [data-testid="stMetricValue"] { color: var(--wa-navy); }
    .stTabs [data-baseweb="tab-list"] { gap: .35rem; border-bottom: 1px solid #dfe8e3; }
    .stTabs [data-baseweb="tab"] { padding: .7rem .85rem; border-radius: 9px 9px 0 0; }
    .stTabs [aria-selected="true"] { color: var(--wa-evergreen); background: #edf5f1; }
    [data-baseweb="tag"] { background-color: var(--wa-evergreen) !important; }
    div[data-testid="stPlotlyChart"] { border: 1px solid #e2e9e5; border-radius: 14px; overflow: hidden; background: white; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="dashboard-header">
        <div class="dashboard-eyebrow">Washington housing intelligence</div>
        <div class="dashboard-title">Residential Real Estate Dashboard</div>
        <p class="dashboard-subtitle">Track pricing, supply, competition, and buyer leverage across Washington markets.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Explore markets")
    level = st.selectbox(
        "Geography",
        ["state", "county", "city", "zip"],
        index=1,
        format_func=lambda value: value.title(),
    )



with st.sidebar:
    with st.expander("Data & settings"):
        cache_path = parquet_path_for_level(level)
        if cache_path.exists():
            st.caption(f"Local {level} data is available.")
        else:
            st.caption(f"No local {level} data found.")
        refresh_clicked = st.button(f"Refresh {level} data", use_container_width=True)
        st.caption("Refresh downloads the latest available public Redfin dataset.")

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
    period_option = st.selectbox(
        "Time period",
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

df = df.tail(50000).copy()



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

pending_market = st.session_state.pop("_pending_market_navigation", None)
if pending_market:
    overview_market_key = f"market_pulse_market_{level}"
    price_markets_key = f"price_markets_{level}"
    st.session_state["market_pulse_search"] = ""
    st.session_state[overview_market_key] = pending_market

    existing_price_markets = list(st.session_state.get(price_markets_key, []))
    if pending_market not in existing_price_markets:
        existing_price_markets.append(pending_market)
    st.session_state[price_markets_key] = existing_price_markets[-5:]

    pending_property_type = st.session_state.pop("_pending_property_type", None)
    if pending_property_type:
        st.session_state[f"price_property_type_{level}"] = pending_property_type
    st.session_state["_activate_dashboard_tab"] = "Overview"

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Overview",
        "Price Trends",
        "Supply / Demand",
        "Market Power",
        "County Map",
        "Opportunity Finder",
    ]
)

tab_to_activate = st.session_state.pop("_activate_dashboard_tab", None)
if tab_to_activate:
    components.html(
        f"""
        <script>
        const target = {tab_to_activate!r};
        let attempts = 0;
        const activateTab = () => {{
            const tabs = Array.from(parent.document.querySelectorAll('[role="tab"]'));
            const match = tabs.find((tab) => tab.textContent.trim() === target);
            if (match) {{
                match.click();
                return;
            }}
            attempts += 1;
            if (attempts < 20) setTimeout(activateTab, 100);
        }};
        setTimeout(activateTab, 50);
        </script>
        """,
        height=0,
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
    st.markdown('<div class="section-kicker">Market overview</div>', unsafe_allow_html=True)
    st.subheader("What is happening now?")
    st.caption("Choose a market to see its latest conditions and direction of travel.")

    latest_date = df[date_col].max()
    latest = df[df[date_col] == latest_date].copy()
    latest[region_col] = latest[region_col].astype(str)

    search_placeholder = {
    "county": "Example: King, Pierce, Snohomish",
    "city": "Example: Bellevue, Seattle, Redmond",
    "zip": "Example: 98052, 98004, 98101",
    "state": "Example: Washington",
    }.get(level, "Search market")

    search_col, market_col = st.columns([1, 1.35])
    with search_col:
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

        preferred_market = {
            "county": "King County, WA",
            "city": "Seattle, WA",
            "state": "Washington",
        }.get(level)
        default_market_index = (
            market_options.index(preferred_market)
            if preferred_market in market_options
            else 0
        )

        with market_col:
            overview_market_key = f"market_pulse_market_{level}"
            if (
                overview_market_key in st.session_state
                and st.session_state[overview_market_key] not in market_options
            ):
                del st.session_state[overview_market_key]
            if overview_market_key in st.session_state:
                selected_market = st.selectbox(
                    "Market",
                    market_options,
                    index=None,
                    key=overview_market_key,
                )
            else:
                selected_market = st.selectbox(
                    "Market",
                    market_options,
                    index=default_market_index,
                    key=overview_market_key,
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
                "Property type",
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

            title = selected_market + (
                f" - {selected_property_type}" if selected_property_type else ""
            )
            market_power = row.get("market_power")
            badge_class = {
                "Buyer advantage": "badge-buyer",
                "Seller advantage": "badge-seller",
                "Balanced": "badge-balanced",
            }.get(market_power, "badge-balanced")
            st.markdown(
                f'<div class="market-heading">{title}</div>'
                f'<div class="market-meta">Latest data: {latest_date:%B %Y} &nbsp; '
                f'<span class="market-badge {badge_class}">{market_power or "Unknown"}</span></div>',
                unsafe_allow_html=True,
            )
            
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

            st.markdown("### Market read")

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
                st.info(" ".join(quick_read_parts))
            else:
                st.write("Not enough clean data to generate a useful read.")
                        
            st.markdown("### Trend dashboard")

            
            
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
                format_func=lambda value: value.replace("_calc", "").replace("_", " ").title(),
            )

            market_history[selected_trend_metric] = pd.to_numeric(
                market_history[selected_trend_metric],
                errors="coerce",
            )

            fig = px.line(
                market_history.sort_values(date_col),
                x=date_col,
                y=selected_trend_metric,
                title=selected_trend_metric.replace("_calc", "").replace("_", " ").title(),
                color_discrete_sequence=["#28735a"],
            )
            fig.update_traces(line_width=3)
            fig.update_layout(
                height=390,
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(l=20, r=20, t=55, b=20),
                xaxis_title=None,
                yaxis_title=None,
                hovermode="x unified",
            )
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#e8eeeb")

            chart_col, context_col = st.columns([1.65, 1])
            with chart_col:
                st.plotly_chart(fig, use_container_width=True)

            with context_col:
                context_metric = "inventory" if "inventory" in market_history.columns else "median_dom"
                context_title = "Inventory" if context_metric == "inventory" else "Days on Market"
                context_fig = px.area(
                    market_history.sort_values(date_col),
                    x=date_col,
                    y=context_metric,
                    title=context_title,
                    color_discrete_sequence=["#4f7f96"],
                )
                context_fig.update_traces(line_width=2.5, fillcolor="rgba(79, 127, 150, 0.16)")
                context_fig.update_layout(
                    height=390,
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    margin=dict(l=20, r=20, t=55, b=20),
                    xaxis_title=None,
                    yaxis_title=None,
                    hovermode="x unified",
                )
                context_fig.update_xaxes(showgrid=False)
                context_fig.update_yaxes(gridcolor="#e8eeeb")
                st.plotly_chart(context_fig, use_container_width=True)

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
    st.caption("Compare price movement across up to five Washington markets.")

    if not available_metrics:
        st.warning("Expected Redfin metric columns were not found.")
    else:
        all_markets = sorted(df[region_col].dropna().astype(str).unique().tolist())

        preferred_market_names = {
            "state": ["Washington"],
            "county": ["King County, WA", "Pierce County, WA", "Snohomish County, WA"],
            "city": ["Seattle, WA", "Bellevue, WA", "Tacoma, WA"],
        }.get(level, [])
        default_markets = [market for market in preferred_market_names if market in all_markets]
        if not default_markets:
            default_markets = all_markets[: min(3, len(all_markets))]

        property_types = (
            sorted(df["property_type"].dropna().astype(str).unique().tolist())
            if "property_type" in df.columns
            else []
        )
        default_property_index = (
            property_types.index("All Residential")
            if "All Residential" in property_types
            else 0
        )

        metric_col, property_col = st.columns([1, 1])
        with metric_col:
            metric = st.selectbox(
                "Price metric",
                available_metrics,
                index=available_metrics.index("median_sale_price")
                if "median_sale_price" in available_metrics
                else 0,
                key="price_metric",
                format_func=lambda value: value.replace("_", " ").title(),
            )

        with property_col:
            price_property_key = f"price_property_type_{level}"
            if property_types and price_property_key in st.session_state:
                selected_property_type = st.selectbox(
                    "Property type",
                    property_types,
                    index=None,
                    key=price_property_key,
                )
            elif property_types:
                selected_property_type = st.selectbox(
                    "Property type",
                    property_types,
                    index=default_property_index,
                    key=price_property_key,
                )
            else:
                selected_property_type = None

        price_markets_key = f"price_markets_{level}"
        if price_markets_key not in st.session_state:
            st.session_state[price_markets_key] = default_markets
        else:
            st.session_state[price_markets_key] = [
                market for market in st.session_state[price_markets_key]
                if market in all_markets
            ][-5:]

        selected_markets = st.multiselect(
            "Markets to compare",
            all_markets,
            max_selections=5,
            key=price_markets_key,
            help="Type to search, then select up to five markets.",
        )

        if not selected_markets:
            st.info("Select at least one market to display a trend.")
        else:
            plot_df = df[df[region_col].astype(str).isin(selected_markets)].copy()
            if selected_property_type and "property_type" in plot_df.columns:
                plot_df = plot_df[
                    plot_df["property_type"].astype(str) == selected_property_type
                ].copy()

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
                    color_discrete_sequence=["#28735a", "#4f7f96", "#d08b49", "#8b6a9e", "#d96c5f"],
                )
                fig.update_traces(line_width=2.8)
                fig.update_layout(
                    height=500,
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    margin=dict(l=20, r=20, t=65, b=20),
                    xaxis_title=None,
                    yaxis_title=None,
                    legend_title_text="Market",
                    hovermode="x unified",
                )
                fig.update_xaxes(showgrid=False)
                fig.update_yaxes(gridcolor="#e8eeeb")

                st.plotly_chart(fig, use_container_width=True)

                market_summaries = []
                for market_name in selected_markets:
                    market_data = plot_df[
                        plot_df[region_col].astype(str) == str(market_name)
                    ].copy()
                    history = market_data[[date_col, metric]].dropna().sort_values(date_col)
                    if history.empty:
                        market_summaries.append(
                            {
                                "market": market_name,
                                "latest": None,
                                "change": None,
                                "latest_date": None,
                            }
                        )
                        continue

                    first_value = history.iloc[0][metric]
                    latest_value = history.iloc[-1][metric]
                    period_change = None
                    if pd.notna(first_value) and first_value != 0 and len(history) > 1:
                        period_change = (latest_value - first_value) / first_value

                    market_summaries.append(
                        {
                            "market": market_name,
                            "latest": latest_value,
                            "change": period_change,
                            "latest_date": history.iloc[-1][date_col],
                        }
                    )

                if market_summaries:
                    summary_df = pd.DataFrame(market_summaries)
                    metric_label = metric.replace("_", " ").title()

                    def format_metric_value(value):
                        if pd.isna(value):
                            return "N/A"
                        if metric in ["median_sale_price", "median_list_price"]:
                            return f"${value:,.0f}"
                        if metric == "median_ppsf":
                            return f"${value:,.0f}/sq ft"
                        if metric in ["avg_sale_to_list", "sold_above_list", "price_drops"]:
                            return f"{value:.1%}"
                        if metric == "months_of_supply":
                            return f"{value:.1f}"
                        return f"{value:,.0f}"

                    st.subheader("Market read")
                    available_summary = summary_df.dropna(subset=["latest"]).copy()
                    missing_summary = summary_df[summary_df["latest"].isna()].copy()

                    if available_summary.empty:
                        st.warning("None of the selected markets has usable data for this metric and property type.")
                    else:
                        available_summary["value_rank"] = available_summary["latest"].rank(
                            method="min",
                            ascending=False,
                        ).astype(int)
                        peer_median = available_summary["latest"].median()
                        latest_leader = available_summary.loc[available_summary["latest"].idxmax()]
                        overview_parts = [
                            f"{latest_leader['market']} has the highest current {metric_label.lower()} "
                            f"at {format_metric_value(latest_leader['latest'])}."
                        ]

                        change_df = available_summary.dropna(subset=["change"])
                        if len(change_df) > 1:
                            strongest = change_df.loc[change_df["change"].idxmax()]
                            weakest = change_df.loc[change_df["change"].idxmin()]
                            change_spread = strongest["change"] - weakest["change"]
                            overview_parts.append(
                                f"Movement ranges from {strongest['change']:+.1%} in {strongest['market']} "
                                f"to {weakest['change']:+.1%} in {weakest['market']}."
                            )
                            overview_parts.append(
                                "The markets are moving similarly."
                                if change_spread < 0.05
                                else f"The {change_spread:.1%} gap indicates meaningful divergence."
                            )

                        st.info(" ".join(overview_parts))

                        st.markdown("**How each selected market compares**")
                        market_read_lines = []
                        for _, market_row in available_summary.sort_values("value_rank").iterrows():
                            relative_gap = (
                                (market_row["latest"] - peer_median) / peer_median
                                if pd.notna(peer_median) and peer_median != 0
                                else None
                            )
                            relative_text = "at the selected-market median"
                            if relative_gap is not None and abs(relative_gap) >= 0.005:
                                relative_text = (
                                    f"{abs(relative_gap):.1%} above the selected-market median"
                                    if relative_gap > 0
                                    else f"{abs(relative_gap):.1%} below the selected-market median"
                                )

                            change_text = "change unavailable"
                            if pd.notna(market_row["change"]):
                                if abs(market_row["change"]) < 0.005:
                                    change_text = "roughly flat over the selected period"
                                else:
                                    direction = "up" if market_row["change"] > 0 else "down"
                                    change_text = f"{direction} {abs(market_row['change']):.1%} over the selected period"

                            market_read_lines.append(
                                f"- **{market_row['market']}**: {format_metric_value(market_row['latest'])} "
                                f"(rank {market_row['value_rank']} of {len(available_summary)}), "
                                f"{relative_text}; {change_text}."
                            )

                        st.markdown("\n".join(market_read_lines))

                    if not missing_summary.empty:
                        missing_markets = ", ".join(missing_summary["market"].astype(str).tolist())
                        st.warning(
                            f"No usable {metric_label.lower()} data was found for: {missing_markets}. "
                            "Try another property type or time period."
                        )

                st.subheader("Latest comparison")

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
    st.subheader("Supply / Demand")
    st.caption("Understand whether housing supply or buyer activity is gaining the upper hand.")

    supply_markets = sorted(df[region_col].dropna().astype(str).unique().tolist())
    preferred_supply_market = {
        "county": "King County, WA",
        "city": "Seattle, WA",
        "state": "Washington",
    }.get(level)
    supply_market_index = (
        supply_markets.index(preferred_supply_market)
        if preferred_supply_market in supply_markets
        else 0
    )

    supply_property_types = (
        sorted(df["property_type"].dropna().astype(str).unique().tolist())
        if "property_type" in df.columns
        else []
    )
    supply_property_index = (
        supply_property_types.index("All Residential")
        if "All Residential" in supply_property_types
        else 0
    )

    supply_market_col, supply_property_col = st.columns([1.35, 1])
    with supply_market_col:
        selected_supply_market = st.selectbox(
            "Market",
            supply_markets,
            index=supply_market_index,
            key=f"supply_market_{level}",
        )
    with supply_property_col:
        selected_supply_property = st.selectbox(
            "Property type",
            supply_property_types,
            index=supply_property_index,
            key=f"supply_property_{level}",
        ) if supply_property_types else None

    supply_history = df[df[region_col].astype(str) == selected_supply_market].copy()
    if selected_supply_property and "property_type" in supply_history.columns:
        supply_history = supply_history[
            supply_history["property_type"].astype(str) == selected_supply_property
        ].copy()
    supply_history = supply_history.sort_values(date_col)

    if supply_history.empty:
        st.warning("No data is available for the selected market and property type.")
    else:
        latest_supply_row = supply_history.iloc[-1]

        def supply_value(metric_name):
            value = latest_supply_row.get(metric_name)
            return pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]

        def supply_change(metric_name):
            return calculate_period_change(supply_history, metric_name, date_col)

        inventory_value = supply_value("inventory")
        months_supply_value = supply_value("months_of_supply")
        new_listings_value = supply_value("new_listings")
        pending_sales_value = supply_value("pending_sales")
        homes_sold_value = supply_value("homes_sold")
        dom_value = supply_value("median_dom")
        sale_to_list_value = supply_value("avg_sale_to_list")
        sold_above_value = supply_value("sold_above_list")

        inventory_change = supply_change("inventory")
        new_listings_change = supply_change("new_listings")
        pending_change = supply_change("pending_sales")
        homes_sold_change = supply_change("homes_sold")
        dom_change = supply_change("median_dom")
        sale_to_list_change = supply_change("avg_sale_to_list")

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric(
            "Homes for Sale",
            f"{inventory_value:,.0f}" if pd.notna(inventory_value) else "N/A",
            f"{inventory_change:+.1%} over period" if inventory_change is not None else None,
        )
        kpi2.metric(
            "Months of Supply",
            f"{months_supply_value:.1f}" if pd.notna(months_supply_value) else "N/A",
        )
        kpi3.metric(
            "New Listings",
            f"{new_listings_value:,.0f}" if pd.notna(new_listings_value) else "N/A",
            f"{new_listings_change:+.1%} over period" if new_listings_change is not None else None,
        )
        kpi4.metric(
            "Pending Sales",
            f"{pending_sales_value:,.0f}" if pd.notna(pending_sales_value) else "N/A",
            f"{pending_change:+.1%} over period" if pending_change is not None else None,
        )

        pressure_score = 0
        pressure_evidence = 0
        if inventory_change is not None:
            pressure_score += 1 if inventory_change > 0.05 else -1 if inventory_change < -0.05 else 0
            pressure_evidence += 1
        if pending_change is not None:
            pressure_score += 1 if pending_change < -0.05 else -1 if pending_change > 0.05 else 0
            pressure_evidence += 1
        if dom_change is not None:
            pressure_score += 1 if dom_change > 0.05 else -1 if dom_change < -0.05 else 0
            pressure_evidence += 1
        if sale_to_list_change is not None:
            pressure_score += 1 if sale_to_list_change < -0.005 else -1 if sale_to_list_change > 0.005 else 0
            pressure_evidence += 1

        if pressure_evidence == 0:
            pressure_label = "Insufficient evidence"
        elif pressure_score >= 2:
            pressure_label = "Supply is gaining leverage"
        elif pressure_score <= -2:
            pressure_label = "Demand is gaining leverage"
        else:
            pressure_label = "Supply and demand look balanced"

        read_parts = [f"Current signal: {pressure_label}."]
        if inventory_change is not None and pending_change is not None:
            if inventory_change > pending_change + 0.05:
                read_parts.append(
                    f"Available inventory changed {inventory_change:+.1%}, while pending sales changed "
                    f"{pending_change:+.1%}; supply is expanding faster than buyer commitments."
                )
            elif pending_change > inventory_change + 0.05:
                read_parts.append(
                    f"Pending sales changed {pending_change:+.1%}, outpacing inventory at "
                    f"{inventory_change:+.1%}; buyers are absorbing supply more quickly."
                )
            else:
                read_parts.append(
                    f"Inventory ({inventory_change:+.1%}) and pending sales ({pending_change:+.1%}) "
                    "are moving at broadly similar rates."
                )
        elif inventory_change is not None:
            read_parts.append(f"Inventory changed {inventory_change:+.1%} over the selected period.")

        if pd.notna(months_supply_value):
            if months_supply_value >= 4:
                read_parts.append(f"At {months_supply_value:.1f} months, supply is relatively loose.")
            elif months_supply_value <= 2:
                read_parts.append(f"At {months_supply_value:.1f} months, available supply remains tight.")
            else:
                read_parts.append(f"At {months_supply_value:.1f} months, supply is in a middle range.")

        if dom_change is not None:
            speed_direction = "slowing" if dom_change > 0.05 else "accelerating" if dom_change < -0.05 else "stable"
            read_parts.append(f"Market speed is {speed_direction}, with days on market changing {dom_change:+.1%}.")

        st.subheader("Supply / demand read")
        st.info(" ".join(read_parts))

        supply_metrics = [metric for metric in ["inventory", "new_listings"] if metric in supply_history.columns]
        demand_metrics = [metric for metric in ["pending_sales", "homes_sold"] if metric in supply_history.columns]
        supply_chart_col, demand_chart_col = st.columns(2)

        def make_pressure_chart(history_df, metrics, title, colors):
            chart_df = history_df[[date_col] + metrics].copy()
            for chart_metric in metrics:
                chart_df[chart_metric] = pd.to_numeric(chart_df[chart_metric], errors="coerce")
            chart_df = chart_df.melt(
                id_vars=[date_col],
                value_vars=metrics,
                var_name="Measure",
                value_name="Value",
            )
            chart_df["Measure"] = chart_df["Measure"].str.replace("_", " ").str.title()
            chart = px.line(
                chart_df,
                x=date_col,
                y="Value",
                color="Measure",
                title=title,
                color_discrete_sequence=colors,
            )
            chart.update_traces(line_width=2.7)
            chart.update_layout(
                height=390,
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(l=20, r=20, t=60, b=20),
                xaxis_title=None,
                yaxis_title=None,
                legend_title_text=None,
                hovermode="x unified",
            )
            chart.update_xaxes(showgrid=False)
            chart.update_yaxes(gridcolor="#e8eeeb")
            return chart

        with supply_chart_col:
            if supply_metrics:
                st.plotly_chart(
                    make_pressure_chart(
                        supply_history,
                        supply_metrics,
                        "Supply entering the market",
                        ["#28735a", "#79a88f"],
                    ),
                    use_container_width=True,
                )
        with demand_chart_col:
            if demand_metrics:
                st.plotly_chart(
                    make_pressure_chart(
                        supply_history,
                        demand_metrics,
                        "Buyer activity",
                        ["#4f7f96", "#d08b49"],
                    ),
                    use_container_width=True,
                )

        st.subheader("Competition and market speed")
        competition1, competition2, competition3, competition4 = st.columns(4)
        competition1.metric(
            "Days on Market",
            f"{dom_value:,.0f}" if pd.notna(dom_value) else "N/A",
            f"{dom_change:+.1%} over period" if dom_change is not None else None,
        )
        competition2.metric(
            "Sale-to-List",
            f"{sale_to_list_value:.2%}" if pd.notna(sale_to_list_value) else "N/A",
            f"{sale_to_list_change:+.1%} over period" if sale_to_list_change is not None else None,
            delta_color="inverse",
        )
        competition3.metric(
            "Sold Above List",
            f"{sold_above_value:.1%}" if pd.notna(sold_above_value) else "N/A",
        )
        competition4.metric(
            "Homes Sold",
            f"{homes_sold_value:,.0f}" if pd.notna(homes_sold_value) else "N/A",
            f"{homes_sold_change:+.1%} over period" if homes_sold_change is not None else None,
        )

with tab4:
    st.subheader("Market Power")
    st.caption("See who has negotiating leverage, what is driving it, and how the balance is changing.")

    power_property_types = (
        sorted(df["property_type"].dropna().astype(str).unique().tolist())
        if "property_type" in df.columns
        else []
    )
    power_property_index = (
        power_property_types.index("All Residential")
        if "All Residential" in power_property_types
        else 0
    )
    power_market_col, power_property_col = st.columns([1.35, 1])
    with power_property_col:
        selected_power_property = st.selectbox(
            "Property type",
            power_property_types,
            index=power_property_index,
            key=f"power_property_{level}",
        ) if power_property_types else None

    power_base_df = df.copy()
    if selected_power_property and "property_type" in power_base_df.columns:
        power_base_df = power_base_df[
            power_base_df["property_type"].astype(str) == selected_power_property
        ].copy()

    signal_df = add_market_signal(power_base_df)
    power_markets = sorted(signal_df[region_col].dropna().astype(str).unique().tolist())
    preferred_power_market = {
        "county": "King County, WA",
        "city": "Seattle, WA",
        "state": "Washington",
    }.get(level)
    power_market_index = (
        power_markets.index(preferred_power_market)
        if preferred_power_market in power_markets
        else 0
    )
    with power_market_col:
        selected_power_market = st.selectbox(
            "Market",
            power_markets,
            index=power_market_index,
            key=f"power_market_{level}",
        )

    power_history = signal_df[
        signal_df[region_col].astype(str) == selected_power_market
    ].copy().sort_values(date_col)

    if power_history.empty:
        st.warning("No market-power data is available for this selection.")
    else:
        latest_power = power_history.iloc[-1]
        current_score = pd.to_numeric(
            pd.Series([latest_power.get("buyer_market_score")]), errors="coerce"
        ).iloc[0]
        current_regime = latest_power.get("market_regime", "Unknown")
        current_mos = pd.to_numeric(
            pd.Series([latest_power.get("months_of_supply")]), errors="coerce"
        ).iloc[0]
        current_dom = pd.to_numeric(
            pd.Series([latest_power.get("median_dom")]), errors="coerce"
        ).iloc[0]
        current_inventory_yoy = pd.to_numeric(
            pd.Series([latest_power.get("inventory_yoy")]), errors="coerce"
        ).iloc[0]
        current_price_yoy = pd.to_numeric(
            pd.Series([latest_power.get("median_sale_price_yoy")]), errors="coerce"
        ).iloc[0]
        current_sale_to_list = pd.to_numeric(
            pd.Series([latest_power.get("avg_sale_to_list")]), errors="coerce"
        ).iloc[0]
        current_sold_above = pd.to_numeric(
            pd.Series([latest_power.get("sold_above_list")]), errors="coerce"
        ).iloc[0]

        first_valid_score = power_history["buyer_market_score"].dropna()
        score_point_change = (
            current_score - first_valid_score.iloc[0]
            if pd.notna(current_score) and not first_valid_score.empty
            else None
        )

        regime_class = {
            "Buyer market": "badge-buyer",
            "Seller market": "badge-seller",
            "Balanced / mixed": "badge-balanced",
        }.get(current_regime, "badge-balanced")
        st.markdown(
            f'<div class="market-heading">{selected_power_market}</div>'
            f'<div class="market-meta">Latest data: {latest_power[date_col]:%B %Y} &nbsp; '
            f'<span class="market-badge {regime_class}">{current_regime}</span></div>',
            unsafe_allow_html=True,
        )

        if pd.isna(current_score):
            leverage_label = "Leverage unavailable"
            leverage_explanation = "There is not enough complete data to assess negotiating leverage."
            marker_position = 50
        elif current_score >= 0.75:
            leverage_label = "Clear buyer advantage"
            leverage_explanation = "Buyers generally have more choice and negotiating room than sellers."
            marker_position = min(96, 50 + (current_score / 1.5) * 46)
        elif current_score >= 0.15:
            leverage_label = "Slight buyer edge"
            leverage_explanation = "Conditions are broadly balanced, but buyers have somewhat more leverage."
            marker_position = min(96, 50 + (current_score / 1.5) * 46)
        elif current_score > -0.15:
            leverage_label = "Evenly balanced"
            leverage_explanation = "Neither side has a clear negotiating advantage based on current indicators."
            marker_position = 50 + (current_score / 1.5) * 46
        elif current_score > -0.75:
            leverage_label = "Slight seller edge"
            leverage_explanation = "The market is still mixed, but sellers retain somewhat more leverage."
            marker_position = max(4, 50 + (current_score / 1.5) * 46)
        else:
            leverage_label = "Clear seller advantage"
            leverage_explanation = "Tighter or faster conditions generally give sellers more negotiating power."
            marker_position = max(4, 50 + (current_score / 1.5) * 46)

        st.markdown(
            f"""
            <div class="leverage-panel">
                <div class="section-kicker">Who has leverage?</div>
                <div class="leverage-title">{leverage_label}</div>
                <div class="leverage-copy">{leverage_explanation}</div>
                <div class="leverage-track">
                    <div class="leverage-marker" style="left: {marker_position:.1f}%;"></div>
                </div>
                <div class="leverage-labels">
                    <span>Seller advantage</span><span>Balanced</span><span>Buyer advantage</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        power1, power2, power3, power4 = st.columns(4)
        power1.metric(
            "Model Score",
            f"{current_score:+.2f}" if pd.notna(current_score) else "N/A",
            f"{score_point_change:+.2f} points over period" if score_point_change is not None else None,
            help="Positive values favor buyers, negative values favor sellers, and values near zero are balanced. This is a relative index, not a percentage.",
        )
        power2.metric(
            "Months of Supply",
            f"{current_mos:.1f}" if pd.notna(current_mos) else "N/A",
        )
        power3.metric(
            "Days on Market",
            f"{current_dom:,.0f}" if pd.notna(current_dom) else "N/A",
        )
        power4.metric(
            "Sale-to-List",
            f"{current_sale_to_list:.2%}" if pd.notna(current_sale_to_list) else "N/A",
        )

        buyer_drivers = []
        seller_drivers = []
        neutral_drivers = []

        if pd.notna(current_mos):
            if current_mos >= 4:
                buyer_drivers.append(f"{current_mos:.1f} months of supply gives buyers more choice")
            elif current_mos <= 2:
                seller_drivers.append(f"only {current_mos:.1f} months of supply keeps choices tight")
            else:
                neutral_drivers.append(f"{current_mos:.1f} months of supply is in a middle range")
        if pd.notna(current_dom):
            if current_dom >= 45:
                buyer_drivers.append(f"homes take {current_dom:.0f} days to sell")
            elif current_dom <= 14:
                seller_drivers.append(f"homes sell quickly at a median {current_dom:.0f} days")
            else:
                neutral_drivers.append(f"the median sale takes {current_dom:.0f} days")
        if pd.notna(current_inventory_yoy):
            if current_inventory_yoy >= 0.10:
                buyer_drivers.append(f"inventory is up {current_inventory_yoy:.1%} year over year")
            elif current_inventory_yoy <= -0.10:
                seller_drivers.append(f"inventory is down {abs(current_inventory_yoy):.1%} year over year")
        if pd.notna(current_price_yoy):
            if current_price_yoy <= -0.03:
                buyer_drivers.append(f"prices are down {abs(current_price_yoy):.1%} year over year")
            elif current_price_yoy >= 0.05:
                seller_drivers.append(f"prices are up {current_price_yoy:.1%} year over year")
        if pd.notna(current_sale_to_list):
            if current_sale_to_list < 0.99:
                buyer_drivers.append(f"homes sell at {current_sale_to_list:.1%} of list price")
            elif current_sale_to_list >= 1.01:
                seller_drivers.append(f"homes sell above asking at {current_sale_to_list:.1%} of list")
        if pd.notna(current_sold_above):
            if current_sold_above >= 0.40:
                seller_drivers.append(f"{current_sold_above:.1%} of homes sell above list")
            elif current_sold_above <= 0.15:
                buyer_drivers.append(f"only {current_sold_above:.1%} of homes sell above list")

        read_parts = []
        if score_point_change is not None:
            if score_point_change > 0.20:
                read_parts.append(f"Conditions shifted toward buyers by {score_point_change:.2f} points over the selected period.")
            elif score_point_change < -0.20:
                read_parts.append(f"Conditions shifted toward sellers by {abs(score_point_change):.2f} points over the selected period.")
            else:
                read_parts.append("Negotiating leverage has remained relatively stable over the selected period.")
        if buyer_drivers:
            read_parts.append("Buyer signals: " + "; ".join(buyer_drivers) + ".")
        if seller_drivers:
            read_parts.append("Seller signals: " + "; ".join(seller_drivers) + ".")
        if neutral_drivers and not buyer_drivers and not seller_drivers:
            read_parts.append("Mixed signals: " + "; ".join(neutral_drivers) + ".")

        st.subheader("Why the market leans this way")
        st.info(" ".join(read_parts))

        if pd.notna(current_score) and current_score >= 0.75:
            buyer_implication = "You may have room to negotiate price, request repairs, or include protective contingencies. Compare listings carefully because more choice can reduce urgency."
            seller_implication = "Expect buyers to compare alternatives and negotiate. Pricing realistically and presenting the home well will matter more than testing an aggressive price."
        elif pd.notna(current_score) and current_score >= 0.15:
            buyer_implication = "There may be modest negotiating room, especially for listings that have been on the market longer. Strong properties can still attract competition."
            seller_implication = "Well-priced homes can still perform, but buyers have some alternatives. Avoid relying on automatic bidding pressure."
        elif pd.notna(current_score) and current_score <= -0.75:
            buyer_implication = "Competition may limit discounts and contingencies. Be prepared to act quickly on desirable homes, while staying within your financial limits."
            seller_implication = "Conditions support stronger pricing and cleaner offers. Accurate pricing can capture demand without unnecessarily limiting the buyer pool."
        elif pd.notna(current_score) and current_score <= -0.15:
            buyer_implication = "Sellers have a modest edge, particularly on desirable homes. Negotiation is still possible, but strong listings may move quickly."
            seller_implication = "You have some leverage, though the market is not strongly seller-dominated. Good preparation and realistic pricing remain important."
        else:
            buyer_implication = "Neither side has a clear advantage. Focus negotiation on the property’s condition, time on market, and seller motivation."
            seller_implication = "Pricing and presentation are likely to matter more than broad market leverage. Expect offers to reflect each property’s specific strengths."

        buyer_meaning_col, seller_meaning_col = st.columns(2)
        with buyer_meaning_col:
            st.markdown(
                f'<div class="meaning-card meaning-buyer"><div class="meaning-title">What this means for buyers</div>'
                f'<div class="meaning-copy">{buyer_implication}</div></div>',
                unsafe_allow_html=True,
            )
        with seller_meaning_col:
            st.markdown(
                f'<div class="meaning-card meaning-seller"><div class="meaning-title">What this means for sellers</div>'
                f'<div class="meaning-copy">{seller_implication}</div></div>',
                unsafe_allow_html=True,
            )

        power_chart = go.Figure()
        power_chart.add_hrect(y0=0.75, y1=3, fillcolor="#e6f1f8", opacity=0.65, line_width=0)
        power_chart.add_hrect(y0=-0.75, y1=0.75, fillcolor="#f1f3f2", opacity=0.8, line_width=0)
        power_chart.add_hrect(y0=-3, y1=-0.75, fillcolor="#fae9e6", opacity=0.65, line_width=0)
        power_chart.add_trace(
            go.Scatter(
                x=power_history[date_col],
                y=power_history["buyer_market_score"],
                mode="lines+markers",
                line=dict(color="#28735a", width=3),
                marker=dict(size=6),
                name="Buyer power score",
                hovertemplate="%{x|%b %Y}<br>Score: %{y:+.2f}<extra></extra>",
            )
        )
        power_chart.add_hline(y=0.75, line_dash="dot", line_color="#4f7f96")
        power_chart.add_hline(y=-0.75, line_dash="dot", line_color="#d96c5f")
        power_chart.add_annotation(
            x=0.01, y=0.90, xref="paper", yref="paper",
            text="Buyer advantage", showarrow=False,
            font=dict(color="#246083", size=12), bgcolor="rgba(230,241,248,0.9)",
        )
        power_chart.add_annotation(
            x=0.01, y=0.50, xref="paper", yref="paper",
            text="Balanced / mixed", showarrow=False,
            font=dict(color="#52616b", size=12), bgcolor="rgba(241,243,242,0.9)",
        )
        power_chart.add_annotation(
            x=0.01, y=0.10, xref="paper", yref="paper",
            text="Seller advantage", showarrow=False,
            font=dict(color="#a7493e", size=12), bgcolor="rgba(250,233,230,0.9)",
        )
        power_chart.update_layout(
            title="How negotiating leverage has changed",
            height=430,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=60, b=20),
            xaxis_title=None,
            yaxis_title=None,
            showlegend=False,
            hovermode="x unified",
        )
        power_chart.update_xaxes(showgrid=False)
        power_chart.update_yaxes(gridcolor="#e8eeeb", zeroline=True, zerolinecolor="#9aa8a1")
        st.plotly_chart(power_chart, use_container_width=True)

        latest_signal = (
            signal_df.sort_values(date_col)
            .groupby(region_col, as_index=False)
            .tail(1)
            .dropna(subset=["buyer_market_score"])
            .copy()
        )
        latest_signal["peer_rank"] = latest_signal["buyer_market_score"].rank(
            method="min",
            ascending=False,
        ).astype(int)
        selected_peer = latest_signal[
            latest_signal[region_col].astype(str) == selected_power_market
        ]

        st.subheader("How this market compares")
        if not selected_peer.empty:
            peer_row = selected_peer.iloc[0]
            st.caption(
                f"{selected_power_market} ranks {peer_row['peer_rank']} of {len(latest_signal)} "
                "markets for buyer leverage. Rank 1 is the most buyer-friendly market in the current comparison."
            )

        peer_view = latest_signal.nlargest(10, "buyer_market_score").copy()
        if not selected_peer.empty and selected_power_market not in peer_view[region_col].astype(str).tolist():
            peer_view = pd.concat([peer_view, selected_peer], ignore_index=True)
        peer_view = peer_view.sort_values("buyer_market_score")
        peer_chart = px.bar(
            peer_view,
            x="buyer_market_score",
            y=region_col,
            orientation="h",
            color="buyer_market_score",
            color_continuous_scale=["#d96c5f", "#f1f3f2", "#4f7f96"],
            color_continuous_midpoint=0,
            title="Markets offering the most buyer leverage",
        )
        peer_chart.update_layout(
            height=max(380, 34 * len(peer_view)),
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=60, b=20),
            xaxis_title="Buyer power score",
            yaxis_title=None,
            coloraxis_showscale=False,
        )
        peer_chart.update_xaxes(gridcolor="#e8eeeb")
        st.plotly_chart(peer_chart, use_container_width=True)

        with st.expander("How the score works"):
            st.write(
                "The model score is a relative index, not a percentage. Positive values lean toward buyers, "
                "negative values lean toward sellers, and values near zero are balanced. Scores of +0.75 or "
                "higher are classified as buyer markets; scores of -0.75 or lower are seller markets. The model "
                "weighs months of supply, days on market, inventory growth, price growth, sales activity, "
                "sale-to-list ratio, and the share of homes sold above list."
            )
            st.caption(
                "Example: -0.49 means a modest seller lean, not 49% less buyer power. Scores are standardized "
                "relative to the markets, property type, and time period being analyzed."
            )

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
    st.subheader("Opportunity Finder")
    st.caption(
        "Screen Washington markets for buyer value or seller strength using current market conditions. "
        "This ranks markets, not individual properties."
    )

    finder_goal = st.radio(
        "I want to",
        ["Find buyer opportunities", "Find seller opportunities"],
        horizontal=True,
        key="opportunity_goal",
    )

    finder_property_types = (
        sorted(df["property_type"].dropna().astype(str).unique().tolist())
        if "property_type" in df.columns
        else []
    )
    finder_property_index = (
        finder_property_types.index("All Residential")
        if "All Residential" in finder_property_types
        else 0
    )

    finder_property_col, finder_results_col = st.columns([1.4, 1])
    with finder_property_col:
        finder_property = st.selectbox(
            "Property type",
            finder_property_types,
            index=finder_property_index,
            key=f"finder_property_{level}",
        ) if finder_property_types else None
    with finder_results_col:
        result_count = st.slider("Results to show", 5, 20, 10, key="finder_result_count")

    finder_df = df.copy()
    if finder_property and "property_type" in finder_df.columns:
        finder_df = finder_df[
            finder_df["property_type"].astype(str) == finder_property
        ].copy()

    latest_opportunities = (
        finder_df.sort_values(date_col)
        .groupby(region_col, as_index=False)
        .tail(1)
        .copy()
    )

    opportunity_metrics = [
        "median_sale_price",
        "median_sale_price_yoy_calc",
        "inventory_yoy_calc",
        "months_of_supply",
        "median_dom",
        "avg_sale_to_list",
        "sold_above_list",
        "price_drops",
        "homes_sold",
        "homes_sold_yoy_calc",
    ]
    for opportunity_metric in opportunity_metrics:
        if opportunity_metric not in latest_opportunities.columns:
            latest_opportunities[opportunity_metric] = None
        latest_opportunities[opportunity_metric] = pd.to_numeric(
            latest_opportunities[opportunity_metric], errors="coerce"
        )

    available_prices = latest_opportunities["median_sale_price"].dropna()
    max_price_default = int(available_prices.quantile(0.75)) if not available_prices.empty else 1000000
    max_price_limit = int(available_prices.max()) if not available_prices.empty else 2000000
    max_price_limit = max(100000, int(math.ceil(max_price_limit / 50000) * 50000))
    max_price_default = min(max_price_default, max_price_limit)

    filter_price_col, filter_activity_col = st.columns(2)
    with filter_price_col:
        if finder_goal == "Find buyer opportunities":
            max_purchase_price = st.slider(
                "Maximum median sale price",
                min_value=100000,
                max_value=max_price_limit,
                value=max(100000, max_price_default),
                step=25000,
                format="$%d",
                key=f"finder_max_price_{level}",
            )
        else:
            max_purchase_price = None
            minimum_price = st.slider(
                "Minimum median sale price",
                min_value=0,
                max_value=max_price_limit,
                value=0,
                step=25000,
                format="$%d",
                key=f"finder_min_price_{level}",
            )
    with filter_activity_col:
        minimum_sales = st.slider(
            "Minimum monthly homes sold",
            min_value=0,
            max_value=max(10, int(latest_opportunities["homes_sold"].max(skipna=True) or 10)),
            value=10 if level in ["county", "city"] else 0,
            step=10,
            key=f"finder_min_sales_{level}",
            help="Filters out very small markets where monthly statistics can be volatile.",
        )

    if finder_goal == "Find buyer opportunities":
        latest_opportunities = latest_opportunities[
            latest_opportunities["median_sale_price"].le(max_purchase_price)
            | latest_opportunities["median_sale_price"].isna()
        ].copy()
    else:
        latest_opportunities = latest_opportunities[
            latest_opportunities["median_sale_price"].ge(minimum_price)
            | latest_opportunities["median_sale_price"].isna()
        ].copy()
    latest_opportunities = latest_opportunities[
        latest_opportunities["homes_sold"].fillna(0) >= minimum_sales
    ].copy()

    def finder_zscore(series):
        numeric = pd.to_numeric(series, errors="coerce")
        std = numeric.std(skipna=True)
        if pd.isna(std) or std == 0:
            return pd.Series(0.0, index=numeric.index)
        return ((numeric - numeric.mean(skipna=True)) / std).fillna(0)

    if latest_opportunities.empty:
        st.warning("No markets match these filters. Try widening the price or sales criteria.")
    else:
        price_z = finder_zscore(latest_opportunities["median_sale_price"])
        price_growth_z = finder_zscore(latest_opportunities["median_sale_price_yoy_calc"])
        inventory_growth_z = finder_zscore(latest_opportunities["inventory_yoy_calc"])
        supply_z = finder_zscore(latest_opportunities["months_of_supply"])
        dom_z = finder_zscore(latest_opportunities["median_dom"])
        sale_to_list_z = finder_zscore(latest_opportunities["avg_sale_to_list"])
        sold_above_z = finder_zscore(latest_opportunities["sold_above_list"])
        price_drops_z = finder_zscore(latest_opportunities["price_drops"])
        sales_growth_z = finder_zscore(latest_opportunities["homes_sold_yoy_calc"])

        latest_opportunities["buyer_opportunity_score"] = (
            -0.25 * price_z
            -0.20 * price_growth_z
            +0.20 * supply_z
            +0.15 * dom_z
            +0.10 * inventory_growth_z
            -0.05 * sale_to_list_z
            +0.05 * price_drops_z
        )
        latest_opportunities["seller_opportunity_score"] = (
            +0.25 * price_growth_z
            -0.20 * supply_z
            -0.15 * dom_z
            +0.15 * sale_to_list_z
            +0.10 * sold_above_z
            +0.10 * sales_growth_z
            +0.05 * price_z
        )

        score_column = (
            "buyer_opportunity_score"
            if finder_goal == "Find buyer opportunities"
            else "seller_opportunity_score"
        )
        latest_opportunities = latest_opportunities.sort_values(
            score_column, ascending=False
        ).copy()
        latest_opportunities["opportunity_rank"] = range(1, len(latest_opportunities) + 1)

        def opportunity_reasons(row, buyer_mode):
            reasons = []
            price = row.get("median_sale_price")
            price_yoy = row.get("median_sale_price_yoy_calc")
            inventory_yoy = row.get("inventory_yoy_calc")
            supply = row.get("months_of_supply")
            dom = row.get("median_dom")
            sale_to_list = row.get("avg_sale_to_list")
            sold_above = row.get("sold_above_list")

            if buyer_mode:
                if pd.notna(price) and price <= latest_opportunities["median_sale_price"].median():
                    reasons.append("below-median pricing")
                if pd.notna(price_yoy) and price_yoy <= 0:
                    reasons.append(f"prices {price_yoy:+.1%} YoY")
                if pd.notna(supply) and supply >= 3:
                    reasons.append(f"{supply:.1f} months of supply")
                if pd.notna(dom) and dom >= 30:
                    reasons.append(f"{dom:.0f} days on market")
                if pd.notna(inventory_yoy) and inventory_yoy >= 0.10:
                    reasons.append(f"inventory up {inventory_yoy:.1%}")
                if pd.notna(sale_to_list) and sale_to_list < 0.99:
                    reasons.append("sales below asking")
            else:
                if pd.notna(price_yoy) and price_yoy >= 0.03:
                    reasons.append(f"prices up {price_yoy:.1%} YoY")
                if pd.notna(supply) and supply <= 2.5:
                    reasons.append(f"tight {supply:.1f}-month supply")
                if pd.notna(dom) and dom <= 21:
                    reasons.append(f"fast {dom:.0f}-day market")
                if pd.notna(sale_to_list) and sale_to_list >= 1:
                    reasons.append("selling at or above asking")
                if pd.notna(sold_above) and sold_above >= 0.30:
                    reasons.append(f"{sold_above:.0%} sell above list")
            return ", ".join(reasons[:3]) if reasons else "relative strength across available indicators"

        buyer_mode = finder_goal == "Find buyer opportunities"
        latest_opportunities["Why it ranks"] = latest_opportunities.apply(
            lambda row: opportunity_reasons(row, buyer_mode), axis=1
        )
        top_opportunities = latest_opportunities.head(result_count).copy()
        leader = top_opportunities.iloc[0]

        if buyer_mode:
            lead_read = (
                f"{leader[region_col]} is the strongest buyer-market candidate under the current filters. "
                f"Its median sale price is ${leader['median_sale_price']:,.0f}, with "
                f"{leader['months_of_supply']:.1f} months of supply and "
                f"{leader['median_dom']:.0f} median days on market. "
                f"Key signals: {leader['Why it ranks']}."
            )
        else:
            lead_read = (
                f"{leader[region_col]} currently shows the strongest conditions for sellers. "
                f"Its median sale price is ${leader['median_sale_price']:,.0f}, homes sell at "
                f"{leader['avg_sale_to_list']:.1%} of list price, and the median sale takes "
                f"{leader['median_dom']:.0f} days. Key signals: {leader['Why it ranks']}."
            )

        st.subheader("Opportunity read")
        st.info(lead_read)
        if st.button(
            f"Open top opportunity: {leader[region_col]}",
            type="primary",
            use_container_width=True,
            key=f"open_top_opportunity_{level}_{finder_goal}",
        ):
            st.session_state["_pending_market_navigation"] = leader[region_col]
            st.session_state["_pending_property_type"] = finder_property
            st.rerun()

        chart_title = "Best markets for buyers" if buyer_mode else "Strongest markets for sellers"
        opportunity_chart = px.bar(
            top_opportunities.sort_values(score_column),
            x=score_column,
            y=region_col,
            orientation="h",
            color=score_column,
            color_continuous_scale=["#d9e4df", "#28735a"] if buyer_mode else ["#f4d8d4", "#b95347"],
            title=chart_title,
            hover_data={
                "median_sale_price": ":$,.0f",
                "months_of_supply": ":.1f",
                "median_dom": ":.0f",
                score_column: ":.2f",
            },
        )
        opportunity_chart.update_layout(
            height=max(390, 36 * len(top_opportunities)),
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=60, b=20),
            xaxis_title="Relative opportunity score",
            yaxis_title=None,
            coloraxis_showscale=False,
        )
        opportunity_chart.update_xaxes(gridcolor="#e8eeeb")
        st.plotly_chart(opportunity_chart, use_container_width=True)

        st.subheader("Ranked market opportunities")
        display_df = top_opportunities[
            [
                "opportunity_rank",
                region_col,
                "median_sale_price",
                "median_sale_price_yoy_calc",
                "months_of_supply",
                "median_dom",
                "avg_sale_to_list",
                "homes_sold",
                "Why it ranks",
            ]
        ].copy()
        display_df.columns = [
            "Rank",
            "Market",
            "Median Sale Price",
            "Price YoY",
            "Months of Supply",
            "Days on Market",
            "Sale-to-List",
            "Homes Sold",
            "Why it ranks",
        ]
        display_df["Median Sale Price"] = display_df["Median Sale Price"].map(
            lambda value: f"${value:,.0f}" if pd.notna(value) else "N/A"
        )
        display_df["Price YoY"] = display_df["Price YoY"].map(
            lambda value: f"{value:.1%}" if pd.notna(value) else "N/A"
        )
        display_df["Months of Supply"] = display_df["Months of Supply"].map(
            lambda value: f"{value:.1f}" if pd.notna(value) else "N/A"
        )
        display_df["Days on Market"] = display_df["Days on Market"].map(
            lambda value: f"{value:,.0f}" if pd.notna(value) else "N/A"
        )
        display_df["Sale-to-List"] = display_df["Sale-to-List"].map(
            lambda value: f"{value:.1%}" if pd.notna(value) else "N/A"
        )
        display_df["Homes Sold"] = display_df["Homes Sold"].map(
            lambda value: f"{value:,.0f}" if pd.notna(value) else "N/A"
        )
        opportunity_selection = st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            key=f"opportunity_results_{level}_{finder_goal}_{finder_property}",
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Rank": st.column_config.NumberColumn(width="small"),
                "Market": st.column_config.TextColumn(width="medium"),
                "Median Sale Price": st.column_config.TextColumn(width="medium"),
                "Price YoY": st.column_config.TextColumn(width="small"),
                "Months of Supply": st.column_config.TextColumn(width="small"),
                "Days on Market": st.column_config.TextColumn(width="small"),
                "Sale-to-List": st.column_config.TextColumn(width="small"),
                "Homes Sold": st.column_config.TextColumn(width="small"),
                "Why it ranks": st.column_config.TextColumn(width="large"),
            },
        )

        selected_opportunity_rows = opportunity_selection.selection.rows
        if selected_opportunity_rows:
            selected_opportunity_index = selected_opportunity_rows[0]
            selected_opportunity_market = display_df.iloc[selected_opportunity_index]["Market"]
            st.caption(
                f"Selected: **{selected_opportunity_market}**. Opening it will also add the market "
                "to the Price Trends comparison."
            )
            if st.button(
                "Open selected market",
                type="primary",
                use_container_width=True,
                key=f"open_opportunity_{level}_{finder_goal}",
            ):
                st.session_state["_pending_market_navigation"] = selected_opportunity_market
                st.session_state["_pending_property_type"] = finder_property
                st.rerun()
        else:
            st.caption("Select a row to open that market in Overview and add it to Price Trends.")

        with st.expander("How opportunities are ranked"):
            if buyer_mode:
                st.write(
                    "Buyer rankings reward lower prices, softer price growth, more months of supply, "
                    "longer market time, inventory growth, price reductions, and weaker sale-to-list pressure."
                )
            else:
                st.write(
                    "Seller rankings reward stronger price growth, tighter supply, faster sales, "
                    "higher sale-to-list ratios, more above-list sales, and stronger sales activity."
                )
            st.caption(
                "Scores are relative to the markets matching the current filters. They identify markets "
                "worth investigating and do not predict a specific transaction price or guarantee a return."
            )

        with st.expander("View underlying latest records"):
            st.dataframe(top_opportunities, use_container_width=True, hide_index=True)
