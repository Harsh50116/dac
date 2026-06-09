"""Phase 3 recommendation engine.

Assembles durable, statistically significant attribute insights into a
next-campaign recipe. All recommendations are testable hypotheses with
evidence, never guarantees.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from dashboard.insights import generate_insights
from dashboard.interactions import attribute_mask, find_interactions
from dashboard.significance_decay import (
    SIGNIFICANCE_P_THRESHOLD,
    durability_for_mask,
    significance_for_mask,
)


@dataclass(frozen=True)
class Recommendation:
    key: str
    phrase: str
    lift: float
    n: int
    p_value: float
    durability_tag: str
    action: str
    hypothesis: str
    evidence: str
    synergy_partner: str | None
    synergy_score: float | None


def _benjamini_hochberg(
    p_values: list[float],
    alpha: float = SIGNIFICANCE_P_THRESHOLD,
) -> list[bool]:
    """Return per-element mask of which p-values survive BH FDR correction."""
    m = len(p_values)
    if m == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * m
    for rank, (orig_idx, p) in enumerate(indexed, 1):
        adjusted[orig_idx] = min(p * m / rank, 1.0)
    sorted_indices = [idx for idx, _ in indexed]
    for i in range(m - 2, -1, -1):
        adjusted[sorted_indices[i]] = min(
            adjusted[sorted_indices[i]], adjusted[sorted_indices[i + 1]],
        )
    return [adj < alpha for adj in adjusted]


def generate_recommendations(
    data: pd.DataFrame,
    kpi: str,
    top_n_labels: int = 30,
) -> list[Recommendation]:
    """Filter to durable + significant (FDR-corrected) insights, enrich with synergy, rank."""
    insights = generate_insights(data, kpi, top_n_labels=top_n_labels)

    candidates: list[tuple] = []
    for insight in insights:
        if np.isnan(insight.lift):
            continue
        mask = attribute_mask(data, insight.key)
        if not mask.any():
            continue
        sig = significance_for_mask(data, mask, kpi)
        if np.isnan(sig.p_value):
            continue
        candidates.append((insight, mask, sig))

    p_values = [sig.p_value for _, _, sig in candidates]
    survives = _benjamini_hochberg(p_values)

    interactions = find_interactions(data, kpi, top_n_labels=top_n_labels)
    phrase_map = {i.key: i.phrase for i in insights}
    synergy_map: dict[str, tuple[str, float]] = {}
    for ix in interactions:
        for i, key in enumerate(ix.attributes):
            partner = ix.attributes[1 - i]
            if key not in synergy_map or abs(ix.synergy_score) > abs(synergy_map[key][1]):
                synergy_map[key] = (partner, ix.synergy_score)

    rec_masks: list[tuple[Recommendation, pd.Series]] = []
    for (insight, mask, sig), significant in zip(candidates, survives):
        if not significant:
            continue

        dur = durability_for_mask(data, mask, kpi)
        if dur.tag != "durable":
            continue

        action = "do_more" if insight.lift > 0 else "avoid"
        synergy_entry = synergy_map.get(insight.key)
        synergy_partner = None
        synergy_score = None
        if synergy_entry:
            synergy_partner = phrase_map.get(synergy_entry[0], synergy_entry[0])
            synergy_score = synergy_entry[1]

        hypothesis = _build_hypothesis(
            insight.phrase, insight.lift, kpi, dur.tag, sig.p_value, action,
        )
        evidence = _build_evidence(
            insight.lift, sig.p_value, dur.tag, insight.n,
            synergy_partner, synergy_score,
        )

        rec_masks.append((
            Recommendation(
                key=insight.key,
                phrase=insight.phrase,
                lift=insight.lift,
                n=insight.n,
                p_value=sig.p_value,
                durability_tag=dur.tag,
                action=action,
                hypothesis=hypothesis,
                evidence=evidence,
                synergy_partner=synergy_partner,
                synergy_score=synergy_score,
            ),
            mask,
        ))

    rec_masks.sort(key=lambda rm: abs(rm[0].lift), reverse=True)
    return _deduplicate(rec_masks)


def _build_hypothesis(
    phrase: str,
    lift: float,
    kpi: str,
    durability: str,
    p_value: float,
    action: str,
) -> str:
    sign = "+" if lift > 0 else ""
    kpi_upper = kpi.upper()
    if action == "do_more":
        return (
            f"Ads using {phrase.lower()} show {sign}{lift:.0f}% {kpi_upper} lift "
            f"(p={p_value:.3f}, {durability}). "
            f"Test increasing usage in your next campaign."
        )
    return (
        f"Ads with {phrase.lower()} show {lift:.0f}% {kpi_upper} drag "
        f"(p={p_value:.3f}, {durability}). "
        f"Test reducing usage in your next campaign."
    )


def _build_evidence(
    lift: float,
    p_value: float,
    durability: str,
    n: int,
    synergy_partner: str | None,
    synergy_score: float | None,
) -> str:
    sign = "+" if lift > 0 else ""
    parts = [
        f"Lift: {sign}{lift:.1f}%",
        f"p-value: {p_value:.4f}",
        f"Durability: {durability}",
        f"n={n:,}",
    ]
    if synergy_partner and synergy_score is not None:
        parts.append(f"Synergy with {synergy_partner}: {synergy_score:+.1f}%")
    return " | ".join(parts)


JACCARD_DEDUP_THRESHOLD = 0.95


def _deduplicate(
    rec_masks: list[tuple[Recommendation, pd.Series]],
) -> list[Recommendation]:
    """Drop later entries whose mask is near-identical to an earlier one."""
    kept: list[tuple[Recommendation, pd.Series]] = []
    for rec, mask in rec_masks:
        duplicate = False
        for _, prev_mask in kept:
            intersection = (mask & prev_mask).sum()
            union = (mask | prev_mask).sum()
            if union > 0 and intersection / union >= JACCARD_DEDUP_THRESHOLD:
                duplicate = True
                break
        if not duplicate:
            kept.append((rec, mask))
    return [rec for rec, _ in kept]
