"""Streamlit entry point: page config, navigation, and global filters."""

import pandas as pd
import streamlit as st

from dashboard.analytics.core import KPI_NAMES, filter_data
from dashboard.data import calendar_months
from dashboard.ui.pages.details import render_details
from dashboard.ui.pages.insights import render_insights
from dashboard.ui.pages.overview import render_overview
from dashboard.ui.pages.recommendations import render_recommendations
from dashboard.ui.state import reset_filters, unload_dataset
from dashboard.ui.styles import apply_styles
from dashboard.ui.upload import render_upload_state


def render_global_controls(data: pd.DataFrame) -> pd.DataFrame:
    """Render global controls and return the filtered dataset."""
    months = calendar_months(data)
    categories = sorted(data["category"].unique())
    media_types = sorted(data["media_type"].unique())

    with st.expander("Filters", expanded=False):
        control_columns = st.columns([1, 2.2, 2, 1.5, 1, 0.8])
        with control_columns[0]:
            kpi = st.radio(
                "KPI",
                KPI_NAMES,
                horizontal=True,
                key="filter_kpi",
            )
        with control_columns[1]:
            period = st.select_slider(
                "Period",
                options=list(months),
                value=(months[0], months[-1]),
                format_func=lambda value: value.strftime("%b %Y"),
                key="filter_period",
            )
        with control_columns[2]:
            selected_categories = st.multiselect(
                "Category",
                categories,
                placeholder="All categories",
                key="filter_categories",
            )
        with control_columns[3]:
            selected_media = st.multiselect(
                "Media",
                media_types,
                placeholder="All media",
                key="filter_media",
            )
        with control_columns[4]:
            top_n = st.number_input(
                "Top N",
                min_value=5,
                max_value=60,
                value=30,
                step=5,
                key="filter_top_n",
            )
        with control_columns[5]:
            st.write("")
            st.button(
                "Reset",
                on_click=reset_filters,
                args=(months,),
                width="stretch",
            )

    filtered = filter_data(
        data,
        start=period[0],
        end=period[1],
        categories=tuple(selected_categories),
        media_types=tuple(selected_media),
    )
    st.session_state["active_kpi"] = kpi
    st.session_state["active_top_n"] = int(top_n)
    return filtered


def render_loaded_state(data: pd.DataFrame) -> None:
    """Render the loaded-file header and global controls."""
    with st.sidebar:
        st.title("DAC")
        st.caption(f"{st.session_state['dataset_name']}")
        page = st.radio(
            "Navigation",
            ("Overview", "Details", "Insights", "Recommendations"),
            label_visibility="collapsed",
            key="sidebar_page",
        )
        st.divider()
        st.button(
            "Unload dataset",
            on_click=unload_dataset,
            width="stretch",
        )

    st.title(page)
    filtered = render_global_controls(data)
    st.caption(f"{len(filtered):,} of {len(data):,} ads in view")

    kpi = st.session_state["active_kpi"]
    top_n = st.session_state["active_top_n"]
    if page == "Overview":
        render_overview(filtered, kpi)
    elif page == "Details":
        render_details(filtered, kpi, top_n)
    elif page == "Insights":
        render_insights(filtered, kpi)
    else:
        render_recommendations(filtered, kpi)


def main() -> None:
    st.set_page_config(
        page_title="Ads Creative Component Performance",
        page_icon="📊",
        layout="wide",
    )
    apply_styles()

    data = st.session_state.get("dataset")
    if data is None:
        render_upload_state()
    else:
        render_loaded_state(data)


main()
