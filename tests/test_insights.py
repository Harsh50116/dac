"""Tests for Phase 2 surface-level insight extraction."""

import unittest
from pathlib import Path

from dashboard.data import load_dataset
from dashboard.insights import (
    Insight,
    _build_statement,
    _confidence,
    _phrase_for_key,
    generate_insights,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE_ONE_DATA = (
    PROJECT_ROOT
    / "data"
    / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"
)


class ConfidenceTests(unittest.TestCase):
    def test_high_threshold(self):
        self.assertEqual(_confidence(200), "high")
        self.assertEqual(_confidence(500), "high")

    def test_medium_threshold(self):
        self.assertEqual(_confidence(50), "medium")
        self.assertEqual(_confidence(199), "medium")

    def test_low_threshold(self):
        self.assertEqual(_confidence(49), "low")
        self.assertEqual(_confidence(1), "low")


class PhraseTests(unittest.TestCase):
    def test_structural_flags(self):
        self.assertEqual(_phrase_for_key("headline_has_numbers"), "Headlines with numbers")
        self.assertEqual(_phrase_for_key("body_over_50"), "Long body copy (>50 chars)")

    def test_categorical(self):
        self.assertEqual(_phrase_for_key("media_type=image"), "Image creative")
        self.assertEqual(_phrase_for_key("aspect_ratio=4:5"), "4:5 aspect ratio")

    def test_label_types(self):
        self.assertEqual(_phrase_for_key("label_type=Noun"), "Noun-type labels")

    def test_label_tokens(self):
        self.assertEqual(_phrase_for_key("label=kit|Noun"), "The word 'kit'")
        self.assertEqual(
            _phrase_for_key("label=adventure awaits|Phrase"),
            "The phrase 'adventure awaits'",
        )
        self.assertEqual(_phrase_for_key("label=img_cap|Image"), "Label 'img_cap'")


class StatementTests(unittest.TestCase):
    def test_positive_lift(self):
        result = _build_statement("Headlines with numbers", 46.0, "ROAS", 412, "high")
        self.assertEqual(result, "Headlines with numbers → +46% ROAS (n=412, high confidence)")

    def test_negative_lift_has_avoid(self):
        result = _build_statement("Long body copy (>50 chars)", -32.0, "ROAS", 622, "high")
        self.assertIn("-32%", result)
        self.assertIn("avoid", result)

    def test_kpi_is_uppercased(self):
        result = _build_statement("Test", 10.0, "ctr", 100, "medium")
        self.assertIn("CTR", result)


class GenerateInsightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)
        cls.insights = generate_insights(cls.data, "ROAS", top_n_labels=10)

    def test_returns_list_of_insights(self):
        self.assertIsInstance(self.insights, list)
        for insight in self.insights:
            self.assertIsInstance(insight, Insight)

    def test_no_nan_lifts(self):
        for insight in self.insights:
            self.assertFalse(
                insight.lift != insight.lift,
                f"NaN lift for {insight.key}",
            )

    def test_sorted_by_score_descending(self):
        scores = [i.score for i in self.insights]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_ground_truth_drivers_rank_above_drains(self):
        drivers = [i for i in self.insights if i.lift > 0]
        drains = [i for i in self.insights if i.lift < 0]
        self.assertGreater(len(drivers), 0)
        self.assertGreater(len(drains), 0)

    def test_known_strong_signals_in_top_drivers(self):
        drivers = [i for i in self.insights if i.lift > 0]
        top_keys = {i.key for i in drivers[:6]}
        self.assertIn("headline_has_numbers", top_keys)
        self.assertIn("media_type=image", top_keys)

    def test_known_drains_present(self):
        drain_keys = {i.key for i in self.insights if i.lift < 0}
        self.assertIn("media_type=video", drain_keys)
        self.assertIn("body_over_50", drain_keys)

    def test_all_insights_have_positive_scores(self):
        for insight in self.insights:
            self.assertGreater(insight.score, 0)

    def test_respects_kpi_switch(self):
        ctr_insights = generate_insights(self.data, "CTR", top_n_labels=5)
        self.assertGreater(len(ctr_insights), 0)
        for insight in ctr_insights:
            self.assertIn("CTR", insight.statement)

    def test_punctuation_excluded_when_absent(self):
        keys = {i.key for i in self.insights}
        self.assertNotIn("has_punctuation", keys)


if __name__ == "__main__":
    unittest.main()
