"""Tests for dashboard theme configuration."""

import unittest
from pathlib import Path

from dashboard.styles import APP_CSS


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StyleTests(unittest.TestCase):
    def test_css_contains_dashboard_tokens_and_responsive_rules(self):
        self.assertIn("--dac-bg: #0d0f13", APP_CSS)
        self.assertIn('[data-testid="stMetric"]', APP_CSS)
        self.assertIn("@media (max-width: 700px)", APP_CSS)

    def test_streamlit_theme_configuration_exists(self):
        config = (PROJECT_ROOT / ".streamlit" / "config.toml").read_text()

        self.assertIn('base = "dark"', config)
        self.assertIn('primaryColor = "#5B8CFF"', config)
        self.assertIn("maxUploadSize = 200", config)


if __name__ == "__main__":
    unittest.main()
