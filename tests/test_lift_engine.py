"""Contract tests for the lift engine — run these before and after refactoring."""

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from dashboard.data import load_dataset
from dashboard.analytics.lift_engine import (
    KPI_NAMES,
    LiftResult,
    compute_lift,
    kpi_series,
    lift_for_flag,
    lift_for_label,
    lift_for_label_type,
    lift_for_value,
    scan_all,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE_ONE_DATA = (
    PROJECT_ROOT
    / "data"
    / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"
)


class LiftResultContractTests(unittest.TestCase):
    """LiftResult shape must not change — Phase 2/3 depend on it."""

    def test_fields_are_present(self):
        result = LiftResult(
            lift=10.0,
            mean_present=4.0,
            mean_absent=3.6,
            n_present=100,
            n_absent=200,
            direction="higher_is_better",
        )
        self.assertEqual(result.lift, 10.0)
        self.assertEqual(result.mean_present, 4.0)
        self.assertEqual(result.mean_absent, 3.6)
        self.assertEqual(result.n_present, 100)
        self.assertEqual(result.n_absent, 200)
        self.assertEqual(result.direction, "higher_is_better")

    def test_result_is_frozen(self):
        result = LiftResult(0, 0, 0, 0, 0, "higher_is_better")
        with self.assertRaises(AttributeError):
            result.lift = 99


class ComputeLiftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)

    def test_roas_lift_returns_correct_shape(self):
        mask = self.data["headline_has_numbers"]
        result = compute_lift(self.data, mask, "ROAS")
        self.assertIsInstance(result, LiftResult)
        self.assertIsInstance(result.lift, float)
        self.assertIsInstance(result.n_present, int)
        self.assertIsInstance(result.n_absent, int)
        self.assertEqual(result.n_present + result.n_absent, len(self.data))
        self.assertEqual(result.direction, "higher_is_better")

    def test_cpp_direction_is_lower_is_better(self):
        mask = self.data["media_type"].eq("image")
        result = compute_lift(self.data, mask, "CPP")
        self.assertEqual(result.direction, "lower_is_better")

    def test_cpp_inversion_positive_means_cheaper(self):
        image = compute_lift(self.data, self.data["media_type"].eq("image"), "CPP")
        video = compute_lift(self.data, self.data["media_type"].eq("video"), "CPP")
        self.assertGreater(image.lift, 0)
        self.assertLess(video.lift, 0)

    def test_cpp_means_are_raw_not_inverted(self):
        result = compute_lift(
            self.data, self.data["media_type"].eq("image"), "CPP",
        )
        # mean_present is raw CPP (spend/purchases) — positive number
        self.assertGreater(result.mean_present, 0)
        self.assertGreater(result.mean_absent, 0)
        # image is cheaper so raw mean_present < mean_absent
        self.assertLess(result.mean_present, result.mean_absent)
        # but lift is positive (inverted) because lower cost = better
        self.assertGreater(result.lift, 0)

    def test_nan_on_empty_group(self):
        empty_mask = pd.Series(False, index=self.data.index)
        result = compute_lift(self.data, empty_mask, "ROAS")
        self.assertTrue(np.isnan(result.lift))
        self.assertEqual(result.n_present, 0)

    def test_nan_on_zero_absent_mean(self):
        all_mask = pd.Series(True, index=self.data.index)
        result = compute_lift(self.data, all_mask, "ROAS")
        self.assertTrue(np.isnan(result.lift))
        self.assertEqual(result.n_absent, 0)

    def test_matches_existing_analytics_lift(self):
        from dashboard.analytics.core import lift

        for kpi in KPI_NAMES:
            for col in ("headline_has_numbers", "body_has_emoji", "body_over_50"):
                with self.subTest(kpi=kpi, col=col):
                    mask = self.data[col].astype(bool)
                    engine_result = compute_lift(self.data, mask, kpi)
                    analytics_result = lift(self.data, mask, kpi)
                    if np.isnan(analytics_result):
                        self.assertTrue(np.isnan(engine_result.lift))
                    else:
                        self.assertAlmostEqual(
                            engine_result.lift, analytics_result, places=10,
                        )


class KpiSeriesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)

    def test_roas_is_revenue_over_spend(self):
        series = kpi_series(self.data, "ROAS")
        row = self.data.iloc[0]
        expected = row["revenue"] / row["spend"]
        self.assertAlmostEqual(series.iloc[0], expected, places=6)

    def test_invalid_kpi_raises(self):
        with self.assertRaises(ValueError):
            kpi_series(self.data, "INVALID")


class HelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)

    def test_lift_for_flag(self):
        result = lift_for_flag(self.data, "headline_has_numbers", "ROAS")
        self.assertIsInstance(result, LiftResult)
        self.assertGreater(result.lift, 0)

    def test_lift_for_value(self):
        result = lift_for_value(self.data, "media_type", "image", "ROAS")
        self.assertIsInstance(result, LiftResult)
        self.assertGreater(result.n_present, 0)

    def test_lift_for_label(self):
        result = lift_for_label(self.data, "cap", "Noun", "ROAS")
        self.assertIsInstance(result, LiftResult)
        self.assertGreater(result.n_present, 0)

    def test_lift_for_label_type(self):
        result = lift_for_label_type(self.data, "Phrase", "ROAS")
        self.assertIsInstance(result, LiftResult)
        self.assertGreater(result.n_present, 0)


class ScanAllTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)
        cls.results = scan_all(cls.data, "ROAS", top_n_labels=10)

    def test_returns_dict_of_lift_results(self):
        self.assertIsInstance(self.results, dict)
        for key, value in self.results.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, LiftResult)

    def test_contains_structural_flags(self):
        for flag in ("headline_has_numbers", "body_has_numbers", "body_has_emoji",
                      "body_over_50", "has_punctuation"):
            self.assertIn(flag, self.results)

    def test_contains_categorical_values(self):
        self.assertIn("media_type=image", self.results)
        self.assertIn("media_type=video", self.results)
        self.assertIn("aspect_ratio=4:5", self.results)

    def test_contains_label_types(self):
        for lt in ("Image", "Video", "Noun", "Verb", "Phrase"):
            self.assertIn(f"label_type={lt}", self.results)

    def test_contains_top_n_labels(self):
        label_keys = [k for k in self.results if k.startswith("label=")]
        self.assertGreater(len(label_keys), 0)
        self.assertLessEqual(len(label_keys), 10)

    def test_ground_truth_structural_directions(self):
        self.assertGreater(self.results["headline_has_numbers"].lift, 0)
        self.assertGreater(self.results["body_has_emoji"].lift, 0)
        self.assertLess(self.results["body_over_50"].lift, 0)

    def test_ground_truth_media_directions(self):
        self.assertGreater(self.results["media_type=image"].lift, 0)
        self.assertLess(self.results["media_type=video"].lift, 0)


if __name__ == "__main__":
    unittest.main()
