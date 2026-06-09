from __future__ import annotations

from pathlib import Path
from io import StringIO
import pandas as pd
import requests
import streamlit as st

from config import (
    REDFIN_STATE_MARKET_TRACKER_URL,
    REDFIN_COUNTY_MARKET_TRACKER_URL,
    REDFIN_CITY_MARKET_TRACKER_URL,
    REDFIN_ZIP_MARKET_TRACKER_URL,
    FRED_CSV_BASE,
)


DATA_DIR = Path("local_data")
DATA_DIR.mkdir(exist_ok=True)


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = (
        out.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
        .str.replace("/", "_", regex=False)
    )
    return out


def detect_date_col(df: pd.DataFrame) -> str | None:
    for c in ["period_end", "period_begin", "date"]:
        if c in df.columns:
            return c
    return None


def detect_region_col(df: pd.DataFrame) -> str:
    if df.empty or len(df.columns) == 0:
        raise ValueError("Dataset is empty or has no columns. Refresh cache may have failed.")

    for c in ["region", "region_name", "county", "city", "zip_code"]:
        if c in df.columns:
            return c

    raise ValueError(f"No region column found. Available columns: {df.columns.tolist()}")


def redfin_url_for_level(level: str) -> str:
    urls = {
        "state": REDFIN_STATE_MARKET_TRACKER_URL,
        "county": REDFIN_COUNTY_MARKET_TRACKER_URL,
        "city": REDFIN_CITY_MARKET_TRACKER_URL,
        "zip": REDFIN_ZIP_MARKET_TRACKER_URL,
    }
    return urls[level]


def parquet_path_for_level(level: str) -> Path:
    return DATA_DIR / f"redfin_wa_{level}.parquet"


def refresh_redfin_cache(level: str, state_filter: str = "Washington") -> pd.DataFrame:
    """
    Download Redfin data once, filter to Washington, and save locally as Parquet.

    This is intentionally run only when the user clicks Refresh Data.
    """
    url = redfin_url_for_level(level)

    use_cols = None

    # Keep only useful columns to reduce memory.
    # If Redfin changes column names, fallback will still try full load.
    useful_cols = [
        "period_begin",
        "period_end",
        "period_duration",
        "region_type",
        "region_type_id",
        "table_id",
        "is_seasonally_adjusted",
        "region",
        "city",
        "state",
        "state_code",
        "property_type",
        "property_type_id",
        "median_sale_price",
        "median_sale_price_mom",
        "median_sale_price_yoy",
        "median_list_price",
        "median_list_price_mom",
        "median_list_price_yoy",
        "median_ppsf",
        "median_ppsf_mom",
        "median_ppsf_yoy",
        "homes_sold",
        "homes_sold_mom",
        "homes_sold_yoy",
        "pending_sales",
        "new_listings",
        "inventory",
        "inventory_mom",
        "inventory_yoy",
        "months_of_supply",
        "months_of_supply_mom",
        "months_of_supply_yoy",
        "median_dom",
        "median_dom_mom",
        "median_dom_yoy",
        "avg_sale_to_list",
        "sold_above_list",
        "price_drops",
    ]

  
            # First read only the header so we know actual column names.
    header_df = pd.read_csv(
    url,
    sep="\t",
    compression="gzip",
    nrows=0,
    )

    raw_columns = header_df.columns.tolist()

    useful_cols_normalized = {
        "period_begin",
        "period_end",
        "period_duration",
        "region_type",
        "region_type_id",
        "table_id",
        "is_seasonally_adjusted",
        "region",
        "city",
        "state",
        "state_code",
        "property_type",
        "property_type_id",
        "median_sale_price",
        "median_sale_price_mom",
        "median_sale_price_yoy",
        "median_list_price",
        "median_list_price_mom",
        "median_list_price_yoy",
        "median_ppsf",
        "median_ppsf_mom",
        "median_ppsf_yoy",
        "homes_sold",
        "homes_sold_mom",
        "homes_sold_yoy",
        "pending_sales",
        "new_listings",
        "inventory",
        "inventory_mom",
        "inventory_yoy",
        "months_of_supply",
        "months_of_supply_mom",
        "months_of_supply_yoy",
        "median_dom",
        "median_dom_mom",
        "median_dom_yoy",
        "avg_sale_to_list",
        "sold_above_list",
        "price_drops",
    }

    def normalize_col_name(c: str) -> str:
        return (
            str(c)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
        )

    selected_raw_cols = [
        c for c in raw_columns
        if normalize_col_name(c) in useful_cols_normalized
    ]

    if not selected_raw_cols:
        raise ValueError(
            f"No matching useful columns found. Raw columns were: {raw_columns[:20]}"
        )

    df = pd.read_csv(
        url,
        sep="\t",
        compression="gzip",
        low_memory=False,
        usecols=selected_raw_cols,
    )
    df = standardize_columns(df)

    # Washington filter
    if "state" in df.columns:
        df = df[df["state"].astype(str).str.contains(state_filter, case=False, na=False)]
    elif "state_code" in df.columns:
        df = df[df["state_code"].astype(str).str.upper().eq("WA")]

    date_col = detect_date_col(df)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col]).sort_values(date_col)

    path = parquet_path_for_level(level)
    df.to_parquet(path, index=False)

    return df


def load_redfin_cached(level: str) -> pd.DataFrame:
    """
    Load Redfin WA data from local Parquet cache.
    If cache does not exist, user must refresh.
    """
    path = parquet_path_for_level(level)

    if not path.exists():
        raise FileNotFoundError(
            f"No local cache found for '{level}'. Click Refresh Data first."
        )

    return pd.read_parquet(path)


def load_fred_series(series_id: str) -> pd.DataFrame:
    url = FRED_CSV_BASE + series_id
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    df = pd.read_csv(StringIO(r.text))
    if len(df.columns) != 2:
        raise ValueError(f"Unexpected FRED CSV columns: {df.columns.tolist()}")

    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["date"])