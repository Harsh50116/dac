"""Plotly chart builders for the Phase 1 Overview."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


GREEN = "#34c77b"
BLUE = "#5b8cff"
AMBER = "#e0a93f"
GRID = "rgba(148, 163, 184, 0.14)"
TEXT = "#cbd5e1"


def volume_performance_chart(
    monthly: pd.DataFrame,
    bar_metric: str,
    rolling_months: int,
) -> go.Figure:
    """Build the monthly volume/performance dual-axis chart."""
    metric_columns = {
        "Ads": ("ads", "# of Ads"),
        "Spend": ("spend", "Spend ($)"),
        "Revenue": ("revenue", "Revenue ($)"),
    }
    column, label = metric_columns[bar_metric]
    roas = monthly["roas"].rolling(rolling_months, min_periods=1).mean()

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_bar(
        x=monthly["date"],
        y=monthly[column],
        name=label,
        marker_color=GREEN,
        secondary_y=False,
    )
    figure.add_scatter(
        x=monthly["date"],
        y=roas,
        name="ROAS",
        mode="lines+markers",
        line={"color": BLUE, "width": 2},
        secondary_y=True,
    )
    _apply_layout(figure, "Month")
    figure.update_yaxes(title_text=label, secondary_y=False)
    figure.update_yaxes(title_text="ROAS", secondary_y=True, showgrid=False)
    return figure


def rolling_lift_chart(series: dict[str, pd.DataFrame]) -> go.Figure:
    """Build a multi-line rolling lift chart."""
    figure = go.Figure()
    for token, data in series.items():
        figure.add_scatter(
            x=data["period"].astype(str),
            y=data["rolling_lift"],
            name=token,
            mode="lines+markers",
        )
    figure.add_hline(y=0, line_dash="dot", line_color=TEXT, opacity=0.5)
    _apply_layout(figure, "Period")
    figure.update_yaxes(title_text="Lift (%)")
    return figure


def label_performance_chart(data: pd.DataFrame) -> go.Figure:
    """Build the label-volume and lift dual-axis chart."""
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_bar(
        x=data["period"].astype(str),
        y=data["ads"],
        name="# of Ads (present)",
        marker_color=AMBER,
        secondary_y=False,
    )
    figure.add_scatter(
        x=data["period"].astype(str),
        y=data["lift"],
        name="Label Lift (%)",
        mode="lines+markers",
        line={"color": BLUE, "width": 2},
        secondary_y=True,
    )
    figure.add_hline(y=0, line_dash="dot", line_color=TEXT, opacity=0.5)
    _apply_layout(figure, "Period")
    figure.update_yaxes(title_text="# of Ads", secondary_y=False)
    figure.update_yaxes(
        title_text="Lift (%)",
        secondary_y=True,
        showgrid=False,
    )
    return figure


def _apply_layout(figure: go.Figure, x_title: str) -> None:
    figure.update_layout(
        height=380,
        margin={"l": 50, "r": 50, "t": 25, "b": 45},
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.08, "x": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT},
    )
    figure.update_xaxes(title_text=x_title, gridcolor=GRID)
    figure.update_yaxes(gridcolor=GRID)
