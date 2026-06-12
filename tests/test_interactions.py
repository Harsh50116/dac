"""Tests for Phase 3 pairwise attribute interactions."""

import unittest
from pathlib import Path

import pandas as pd

from dashboard.data import load_dataset
from dashboard.analytics.interactions import (
    DEFAULT_MIN_N,
    Interaction,
    attribute_mask,
    find_interactions,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE_ONE_DATA = (
    PROJECT_ROOT
    / "data"
    / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"
)


class AttributeMaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)

    def test_structural_flag(self):
        mask = attribute_mask(self.data, "headline_has_numbers")
        self.assertEqual(mask.dtype, bool)
        self.assertEqual(
            int(mask.sum()),
            int(self.data["headline_has_numbers"].astype(bool).sum()),
        )

    def test_categorical_media_type(self):
        mask = attribute_mask(self.data, "media_type=image")
        self.assertEqual(int(mask.sum()), int(self.data["media_type"].eq("image").sum()))

    def test_categorical_aspect_ratio(self):
        mask = attribute_mask(self.data, "aspect_ratio=1:1")
        self.assertEqual(int(mask.sum()), int(self.data["aspect_ratio"].eq("1:1").sum()))

    def test_label_type(self):
        mask = attribute_mask(self.data, "label_type=Noun")
        expected = self.data["label_types"].map(lambda t: "Noun" in t).sum()
        self.assertEqual(int(mask.sum()), int(expected))

    def test_label_token(self):
        first_pair = next(iter(self.data["label_pairs"].iloc[0]))
        token, label_type = first_pair
        mask = attribute_mask(self.data, f"label={token}|{label_type}")
        expected = self.data["label_pairs"].map(
            lambda pairs: (token, label_type) in pairs,
        ).sum()
        self.assertGreater(int(mask.sum()), 0)
        self.assertEqual(int(mask.sum()), int(expected))

    def test_missing_structural_flag_returns_all_false(self):
        mask = attribute_mask(self.data, "nonexistent_flag")
        self.assertFalse(mask.any())
        self.assertEqual(len(mask), len(self.data))

    def test_missing_categorical_column_returns_all_false(self):
        mask = attribute_mask(self.data, "nonexistent_col=foo")
        self.assertFalse(mask.any())


class FindInteractionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)
        cls.interactions = find_interactions(cls.data, "ROAS", top_n_labels=10)

    def test_returns_non_empty_list_of_interaction(self):
        self.assertIsInstance(self.interactions, list)
        self.assertGreater(len(self.interactions), 0)
        for item in self.interactions:
            self.assertIsInstance(item, Interaction)

    def test_n_both_meets_min(self):
        for item in self.interactions:
            self.assertGreaterEqual(item.n_both, DEFAULT_MIN_N)

    def test_no_nan_metrics(self):
        for item in self.interactions:
            self.assertFalse(pd.isna(item.combined_lift))
            self.assertFalse(pd.isna(item.synergy_score))
            for lift in item.individual_lifts:
                self.assertFalse(pd.isna(lift))

    def test_sorted_by_abs_synergy_desc(self):
        scores = [abs(i.synergy_score) for i in self.interactions]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_pair_attributes_distinct(self):
        for item in self.interactions:
            a, b = item.attributes
            self.assertNotEqual(a, b)

    def test_synergy_differs_from_naive_subtraction(self):
        # Four-cell interaction term is NOT combined_lift - (lift_a + lift_b).
        # At least one pair should show a meaningful difference.
        diffs = []
        for item in self.interactions[:10]:
            naive = item.combined_lift - sum(item.individual_lifts)
            diffs.append(abs(item.synergy_score - naive))
        self.assertTrue(
            any(d > 0.01 for d in diffs),
            "four-cell synergy should differ from naive subtraction",
        )

    def test_mutually_exclusive_pairs_pruned(self):
        # media_type=image and media_type=video can never co-occur → never
        # appear together as a pair (n_both = 0, pruned by min_n).
        for item in self.interactions:
            pair = set(item.attributes)
            self.assertNotEqual(
                pair, {"media_type=image", "media_type=video"},
            )

    def test_image_plus_headline_numbers_positive_synergy(self):
        target = {"media_type=image", "headline_has_numbers"}
        match = next(
            (i for i in self.interactions if set(i.attributes) == target),
            None,
        )
        self.assertIsNotNone(
            match,
            "(media_type=image, headline_has_numbers) should appear in interactions",
        )
        self.assertGreater(match.n_both, DEFAULT_MIN_N)
        self.assertGreater(match.synergy_score, 0)

    def test_kpi_switch_changes_metrics(self):
        ctr = find_interactions(self.data, "CTR", top_n_labels=10)
        self.assertGreater(len(ctr), 0)
        roas_by_pair = {
            tuple(sorted(i.attributes)): i.combined_lift
            for i in self.interactions
        }
        ctr_by_pair = {
            tuple(sorted(i.attributes)): i.combined_lift for i in ctr
        }
        common = set(roas_by_pair) & set(ctr_by_pair)
        self.assertTrue(common, "expected at least one pair common to ROAS and CTR")
        differing = [
            pair for pair in common
            if roas_by_pair[pair] != ctr_by_pair[pair]
        ]
        self.assertTrue(
            differing,
            "expected combined lift to differ between ROAS and CTR for some pair",
        )

    def test_min_n_tightening_shrinks_results(self):
        loose = find_interactions(self.data, "ROAS", min_n=10, top_n_labels=5)
        strict = find_interactions(self.data, "ROAS", min_n=500, top_n_labels=5)
        self.assertGreaterEqual(len(loose), len(strict))
        for item in strict:
            self.assertGreaterEqual(item.n_both, 500)


if __name__ == "__main__":
    unittest.main()
