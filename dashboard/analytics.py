"""Pure analytics functions for the Phase 1 dashboard."""

import numpy as np
import pandas as pd

from dashboard.data import calendar_months


KPI_NAMES = ("ROAS", "CTR", "CPP")


def filter_data(
    data: pd.DataFrame,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    categories: tuple[str, ...] = (),
    media_types: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Apply the dashboard's global filters."""
    mask = pd.Series(True, index=data.index)
    if start is not None:
        mask &= data["date"].ge(pd.Timestamp(start))
    if end is not None:
        mask &= data["date"].le(pd.Timestamp(end))
    if categories:
        mask &= data["category"].isin(categories)
    if media_types:
        mask &= data["media_type"].isin(media_types)
    return data.loc[mask].copy()


def kpi_series(data: pd.DataFrame, kpi: str) -> pd.Series:
    """Return the per-ad KPI values used for lift comparisons."""
    name = _normalize_kpi(kpi)
    if name == "ROAS":
        values = data["revenue"].div(data["spend"].replace(0, np.nan))
    elif name == "CTR":
        values = data["clicks"].div(data["impressions"].replace(0, np.nan))
    else:
        values = data["spend"].div(data["purchases"].replace(0, np.nan))
    return values.replace([np.inf, -np.inf], np.nan)


def aggregate_kpi(data: pd.DataFrame, kpi: str) -> float:
    """Compute a ratio-of-totals KPI for cards and time-series summaries."""
    name = _normalize_kpi(kpi)
    if data.empty:
        return np.nan
    if name == "ROAS":
        return _safe_ratio(data["revenue"].sum(), data["spend"].sum())
    if name == "CTR":
        return _safe_ratio(data["clicks"].sum(), data["impressions"].sum())
    return _safe_ratio(data["spend"].sum(), data["purchases"].sum())


def kpi_summary(data: pd.DataFrame) -> dict[str, float]:
    """Return the seven headline values shown in the dashboard."""
    return {
        "ads": len(data),
        "spend": data["spend"].sum(),
        "revenue": data["revenue"].sum(),
        "impressions": data["impressions"].sum(),
        "clicks": data["clicks"].sum(),
        "purchases": data["purchases"].sum(),
        "roas": aggregate_kpi(data, "ROAS"),
    }


def lift(data: pd.DataFrame, present: pd.Series, kpi: str) -> float:
    """Return percent lift for present versus absent ads."""
    name = _normalize_kpi(kpi)
    present = present.reindex(data.index, fill_value=False).astype(bool)
    values = kpi_series(data, name)
    present_value = values[present].mean()
    absent_value = values[~present].mean()
    if pd.isna(present_value) or pd.isna(absent_value) or absent_value == 0:
        return np.nan
    result = (present_value / absent_value - 1) * 100
    return -result if name == "CPP" else result


def monthly_performance(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate all calendar months, retaining months with no ads."""
    months = calendar_months(data)
    grouped = data.groupby("date").agg(
        ads=("ad_id", "size"),
        spend=("spend", "sum"),
        revenue=("revenue", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        purchases=("purchases", "sum"),
    )
    result = grouped.reindex(months, fill_value=0).rename_axis("date").reset_index()
    result["roas"] = _ratio_columns(result, "revenue", "spend")
    result["ctr"] = _ratio_columns(result, "clicks", "impressions")
    result["cpp"] = _ratio_columns(result, "spend", "purchases")
    return result


def label_table(
    data: pd.DataFrame,
    kpi: str,
    label_types: tuple[str, ...] = (),
    min_ads: int = 1,
) -> pd.DataFrame:
    """Return sample size and lift for each token/type label pair."""
    rows = []
    pairs = sorted(
        {
            pair
            for labels in data["label_pairs"]
            for pair in labels
            if not label_types or pair[1] in label_types
        }
    )
    for token, label_type in pairs:
        present = data["label_pairs"].map(
            lambda labels: (token, label_type) in labels
        )
        count = int(present.sum())
        if count >= min_ads and count < len(data):
            rows.append(
                {
                    "token": token,
                    "label_type": label_type,
                    "ads": count,
                    "lift": lift(data, present, kpi),
                }
            )
    return pd.DataFrame(rows, columns=["token", "label_type", "ads", "lift"])


def label_type_table(data: pd.DataFrame, kpi: str) -> pd.DataFrame:
    """Return sample size and lift for each label type."""
    rows = []
    for label_type in sorted(
        {label_type for labels in data["label_types"] for label_type in labels}
    ):
        present = data["label_types"].map(lambda labels: label_type in labels)
        rows.append(
            {
                "label_type": label_type,
                "ads": int(present.sum()),
                "lift": lift(data, present, kpi),
            }
        )
    return pd.DataFrame(rows)


def categorical_lift_table(
    data: pd.DataFrame,
    column: str,
    kpi: str,
    order: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Return sample size and lift for each value in a categorical column."""
    values = order or tuple(sorted(data[column].unique()))
    rows = []
    for value in values:
        present = data[column].eq(value)
        if present.any():
            rows.append(
                {
                    "value": value,
                    "ads": int(present.sum()),
                    "lift": lift(data, present, kpi),
                }
            )
    return pd.DataFrame(rows)


def binary_lift_table(
    data: pd.DataFrame,
    column: str,
    kpi: str,
) -> pd.DataFrame:
    """Return lift for the true and false groups of a Boolean feature."""
    present = data[column].astype(bool)
    return pd.DataFrame(
        [
            {
                "value": "True",
                "ads": int(present.sum()),
                "lift": lift(data, present, kpi),
            },
            {
                "value": "False",
                "ads": int((~present).sum()),
                "lift": lift(data, ~present, kpi),
            },
        ]
    )


def rolling_label_lift(
    data: pd.DataFrame,
    token: str,
    kpi: str,
    frequency: str = "quarter",
    window: int = 1,
    label_types: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Compute rolling lift for one label across months or quarters."""
    if frequency not in {"month", "quarter"}:
        raise ValueError("frequency must be 'month' or 'quarter'")
    if window < 1:
        raise ValueError("window must be at least 1")

    periods = (
        calendar_months(data).to_period("M" if frequency == "month" else "Q")
    )
    period_values = data["date"].dt.to_period(
        "M" if frequency == "month" else "Q"
    )
    results = []
    for period in periods.unique():
        group = data.loc[period_values.eq(period)]
        present = group["label_pairs"].map(
            lambda labels: any(
                label_token == token
                and (not label_types or label_type in label_types)
                for label_token, label_type in labels
            )
        )
        results.append(
            {
                "period": period,
                "ads": int(present.sum()),
                "lift": lift(group, present, kpi) if not group.empty else np.nan,
            }
        )
    result = pd.DataFrame(results)
    result["rolling_lift"] = result["lift"].rolling(window, min_periods=1).mean()
    return result


def label_performance_over_time(
    data: pd.DataFrame,
    tokens: tuple[str, ...],
    kpi: str,
    frequency: str = "quarter",
    label_types: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Return label volume and lift for every month or quarter."""
    if frequency not in {"month", "quarter"}:
        raise ValueError("frequency must be 'month' or 'quarter'")

    period_frequency = "M" if frequency == "month" else "Q"
    periods = calendar_months(data).to_period(period_frequency).unique()
    period_values = data["date"].dt.to_period(period_frequency)
    results = []
    for period in periods:
        group = data.loc[period_values.eq(period)]
        present = group["label_pairs"].map(
            lambda labels: any(
                token in tokens
                and (not label_types or label_type in label_types)
                for token, label_type in labels
            )
        )
        results.append(
            {
                "period": period,
                "ads": int(present.sum()),
                "lift": lift(group, present, kpi) if not group.empty else np.nan,
            }
        )
    return pd.DataFrame(results)


def rows_with_labels(
    data: pd.DataFrame,
    tokens: tuple[str, ...],
    label_types: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Return rows containing any selected token/type pair."""
    if not tokens:
        return data.copy()
    present = data["label_pairs"].map(
        lambda labels: any(
            token in tokens and (not label_types or label_type in label_types)
            for token, label_type in labels
        )
    )
    return data.loc[present].copy()


def _normalize_kpi(kpi: str) -> str:
    name = kpi.upper()
    if name not in KPI_NAMES:
        raise ValueError(f"Unsupported KPI '{kpi}'.")
    return name


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else np.nan


def _ratio_columns(
    data: pd.DataFrame, numerator: str, denominator: str
) -> pd.Series:
    return data[numerator].div(data[denominator].replace(0, np.nan))
