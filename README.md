# DAC — Ads Creative Component Performance

DAC is a marketing decision-support project: a Streamlit dashboard that
analyzes ad creative component performance. Four pages:

- **Overview** — KPI cards, volume/ROAS trend, rolling lift, label performance
- **Details** — lift by label type, circular chart, word cloud, copy comparisons
- **Insights** — every creative lever ranked by its effect on the selected KPI
- **Recommendations** — pair-based plays (two levers + their quadrant interaction)

Insights and Recommendations include an **Explain** panel: an LLM layer that
answers questions about the computed results. It is a translator, not a
calculator — it only cites figures from the analytics layer, frames pair
recommendations as exploratory, and never asserts cause.

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Open `http://localhost:8501`, then upload a supported dataset or select
**Load sample creative dataset**.

### Explain panel setup (optional)

The Explain feature calls Hyperbolic (Llama 3.3 70B). Create a `.env` file
in the project root:

```text
HYPERBOLIC_KEY=<your key>
```

Without a key the dashboard works fully; Explain answers degrade to
"explanation unavailable."

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

## Evidence tiers

Not every number in the dashboard carries the same weight. Three tiers,
from strongest to weakest:

- **Tested** — Label insights on the Insights page. Each label must pass
  Welch's t-test (p < 0.05) against attribute-absent ads and have n ≥ 150
  before it is shown.
- **Directional** — Format, Aspect Ratio, and Ad Copy insights. Ranked
  associations with sample-size tiers only; no statistical test. Levers
  with n < 200 are additionally flagged "thin".
- **Exploratory** — pair recommendations on the Recommendations page.
  Minimum sample-size checks only: no significance test, no multiple-
  comparison correction, no durability check. Treat them as testable
  hypotheses for the next campaign, not conclusions.

The Explain panel receives this metadata with every item and answers
questions about reliability truthfully from it.

## Verification

```bash
python3 -m unittest discover -s tests -v
python3 validate.py data/ads-monthly_v1_2026-06-06_2023-01_2025-01.csv
```

To check the Explain guardrails after a prompt or model change (live API
calls, requires `HYPERBOLIC_KEY`):

```bash
python3 eval_explain.py
```