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
  min-height: 104px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 1rem 0.9rem;
  background: linear-gradient(145deg, rgba(24, 28, 35, 0.96), rgba(20, 23, 29, 0.92));
  border: 1px solid var(--dac-border);
  border-radius: 14px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.14);
}

[data-testid="stMetricLabel"] {
  min-height: 0;
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
  min-height: 80px;
  padding: 1rem 1.5rem;
  background: rgba(20, 23, 29, 0.9);
  border: 1px dashed rgba(91, 140, 255, 0.45);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
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
  margin-top: 1.8rem;
  margin-bottom: 0.6rem;
  padding-bottom: 0.4rem;
  color: var(--dac-text);
  font-size: 0.92rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border-bottom: 1px solid var(--dac-border);
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
  display: flex;
  gap: 1.5rem;
  padding: 1.1rem 1.3rem;
  margin-bottom: 0.75rem;
  background: linear-gradient(145deg, rgba(24, 28, 35, 0.92), rgba(20, 23, 29, 0.86));
  border: 1px solid var(--dac-border);
  border-radius: 14px;
}

.rec-card.do-more {
  border-left: 3px solid #34c77b;
}

.rec-card.stop {
  border-left: 3px solid #e5533f;
}

.rec-body {
  flex: 1 1 auto;
  min-width: 0;
}

.rec-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.45rem;
}

.rec-action-tag {
  padding: 0.15rem 0.5rem;
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-radius: 5px;
}

.rec-action-tag.do-more {
  color: #34c77b;
  background: rgba(52, 199, 123, 0.14);
}

.rec-action-tag.stop {
  color: #e5533f;
  background: rgba(229, 83, 63, 0.14);
}

.rec-priority {
  color: var(--dac-muted);
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.rec-title {
  color: var(--dac-text);
  font-size: 1.12rem;
  font-weight: 700;
  line-height: 1.35;
  margin-bottom: 0.3rem;
}

.rec-desc {
  color: var(--dac-muted);
  font-size: 0.92rem;
  line-height: 1.5;
  margin-bottom: 0.65rem;
}

.rec-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.85rem;
}

.rec-stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.rec-stat-label {
  color: var(--dac-muted);
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.rec-stat-value {
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 1.05rem;
  font-weight: 700;
}

.rec-quadrant-wrap {
  flex: 0 0 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.rec-quadrant {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 4px;
  width: 220px;
  height: 170px;
}

.rec-qcell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  padding: 0.3rem;
}

.rec-qcell-value {
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 1.05rem;
  font-weight: 700;
}

.rec-qcell-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--dac-muted);
  text-align: center;
  line-height: 1.2;
}

.rec-quadrant-footer {
  margin-top: 0.3rem;
  color: var(--dac-muted);
  font-size: 0.75rem;
  text-align: center;
}

.rec-counter {
  color: var(--dac-muted);
  font-size: 0.85rem;
  margin-bottom: 0.3rem;
}

