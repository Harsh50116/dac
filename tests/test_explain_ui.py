"""AppTest coverage for Explain panel wiring. LLM calls are mocked."""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from dashboard.llm.client import LLMResponse


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def loaded_app(page: str) -> AppTest:
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    app.button[0].click().run()
    app.radio(key="sidebar_page").set_value(page).run()
    return app


class ExplainButtonTests(unittest.TestCase):
    def test_recommendations_page_has_explain_buttons(self):
        app = loaded_app("Recommendations")
        self.assertEqual(len(app.exception), 0)
        keys = {button.key for button in app.button}
        self.assertIn("explain_recs_page", keys)
        self.assertIn("explain_rec_1", keys)

    def test_insights_page_has_section_explain_buttons(self):
        app = loaded_app("Insights")
        self.assertEqual(len(app.exception), 0)
        keys = {button.key for button in app.button}
        self.assertIn("explain_insights_page", keys)
        self.assertIn("explain_sec_format", keys)


class ExplainConversationTests(unittest.TestCase):
    def test_clicking_explain_seeds_grounded_conversation(self):
        app = loaded_app("Recommendations")
        with patch(
            "dashboard.llm.explain_panel.ask",
            return_value=LLMResponse(text="Image creative leads here.", ok=True),
        ):
            app.button(key="explain_rec_1").click().run()
        self.assertEqual(len(app.exception), 0)
        messages = app.session_state["explain_messages"]
        self.assertTrue(messages[0].get("seed"))
        self.assertEqual(messages[-1]["role"], "assistant")
        self.assertEqual(messages[-1]["content"], "Image creative leads here.")
        self.assertNotIn("caveat", messages[-1])

    def test_unverified_numbers_are_flagged(self):
        app = loaded_app("Recommendations")
        with patch(
            "dashboard.llm.explain_panel.ask",
            return_value=LLMResponse(text="Expect a 9,999% lift.", ok=True),
        ):
            app.button(key="explain_rec_1").click().run()
        self.assertEqual(len(app.exception), 0)
        messages = app.session_state["explain_messages"]
        self.assertIn("9,999", messages[-1]["caveat"])

    def test_failed_seed_is_not_persisted_and_reopen_retries(self):
        app = loaded_app("Recommendations")
        from dashboard.llm.client import FALLBACK_TEXT

        with patch(
            "dashboard.llm.explain_panel.ask",
            return_value=LLMResponse(text=FALLBACK_TEXT, ok=False),
        ):
            app.button(key="explain_recs_page").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state["explain_messages"], [])

        with patch(
            "dashboard.llm.explain_panel.ask",
            return_value=LLMResponse(text="Now it works.", ok=True),
        ):
            app.button(key="explain_recs_page").click().run()
        self.assertEqual(len(app.exception), 0)
        messages = app.session_state["explain_messages"]
        self.assertEqual(messages[-1]["content"], "Now it works.")


if __name__ == "__main__":
    unittest.main()
