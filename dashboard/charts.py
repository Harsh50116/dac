"""Plotly chart builders for the Phase 1 Overview."""

import math

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


GREEN = "#34c77b"
BLUE = "#5b8cff"
AMBER = "#e0a93f"
GRID = "rgba(148, 163, 184, 0.14)"
TEXT = "#cbd5e1"
RED = "#e5533f"
FONT = "Arial, sans-serif"


def lift_color(value: float) -> str:
    stops = [
        (-50, (229, 72, 77)), (-15, (240, 138, 60)), (0, (227, 179, 65)),
        (18, (123, 200, 108)), (45, (47, 179, 68)),
    ]
    v = max(-50, min(45, value))
    for i in range(len(stops) - 1):
        a, ca = stops[i]
        b, cb = stops[i + 1]
        if a <= v <= b:
            t = (v - a) / (b - a)
            c = tuple(round(ca[j] + (cb[j] - ca[j]) * t) for j in range(3))
            return f"rgb({c[0]},{c[1]},{c[2]})"
    return "rgb(227,179,65)"


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


def lift_bar_chart(
    data: pd.DataFrame,
    label_column: str,
    height: int = 320,
) -> go.Figure:
    """Build a categorical lift bar chart."""
    colors = [lift_color(value) for value in data["lift"]]
    figure = go.Figure(
        go.Bar(
            x=data[label_column],
            y=data["lift"],
            marker_color=colors,
            customdata=data[["ads"]],
            text=data["lift"].map(lambda value: f"{value:+.1f}%"),
            textposition="outside",
            hovertemplate=(
                "%{x}<br>Lift: %{y:+.1f}%<br>Ads: %{customdata[0]:,}"
                "<extra></extra>"
            ),
        )
    )
    figure.add_hline(y=0, line_color=TEXT, opacity=0.5)
    _apply_layout(figure, "")
    figure.update_layout(height=height, showlegend=False)
    figure.update_yaxes(title_text="Lift (%)")
    return figure


def circular_lift_chart(data: pd.DataFrame) -> go.Figure:
    """Build a polar lift chart with compact token labels."""
    colors = [lift_color(value) for value in data["lift"]]
    n = len(data)
    step = 1 if n <= 30 else 2 if n <= 44 else 3
    tokens = [t[:12] + "…" if len(t) > 13 else t for t in data["token"]]
    figure = go.Figure(
        go.Barpolar(
            r=data["lift"].abs(),
            theta=tokens,
            marker_color=colors,
            customdata=data[["label_type", "ads", "lift", "token"]],
            hovertemplate=(
                "%{customdata[3]}<br>Type: %{customdata[0]}"
                "<br>Lift: %{customdata[2]:+.1f}%"
                "<br>Ads: %{customdata[1]:,}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        height=480,
        margin={"l": 70, "r": 70, "t": 35, "b": 35},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT, "family": FONT},
        hoverlabel={
            "bgcolor": "#181c23",
            "bordercolor": "rgba(255,255,255,0.14)",
            "font": {"color": "#e7e9ee", "family": FONT},
        },
        showlegend=False,
        polar={
            "bgcolor": "rgba(0,0,0,0)",
            "angularaxis": {
                "gridcolor": GRID,
                "tickfont": {"size": 9.5},
                "tickvals": tokens,
                "ticktext": [
                    t if i % step == 0 else ""
                    for i, t in enumerate(tokens)
                ],
            },
            "radialaxis": {
                "gridcolor": GRID,
                "showticklabels": False,
            },
        },
    )
    return figure


def word_cloud_chart(data: pd.DataFrame) -> go.Figure:
    """Build a deterministic Plotly text cloud."""
    if data.empty:
        return go.Figure()
    minimum = data["ads"].min()
    maximum = data["ads"].max()
    spread = maximum - minimum or 1
    sizes = 13 + (data["ads"] - minimum) / spread * 33
    colors = [lift_color(value) for value in data["lift"]]
    n = len(data)
    golden = 2.3998277
    x = [math.sqrt(i + 0.5) * 0.8 * math.cos(i * golden) for i in range(n)]
    y = [math.sqrt(i + 0.5) * 0.8 * math.sin(i * golden) for i in range(n)]
    figure = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="text",
            text=data["token"],
            textfont={"size": sizes.tolist(), "color": colors},
            customdata=data[["label_type", "ads", "lift"]],
            hovertemplate=(
                "%{text}<br>Type: %{customdata[0]}"
                "<br>Ads: %{customdata[1]:,}"
                "<br>Lift: %{customdata[2]:+.1f}%<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        height=480,
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT, "family": FONT},
        hoverlabel={
            "bgcolor": "#181c23",
            "bordercolor": "rgba(255,255,255,0.14)",
            "font": {"color": "#e7e9ee", "family": FONT},
        },
        xaxis={"visible": False},
        yaxis={"visible": False},
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
        font={"color": TEXT, "family": FONT, "size": 12},
        hoverlabel={
            "bgcolor": "#181c23",
            "bordercolor": "rgba(255,255,255,0.14)",
            "font": {"color": "#e7e9ee", "family": FONT},
        },
        bargap=0.22,
    )
    figure.update_xaxes(
        title_text=x_title,
        gridcolor=GRID,
        linecolor=GRID,
        zerolinecolor=GRID,
    )
    figure.update_yaxes(
        gridcolor=GRID,
        linecolor=GRID,
        zerolinecolor=GRID,
    )
