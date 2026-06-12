"""Phase 3 recommendation engine.

Assembles durable, statistically significant attribute insights into a
next-campaign recipe. All recommendations are testable hypotheses with
evidence, never guarantees.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from dashboard.analytics.insights import _phrase_for_key, generate_insights
from dashboard.analytics.interactions import attribute_mask, find_interactions
from dashboard.analytics.lift_engine import kpi_series, scan_all
from dashboard.analytics.significance_decay import (
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


@dataclass(frozen=True)
class PairRecommendation:
    attributes: tuple[str, str]
    phrases: tuple[str, str]
    action: str
    combined_lift: float
    individual_lifts: tuple[float, float]
    synergy_score: float
    n_both: int
    cell_lifts: tuple[float, float, float, float]
    headroom: float
    title: str
    description: str


def generate_pair_recommendations(
    data: pd.DataFrame,
    kpi: str,
    top_n: int = 3,
    top_n_labels: int = 30,
) -> list[PairRecommendation]:
    """Build pair-based recommendations from attribute interactions."""
    interactions = find_interactions(data, kpi, top_n_labels=top_n_labels)
    if not interactions:
        return []

    phrase_map = {key: _phrase_for_key(key) for key in scan_all(data, kpi, top_n_labels=top_n_labels)}

    values = kpi_series(data, kpi)
    is_cpp = kpi.upper() == "CPP"
    total_spend = float(data["spend"].sum())

    ranked: list[tuple[PairRecommendation, pd.Series]] = []
    for ix in interactions:
        key_a, key_b = ix.attributes
        mask_a = attribute_mask(data, key_a)
        mask_b = attribute_mask(data, key_b)
        mask_ab = mask_a & mask_b
        mask_a_notb = mask_a & ~mask_b
        mask_nota_b = ~mask_a & mask_b
        mask_neither = ~mask_a & ~mask_b

        m_ab = float(values[mask_ab].mean())
        m_a_notb = float(values[mask_a_notb].mean())
        m_nota_b = float(values[mask_nota_b].mean())
        m_neither = float(values[mask_neither].mean())
        if m_neither == 0:
            continue

        ab_raw = (m_ab / m_neither - 1) * 100
        a_raw = (m_a_notb / m_neither - 1) * 100
        b_raw = (m_nota_b / m_neither - 1) * 100
        if is_cpp:
            cell_lifts = (-ab_raw, -a_raw, -b_raw, 0.0)
        else:
            cell_lifts = (ab_raw, a_raw, b_raw, 0.0)

        combo_spend = float(data.loc[mask_ab, "spend"].sum())
        if ix.combined_lift > 0:
            headroom = (1 - combo_spend / total_spend) * 100 if total_spend else 0.0
        else:
            headroom = (combo_spend / total_spend) * 100 if total_spend else 0.0

        action = "do_more" if ix.combined_lift > 0 else "stop"
        phrase_a = phrase_map.get(key_a, key_a)
        phrase_b = phrase_map.get(key_b, key_b)

        title = _build_pair_title(phrase_a, phrase_b, action)
        description = _build_pair_description(
            phrase_a, phrase_b, ix.combined_lift,
            ix.synergy_score, headroom, kpi, action,
        )

        ranked.append((
            PairRecommendation(
                attributes=(key_a, key_b),
                phrases=(phrase_a, phrase_b),
                action=action,
                combined_lift=ix.combined_lift,
                individual_lifts=ix.individual_lifts,
                synergy_score=ix.synergy_score,
                n_both=ix.n_both,
                cell_lifts=cell_lifts,
                headroom=headroom,
                title=title,
                description=description,
            ),
            mask_ab,
        ))

    ranked.sort(key=lambda r: abs(r[0].combined_lift), reverse=True)
    return _deduplicate_pairs(ranked, top_n)


def _deduplicate_pairs(
    ranked: list[tuple[PairRecommendation, pd.Series]],
    top_n: int,
) -> list[PairRecommendation]:
    """Keep top_n pairs that don't share individual levers or overlap excessively."""
    kept: list[tuple[PairRecommendation, pd.Series]] = []
    used_levers: set[str] = set()
    for rec, mask in ranked:
        if rec.attributes[0] in used_levers or rec.attributes[1] in used_levers:
            continue
        duplicate = False
        for _, prev_mask in kept:
            intersection = int((mask & prev_mask).sum())
            union = int((mask | prev_mask).sum())
            if union > 0 and intersection / union >= JACCARD_DEDUP_THRESHOLD:
                duplicate = True
                break
        if not duplicate:
            kept.append((rec, mask))
            used_levers.update(rec.attributes)
        if len(kept) >= top_n:
            break
    return [r for r, _ in kept]


def _build_pair_title(phrase_a: str, phrase_b: str, action: str) -> str:
    a = phrase_a.lower()
    b = phrase_b.lower()
    if action == "do_more":
        return f"Pair {a} with {b}"
    return f"Avoid combining {a} with {b}"


def _build_pair_description(
    phrase_a: str,
    phrase_b: str,
    combined_lift: float,
    synergy: float,
    headroom: float,
    kpi: str,
    action: str,
) -> str:
    kpi_upper = kpi.upper()
    a = phrase_a.lower()
    b = phrase_b.lower()
    if action == "do_more":
        return (
            f"Historically, ads using {a} and {b} together showed "
            f"{combined_lift:+.0f}% {kpi_upper} vs baseline — {synergy:+.1f}% beyond what "
            f"either delivered alone. {headroom:.0f}% of spend hasn't tried "
            f"this combination yet. Test this pairing in your next campaign."
        )
    return (
        f"Historically, combining {a} with {b} dragged {kpi_upper} by "
        f"{combined_lift:.0f}% vs baseline. {headroom:.0f}% of current spend "
        f"uses this combination. Test reducing this pairing."
    )
