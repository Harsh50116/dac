"""Helpers used by more than one dashboard page."""

import pandas as pd
import streamlit as st

from dashboard.analytics.insights import generate_insights, group_by_category
from dashboard.analytics.interactions import attribute_mask
from dashboard.analytics.recommend import generate_pair_recommendations
from dashboard.analytics.significance_decay import significance_for_mask


LABEL_TYPES = ("Image", "Video", "Noun", "Verb", "Phrase")


def label_options(data: pd.DataFrame, label_types: list[str]) -> list[str]:
    """Return available tokens for selected label types."""
    return sorted(
        {
            token
            for labels in data["label_pairs"]
            for token, label_type in labels
            if not label_types or label_type in label_types
        }
    )


@st.cache_data(show_spinner="Analyzing insights…")
def analyze_insights(
    data: pd.DataFrame, kpi: str, top_n_labels: int,
) -> tuple[dict, float]:
    """Group insights by category; filter labels by significance + n >= 150 + top_n."""
    insights = generate_insights(data, kpi, top_n_labels=top_n_labels)
    if not insights:
        return {}, 0.0

    groups = group_by_category(insights)
    max_abs_lift = max(abs(i.lift) for i in insights)

    if "Labels" in groups:
        filtered = []
        for insight in groups["Labels"]:
            if insight.n < 150:
                continue
            mask = attribute_mask(data, insight.key)
            sig = significance_for_mask(data, mask, kpi)
            if sig.significant:
                filtered.append(insight)
        filtered.sort(key=lambda i: abs(i.lift), reverse=True)
        if filtered:
            groups["Labels"] = filtered[:top_n_labels]
        else:
            del groups["Labels"]

    return groups, max_abs_lift


@st.cache_data(show_spinner="Generating recommendations…")
def cached_pair_recommendations(
    data: pd.DataFrame, kpi: str, top_n: int,
) -> list:
    return generate_pair_recommendations(data, kpi, top_n=top_n)
