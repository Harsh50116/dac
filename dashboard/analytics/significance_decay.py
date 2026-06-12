"""Phase 3: statistical significance + quarterly durability tagging.

Consumes the frozen lift_engine contract. Each attribute can be evaluated
for (a) whether its lift is statistically distinguishable from zero via
Welch's two-sample t-test on per-ad KPI values, and (b) whether that lift
holds up across quarters or is decaying.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from dashboard.analytics.lift_engine import compute_lift, kpi_series


SIGNIFICANCE_P_THRESHOLD = 0.05
DECAY_THRESHOLD = 0.40
MIN_QUARTERS = 4
MIN_QUARTER_N = 10


@dataclass(frozen=True)
class SignificanceResult:
    t_statistic: float
    p_value: float
    significant: bool
    n_present: int
    n_absent: int


@dataclass(frozen=True)
class DurabilityResult:
    tag: str  # "durable" | "ephemeral" | "insufficient_data"
    quarters_observed: int
    peak_quarter: pd.Period | None
    peak_lift: float | None
    latest_quarter: pd.Period | None
    latest_lift: float | None
    decay_ratio: float | None


def significance_for_mask(
    data: pd.DataFrame,
    attribute_mask: pd.Series,
    kpi: str,
) -> SignificanceResult:
    """Welch's two-sample t-test on per-ad KPI values split by the mask."""
    mask = attribute_mask.reindex(data.index, fill_value=False).astype(bool)
    values = kpi_series(data, kpi)

    present = values[mask].replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    absent = values[~mask].replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    n_present = int(mask.sum())
    n_absent = int((~mask).sum())

    if len(present) < 2 or len(absent) < 2:
        return SignificanceResult(
            t_statistic=float("nan"),
            p_value=float("nan"),
            significant=False,
            n_present=n_present,
            n_absent=n_absent,
        )

    result = stats.ttest_ind(present, absent, equal_var=False, nan_policy="omit")
    t_stat = float(result.statistic)
    p_value = float(result.pvalue)
    significant = bool(np.isfinite(p_value) and p_value < SIGNIFICANCE_P_THRESHOLD)

    return SignificanceResult(
        t_statistic=t_stat,
        p_value=p_value,
        significant=significant,
        n_present=n_present,
        n_absent=n_absent,
    )


def quarterly_lifts(
    data: pd.DataFrame,
    attribute_mask: pd.Series,
    kpi: str,
) -> pd.DataFrame:
    """Return per-quarter lift and n_present for the given mask."""
    mask = attribute_mask.reindex(data.index, fill_value=False).astype(bool)
    periods = data["date"].dt.to_period("Q")
    rows = []
    for period in sorted(periods.unique()):
        slice_df = data.loc[periods.eq(period)]
        result = compute_lift(slice_df, mask, kpi)
        rows.append({
            "period": period,
            "lift": result.lift,
            "n_present": result.n_present,
        })
    return pd.DataFrame(rows, columns=["period", "lift", "n_present"])


def durability_for_mask(
    data: pd.DataFrame,
    attribute_mask: pd.Series,
    kpi: str,
    decay_threshold: float = DECAY_THRESHOLD,
    min_quarters: int = MIN_QUARTERS,
    min_n_per_quarter: int = MIN_QUARTER_N,
) -> DurabilityResult:
    """Tag attribute as durable / ephemeral / insufficient_data."""
    table = quarterly_lifts(data, attribute_mask, kpi)
    valid = table[
        table["n_present"].ge(min_n_per_quarter) & table["lift"].notna()
    ]
    quarters_observed = int(len(valid))

    insufficient = DurabilityResult(
        tag="insufficient_data",
        quarters_observed=quarters_observed,
        peak_quarter=None,
        peak_lift=None,
        latest_quarter=None,
        latest_lift=None,
        decay_ratio=None,
    )
    if quarters_observed < min_quarters:
        return insufficient

    valid = valid.sort_values("period").reset_index(drop=True)
    peak_row = valid.loc[valid["lift"].abs().idxmax()]
    latest_row = valid.iloc[-1]
    peak_lift = float(peak_row["lift"])
    latest_lift = float(latest_row["lift"])

    if peak_lift == 0:
        return insufficient

    has_positive = bool((valid["lift"] > 0).any())
    has_negative = bool((valid["lift"] < 0).any())
    if has_positive and has_negative:
        tag = "ephemeral"
        decay_ratio = 1.0
    else:
        decay_ratio = (abs(peak_lift) - abs(latest_lift)) / abs(peak_lift)
        tag = "ephemeral" if decay_ratio >= decay_threshold else "durable"

    return DurabilityResult(
        tag=tag,
        quarters_observed=quarters_observed,
        peak_quarter=peak_row["period"],
        peak_lift=peak_lift,
        latest_quarter=latest_row["period"],
        latest_lift=latest_lift,
        decay_ratio=float(decay_ratio),
    )
