"""Surface-level insight extraction — Phase 2.

Ranks single-variable lift observations into plain-language statements.
No interactions, no temporal reasoning — that's Phase 3.
"""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from dashboard.analytics.interactions import attribute_mask
from dashboard.analytics.lift_engine import LiftResult, scan_all


JACCARD_DEDUP_THRESHOLD = 0.95
CONFIDENCE_THRESHOLDS = {"high": 200, "medium": 50}
CONFIDENCE_WEIGHTS = {"high": 1.0, "medium": 0.6, "low": 0.3}

PHRASE_LOOKUP = {
    "headline_has_numbers": "Headlines with numbers",
    "body_has_numbers": "Body copy with numbers",
    "body_has_emoji": "Emoji in body copy",
    "body_over_50": "Long body copy (>50 chars)",
    "has_punctuation": "Punctuation in headline/body",
}


@dataclass(frozen=True)
class Insight:
    key: str
    phrase: str
    lift: float
    n: int
    confidence: str
    score: float
    statement: str


def generate_insights(
    data: pd.DataFrame,
    kpi: str,
    top_n_labels: int = 30,
) -> list[Insight]:
    """Scan all attributes, rank by actionability, return plain-language insights."""
    results = scan_all(data, kpi, top_n_labels=top_n_labels)
    insights = []
    for key, result in results.items():
        if np.isnan(result.lift) or result.n_present == 0:
            continue
        confidence = _confidence(result.n_present)
        score = (
            abs(result.lift)
            * CONFIDENCE_WEIGHTS[confidence]
            * math.log1p(result.n_present)
        )
        phrase = _phrase_for_key(key)
        statement = _build_statement(phrase, result.lift, kpi, result.n_present, confidence)
        insights.append(Insight(
            key=key,
            phrase=phrase,
            lift=result.lift,
            n=result.n_present,
            confidence=confidence,
            score=score,
            statement=statement,
        ))
    insights.sort(key=lambda x: x.score, reverse=True)
    return _deduplicate_insights(data, insights)


def _confidence(n: int) -> str:
    if n >= CONFIDENCE_THRESHOLDS["high"]:
        return "high"
    if n >= CONFIDENCE_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def _phrase_for_key(key: str) -> str:
    if key in PHRASE_LOOKUP:
        return PHRASE_LOOKUP[key]
    if key.startswith("media_type="):
        value = key.split("=", 1)[1]
        return f"{value.capitalize()} creative"
    if key.startswith("aspect_ratio="):
        value = key.split("=", 1)[1]
        return f"{value} aspect ratio"
    if key.startswith("label_type="):
        value = key.split("=", 1)[1]
        return f"{value}-type labels"
    if key.startswith("label="):
        rest = key[len("label="):]
        token, lt = rest.rsplit("|", 1)
        if lt == "Phrase":
            return f"The phrase '{token}'"
        if lt in ("Image", "Video"):
            return f"Label '{token}'"
        return f"The word '{token}'"
    return key


def _deduplicate_insights(
    data: pd.DataFrame, insights: list[Insight],
) -> list[Insight]:
    """Drop later entries whose attribute mask is near-identical to an earlier one."""
    kept: list[tuple[Insight, pd.Series]] = []
    for insight in insights:
        mask = attribute_mask(data, insight.key)
        duplicate = False
        for _, prev_mask in kept:
            intersection = int((mask & prev_mask).sum())
            union = int((mask | prev_mask).sum())
            if union > 0 and intersection / union >= JACCARD_DEDUP_THRESHOLD:
                duplicate = True
                break
        if not duplicate:
            kept.append((insight, mask))
    return [ins for ins, _ in kept]


def group_by_category(insights: list[Insight]) -> dict[str, list[Insight]]:
    """Group insights into UI display categories."""
    groups: dict[str, list[Insight]] = {
        "Format": [],
        "Aspect Ratio": [],
        "Ad Copy": [],
        "Labels": [],
    }
    for insight in insights:
        key = insight.key
        if key.startswith("media_type="):
            groups["Format"].append(insight)
        elif key.startswith("aspect_ratio="):
            groups["Aspect Ratio"].append(insight)
        elif key.startswith("label="):
            groups["Labels"].append(insight)
        elif key.startswith("label_type="):
            continue
        else:
            groups["Ad Copy"].append(insight)
    return {k: v for k, v in groups.items() if v}


def _build_statement(
    phrase: str, lift: float, kpi: str, n: int, confidence: str,
) -> str:
    sign = "+" if lift > 0 else ""
    suffix = " — avoid" if lift < 0 else ""
    return (
        f"{phrase} → {sign}{lift:.0f}% {kpi.upper()}"
        f" (n={n:,}, {confidence} confidence){suffix}"
    )
