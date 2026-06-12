"""Dataset loading and normalization for the Phase 1 dashboard."""

from pathlib import Path
from typing import BinaryIO

import pandas as pd


REQUIRED_COLUMNS = (
    "ad_id",
    "date",
    "spend",
    "revenue",
    "impressions",
    "clicks",
    "purchases",
    "headline",
    "body",
    "media_type",
    "aspect_ratio",
    "category",
    "labels",
)
NUMERIC_COLUMNS = (
    "spend",
    "revenue",
    "impressions",
    "clicks",
    "purchases",
)
EXPECTED_MEDIA_TYPES = {"image", "video"}
EXPECTED_ASPECT_RATIOS = {"1:1", "4:5", "9:16"}
MIN_ROW_COUNT = 100


class DataValidationError(ValueError):
    """Raised when an uploaded dataset does not match the required contract."""


def load_dataset(source: str | Path | BinaryIO) -> pd.DataFrame:
    """Read and normalize a supported ad-performance dataset."""
    name = Path(source).name if isinstance(source, (str, Path)) else source.name
    suffix = Path(name).suffix.lower()

    if suffix == ".csv":
        frame = pd.read_csv(source)
    elif suffix == ".parquet":
        frame = pd.read_parquet(source)
    elif suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(source)
    else:
        raise DataValidationError(
            f"Unsupported file type '{suffix or 'unknown'}'. "
            "Use CSV, Parquet, or Excel."
        )

    return normalize_dataset(frame)


def normalize_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the dataset contract and add fields used by the dashboard."""
    data = frame.copy()
    data.columns = [str(column).strip().lower() for column in data.columns]

    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise DataValidationError(
            "Missing required columns: " + ", ".join(missing)
        )

    data = data.loc[:, REQUIRED_COLUMNS].copy()
    if data.isna().any().any():
        null_columns = data.columns[data.isna().any()].tolist()
        raise DataValidationError(
            "Null values are not allowed in: " + ", ".join(null_columns)
        )

    for column in NUMERIC_COLUMNS:
        try:
            data[column] = pd.to_numeric(data[column], errors="raise")
        except (TypeError, ValueError) as error:
            raise DataValidationError(
                f"Column '{column}' must contain numeric values."
            ) from error
        if (data[column] < 0).any():
            raise DataValidationError(
                f"Column '{column}' cannot contain negative values."
            )

    parsed_dates = pd.to_datetime(data["date"], errors="coerce")
    if parsed_dates.isna().any():
        raise DataValidationError("Column 'date' must contain valid dates.")
    data["date"] = parsed_dates.dt.to_period("M").dt.to_timestamp()

    text_columns = (
        "ad_id",
        "headline",
        "body",
        "media_type",
        "aspect_ratio",
        "category",
        "labels",
    )
    for column in text_columns:
        data[column] = data[column].astype(str).str.strip()
        if data[column].eq("").any():
            raise DataValidationError(f"Column '{column}' cannot be empty.")

    if data["ad_id"].duplicated().any():
        raise DataValidationError("Column 'ad_id' must contain unique values.")

    unexpected_media = set(data["media_type"].unique()) - EXPECTED_MEDIA_TYPES
    if unexpected_media:
        raise DataValidationError(
            f"Unexpected media_type values: {', '.join(sorted(unexpected_media))}. "
            f"Expected: {', '.join(sorted(EXPECTED_MEDIA_TYPES))}."
        )
    unexpected_aspect = set(data["aspect_ratio"].unique()) - EXPECTED_ASPECT_RATIOS
    if unexpected_aspect:
        raise DataValidationError(
            f"Unexpected aspect_ratio values: {', '.join(sorted(unexpected_aspect))}. "
            f"Expected: {', '.join(sorted(EXPECTED_ASPECT_RATIOS))}."
        )
    if len(data) < MIN_ROW_COUNT:
        raise DataValidationError(
            f"Dataset has only {len(data):,} rows. "
            f"At least {MIN_ROW_COUNT:,} rows are needed for meaningful analysis."
        )

    parsed_labels = data["labels"].map(parse_labels)
    data["label_pairs"] = parsed_labels
    data["label_tokens"] = parsed_labels.map(
        lambda labels: tuple(token for token, _ in labels)
    )
    data["label_types"] = parsed_labels.map(
        lambda labels: tuple(label_type for _, label_type in labels)
    )

    data["headline_has_numbers"] = data["headline"].str.contains(r"\d")
    data["body_has_numbers"] = data["body"].str.contains(r"\d")
    data["body_has_emoji"] = data["body"].str.contains(
        r"[\U0001F300-\U0001FAFF\u2600-\u27BF]",
        regex=True,
    )
    data["body_over_50"] = data["body"].str.len().gt(50)
    data["has_punctuation"] = (
        data["headline"].str.contains(r"[!?]")
        | data["body"].str.contains(r"[!?]")
    )

    return data.sort_values(["date", "ad_id"]).reset_index(drop=True)


def parse_labels(value: str) -> tuple[tuple[str, str], ...]:
    """Parse a pipe-delimited token:type label string."""
    labels = []
    for part in value.split("|"):
        if ":" not in part:
            raise DataValidationError(f"Malformed label '{part}'.")
        token, label_type = (item.strip() for item in part.rsplit(":", 1))
        if not token or not label_type:
            raise DataValidationError(f"Malformed label '{part}'.")
        labels.append((token, label_type))
    return tuple(labels)


def calendar_months(data: pd.DataFrame) -> pd.DatetimeIndex:
    """Return every calendar month between the dataset bounds, inclusive."""
    if data.empty:
        return pd.DatetimeIndex([])
    return pd.date_range(data["date"].min(), data["date"].max(), freq="MS")
