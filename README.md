# DAC Phase 1 Dashboard

DAC is a marketing decision-support project. Phase 1 reproduces the existing
Ads Creative Component Performance dashboard using controlled synthetic data
with known, learnable performance patterns.

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Open `http://localhost:8501`, then upload a supported dataset or select
**Load sample creative dataset**.

## Supported data

The app accepts CSV, Parquet, and Excel files with these columns:

```text
ad_id, date, spend, revenue, impressions, clicks, purchases,
headline, body, media_type, aspect_ratio, category, labels
```

`labels` uses pipe-delimited `token:Type` values, for example:

```text
img_cap:Image|cap:Noun|train:Verb
```

The bundled Phase 1 dataset is:

```text
data/ads-monthly_v1_2026-06-06_2023-01_2025-01.csv
```

## Analytics contract

- ROAS: revenue / spend
- CTR: clicks / impressions
- CPP: spend / purchases
- Lift: mean per-ad KPI for attribute-present ads versus attribute-absent ads
- CPP lift is direction-adjusted so positive values always mean better results
- Missing calendar months remain visible in time-series results

## Verification

```bash
python3 -m unittest discover -s tests -v
python3 validate.py data/ads-monthly_v1_2026-06-06_2023-01_2025-01.csv
```

The implementation follows the constraints in `CLAUDE.md`.
