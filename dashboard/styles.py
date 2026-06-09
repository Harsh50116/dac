"""Visual styling for the Streamlit dashboard."""

import streamlit as st


APP_CSS = """
<style>
:root {
  --dac-bg: #0d0f13;
  --dac-surface: #14171d;
  --dac-surface-2: #181c23;
  --dac-border: rgba(255, 255, 255, 0.09);
  --dac-text: #e7e9ee;
  --dac-muted: #9aa0ab;
  --dac-accent: #5b8cff;
}

.stApp {
  background:
    radial-gradient(900px 520px at 85% -10%, rgba(91, 140, 255, 0.08), transparent 60%),
    radial-gradient(700px 460px at 0% 0%, rgba(52, 199, 123, 0.05), transparent 55%),
    var(--dac-bg);
}

[data-testid="stHeader"] {
  background: rgba(13, 15, 19, 0.82);
  border-bottom: 1px solid var(--dac-border);
  backdrop-filter: blur(14px);
}

[data-testid="stMainBlockContainer"] {
  max-width: 1640px;
  padding-top: 2rem;
  padding-bottom: 4rem;
}

h1, h2, h3, h4 {
  letter-spacing: -0.025em;
}

h1 {
  font-size: clamp(1.75rem, 3vw, 2.45rem) !important;
  font-weight: 800 !important;
}

h3 {
  margin-top: 0.35rem !important;
}

[data-testid="stCaptionContainer"] {
  color: var(--dac-muted);
}

[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(20, 23, 29, 0.82);
  border: 1px solid var(--dac-border) !important;
  border-radius: 16px;
  box-shadow: 0 12px 34px rgba(0, 0, 0, 0.16);
}

[data-testid="stMetric"] {
  min-height: 116px;
  padding: 1rem 0.9rem;
  background: linear-gradient(145deg, rgba(24, 28, 35, 0.96), rgba(20, 23, 29, 0.92));
  border: 1px solid var(--dac-border);
  border-radius: 14px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.14);
}

[data-testid="stMetricLabel"] {
  min-height: 2.2rem;
  color: var(--dac-muted);
  font-size: 0.72rem;
  font-weight: 650;
}

[data-testid="stMetricValue"] {
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: clamp(1.15rem, 1.55vw, 1.6rem);
  font-weight: 700;
}

.sparkline-wrap {
  margin-top: -0.6rem;
  line-height: 0;
}

[data-testid="stExpander"] {
  overflow: hidden;
  background: rgba(16, 19, 25, 0.72);
  border: 1px solid var(--dac-border);
  border-radius: 12px;
}

[data-testid="stExpander"] summary {
  font-weight: 700;
}

[data-testid="stExpanderDetails"] {
  min-height: 5.5rem;
}

[data-testid="stPlotlyChart"] {
  margin-top: 0.65rem;
  padding: 0.45rem;
  background: rgba(20, 23, 29, 0.74);
  border: 1px solid var(--dac-border);
  border-radius: 15px;
}

[data-testid="stFileUploaderDropzone"] {
  min-height: 250px;
  padding: 2.2rem;
  background: rgba(20, 23, 29, 0.9);
  border: 1px dashed rgba(91, 140, 255, 0.45);
  border-radius: 18px;
}

[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--dac-accent);
  background: rgba(91, 140, 255, 0.06);
}

.stButton > button {
  border-radius: 10px;
  font-weight: 700;
}

.stButton > button[kind="primary"] {
  border-color: var(--dac-accent);
  background: var(--dac-accent);
}

.stButton > button[kind="primary"]:hover {
  border-color: #76a0ff;
  background: #6d99ff;
}

[data-baseweb="select"] > div,
[data-testid="stNumberInput"] input {
  background: var(--dac-surface);
  border-color: var(--dac-border);
  border-radius: 9px;
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 1.5rem;
  border-bottom: 1px solid var(--dac-border);
}

[data-testid="stTabs"] [data-baseweb="tab"] {
  height: 3rem;
  padding-right: 0;
  padding-left: 0;
  font-weight: 700;
}

[data-testid="stTabs"] [aria-selected="true"] {
  color: var(--dac-text);
}

[data-testid="stAlert"] {
  border-radius: 12px;
}

.insight-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.6rem 0.85rem;
  margin-bottom: 0.35rem;
  background: linear-gradient(145deg, rgba(24, 28, 35, 0.92), rgba(20, 23, 29, 0.86));
  border: 1px solid var(--dac-border);
  border-radius: 10px;
}

.insight-rank {
  flex-shrink: 0;
  width: 2rem;
  color: var(--dac-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.insight-phrase {
  flex: 1 1 auto;
  color: var(--dac-text);
  font-size: 0.88rem;
  font-weight: 600;
}

.insight-lift {
  flex-shrink: 0;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 0.92rem;
  font-weight: 700;
}

.insight-n {
  flex-shrink: 0;
  color: var(--dac-muted);
  font-size: 0.72rem;
}

.insight-conf {
  flex-shrink: 0;
  padding: 0.15rem 0.5rem;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-radius: 6px;
}

.insight-conf.high {
  color: #34c77b;
  background: rgba(52, 199, 123, 0.12);
}

.insight-conf.medium {
  color: #e0a93f;
  background: rgba(224, 169, 63, 0.12);
}

.insight-conf.low {
  color: var(--dac-muted);
  background: rgba(154, 160, 171, 0.1);
}

.insight-section-header {
  margin-top: 1.2rem;
  margin-bottom: 0.5rem;
  color: var(--dac-muted);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.insight-bar-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.45rem 0;
}

.insight-bar-label {
  flex: 0 0 200px;
  color: var(--dac-text);
  font-size: 0.84rem;
  font-weight: 600;
}

.insight-bar-track {
  position: relative;
  flex: 1 1 auto;
  height: 26px;
  background: rgba(148, 163, 184, 0.08);
  border-radius: 5px;
  overflow: hidden;
}

.insight-bar-fill {
  position: absolute;
  top: 0;
  height: 100%;
  border-radius: 5px;
}

.insight-bar-stats {
  flex: 0 0 70px;
  text-align: right;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 0.82rem;
  font-weight: 700;
  line-height: 1.35;
}

.insight-bar-n {
  display: block;
  color: var(--dac-muted);
  font-size: 0.68rem;
  font-weight: 500;
}

.insight-thin {
  display: inline-block;
  margin-left: 0.4rem;
  padding: 0.08rem 0.35rem;
  color: var(--dac-muted);
  font-size: 0.58rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: rgba(154, 160, 171, 0.12);
  border-radius: 4px;
  vertical-align: middle;
}

.insight-legend {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.8rem;
  color: var(--dac-muted);
  font-size: 0.72rem;
}

.insight-legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.insight-footnote {
  margin-top: 1.5rem;
  color: var(--dac-muted);
  font-size: 0.68rem;
  line-height: 1.5;
}

.rec-card {
  padding: 0.85rem 1rem;
  margin-bottom: 0.5rem;
  background: linear-gradient(145deg, rgba(24, 28, 35, 0.92), rgba(20, 23, 29, 0.86));
  border: 1px solid var(--dac-border);
  border-radius: 12px;
}

.rec-card.do-more {
  border-left: 3px solid #34c77b;
}

.rec-card.avoid {
  border-left: 3px solid #e5533f;
}

.rec-hypothesis {
  color: var(--dac-text);
  font-size: 0.85rem;
  line-height: 1.45;
  margin-bottom: 0.5rem;
}

.rec-evidence {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
}

.rec-lift {
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 0.9rem;
  font-weight: 700;
}

.rec-stat {
  color: var(--dac-muted);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 0.72rem;
}

.rec-tag {
  padding: 0.12rem 0.45rem;
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-radius: 5px;
}

.rec-tag.durable {
  color: #34c77b;
  background: rgba(52, 199, 123, 0.12);
}

.rec-n {
  color: var(--dac-muted);
  font-size: 0.72rem;
}

.rec-synergy {
  margin-top: 0.4rem;
  color: var(--dac-accent);
  font-size: 0.75rem;
  font-style: italic;
}

hr {
  border-color: var(--dac-border) !important;
}

@media (max-width: 1100px) {
  [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap;
  }

  [data-testid="column"] {
    min-width: min(100%, 280px);
    flex: 1 1 280px;
  }

  [data-testid="stMetric"] {
    min-height: 104px;
  }
}

@media (max-width: 700px) {
  [data-testid="stMainBlockContainer"] {
    padding-right: 1rem;
    padding-left: 1rem;
  }

  [data-testid="column"] {
    min-width: 100%;
  }

  [data-testid="stFileUploaderDropzone"] {
    min-height: 210px;
    padding: 1.25rem;
  }
}
</style>
"""


def apply_styles() -> None:
    """Inject the dashboard's scoped CSS theme."""
    st.markdown(APP_CSS, unsafe_allow_html=True)
