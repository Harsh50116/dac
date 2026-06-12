"""Details page: label-type lift, circular chart, word cloud, copy charts."""

import pandas as pd
import streamlit as st

from dashboard.analytics.core import (
    binary_lift_table,
    categorical_lift_table,
    label_table,
    label_type_table,
)
from dashboard.ui.charts import (
    circular_lift_chart,
    lift_bar_chart,
    word_cloud_chart,
)
from dashboard.ui.pages.shared import LABEL_TYPES


def render_label_details(data: pd.DataFrame, kpi: str, top_n: int) -> None:
    """Render label-type, circular-lift, and word-cloud charts."""
    st.subheader("Lift by Label Type")
    st.caption(f"{kpi} lift versus ads without each label type")
    st.plotly_chart(
        lift_bar_chart(label_type_table(data, kpi), "label_type"),
        width="stretch",
    )

    circular, cloud = st.columns(2)
    with circular:
        st.subheader("Circular Lift by Label")
        st.caption(f"Strongest {top_n} token lifts")
        with st.expander("Controls", expanded=False):
            circular_types = st.multiselect(
                "Label type(s)",
                LABEL_TYPES,
                default=["Noun", "Verb"],
                key="circular_label_types",
            )
        circular_data = label_table(
            data,
            kpi,
            label_types=tuple(circular_types),
            min_ads=8,
        )
        circular_data = (
            circular_data.assign(strength=circular_data["lift"].abs())
            .sort_values("strength", ascending=False)
            .head(top_n)
        )
        st.plotly_chart(
            circular_lift_chart(circular_data),
            width="stretch",
        )

    with cloud:
        st.subheader("Word Cloud")
        st.caption("Size = frequency · color = lift")
        with st.expander("Controls", expanded=False):
            cloud_types = st.multiselect(
                "Label type(s)",
                LABEL_TYPES,
                default=["Noun", "Verb", "Phrase"],
                key="cloud_label_types",
            )
        cloud_data = (
            label_table(
                data,
                kpi,
                label_types=tuple(cloud_types),
                min_ads=1,
            )
            .sort_values("ads", ascending=False)
            .head(44)
        )
        st.plotly_chart(word_cloud_chart(cloud_data), width="stretch")


def render_copy_details(data: pd.DataFrame, kpi: str) -> None:
    """Render visual-format and structural-copy comparisons."""
    st.subheader("Ad Copy / Headline Charts")
    first, second = st.columns(2)
    with first:
        st.markdown("#### Visual Asset Aspect Ratio Performance")
        aspect = categorical_lift_table(
            data,
            "aspect_ratio",
            kpi,
            order=("1:1", "4:5", "9:16"),
        )
        st.plotly_chart(lift_bar_chart(aspect, "value"), width="stretch")
    with second:
        st.markdown("#### Body Text Over 50?")
        st.plotly_chart(
            lift_bar_chart(
                binary_lift_table(data, "body_over_50", kpi),
                "value",
            ),
            width="stretch",
        )

    comparisons = (
        ("Body Has Emojis?", "body_has_emoji"),
        ("Headline Has Numbers?", "headline_has_numbers"),
        ("Body Has Numbers?", "body_has_numbers"),
    )
    for index in range(0, len(comparisons), 2):
        columns = st.columns(2)
        for column, (title, feature) in zip(
            columns,
            comparisons[index : index + 2],
        ):
            with column:
                st.markdown(f"#### {title}")
                st.plotly_chart(
                    lift_bar_chart(
                        binary_lift_table(data, feature, kpi),
                        "value",
                        height=290,
                    ),
                    width="stretch",
                )


def render_details(data: pd.DataFrame, kpi: str, top_n: int) -> None:
    """Render the complete Details tab."""
    if data.empty:
        st.warning("No ads match the selected global filters.")
        return
    render_label_details(data, kpi, top_n)
    st.divider()
    render_copy_details(data, kpi)
