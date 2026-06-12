"""LLM grounding context for the Explain panel.

Assembles already-computed analytics outputs into a structured,
JSON-serializable context block with stable IDs and per-item evidence
metadata. Pure functions: no LLM calls, no number computation — every
figure here is read from the analytics layer's outputs.
"""

import hashlib
import json
import re

from dashboard.analytics.insights import Insight
from dashboard.analytics.recommend import PairRecommendation


# Plain-language definitions of every metric that appears in context
# items, so the model reads meanings instead of guessing them.
METRIC_DEFINITIONS = {
    "lift_pct": (
        "Percent difference in the KPI for ads with this attribute versus "
        "ads without it, in this dataset. Positive always means better — "
        "for CPP the sign is flipped so positive means cheaper."
    ),
    "combined_lift_pct": (
        "Percent difference in the KPI for ads running both attributes "
        "versus ads running neither."
    ),
    "individual_lift_pct": (
        "Each attribute's solo lift versus ads without that attribute."
    ),
    "synergy_pct": (
        "How much the pair's effect exceeds the sum of the two attributes' "
        "separate effects, as a percent of the neither-baseline. Positive "
        "means the pair outperforms its parts; near zero means roughly "
        "additive."
    ),
    "headroom_pct": (
        "For 'do_more' plays: the share of total ad spend NOT yet on this "
        "pairing — the budget room left to shift into it. For 'stop' "
        "plays: the share of spend currently on it. A share of spend, not "
        "a share of ads."
    ),
    "n": "Number of ads carrying the attribute.",
    "n_both": "Number of ads running both attributes of the pair.",
    "quadrant_lift_pct": (
        "KPI lift of each combination (both, A only, B only) versus the "
        "ads with neither attribute."
    ),
    "confidence": (
        "Sample-size tier only (high: n>=200, medium: n>=50, low: below) "
        "— not a statistical test."
    ),
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def insight_id(insight: Insight) -> str:
    return f"insight_{_slug(insight.key)}"


def pair_rec_id(rec: PairRecommendation) -> str:
    return f"rec_pair_{_slug(rec.attributes[0])}__{_slug(rec.attributes[1])}"


def insight_item(insight: Insight, category: str) -> dict:
    """One Insights-page bar as a context item.

    Only the Labels group is significance-gated before display
    (p<0.05, n>=150 in the app); other categories are directional
    associations ranked by lift and sample size.
    """
    tested = category == "Labels"
    return {
        "id": insight_id(insight),
        "kind": "insight",
        "category": category,
        "phrase": insight.phrase,
        "lift_pct": round(insight.lift, 1),
        "n": insight.n,
        "confidence": insight.confidence,
        "evidence": {
            "evidence_level": "tested" if tested else "directional",
            "statistically_tested": tested,
            "durability_tested": False,
        },
    }


def pair_rec_item(rec: PairRecommendation, rank: int) -> dict:
    """One Recommendations-page pair card as a context item.

    Pair recommendations carry minimum sample-size controls only — no
    significance test, no FDR correction, no durability gate.
    """
    both, a_only, b_only, neither = rec.cell_lifts
    return {
        "id": pair_rec_id(rec),
        "kind": "pair_recommendation",
        "rank": rank,
        "title": rec.title,
        "action": rec.action,
        "attribute_a": rec.phrases[0],
        "attribute_b": rec.phrases[1],
        "combined_lift_pct": round(rec.combined_lift, 1),
        "individual_lift_pct": [round(v, 1) for v in rec.individual_lifts],
        "synergy_pct": round(rec.synergy_score, 1),
        "headroom_pct": round(rec.headroom, 1),
        "n_both": rec.n_both,
        "quadrant_lift_pct": {
            "both": round(both, 1),
            "a_only": round(a_only, 1),
            "b_only": round(b_only, 1),
            "neither": round(neither, 1),
        },
        "evidence": {
            "evidence_level": "exploratory",
            "statistically_tested": False,
            "durability_tested": False,
            "note": (
                "Minimum sample-size controls only; no significance test, "
                "no FDR correction, no durability check."
            ),
        },
    }


def build_context(
    *,
    page: str,
    kpi: str,
    dataset_name: str,
    n_ads_in_view: int,
    n_ads_total: int,
    filters: dict,
    insight_groups: dict[str, list[Insight]] | None = None,
    pair_recs: list[PairRecommendation] | None = None,
    focus_id: str | None = None,
) -> dict:
    """Assemble the full grounding block for one Explain conversation.

    ``focus_id`` marks the component the user clicked Explain on; it is
    dropped if it doesn't match any assembled item.
    """
    items: list[dict] = []
    if insight_groups:
        for category, insights in insight_groups.items():
            items.extend(insight_item(ins, category) for ins in insights)
    if pair_recs:
        items.extend(
            pair_rec_item(rec, rank)
            for rank, rec in enumerate(pair_recs, 1)
        )

    known_ids = {item["id"] for item in items}
    if focus_id is not None and focus_id not in known_ids:
        focus_id = None

    return {
        "page": page,
        "kpi": kpi.upper(),
        "dataset": dataset_name,
        "ads_in_view": n_ads_in_view,
        "ads_total": n_ads_total,
        "filters": filters,
        "focus_id": focus_id,
        "metric_definitions": METRIC_DEFINITIONS,
        "items": items,
        "scope_note": (
            "All figures are historical associations from this dataset, "
            "not causal effects and not predictions."
        ),
    }


def context_fingerprint(context: dict) -> str:
    """Hash of the grounding data, ignoring which item is focused.

    A changed fingerprint means prior conversation turns reference
    numbers that no longer apply and must be cleared.
    """
    payload = {k: v for k, v in context.items() if k != "focus_id"}
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    )
    return digest.hexdigest()
