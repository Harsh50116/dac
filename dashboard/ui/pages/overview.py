"""Overview page: KPI cards, volume, rolling lift, and label performance."""

import pandas as pd
import streamlit as st

from dashboard.analytics.core import (
    kpi_summary,
    label_performance_over_time,
    label_table,
    monthly_performance,
    rolling_label_lift,
    rows_with_labels,
)
from dashboard.ui.charts import (
    label_performance_chart,
    rolling_lift_chart,
    volume_performance_chart,
)
from dashboard.ui.pages.shared import LABEL_TYPES, label_options


def _compact_number(value: float, prefix: str = "") -> str:
    """Format large values as 526.4K / 2.1M so cards never truncate."""
    if abs(value) >= 1_000_000_000:
        return f"{prefix}{value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"{prefix}{value / 1_000_000:.1f}M"
    if abs(value) >= 100_000:
        return f"{prefix}{value / 1_000:.1f}K"
    return f"{prefix}{value:,.0f}"


def render_kpi_cards(data: pd.DataFrame) -> None:
    """Render the seven Overview headline values."""
    summary = kpi_summary(data)
    cards = (
        ("No. of Ads", f"{summary['ads']:,}"),
        ("Total Spend", _compact_number(summary["spend"], "$")),
        ("Total Revenue", _compact_number(summary["revenue"], "$")),
        ("Total Impressions", _compact_number(summary["impressions"])),
        ("Total Clicks", _compact_number(summary["clicks"])),
        ("Total Purchases", _compact_number(summary["purchases"])),
        ("Total ROAS", f"{summary['roas']:.2f}"),
    )
    columns = st.columns(7)
    for column, (label, value) in zip(columns, cards):
        with column:
            st.metric(label, value)


def render_volume_chart(data: pd.DataFrame) -> None:
    """Render monthly ad volume and ROAS with chart-specific controls."""
    st.subheader("Ads Volume & Performance over Time")
    st.caption("Monthly volume with aggregated ROAS")
    with st.expander("Controls", expanded=False):
        columns = st.columns(5)
        bar_metric = columns[0].selectbox(
            "Bar metric",
            ("Ads", "Spend", "Revenue"),
            key="volume_bar_metric",
        )
        rolling = columns[1].slider(
            "ROAS rolling (months)",
            1,
            6,
            1,
            key="volume_rolling",
        )
        min_ads = columns[2].slider(
            "Min ads / month",
            0,
            50,
            0,
            5,
            key="volume_min_ads",
        )
        selected_types = columns[3].multiselect(
            "Label type(s)",
            LABEL_TYPES,
            key="volume_label_types",
        )
        options = label_options(data, selected_types)
        selected_labels = columns[4].multiselect(
            "Labels",
            options,
            key="volume_labels",
        )

    chart_rows = rows_with_labels(
        data,
        tuple(selected_labels),
        tuple(selected_types),
    )
    monthly = monthly_performance(chart_rows)
    if min_ads:
        monthly.loc[monthly["ads"].lt(min_ads), "roas"] = pd.NA
    figure = volume_performance_chart(monthly, bar_metric, rolling)
    st.plotly_chart(figure, width="stretch")


def render_rolling_lift_chart(data: pd.DataFrame, kpi: str) -> None:
    """Render rolling lift for selected labels."""
    st.subheader("Rolling Lift (by Label)")
    st.caption(f"{kpi} lift versus ads without each label")
    with st.expander("Controls", expanded=False):
        columns = st.columns(4)
        selected_types = columns[0].multiselect(
            "Label type(s)",
            LABEL_TYPES,
            default=["Phrase"],
            key="rolling_label_types",
        )
        table = label_table(
            data,
            kpi,
            label_types=tuple(selected_types),
            min_ads=5,
        ).sort_values("ads", ascending=False)
        options = table["token"].tolist()
        defaults = options[: min(3, len(options))]
        selected_labels = columns[1].multiselect(
            "Labels",
            options,
            default=defaults,
            key="rolling_labels",
        )
        frequency = columns[2].radio(
            "Frequency",
            ("Quarter", "Month"),
            horizontal=True,
            key="rolling_frequency",
        )
        window = columns[3].slider(
            "Rolling window",
            1,
            6,
            3,
            key="rolling_window",
        )

    if not selected_labels:
        st.info("Select at least one label to display rolling lift.")
        return
    series = {
        token: rolling_label_lift(
            data,
            token,
            kpi,
            frequency=frequency.lower(),
            window=window,
            label_types=tuple(selected_types),
        )
        for token in selected_labels
    }
    st.plotly_chart(
        rolling_lift_chart(series),
        width="stretch",
    )


def render_label_performance_chart(data: pd.DataFrame, kpi: str) -> None:
    """Render label volume and lift over time."""
    st.subheader("Label Performance over Time")
    st.caption("Volume present versus lift")
    with st.expander("Controls", expanded=False):
        columns = st.columns(3)
        selected_types = columns[0].multiselect(
            "Label type(s)",
            LABEL_TYPES,
            default=["Phrase"],
            key="performance_label_types",
        )
        options = label_options(data, selected_types)
        selected_labels = columns[1].multiselect(
            "Labels",
            options,
            default=options[:1],
            key="performance_labels",
        )
        frequency = columns[2].radio(
            "Frequency",
            ("Quarter", "Month"),
            horizontal=True,
            key="performance_frequency",
        )

    if not selected_labels:
        st.info("Select at least one label to display performance.")
        return
    performance = label_performance_over_time(
        data,
        tuple(selected_labels),
        kpi,
        frequency=frequency.lower(),
        label_types=tuple(selected_types),
    )
    st.plotly_chart(
        label_performance_chart(performance),
        width="stretch",
    )


def render_overview(data: pd.DataFrame, kpi: str) -> None:
    """Render the complete Overview tab."""
    if data.empty:
        st.warning("No ads match the selected global filters.")
        return
    render_kpi_cards(data)
    st.divider()
    render_volume_chart(data)
    render_rolling_lift_chart(data, kpi)
    render_label_performance_chart(data, kpi)
