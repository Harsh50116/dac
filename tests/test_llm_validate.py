"""Tests for numeric-claim validation of Explain answers."""

import unittest

from dashboard.llm.validate import unverified_numbers


CONTEXT = {
    "kpi": "ROAS",
    "ads_in_view": 2650,
    "items": [
        {
            "id": "rec_pair_a__b",
            "title": "Shift portrait spend into Image + 4:5",
            "combined_lift_pct": 112.4,
            "synergy_pct": 39.0,
            "headroom_pct": 88.0,
            "n_both": 310,
        },
    ],
}


class UnverifiedNumbersTests(unittest.TestCase):
    def test_grounded_exact_and_rounded_numbers_pass(self):
        answer = "The pairing lifted ROAS by +112.4% — roughly 112% — with 88% headroom."
        self.assertEqual(unverified_numbers(answer, CONTEXT), [])

    def test_comma_formatted_count_passes(self):
        answer = "Based on 2,650 ads in view and n=310 running both."
        self.assertEqual(unverified_numbers(answer, CONTEXT), [])

    def test_numbers_inside_context_strings_pass(self):
        answer = "The 4:5 ratio works with image creative."
        self.assertEqual(unverified_numbers(answer, CONTEXT), [])

    def test_invented_number_is_flagged(self):
        answer = "This should lift ROAS by 250% next quarter."
        self.assertEqual(unverified_numbers(answer, CONTEXT), ["250"])

    def test_small_integers_are_ignored(self):
        answer = "There are 3 moves; the top 2 matter most."
        self.assertEqual(unverified_numbers(answer, CONTEXT), [])

    def test_flagged_tokens_are_deduplicated(self):
        answer = "Expect 250% now and 250% later, plus an invented 77."
        self.assertEqual(unverified_numbers(answer, CONTEXT), ["250", "77"])

    def test_answer_without_numbers_passes(self):
        self.assertEqual(unverified_numbers("No figures here.", CONTEXT), [])


if __name__ == "__main__":
    unittest.main()
