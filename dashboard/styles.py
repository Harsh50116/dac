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

[data-testid="stExpander"] {
  overflow: hidden;
  background: rgba(16, 19, 25, 0.72);
  border: 1px solid var(--dac-border);
  border-radius: 12px;
}

[data-testid="stExpander"] summary {
  font-weight: 700;
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
