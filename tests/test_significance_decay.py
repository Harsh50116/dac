"""Tests for Phase 3 significance and durability tagging."""

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from dashboard.data import load_dataset
from dashboard.significance_decay import (
    MIN_QUARTERS,
    DurabilityResult,
    SignificanceResult,
    durability_for_mask,
    quarterly_lifts,
    significance_for_mask,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE_ONE_DATA = (
    PROJECT_ROOT / "data" / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"
)


def _roas_frame(present_values, absent_values):
    """Tiny per-ad frame with controllable per-ad ROAS (revenue/spend)."""
    rows = []
    for v in present_values:
        rows.append({"spend": 1.0, "revenue": float(v), "present": True})
    for v in absent_values:
        rows.append({"spend": 1.0, "revenue": float(v), "present": False})
    df = pd.DataFrame(rows).reset_index(drop=True)
    return df, df["present"]


def _quarter_frame(quarters):
    """Per-ad frame across quarters with controllable present/absent ROAS.

    quarters: list of (quarter_start_date, present_revenue, absent_revenue).
    Each quarter gets 30 present + 30 absent ads, spend=1.0 throughout.
    Small per-ad jitter is added so Welch's never sees zero variance.
    """
    rng = np.random.default_rng(0)
    rows = []
    ad_id = 0
    for date, present_rev, absent_rev in quarters:
        for _ in range(30):
            ad_id += 1
            rows.append({
                "ad_id": f"ad{ad_id}",
                "date": pd.Timestamp(date),
                "spend": 1.0,
                "revenue": float(present_rev) + float(rng.normal(0, 0.01)),
                "present": True,
            })
        for _ in range(30):
            ad_id += 1
            rows.append({
                "ad_id": f"ad{ad_id}",
                "date": pd.Timestamp(date),
                "spend": 1.0,
                "revenue": float(absent_rev) + float(rng.normal(0, 0.01)),
                "present": False,
            })
    df = pd.DataFrame(rows).reset_index(drop=True)
    return df, df["present"]


class SignificanceSyntheticTests(unittest.TestCase):
    def test_different_means_are_significant(self):
        rng = np.random.default_rng(42)
        df, mask = _roas_frame(
            rng.normal(2.0, 0.1, 50).tolist(),
            rng.normal(1.0, 0.1, 50).tolist(),
        )
        result = significance_for_mask(df, mask, "ROAS")
        self.assertIsInstance(result, SignificanceResult)
        self.assertTrue(result.significant)
        self.assertLess(result.p_value, 0.05)
        self.assertEqual(result.n_present, 50)
        self.assertEqual(result.n_absent, 50)

    def test_same_distribution_not_significant(self):
        rng = np.random.default_rng(7)
        df, mask = _roas_frame(
            rng.normal(1.0, 0.5, 100).tolist(),
            rng.normal(1.0, 0.5, 100).tolist(),
        )
        result = significance_for_mask(df, mask, "ROAS")
        self.assertFalse(result.significant)
        self.assertGreaterEqual(result.p_value, 0.05)

    def test_too_small_returns_nan(self):
        df, mask = _roas_frame([2.0], [1.0])
        result = significance_for_mask(df, mask, "ROAS")
        self.assertFalse(result.significant)
        self.assertTrue(np.isnan(result.p_value))
        self.assertTrue(np.isnan(result.t_statistic))


class SignificanceRealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)

    def test_image_media_type_is_significant(self):
        mask = self.data["media_type"].eq("image")
        result = significance_for_mask(self.data, mask, "ROAS")
        self.assertTrue(result.significant)
        self.assertLess(result.p_value, 0.05)

    def test_headline_numbers_significant(self):
        mask = self.data["headline_has_numbers"].astype(bool)
        result = significance_for_mask(self.data, mask, "ROAS")
        self.assertTrue(result.significant)


class QuarterlyLiftsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)

    def test_columns_and_period_type(self):
        mask = self.data["media_type"].eq("image")
        table = quarterly_lifts(self.data, mask, "ROAS")
        self.assertEqual(list(table.columns), ["period", "lift", "n_present"])
        self.assertGreater(len(table), 0)
        self.assertIsInstance(table["period"].iloc[0], pd.Period)

    def test_n_present_sums_to_mask_total(self):
        mask = self.data["media_type"].eq("image")
        table = quarterly_lifts(self.data, mask, "ROAS")
        self.assertEqual(int(table["n_present"].sum()), int(mask.sum()))


