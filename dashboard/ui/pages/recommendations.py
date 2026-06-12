"""Recommendations page: pair-based plays with quadrant interactions."""

from html import escape

import pandas as pd
import streamlit as st

from dashboard.llm.context import build_context, pair_rec_id
from dashboard.llm.explain_panel import SEED_FOCUS, SEED_PAGE, open_explain
from dashboard.ui.charts import lift_color
from dashboard.ui.pages.shared import (
    analyze_insights,
    cached_pair_recommendations,
)
from dashboard.ui.state import active_filter_summary


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
    """Render the Recommendations tab with pair-based cards."""
    if data.empty:
        st.warning("No ads match the selected global filters.")
        return

    top_n = 3
    recs = cached_pair_recommendations(data, kpi, top_n)
    if not recs:
        st.info("Not enough data to generate recommendations.")
        return

    kpi_upper = kpi.upper()
    header_cols = st.columns([5, 1], vertical_alignment="center")
    with header_cols[0]:
        st.subheader(f"Your next {len(recs)} moves")
    with header_cols[1]:
        page_clicked = st.button(
            "Inspect", key="explain_recs_page", width="stretch",
        )
    st.markdown(
        f'<div class="rec-counter">'
        f"Showing top {len(recs)} pair-based recommendations for {kpi_upper}. "
        f"Each card pairs two creative levers and shows their combined effect. "
        f"Pair plays are exploratory: ranked by observed lift with minimum "
        f"sample-size checks, not statistically tested like Label insights."
        f"</div>",
        unsafe_allow_html=True,
    )

    focused_rec = None
    for rank, rec in enumerate(recs, 1):
        with st.container(key=f"rec_wrap_{rank}"):
            st.markdown(
                _rec_card_html(rec, rank, kpi),
                unsafe_allow_html=True,
            )
            if st.button(":material/open_in_new:", key=f"explain_rec_{rank}"):
                focused_rec = rec

    if focused_rec is None and not page_clicked:
        return

    focus_id = pair_rec_id(focused_rec) if focused_rec is not None else None
    insight_groups, _ = analyze_insights(
        data, kpi, st.session_state.get("active_top_n", 30),
    )
    context = build_context(
        page="Recommendations",
        kpi=kpi,
        dataset_name=st.session_state.get("dataset_name", ""),
        n_ads_in_view=len(data),
        n_ads_total=len(st.session_state["dataset"]),
        filters=active_filter_summary(),
        insight_groups=insight_groups,
        pair_recs=recs,
        focus_id=focus_id,
    )
    if focused_rec is not None:
        rec = focused_rec
        lift_sign = "+" if rec.combined_lift > 0 else ""
        syn_sign = "+" if rec.synergy_score > 0 else ""
        open_explain(
            target=focus_id,
            context=context,
            seed_question=SEED_FOCUS,
            title=rec.title.capitalize(),
            chips=[
                ("Combined lift", f"{lift_sign}{rec.combined_lift:.0f}%",
                 lift_color(rec.combined_lift)),
                ("Synergy", f"{syn_sign}{rec.synergy_score:.1f}%",
                 lift_color(rec.synergy_score)),
                ("Headroom", f"{rec.headroom:.0f}%", None),
                ("n (both)", f"{rec.n_both:,}", None),
            ],
        )
    else:
        open_explain(
            target="recs_page",
            context=context,
            seed_question=SEED_PAGE,
            title=f"Your next {len(recs)} moves",
            chips=[
                ("KPI", kpi_upper, None),
                ("Plays", str(len(recs)), None),
                ("Ads in view", f"{len(data):,}", None),
            ],
        )
