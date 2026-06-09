"""Streamlit entry point for the Phase 1 dashboard."""

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard.analytics import (
    KPI_NAMES,
    binary_lift_table,
    categorical_lift_table,
    filter_data,
    kpi_summary,
    label_performance_over_time,
    label_table,
    label_type_table,
    monthly_performance,
    rolling_label_lift,
    rows_with_labels,
)
from dashboard.charts import (
    circular_lift_chart,
    label_performance_chart,
    lift_bar_chart,
    lift_color,
    rolling_lift_chart,
    sparkline_svg,
    volume_performance_chart,
    word_cloud_chart,
)
from dashboard.insights import generate_insights, group_by_category
from dashboard.recommend import generate_recommendations
from dashboard.data import DataValidationError, calendar_months, load_dataset
from dashboard.styles import apply_styles


SAMPLE_DATA = (
    Path(__file__).parent
    / "data"
    / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"
)
FILTER_KEYS = (
    "filter_kpi",
    "filter_period",
    "filter_categories",
    "filter_media",
    "filter_top_n",
)
LABEL_TYPES = ("Image", "Video", "Noun", "Verb", "Phrase")


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


def load_sample() -> None:
    """Load the bundled Phase 1 dataset."""
    set_dataset(load_dataset(SAMPLE_DATA), SAMPLE_DATA.name)


def reset_filters(months: pd.DatetimeIndex) -> None:
    """Restore all global controls to their dataset-wide defaults."""
    st.session_state["filter_kpi"] = "ROAS"
    st.session_state["filter_period"] = (months[0], months[-1])
    st.session_state["filter_categories"] = []
    st.session_state["filter_media"] = []
    st.session_state["filter_top_n"] = 30


def render_upload_state() -> None:
    """Render the initial upload and sample-data actions."""
    st.title("Ads Creative Component Performance")
    st.caption(
        "Upload ad-level performance data to explore creative-component lift."
    )

    uploaded = st.file_uploader(
        "Upload dataset",
        type=["csv", "parquet", "xlsx", "xls"],
        help="CSV, Parquet, or Excel. Maximum upload size: 200 MB.",
    )
    st.caption(
        "Required columns: ad_id, date, spend, revenue, impressions, clicks, "
        "purchases, headline, body, media_type, aspect_ratio, category, labels"
    )

    if uploaded is not None:
        try:
            set_dataset(load_dataset(uploaded), uploaded.name)
        except DataValidationError as error:
            st.error(str(error))
        else:
            st.rerun()

    st.button(
        "Load sample creative dataset",
        type="primary",
        on_click=load_sample,
    )


def render_global_controls(data: pd.DataFrame) -> pd.DataFrame:
    """Render global controls and return the filtered dataset."""
    months = calendar_months(data)
    categories = sorted(data["category"].unique())
    media_types = sorted(data["media_type"].unique())

    with st.container(border=True):
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


def render_kpi_cards(data: pd.DataFrame) -> None:
    """Render the seven Overview headline values with sparklines."""
    summary = kpi_summary(data)
    monthly = monthly_performance(data)
    cards = (
        ("No. of Ads", f"{summary['ads']:,}", monthly["ads"]),
        ("Total Amount Spent", f"${summary['spend']:,.0f}", monthly["spend"]),
        ("Total Revenue", f"${summary['revenue']:,.0f}", monthly["revenue"]),
        ("Total Impressions", f"{summary['impressions']:,.0f}", monthly["impressions"]),
        ("Total Clicks", f"{summary['clicks']:,.0f}", monthly["clicks"]),
        ("Total Purchases", f"{summary['purchases']:,.0f}", monthly["purchases"]),
        ("Total ROAS", f"{summary['roas']:.2f}", monthly["roas"]),
    )
    columns = st.columns(7)
    for i, (column, (label, value, series)) in enumerate(zip(columns, cards)):
        spark_values = series.tolist()
        with column:
            st.metric(label, value)
            st.markdown(
                f'<div class="sparkline-wrap">'
                f"{sparkline_svg(spark_values, '#888', idx=i)}</div>",
                unsafe_allow_html=True,
            )


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


