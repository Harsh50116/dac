"""Dataset and filter session-state helpers shared across pages."""

import pandas as pd
import streamlit as st


FILTER_KEYS = (
    "filter_kpi",
    "filter_period",
    "filter_categories",
    "filter_media",
    "filter_top_n",
)


def set_dataset(data: pd.DataFrame, name: str) -> None:
    """Store a normalized dataset and clear filters from any previous file."""
    st.session_state["dataset"] = data
    st.session_state["dataset_name"] = name
    for key in FILTER_KEYS:
        st.session_state.pop(key, None)


def unload_dataset() -> None:
    """Return the application to its initial upload state."""
    st.session_state.pop("dataset", None)
    st.session_state.pop("dataset_name", None)
    for key in FILTER_KEYS:
        st.session_state.pop(key, None)


def reset_filters(months: pd.DatetimeIndex) -> None:
    """Restore all global controls to their dataset-wide defaults."""
    st.session_state["filter_kpi"] = "ROAS"
    st.session_state["filter_period"] = (months[0], months[-1])
    st.session_state["filter_categories"] = []
    st.session_state["filter_media"] = []
    st.session_state["filter_top_n"] = 30


def active_filter_summary() -> dict:
    """Current global filters as a JSON-friendly dict for LLM grounding."""
    period = st.session_state.get("filter_period")
    return {
        "period": (
            [ts.strftime("%Y-%m") for ts in period] if period else "all"
        ),
        "categories": list(st.session_state.get("filter_categories") or []) or "all",
        "media_types": list(st.session_state.get("filter_media") or []) or "all",
    }
