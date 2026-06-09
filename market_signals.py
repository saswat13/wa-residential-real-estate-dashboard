import numpy as np
import pandas as pd


def _z(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    std = s.std(skipna=True)
    if std is None or std == 0 or np.isnan(std):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.mean(skipna=True)) / std


def classify_score(score: float) -> str:
    if pd.isna(score):
        return "Unknown"
    if score >= 0.75:
        return "Buyer market"
    if score <= -0.75:
        return "Seller market"
    return "Balanced / mixed"


def add_market_signal(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # Make columns exist even if Redfin schema changes.
    for col in [
        "months_of_supply",
        "median_dom",
        "inventory_yoy",
        "median_sale_price_yoy",
        "homes_sold_yoy",
        "avg_sale_to_list",
        "sold_above_list",
    ]:
        if col not in out.columns:
            out[col] = np.nan

    # Higher = more buyer-friendly.
    out["buyer_market_score"] = (
        0.30 * _z(out["months_of_supply"])
        + 0.25 * _z(out["median_dom"])
        + 0.20 * _z(out["inventory_yoy"])
        - 0.15 * _z(out["median_sale_price_yoy"])
        - 0.05 * _z(out["homes_sold_yoy"])
        - 0.03 * _z(out["avg_sale_to_list"])
        - 0.02 * _z(out["sold_above_list"])
    )

    out["market_regime"] = out["buyer_market_score"].apply(classify_score)
    return out
