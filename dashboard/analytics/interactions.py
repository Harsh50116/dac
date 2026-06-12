"""Pairwise attribute interaction lift — Phase 3.

Builds on the frozen lift_engine to find attribute pairs whose joint presence
beats (or under-performs) the additive expectation of each attribute alone.
"""

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd

from dashboard.analytics.lift_engine import compute_lift, kpi_series, scan_all


DEFAULT_MIN_N = 50


@dataclass(frozen=True)
class Interaction:
    attributes: tuple[str, str]
    combined_lift: float
    individual_lifts: tuple[float, float]
    n_both: int
    synergy_score: float


def attribute_mask(data: pd.DataFrame, key: str) -> pd.Series:
    """Build the boolean mask described by a scan_all-style key.

    Returns an all-False series when the underlying column is absent so callers
    can iterate keys without guarding for missing features.
    """
    if "=" not in key:
        if key not in data.columns:
            return pd.Series(False, index=data.index)
        return data[key].astype(bool)

    prefix, value = key.split("=", 1)
    if prefix == "label_type":
        return data["label_types"].map(lambda types: value in types).astype(bool)
    if prefix == "label":
        token, label_type = value.rsplit("|", 1)
        return data["label_pairs"].map(
            lambda pairs: (token, label_type) in pairs,
        ).astype(bool)
    if prefix not in data.columns:
        return pd.Series(False, index=data.index)
    return data[prefix].eq(value)


def find_interactions(
    data: pd.DataFrame,
    kpi: str,
    min_n: int = DEFAULT_MIN_N,
    top_n_labels: int = 30,
) -> list[Interaction]:
    """Compute pairwise attribute interaction lifts using a four-cell model.

    All four cells (A&B, A&~B, ~A&B, ~A&~B) must have at least min_n
    observations. Synergy is the interaction term as a percentage of
    the baseline (~A&~B) mean.
    """
    solo = scan_all(data, kpi, top_n_labels=top_n_labels)
    masks: dict[str, pd.Series] = {}
    for key in solo:
        mask = attribute_mask(data, key)
        if mask.any() and not mask.all():
            masks[key] = mask

    values = kpi_series(data, kpi)
    is_cpp = kpi.upper() == "CPP"

    interactions: list[Interaction] = []
    for key_a, key_b in combinations(sorted(masks), 2):
        mask_a = masks[key_a]
        mask_b = masks[key_b]
        mask_ab = mask_a & mask_b
        n_both = int(mask_ab.sum())
        if n_both < min_n:
            continue

        mask_a_notb = mask_a & ~mask_b
        mask_nota_b = ~mask_a & mask_b
        mask_neither = ~mask_a & ~mask_b
        if (
            int(mask_a_notb.sum()) < min_n
            or int(mask_nota_b.sum()) < min_n
            or int(mask_neither.sum()) < min_n
        ):
            continue

        m_ab = float(values[mask_ab].mean())
        m_a_notb = float(values[mask_a_notb].mean())
        m_nota_b = float(values[mask_nota_b].mean())
        m_neither = float(values[mask_neither].mean())

        if any(np.isnan(v) for v in (m_ab, m_a_notb, m_nota_b, m_neither)):
            continue
        if m_neither == 0:
            continue

        combined_raw = (m_ab / m_neither - 1) * 100
        combined_lift = -combined_raw if is_cpp else combined_raw

        interaction_term = m_ab - m_a_notb - m_nota_b + m_neither
        synergy_raw = interaction_term / m_neither * 100
        synergy = -synergy_raw if is_cpp else synergy_raw

        lift_a = solo[key_a].lift
        lift_b = solo[key_b].lift
        if np.isnan(lift_a) or np.isnan(lift_b):
            continue

        interactions.append(Interaction(
            attributes=(key_a, key_b),
            combined_lift=combined_lift,
            individual_lifts=(lift_a, lift_b),
            n_both=n_both,
            synergy_score=synergy,
        ))

    interactions.sort(key=lambda i: abs(i.synergy_score), reverse=True)
    return interactions
