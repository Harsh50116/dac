"""Streamlit interaction tests for upload state and global controls."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class AppStateTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(APP_PATH).run()

    def test_app_starts_in_upload_state(self):
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(
            self.app.title[0].value,
            "Ads Creative Component Performance",
        )
        self.assertEqual(
            self.app.button[0].label,
            "Load sample creative dataset",
        )

    def test_sample_data_loads_global_controls(self):
        self.app.button[0].click().run()

        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(
            any(
                "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv" in c.value
                for c in self.app.caption
            )
        )
        self.assertEqual(self.app.radio(key="sidebar_page").value, "Overview")
        self.assertEqual(self.app.radio(key="filter_kpi").value, "ROAS")
        self.assertEqual(self.app.number_input[0].value, 30)
        self.assertGreaterEqual(len(self.app.multiselect), 2)
        self.assertTrue(
            any("2,650 of 2,650 ads in view" in c.value for c in self.app.caption)
        )
        self.assertEqual(len(self.app.metric), 7)
        self.assertEqual(self.app.metric[0].value, "2,650")
        self.assertGreaterEqual(len(self.app.get("plotly_chart")), 3)

    def test_global_filters_update_ads_in_view(self):
        self.app.button[0].click().run()
        self.app.multiselect[0].set_value(["mountain"]).run()
        self.app.multiselect[1].set_value(["image"]).run()
        self.app.radio(key="filter_kpi").set_value("CTR").run()
        self.app.number_input[0].set_value(20).run()

        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(self.app.radio(key="filter_kpi").value, "CTR")
        self.assertEqual(self.app.number_input[0].value, 20)
        view_caption = next(
            caption.value
            for caption in self.app.caption
            if "ads in view" in caption.value
        )
        self.assertIn("of 2,650 ads in view", view_caption)
        self.assertNotIn("2,650 of 2,650", view_caption)

    def test_unload_returns_to_upload_state(self):
        self.app.button[0].click().run()
        unload = next(
            button
            for button in self.app.button
            if button.label == "Unload dataset"
        )
        unload.click().run()

        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.app.radio), 0)
        self.assertEqual(
            self.app.button[0].label,
            "Load sample creative dataset",
        )


if __name__ == "__main__":
    unittest.main()
