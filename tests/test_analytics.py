"""Tests for Phase 1 dashboard analytics."""

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from dashboard.analytics import (
    aggregate_kpi,
    filter_data,
    kpi_summary,
    label_table,
    label_type_table,
    label_performance_over_time,
    lift,
    monthly_performance,
    rolling_label_lift,
    rows_with_labels,
)
from dashboard.data import load_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE_ONE_DATA = (
    PROJECT_ROOT
    / "data"
    / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"
)


class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)

    def test_kpi_summary_matches_phase_one_totals(self):
        summary = kpi_summary(self.data)

        self.assertEqual(summary["ads"], 2650)
        self.assertAlmostEqual(summary["spend"], 526486.68, places=2)
        self.assertAlmostEqual(summary["revenue"], 2061352.00, places=2)
        self.assertEqual(summary["impressions"], 49257553)
        self.assertEqual(summary["clicks"], 411102)
        self.assertEqual(summary["purchases"], 8329)
        self.assertAlmostEqual(summary["roas"], 3.9153, places=4)
        self.assertAlmostEqual(aggregate_kpi(self.data, "CTR"), 0.008346, places=6)
        self.assertAlmostEqual(aggregate_kpi(self.data, "CPP"), 63.2113, places=4)

    def test_filters_apply_together(self):
        filtered = filter_data(
            self.data,
            start=pd.Timestamp("2024-01-01"),
            end=pd.Timestamp("2024-12-01"),
            categories=("mountain",),
            media_types=("image",),
        )

        self.assertFalse(filtered.empty)
        self.assertTrue(filtered["date"].between("2024-01-01", "2024-12-01").all())
        self.assertEqual(set(filtered["category"]), {"mountain"})
        self.assertEqual(set(filtered["media_type"]), {"image"})

    def test_structural_roas_lifts_recover_expected_direction(self):
        expected = {
            "headline_has_numbers": (40, 65),
            "body_has_numbers": (35, 55),
            "body_has_emoji": (10, 30),
            "body_over_50": (-40, -20),
        }
        for feature, bounds in expected.items():
            with self.subTest(feature=feature):
                value = lift(self.data, self.data[feature], "ROAS")
                self.assertGreater(value, bounds[0])
                self.assertLess(value, bounds[1])

    def test_cpp_lift_treats_lower_cost_as_positive(self):
        image_lift = lift(
            self.data, self.data["media_type"].eq("image"), "CPP"
        )
        video_lift = lift(
            self.data, self.data["media_type"].eq("video"), "CPP"
        )

        self.assertGreater(image_lift, 0)
        self.assertLess(video_lift, 0)
        self.assertTrue(np.isfinite(image_lift))

    def test_monthly_performance_retains_empty_months(self):
        monthly = monthly_performance(self.data)
        february = monthly.loc[monthly["date"].eq("2023-02-01")].iloc[0]

        self.assertEqual(len(monthly), 25)
        self.assertEqual(february["ads"], 0)
        self.assertTrue(pd.isna(february["roas"]))
        self.assertTrue(pd.isna(february["ctr"]))
        self.assertTrue(pd.isna(february["cpp"]))

    def test_label_tables_include_counts_and_lift(self):
        labels = label_table(
            self.data, "ROAS", label_types=("Phrase",), min_ads=20
        )
        types = label_type_table(self.data, "ROAS")

        self.assertFalse(labels.empty)
        self.assertEqual(set(labels["label_type"]), {"Phrase"})
        self.assertTrue(labels["ads"].ge(20).all())
        self.assertEqual(
            set(types["label_type"]),
            {"Image", "Noun", "Phrase", "Verb", "Video"},
        )

    def test_rolling_lift_contains_every_quarter(self):
        result = rolling_label_lift(
            self.data,
            token="adventure awaits",
            kpi="ROAS",
            frequency="quarter",
            window=2,
            label_types=("Phrase",),
        )

        self.assertEqual(len(result), 9)
        self.assertEqual(str(result.iloc[0]["period"]), "2023Q1")
        self.assertEqual(str(result.iloc[-1]["period"]), "2025Q1")
        self.assertIn("rolling_lift", result)

    def test_label_performance_and_row_filtering(self):
        filtered = rows_with_labels(
            self.data,
            ("adventure awaits",),
            ("Phrase",),
        )
        performance = label_performance_over_time(
            self.data,
            ("adventure awaits",),
            "ROAS",
            frequency="quarter",
            label_types=("Phrase",),
        )

        self.assertGreater(len(filtered), 0)
        self.assertTrue(
            filtered["label_tokens"].map(
                lambda labels: "adventure awaits" in labels
            ).all()
        )
        self.assertEqual(len(performance), 9)
        self.assertIn("ads", performance)
        self.assertIn("lift", performance)


if __name__ == "__main__":
    unittest.main()
