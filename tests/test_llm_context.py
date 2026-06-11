"""Tests for LLM grounding context assembly."""

import json
import unittest

from dashboard.insights import Insight
from dashboard.llm_context import (
    build_context,
    context_fingerprint,
    insight_id,
    insight_item,
    pair_rec_id,
    pair_rec_item,
)
from dashboard.recommend import PairRecommendation


def make_insight(key="media_type=image", lift=42.0, n=900, confidence="high"):
    return Insight(
        key=key,
        phrase="Image creative",
        lift=lift,
        n=n,
        confidence=confidence,
        score=100.0,
        statement="Image creative → +42% ROAS",
    )


def make_pair_rec():
    return PairRecommendation(
        attributes=("media_type=image", "aspect_ratio=4:5"),
        phrases=("Image creative", "4:5 aspect ratio"),
        action="do_more",
        combined_lift=112.4,
        individual_lifts=(61.0, 9.0),
        synergy_score=39.0,
        n_both=310,
        cell_lifts=(112.4, 61.0, 9.0, 0.0),
        headroom=88.0,
        title="Shift portrait spend into Image + 4:5",
        description="Image creative and the 4:5 ratio each lift ROAS.",
    )


class StableIdTests(unittest.TestCase):
    def test_insight_id_is_stable_and_sanitized(self):
        insight = make_insight(key="label=free shipping|Phrase")
        self.assertEqual(insight_id(insight), "insight_label_free_shipping_phrase")
        self.assertEqual(insight_id(insight), insight_id(make_insight(key="label=free shipping|Phrase")))

    def test_pair_rec_id_is_stable(self):
        rec = make_pair_rec()
        self.assertEqual(pair_rec_id(rec), "rec_pair_media_type_image__aspect_ratio_4_5")
        self.assertEqual(pair_rec_id(rec), pair_rec_id(make_pair_rec()))


class EvidenceMetadataTests(unittest.TestCase):
    def test_label_insights_are_marked_tested(self):
        item = insight_item(make_insight(key="label=sale|Word"), "Labels")
        self.assertTrue(item["evidence"]["statistically_tested"])
        self.assertEqual(item["evidence"]["evidence_level"], "tested")

    def test_non_label_insights_are_directional(self):
        item = insight_item(make_insight(), "Format")
        self.assertFalse(item["evidence"]["statistically_tested"])
        self.assertEqual(item["evidence"]["evidence_level"], "directional")
        self.assertFalse(item["evidence"]["durability_tested"])

    def test_pair_recs_are_exploratory_and_untested(self):
        item = pair_rec_item(make_pair_rec(), rank=1)
        evidence = item["evidence"]
        self.assertEqual(evidence["evidence_level"], "exploratory")
        self.assertFalse(evidence["statistically_tested"])
        self.assertFalse(evidence["durability_tested"])

    def test_pair_rec_numbers_match_source(self):
        rec = make_pair_rec()
        item = pair_rec_item(rec, rank=1)
        self.assertEqual(item["combined_lift_pct"], 112.4)
        self.assertEqual(item["synergy_pct"], 39.0)
        self.assertEqual(item["headroom_pct"], 88.0)
        self.assertEqual(item["n_both"], 310)
        self.assertEqual(item["quadrant_lift_pct"]["both"], 112.4)
        self.assertEqual(item["quadrant_lift_pct"]["neither"], 0.0)


class BuildContextTests(unittest.TestCase):
    def build(self, focus_id=None):
        return build_context(
            page="Recommendations",
            kpi="roas",
            dataset_name="ads_seed42.csv",
            n_ads_in_view=2650,
            n_ads_total=2650,
            filters={"period": ["2023-01", "2025-01"], "categories": []},
            insight_groups={"Format": [make_insight()]},
            pair_recs=[make_pair_rec()],
            focus_id=focus_id,
        )

    def test_contains_both_item_kinds_and_is_json_serializable(self):
        context = self.build()
        kinds = {item["kind"] for item in context["items"]}
        self.assertEqual(kinds, {"insight", "pair_recommendation"})
        json.dumps(context)

    def test_kpi_is_uppercased(self):
        self.assertEqual(self.build()["kpi"], "ROAS")

    def test_valid_focus_id_is_kept(self):
        focus = pair_rec_id(make_pair_rec())
        self.assertEqual(self.build(focus_id=focus)["focus_id"], focus)

    def test_unknown_focus_id_is_dropped(self):
        self.assertIsNone(self.build(focus_id="rec_pair_bogus")["focus_id"])

    def test_metric_definitions_cover_item_fields(self):
        context = self.build()
        definitions = context["metric_definitions"]
        for field in ("lift_pct", "combined_lift_pct", "synergy_pct",
                      "headroom_pct", "n_both", "quadrant_lift_pct"):
            self.assertIn(field, definitions)
            self.assertTrue(definitions[field])
        self.assertIn("spend", definitions["headroom_pct"])

    def test_fingerprint_ignores_focus_changes(self):
        focus = pair_rec_id(make_pair_rec())
        self.assertEqual(
            context_fingerprint(self.build()),
            context_fingerprint(self.build(focus_id=focus)),
        )

    def test_fingerprint_changes_when_data_changes(self):
        other = build_context(
            page="Recommendations",
            kpi="cpp",
            dataset_name="ads_seed42.csv",
            n_ads_in_view=2650,
            n_ads_total=2650,
            filters={"period": ["2023-01", "2025-01"], "categories": []},
            insight_groups={"Format": [make_insight()]},
            pair_recs=[make_pair_rec()],
        )
        self.assertNotEqual(
            context_fingerprint(self.build()), context_fingerprint(other),
        )


if __name__ == "__main__":
    unittest.main()
