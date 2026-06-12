"""Initial upload state: file uploader, sample datasets, and previews."""

from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard.data import DataValidationError, load_dataset
from dashboard.ui.state import set_dataset


_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SAMPLE_DATASETS = (
    ("Load sample dataset 1", _DATA_DIR / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"),
    ("Load sample dataset 2", _DATA_DIR / "ads_seed42.csv"),
    ("Load sample dataset 3", _DATA_DIR / "ads_flipped.csv"),
)


def _make_loader(path: Path):
    """Return a callback that loads the given sample dataset."""
    def _load():
        set_dataset(load_dataset(path), path.name)
    return _load


@st.cache_data
def _sample_preview(path_str: str) -> tuple[pd.DataFrame, int]:
    """First rows of a sample dataset, as they appear in the file."""
    frame = pd.read_csv(path_str)
    return frame.head(50), len(frame)


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

    with st.expander("Preview sample datasets"):
        tabs = st.tabs(
            [f"Sample dataset {n}" for n in range(1, len(SAMPLE_DATASETS) + 1)]
        )
        for tab, (label, path) in zip(tabs, SAMPLE_DATASETS):
            with tab:
                preview, total = _sample_preview(str(path))
                st.caption(
                    f"{path.name} · showing first {len(preview)} "
                    f"of {total:,} rows"
                )
                st.dataframe(preview, width="stretch", hide_index=True)
