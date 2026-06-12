"""Tests for Phase 3 recommendation engine."""

import unittest
from pathlib import Path

from dashboard.data import load_dataset
from dashboard.analytics.recommend import Recommendation, generate_recommendations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE_ONE_DATA = (
    PROJECT_ROOT / "data" / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"
)


class RecommendationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = generate_recommendations(
            load_dataset(PHASE_ONE_DATA), "ROAS",
        )

    def test_returns_list_of_recommendations(self):
        self.assertIsInstance(self.recs, list)
        self.assertGreater(len(self.recs), 0)
        for rec in self.recs:
            self.assertIsInstance(rec, Recommendation)

    def test_all_are_significant_and_durable(self):
        for rec in self.recs:
            self.assertLess(rec.p_value, 0.05)
            self.assertEqual(rec.durability_tag, "durable")

    def test_do_more_has_positive_lift(self):
        do_more = [r for r in self.recs if r.action == "do_more"]
        self.assertGreater(len(do_more), 0)
        for rec in do_more:
            self.assertGreater(rec.lift, 0)

    def test_avoid_has_negative_lift(self):
        avoid = [r for r in self.recs if r.action == "avoid"]
        self.assertGreater(len(avoid), 0)
        for rec in avoid:
            self.assertLess(rec.lift, 0)

    def test_known_driver_image_present(self):
        do_more_keys = {r.key for r in self.recs if r.action == "do_more"}
        self.assertIn("media_type=image", do_more_keys)

    def test_known_drain_video_present(self):
        avoid_keys = {r.key for r in self.recs if r.action == "avoid"}
        self.assertIn("media_type=video", avoid_keys)

    def test_no_guarantee_language(self):
        guarantee_words = {"guarantee", "guaranteed", "will always", "ensures"}
        for rec in self.recs:
            lower = rec.hypothesis.lower()
            for word in guarantee_words:
                self.assertNotIn(word, lower)

    def test_every_recommendation_has_evidence(self):
        for rec in self.recs:
            self.assertIn("Lift:", rec.evidence)
            self.assertIn("p-value:", rec.evidence)
            self.assertIn("Durability:", rec.evidence)

    def test_hypothesis_contains_test_language(self):
        for rec in self.recs:
            self.assertIn("Test", rec.hypothesis)

    def test_sorted_by_abs_lift_descending(self):
        lifts = [abs(r.lift) for r in self.recs]
        self.assertEqual(lifts, sorted(lifts, reverse=True))


if __name__ == "__main__":
    unittest.main()
