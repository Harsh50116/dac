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
from dashboard.interactions import attribute_mask
from dashboard.recommend import generate_pair_recommendations, generate_recommendations
from dashboard.data import DataValidationError, calendar_months, load_dataset
from dashboard.significance_decay import significance_for_mask
from dashboard.styles import apply_styles


_DATA_DIR = Path(__file__).parent / "data"
SAMPLE_DATASETS = (
    ("Load sample dataset 1", _DATA_DIR / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"),
    ("Load sample dataset 2", _DATA_DIR / "ads_seed42.csv"),
    ("Load sample dataset 3", _DATA_DIR / "ads_flipped.csv"),
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


def _make_loader(path: Path):
    """Return a callback that loads the given sample dataset."""
    def _load():
        set_dataset(load_dataset(path), path.name)
    return _load


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
            st.info("Try one of the sample datasets below to explore the dashboard.")
        else:
            st.rerun()

    cols = st.columns(len(SAMPLE_DATASETS))
    for col, (label, path) in zip(cols, SAMPLE_DATASETS):
        with col:
            st.button(
                label,
                type="primary",
                on_click=_make_loader(path),
                use_container_width=True,
            )


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
    """Render the complete Phase 1 Overview tab."""
    if data.empty:
        st.warning("No ads match the selected global filters.")
        return
    render_kpi_cards(data)
    st.divider()
    render_volume_chart(data)
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


@st.cache_data(show_spinner="Analyzing insights…")
def _analyze_insights(
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


def render_insights(data: pd.DataFrame, kpi: str) -> None:
    """Render the Insights tab with grouped horizontal bars by category."""
    if data.empty:
        st.warning("No ads match the selected global filters.")
        return

    top_n = st.session_state.get("active_top_n", 30)
    groups, max_abs_lift = _analyze_insights(data, kpi, top_n)
    if not groups:
        st.info("Not enough data to generate insights.")
        return

    kpi_upper = kpi.upper()
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

    for category in ("Format", "Aspect Ratio", "Ad Copy"):
        if category not in groups:
            continue
        items = groups[category]
        html = f'<div class="insight-section-header">{escape(category)}</div>'
        for insight in items:
            html += _insight_bar_html(insight, max_abs_lift, kpi_upper)
        st.markdown(html, unsafe_allow_html=True)

    if "Labels" in groups:
        html = '<div class="insight-section-header">Labels</div>'
        for insight in groups["Labels"]:
            html += _insight_bar_html(insight, max_abs_lift, kpi_upper)
        st.markdown(html, unsafe_allow_html=True)

    st.markdown(
        f'<div class="insight-footnote">'
        f"Lift is computed per lever against the filtered universe, not "
        f"against each other — so percentages don't sum. "
        f"<b>n</b> is the number of ads carrying that attribute. "
        f"Labels require statistical significance (p&lt;0.05) and "
        f"n≥150 to appear. "
        f'Levers with n&lt;200 are flagged <span class="insight-thin">thin</span> '
        f"and should be read as directional, not conclusive."
        f"</div>",
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner="Generating recommendations…")
def _cached_pair_recommendations(
    data: pd.DataFrame, kpi: str, top_n: int,
) -> list:
    return generate_pair_recommendations(data, kpi, top_n=top_n)


def _quadrant_html(rec) -> str:
    """Build the 2x2 quadrant grid for a pair recommendation."""
    ab, a_only, b_only, neither = rec.cell_lifts
    phrase_a = escape(rec.phrases[0])
    phrase_b = escape(rec.phrases[1])

    def _cell(value: float, label: str) -> str:
        color = lift_color(value)
        bg = f"rgba({_rgb_from_lift(value)}, 0.12)"
        sign = "+" if value > 0 else ""
        return (
            f'<div class="rec-qcell" style="background:{bg}">'
            f'<span class="rec-qcell-value" style="color:{color}">'
            f"{sign}{value:.0f}%</span>"
            f'<span class="rec-qcell-label">{escape(label)}</span>'
            f"</div>"
        )

    both_cell = _cell(ab, "Both")
    neither_cell = _cell(neither, "Neither")
    return (
        f'<div class="rec-quadrant">'
        f'{_cell(a_only, phrase_a + " only")}'
        f"{both_cell}"
        f"{neither_cell}"
        f'{_cell(b_only, phrase_b + " only")}'
        f"</div>"
        f'<div class="rec-quadrant-footer">KPI lift vs baseline (neither)</div>'
    )


def _rgb_from_lift(value: float) -> str:
    """Extract RGB values from lift_color for use in rgba()."""
    color = lift_color(value)
    return color[4:-1]


def _rec_card_html(rec, rank: int, kpi: str) -> str:
    """Render one full-width recommendation card."""
    action_cls = rec.action.replace("_", "-")
    action_label = "DO MORE OF" if rec.action == "do_more" else "STOP"
    ordinals = {1: "1st", 2: "2nd", 3: "3rd"}
    priority = ordinals.get(rank, f"{rank}th")

    lift_color_val = lift_color(rec.combined_lift)
    synergy_color = lift_color(rec.synergy_score)
    sign = "+" if rec.combined_lift > 0 else ""
    syn_sign = "+" if rec.synergy_score > 0 else ""

    return (
        f'<div class="rec-card {action_cls}">'
        f'<div class="rec-body">'
        f'<div class="rec-header">'
        f'<span class="rec-action-tag {action_cls}">{action_label}</span>'
        f'<span class="rec-priority">{priority} priority</span>'
        f"</div>"
        f'<div class="rec-title">{escape(rec.title.capitalize())}</div>'
        f'<div class="rec-desc">{escape(rec.description)}</div>'
        f'<div class="rec-stats">'
        f'<div class="rec-stat-item">'
        f'<span class="rec-stat-label">Combined lift</span>'
        f'<span class="rec-stat-value" style="color:{lift_color_val}">'
        f"{sign}{rec.combined_lift:.0f}%</span>"
        f"</div>"
        f'<div class="rec-stat-item">'
        f'<span class="rec-stat-label">Synergy</span>'
        f'<span class="rec-stat-value" style="color:{synergy_color}">'
        f"{syn_sign}{rec.synergy_score:.1f}%</span>"
        f"</div>"
        f'<div class="rec-stat-item">'
        f'<span class="rec-stat-label">Headroom</span>'
        f'<span class="rec-stat-value">{rec.headroom:.0f}%</span>'
        f"</div>"
        f'<div class="rec-stat-item">'
        f'<span class="rec-stat-label">n (both)</span>'
        f'<span class="rec-stat-value">{rec.n_both:,}</span>'
        f"</div>"
        f"</div>"
        f"</div>"
        f'<div class="rec-quadrant-wrap">'
        f"{_quadrant_html(rec)}"
        f"</div>"
        f"</div>"
    )


def render_recommendations(data: pd.DataFrame, kpi: str) -> None:
    """Render the Phase 3 Recommendations tab with pair-based cards."""
    if data.empty:
        st.warning("No ads match the selected global filters.")
        return

    top_n = 3
    recs = _cached_pair_recommendations(data, kpi, top_n)
    if not recs:
        st.info("Not enough data to generate recommendations.")
        return

    kpi_upper = kpi.upper()
    st.subheader(f"Your next {len(recs)} moves")
    st.markdown(
        f'<div class="rec-counter">'
        f"Showing top {len(recs)} pair-based recommendations for {kpi_upper}. "
        f"Each card pairs two creative levers and shows their combined effect."
        f"</div>",
        unsafe_allow_html=True,
    )

    for rank, rec in enumerate(recs, 1):
        st.markdown(
            _rec_card_html(rec, rank, kpi),
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

    st.title("Ads Creative Component Performance")
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
