"""Lift engine — single source of truth for all lift computations.

Frozen contract: do not change LiftResult shape or compute_lift semantics
after validation. Phase 2 and Phase 3 build against this interface.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


KPI_NAMES = ("ROAS", "CTR", "CPP")

STRUCTURAL_FLAGS = (
    "headline_has_numbers",
    "body_has_numbers",
    "body_has_emoji",
    "body_over_50",
    "has_punctuation",
)

CATEGORICAL_COLUMNS = (
    "media_type",
    "aspect_ratio",
)

LABEL_TYPES = ("Image", "Video", "Noun", "Verb", "Phrase")


@dataclass(frozen=True)
class LiftResult:
    """lift is direction-normalized as a percentage: positive = better for all
    KPIs.  mean_present / mean_absent are raw (not direction-adjusted).
    direction documents which raw convention applies."""

    lift: float
    mean_present: float
    mean_absent: float
    n_present: int
    n_absent: int
    direction: str  # "higher_is_better" | "lower_is_better"


def kpi_series(data: pd.DataFrame, kpi: str) -> pd.Series:
    name = _normalize_kpi(kpi)
    if name == "ROAS":
        values = data["revenue"].div(data["spend"].replace(0, np.nan))
    elif name == "CTR":
        values = data["clicks"].div(data["impressions"].replace(0, np.nan))
    else:
        values = data["spend"].div(data["purchases"].replace(0, np.nan))
    return values.replace([np.inf, -np.inf], np.nan)


def compute_lift(
    data: pd.DataFrame,
    attribute_mask: pd.Series,
    kpi: str,
) -> LiftResult:
    name = _normalize_kpi(kpi)
    mask = attribute_mask.reindex(data.index, fill_value=False).astype(bool)
    values = kpi_series(data, name)

    mean_present = float(values[mask].mean())
    mean_absent = float(values[~mask].mean())
    n_present = int(mask.sum())
    n_absent = int((~mask).sum())
    direction = "lower_is_better" if name == "CPP" else "higher_is_better"

    if pd.isna(mean_present) or pd.isna(mean_absent) or mean_absent == 0:
        lift_value = np.nan
    else:
        raw = (mean_present / mean_absent - 1) * 100
        lift_value = -raw if name == "CPP" else raw

    return LiftResult(
        lift=lift_value,
        mean_present=mean_present,
        mean_absent=mean_absent,
        n_present=n_present,
        n_absent=n_absent,
        direction=direction,
    )


def lift_for_flag(
    data: pd.DataFrame, column: str, kpi: str,
) -> LiftResult:
    return compute_lift(data, data[column].astype(bool), kpi)


def lift_for_value(
    data: pd.DataFrame, column: str, value: str, kpi: str,
) -> LiftResult:
    return compute_lift(data, data[column].eq(value), kpi)


def lift_for_label(
    data: pd.DataFrame, token: str, label_type: str, kpi: str,
) -> LiftResult:
    mask = data["label_pairs"].map(lambda labels: (token, label_type) in labels)
    return compute_lift(data, mask, kpi)


def lift_for_label_type(
    data: pd.DataFrame, label_type: str, kpi: str,
) -> LiftResult:
    mask = data["label_types"].map(lambda types: label_type in types)
    return compute_lift(data, mask, kpi)


def scan_all(
    data: pd.DataFrame,
    kpi: str,
    top_n_labels: int = 30,
) -> dict[str, LiftResult]:
    """Batch entry point for Phase 2 / Phase 3."""
    results: dict[str, LiftResult] = {}

    for flag in STRUCTURAL_FLAGS:
        if flag in data.columns:
            results[flag] = lift_for_flag(data, flag, kpi)

    for column in CATEGORICAL_COLUMNS:
        if column in data.columns:
            for value in sorted(data[column].unique()):
                results[f"{column}={value}"] = lift_for_value(
                    data, column, value, kpi,
                )

    for lt in LABEL_TYPES:
        results[f"label_type={lt}"] = lift_for_label_type(data, lt, kpi)

    pair_counts: dict[tuple[str, str], int] = {}
    for labels in data["label_pairs"]:
        for token, lt in labels:
            pair_counts[(token, lt)] = pair_counts.get((token, lt), 0) + 1
    top_pairs = sorted(
        pair_counts.items(), key=lambda x: x[1], reverse=True,
    )[:top_n_labels]
    for (token, lt), _ in top_pairs:
        results[f"label={token}|{lt}"] = lift_for_label(
            data, token, lt, kpi,
        )

    return results


def _normalize_kpi(kpi: str) -> str:
    name = kpi.upper()
    if name not in KPI_NAMES:
        raise ValueError(f"Unsupported KPI '{kpi}'.")
    return name