[data-testid="stSidebar"] {
  background: var(--dac-surface);
  border-right: 1px solid var(--dac-border);
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div {
  gap: 0.2rem;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] > label {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.6rem 0.85rem;
  margin: 0;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.92rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  background: rgba(91, 140, 255, 0.10);
}

[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {
  display: none;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label:has([aria-checked="true"]),
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked),
[data-testid="stSidebar"] [data-testid="stRadio"] label.nav-active {
  background: rgba(91, 140, 255, 0.15);
  color: #5b8cff;
  font-weight: 700;
}

hr {
  border-color: var(--dac-border) !important;
}

/* ---- Explain panel (right-side drawer) ---- */

/* The backdrop scrolls by default when the dialog outgrows the viewport,
   which drags the 100vh drawer out of alignment — pin it shut. */
div[data-testid="stDialog"] {
  overflow: hidden !important;
}

/* The modal container's top padding pushes the 100vh drawer past the
   viewport, making the backdrop scrollable even with short content. */
div[data-testid="stDialog"] > div {
  padding-top: 0 !important;
}

div[data-testid="stDialog"] div[role="dialog"] {
  width: 75vw !important;
  max-width: 75vw !important;
  height: 100vh;
  max-height: 100vh !important;
  margin: 0 0 0 auto;
  border-radius: 18px 0 0 18px;
  background: var(--dac-surface);
  border: 1px solid var(--dac-border);
  border-right: none;
  overflow-y: auto;
}

/* Shrink the conversation on short viewports so the header, chips, and
   chat input always fit inside the drawer (overrides the inline 500px). */
div[data-testid="stDialog"] .st-key-explain_conversation {
  height: min(500px, calc(100vh - 22rem)) !important;
  min-height: 180px;
}

.explain-disclaimer {
  font-size: 0.8rem;
  color: var(--dac-muted);
  border: 1px solid var(--dac-border);
  border-radius: 10px;
  padding: 0.5rem 0.75rem;
  margin-bottom: 0.6rem;
  background: var(--dac-surface-2);
}

.explain-title {
  font-size: 1.05rem;
  font-weight: 700;
  margin: 0.2rem 0 0.5rem;
}

.explain-chips {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.9rem;
}

.explain-chip {
  font-size: 0.8rem;
  color: var(--dac-muted);
  border: 1px solid var(--dac-border);
  background: var(--dac-surface-2);
  border-radius: 999px;
  padding: 0.25rem 0.7rem;
}

.explain-chip b {
  margin-left: 0.35rem;
}

[data-testid="stChatInput"] {
  background: var(--dac-surface-2);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 12px;
}

[data-testid="stChatInput"]:focus-within {
  border-color: rgba(91, 140, 255, 0.65);
}

[data-testid="stChatInput"] textarea {
  background: transparent;
  font-size: 1rem;
}
/* Explain buttons overlaid on the top-right of cards and sections */

[class*="st-key-rec_wrap_"],
[class*="st-key-insight_sec_"] {
  position: relative;
}

[class*="st-key-rec_wrap_"] [data-testid="stElementContainer"]:has(button),
[class*="st-key-insight_sec_"] [data-testid="stElementContainer"]:has(button) {
  position: absolute;
  right: 1.1rem;
  z-index: 5;
  width: auto;
}

[class*="st-key-rec_wrap_"] [data-testid="stElementContainer"]:has(button) {
  top: 1rem;
}

[class*="st-key-insight_sec_"] [data-testid="stElementContainer"]:has(button) {
  top: 1.4rem;
}

[class*="st-key-rec_wrap_"] .stButton button,
[class*="st-key-insight_sec_"] .stButton button {
  font-size: 0.8rem;
  padding: 0.1rem 0.45rem;
  min-height: 1.7rem;
  background: rgba(91, 140, 255, 0.1);
  border: 1px solid rgba(91, 140, 255, 0.35);
  color: #cfe0ff;
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
    min-height: 70px;
    padding: 0.85rem 1rem;
  }
}
</style>
"""


NAV_HIGHLIGHT_JS = """
<script>
function highlightNav() {
  const sidebar = document.querySelector('[data-testid="stSidebar"]');
  if (!sidebar) return;
  const labels = sidebar.querySelectorAll('[data-testid="stRadio"] label');
  labels.forEach(label => {
    const checked = label.querySelector('input:checked, [aria-checked="true"]');
    if (checked) {
      label.classList.add('nav-active');
    } else {
      label.classList.remove('nav-active');
    }
  });
}
const observer = new MutationObserver(highlightNav);
observer.observe(document.body, {subtree: true, attributes: true, childList: true});
highlightNav();
</script>
"""


def apply_styles() -> None:
    """Inject the dashboard's scoped CSS theme."""
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.markdown(NAV_HIGHLIGHT_JS, unsafe_allow_html=True)
