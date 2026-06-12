"""Insights page: every creative lever ranked by effect on the KPI."""

from html import escape

import pandas as pd
import streamlit as st

from dashboard.llm.context import build_context
from dashboard.llm.explain_panel import SEED_PAGE, open_explain
from dashboard.ui.charts import lift_color
from dashboard.ui.pages.shared import (
    analyze_insights,
    cached_pair_recommendations,
)
from dashboard.ui.state import active_filter_summary


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

    top_n = st.session_state.get("active_top_n", 30)
    groups, max_abs_lift = analyze_insights(data, kpi, top_n)
    if not groups:
        st.info("Not enough data to generate insights.")
        return

    kpi_upper = kpi.upper()
    header_cols = st.columns([5, 1], vertical_alignment="center")
    with header_cols[0]:
        st.subheader(f"What moves {kpi_upper}")
    with header_cols[1]:
        page_clicked = st.button(
            "Inspect", key="explain_insights_page", width="stretch",
        )
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

    section_slugs = {
        "Format": "format",
        "Aspect Ratio": "ratio",
        "Ad Copy": "copy",
        "Labels": "labels",
    }
    focused_section = None
    for category in ("Format", "Aspect Ratio", "Ad Copy", "Labels"):
        if category not in groups:
            continue
        items = groups[category]
        html = f'<div class="insight-section-header">{escape(category)}</div>'
        for insight in items:
            html += _insight_bar_html(insight, max_abs_lift, kpi_upper)
        slug = section_slugs[category]
        with st.container(key=f"insight_sec_{slug}"):
            st.markdown(html, unsafe_allow_html=True)
            if st.button(":material/open_in_new:", key=f"explain_sec_{slug}"):
                focused_section = category

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

    if focused_section is None and not page_clicked:
        return

    context = build_context(
        page="Insights",
        kpi=kpi,
        dataset_name=st.session_state.get("dataset_name", ""),
        n_ads_in_view=len(data),
        n_ads_total=len(st.session_state["dataset"]),
        filters=active_filter_summary(),
        insight_groups=groups,
        pair_recs=cached_pair_recommendations(data, kpi, 3),
    )
    if focused_section is not None:
        items = groups[focused_section]
        open_explain(
            target=f"insights_sec_{section_slugs[focused_section]}",
            context=context,
            seed_question=(
                f"Explain the {focused_section} results: what do they "
                f"show, how do they connect to the other findings, and "
                f"what should I do next?"
            ),
            title=f"{focused_section} levers",
            chips=[
                ("KPI", kpi_upper, None),
                ("Levers", str(len(items)), None),
                ("Ads in view", f"{len(data):,}", None),
            ],
        )
    else:
        open_explain(
            target="insights_page",
            context=context,
            seed_question=SEED_PAGE,
            title=f"What moves {kpi_upper}",
            chips=[
                ("KPI", kpi_upper, None),
                ("Levers", str(sum(len(v) for v in groups.values())), None),
                ("Ads in view", f"{len(data):,}", None),
            ],
        )