def render_volume_chart(data: pd.DataFrame) -> None:
    """Render monthly ad volume and ROAS with chart-specific controls."""
    st.subheader("Ads Volume & Performance over Time")
    st.caption("Monthly volume with aggregated ROAS")
    with st.expander("Controls", expanded=True):
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
    with st.expander("Controls", expanded=True):
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
    with st.expander("Controls", expanded=True):
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
    """Render the complete Phase 1 Overview tab."""
    if data.empty:
        st.warning("No ads match the selected global filters.")
        return
    render_kpi_cards(data)
    st.divider()
    first, second = st.columns(2)
    with first:
        render_volume_chart(data)
    with second:
        render_rolling_lift_chart(data, kpi)
    render_label_performance_chart(data, kpi)


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
        with st.expander("Controls", expanded=True):
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
        with st.expander("Controls", expanded=True):
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
        st.markdown("#### Punctuation Performance")
        if data["has_punctuation"].nunique() < 2:
            st.info(
                "Unavailable: the current dataset has no ads containing "
                "headline or body punctuation (! or ?)."
            )
        else:
            punctuation = binary_lift_table(data, "has_punctuation", kpi)
            st.plotly_chart(
                lift_bar_chart(punctuation, "value"),
                width="stretch",
            )

    comparisons = (
        ("Body Text Over 50?", "body_over_50"),
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


def _insight_bar_html(
    insight, max_abs_lift: float, kpi_upper: str,
) -> str:
    """Render one horizontal bar row matching the mockup layout."""
    phrase = escape(insight.phrase)
    color = lift_color(insight.lift)
    sign = "+" if insight.lift > 0 else ""
    thin = '<span class="insight-thin">thin</span>' if insight.n < 200 else ""

    pct = abs(insight.lift) / max_abs_lift * 45 if max_abs_lift else 0
    if insight.lift >= 0:
        bar_style = f"left:50%;width:{pct:.1f}%;background:{color};"
    else:
        bar_style = f"right:50%;width:{pct:.1f}%;background:{color};"

    return (
        f'<div class="insight-bar-row">'
        f'<span class="insight-bar-label">{phrase}{thin}</span>'
        f'<div class="insight-bar-track">'
        f'<div class="insight-bar-fill" style="{bar_style}"></div>'
        f"</div>"
        f'<span class="insight-bar-stats" style="color:{color}">'
        f"{sign}{insight.lift:.0f}%"
        f'<span class="insight-bar-n">n={insight.n:,}</span>'
        f"</span>"
        f"</div>"
    )


def render_insights(data: pd.DataFrame, kpi: str) -> None:
    """Render the Insights tab with grouped horizontal bars by category."""
    if data.empty:
        st.warning("No ads match the selected global filters.")
        return
    insights = generate_insights(data, kpi)
    if not insights:
        st.info("Not enough data to generate insights.")
        return

    kpi_upper = kpi.upper()
    groups = group_by_category(insights)
    max_abs_lift = max(abs(i.lift) for i in insights)

    st.subheader(f"What moves {kpi_upper}")
    st.caption(
        f"Every creative lever ranked by its effect on {kpi_upper} versus "
        f"the account baseline. Bars read left (drains) to right (drivers); "
        f"width is magnitude."
    )
    st.markdown(
        f'<div class="insight-legend">'
        f'<span class="insight-legend-dot" style="background:#e5533f;"></span>'
        f"Drains {kpi_upper}"
        f"&nbsp;&nbsp;← 0% →&nbsp;&nbsp;"
        f'<span class="insight-legend-dot" style="background:#34c77b;"></span>'
        f"Lifts {kpi_upper}"
        f"</div>",
        unsafe_allow_html=True,
    )

    for category in ("Format", "Aspect Ratio", "Ad Copy", "Labels"):
        if category not in groups:
            continue
        items = [i for i in groups[category] if i.n >= 200]
        if not items:
            continue
        html = f'<div class="insight-section-header">{escape(category)}</div>'
        for insight in items:
            html += _insight_bar_html(insight, max_abs_lift, kpi_upper)
        st.markdown(html, unsafe_allow_html=True)

    st.markdown(
        f'<div class="insight-footnote">'
        f"Lift is computed per lever against the filtered universe, not "
        f"against each other — so percentages don't sum. "
        f"<b>n</b> is the number of ads carrying that attribute. "
        f"Levers with n&lt;200 are excluded as directional only."
        f"</div>",
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner="Generating recommendations…")
def _cached_recommendations(
    data: pd.DataFrame, kpi: str,
) -> list:
    return generate_recommendations(data, kpi)


def render_recommendations(data: pd.DataFrame, kpi: str) -> None:
    """Render the Phase 3 Recommendations tab."""
    if data.empty:
        st.warning("No ads match the selected global filters.")
        return
    recs = _cached_recommendations(data, kpi)
    if not recs:
        st.info("Not enough data to generate recommendations.")
        return

    do_more = [r for r in recs if r.action == "do_more"]
    avoid = [r for r in recs if r.action == "avoid"]

    left, right = st.columns(2)
    with left:
        st.subheader("Do More Of")
        st.caption(f"Durable, significant drivers of {kpi}")
        for rec in do_more:
            color = lift_color(rec.lift)
            hypothesis = escape(rec.hypothesis)
            tag = escape(rec.durability_tag)
            synergy_html = ""
            if rec.synergy_partner and rec.synergy_score is not None:
                partner = escape(rec.synergy_partner)
                synergy_html = (
                    f'<div class="rec-synergy">Synergy with '
                    f"{partner}: "
                    f"{rec.synergy_score:+.1f}%</div>"
                )
            st.markdown(
                f'<div class="rec-card do-more">'
                f'<div class="rec-hypothesis">{hypothesis}</div>'
                f'<div class="rec-evidence">'
                f'<span class="rec-lift" style="color:{color}">'
                f"+{rec.lift:.0f}%</span>"
                f'<span class="rec-stat">p={rec.p_value:.4f}</span>'
                f'<span class="rec-tag durable">{tag}</span>'
                f'<span class="rec-n">n={rec.n:,}</span>'
                f"</div>"
                f"{synergy_html}"
                f"</div>",
                unsafe_allow_html=True,
            )
    with right:
        st.subheader("Avoid")
        st.caption(f"Durable, significant drains on {kpi}")
        for rec in avoid:
            color = lift_color(rec.lift)
            hypothesis = escape(rec.hypothesis)
            tag = escape(rec.durability_tag)
            synergy_html = ""
            if rec.synergy_partner and rec.synergy_score is not None:
                partner = escape(rec.synergy_partner)
                synergy_html = (
                    f'<div class="rec-synergy">Synergy with '
                    f"{partner}: "
                    f"{rec.synergy_score:+.1f}%</div>"
                )
            st.markdown(
                f'<div class="rec-card avoid">'
                f'<div class="rec-hypothesis">{hypothesis}</div>'
                f'<div class="rec-evidence">'
                f'<span class="rec-lift" style="color:{color}">'
                f"{rec.lift:.0f}%</span>"
                f'<span class="rec-stat">p={rec.p_value:.4f}</span>'
                f'<span class="rec-tag durable">{tag}</span>'
                f'<span class="rec-n">n={rec.n:,}</span>'
                f"</div>"
                f"{synergy_html}"
                f"</div>",
                unsafe_allow_html=True,
            )


def render_details(data: pd.DataFrame, kpi: str, top_n: int) -> None:
    """Render the complete Phase 1 Details tab."""
    if data.empty:
        st.warning("No ads match the selected global filters.")
        return
    render_label_details(data, kpi, top_n)
    st.divider()
    render_copy_details(data, kpi)


def render_loaded_state(data: pd.DataFrame) -> None:
    """Render the loaded-file header and global controls."""
    header, action = st.columns([5, 1])
    with header:
        st.title("Ads Creative Component Performance")
        st.caption(f"Loaded: {st.session_state['dataset_name']}")
    with action:
        st.write("")
        st.button(
            "Unload dataset",
            on_click=unload_dataset,
            width="stretch",
        )

    filtered = render_global_controls(data)
    st.caption(f"{len(filtered):,} of {len(data):,} ads in view")
    overview, details, insights_tab, recommendations_tab = st.tabs(
        ("Overview", "Details", "Insights", "Recommendations"),
    )
    with overview:
        render_overview(filtered, st.session_state["active_kpi"])
    with details:
        render_details(
            filtered,
            st.session_state["active_kpi"],
            st.session_state["active_top_n"],
        )
    with insights_tab:
        render_insights(filtered, st.session_state["active_kpi"])
    with recommendations_tab:
        render_recommendations(filtered, st.session_state["active_kpi"])


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