class DurabilitySyntheticTests(unittest.TestCase):
    def test_insufficient_data_under_min_quarters(self):
        df, mask = _quarter_frame([
            ("2024-01-01", 2.0, 1.0),
            ("2024-04-01", 1.5, 1.0),
            ("2024-07-01", 1.2, 1.0),
        ])
        result = durability_for_mask(df, mask, "ROAS")
        self.assertIsInstance(result, DurabilityResult)
        self.assertEqual(result.tag, "insufficient_data")
        self.assertEqual(result.quarters_observed, 3)
        self.assertIsNone(result.decay_ratio)

    def test_ephemeral_when_decay_large(self):
        # Per-quarter ROAS lifts: 100%, 80%, 50%, 20%
        # peak=100% (Q1), latest=20% (Q4), decay=(100-20)/100=0.80 → ephemeral
        df, mask = _quarter_frame([
            ("2024-01-01", 2.0, 1.0),
            ("2024-04-01", 1.8, 1.0),
            ("2024-07-01", 1.5, 1.0),
            ("2024-10-01", 1.2, 1.0),
        ])
        result = durability_for_mask(df, mask, "ROAS")
        self.assertEqual(result.tag, "ephemeral")
        self.assertEqual(result.quarters_observed, 4)
        self.assertAlmostEqual(result.peak_lift, 100.0, delta=2)
        self.assertAlmostEqual(result.latest_lift, 20.0, delta=2)
        self.assertAlmostEqual(result.decay_ratio, 0.80, delta=0.02)

    def test_durable_when_decay_small(self):
        # Per-quarter ROAS lifts ~50%, 45%, 48%, 42%
        # peak=50% (Q1), latest=42% (Q4), decay=(50-42)/50=0.16 → durable
        df, mask = _quarter_frame([
            ("2024-01-01", 1.50, 1.0),
            ("2024-04-01", 1.45, 1.0),
            ("2024-07-01", 1.48, 1.0),
            ("2024-10-01", 1.42, 1.0),
        ])
        result = durability_for_mask(df, mask, "ROAS")
        self.assertEqual(result.tag, "durable")
        self.assertEqual(result.quarters_observed, 4)
        self.assertLess(result.decay_ratio, 0.40)


    def test_direction_reversal_is_ephemeral(self):
        # Lift flips from ~+50% to ~-50%: same magnitude but opposite sign
        df, mask = _quarter_frame([
            ("2024-01-01", 1.50, 1.0),
            ("2024-04-01", 1.40, 1.0),
            ("2024-07-01", 0.80, 1.0),
            ("2024-10-01", 0.50, 1.0),
        ])
        result = durability_for_mask(df, mask, "ROAS")
        self.assertEqual(result.tag, "ephemeral")

    def test_fading_drain_is_ephemeral(self):
        # Negative lifts that fade: -50%, -40%, -30%, -10%
        # peak_abs=50% (Q1), latest_abs=10% (Q4), decay=(50-10)/50=0.80
        df, mask = _quarter_frame([
            ("2024-01-01", 0.5, 1.0),
            ("2024-04-01", 0.6, 1.0),
            ("2024-07-01", 0.7, 1.0),
            ("2024-10-01", 0.9, 1.0),
        ])
        result = durability_for_mask(df, mask, "ROAS")
        self.assertEqual(result.tag, "ephemeral")
        self.assertGreater(result.decay_ratio, 0.40)

    def test_persistent_drain_is_durable(self):
        # Negative lifts that persist: ~-50% throughout
        df, mask = _quarter_frame([
            ("2024-01-01", 0.50, 1.0),
            ("2024-04-01", 0.48, 1.0),
            ("2024-07-01", 0.52, 1.0),
            ("2024-10-01", 0.50, 1.0),
        ])
        result = durability_for_mask(df, mask, "ROAS")
        self.assertEqual(result.tag, "durable")
        self.assertLess(result.decay_ratio, 0.40)


class DurabilityRealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)

    def test_image_media_type_is_durable(self):
        mask = self.data["media_type"].eq("image")
        result = durability_for_mask(self.data, mask, "ROAS")
        self.assertGreaterEqual(result.quarters_observed, MIN_QUARTERS)
        self.assertEqual(result.tag, "durable")

    def test_headline_numbers_is_durable(self):
        mask = self.data["headline_has_numbers"].astype(bool)
        result = durability_for_mask(self.data, mask, "ROAS")
        self.assertGreaterEqual(result.quarters_observed, MIN_QUARTERS)
        self.assertEqual(result.tag, "durable")


if __name__ == "__main__":
    unittest.main()
