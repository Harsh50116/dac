"""Tests for Plotly Overview chart construction."""

import unittest
from pathlib import Path

from dashboard.analytics.core import (
    binary_lift_table,
    categorical_lift_table,
    label_table,
    label_performance_over_time,
    monthly_performance,
    rolling_label_lift,
)
from dashboard.ui.charts import (
    circular_lift_chart,
    label_performance_chart,
    lift_bar_chart,
    rolling_lift_chart,
    volume_performance_chart,
    word_cloud_chart,
)
from dashboard.data import load_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE_ONE_DATA = (
    PROJECT_ROOT
    / "data"
    / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"
)


class OverviewChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)

    def test_volume_chart_has_bar_and_roas_line(self):
        figure = volume_performance_chart(
            monthly_performance(self.data),
            "Ads",
            3,
        )

        self.assertEqual(len(figure.data), 2)
        self.assertEqual(figure.data[0].type, "bar")
        self.assertEqual(figure.data[1].type, "scatter")
        self.assertEqual(len(figure.data[0].x), 25)

    def test_rolling_lift_chart_has_one_trace_per_label(self):
        series = {
            token: rolling_label_lift(
                self.data,
                token,
                "ROAS",
                label_types=("Phrase",),
            )
            for token in ("adventure awaits", "new arrivals")
        }
        figure = rolling_lift_chart(series)

        self.assertEqual(len(figure.data), 2)
        self.assertEqual(
            {trace.name for trace in figure.data},
            {"adventure awaits", "new arrivals"},
        )

    def test_label_performance_chart_has_volume_and_lift(self):
        data = label_performance_over_time(
            self.data,
            ("adventure awaits",),
            "ROAS",
            label_types=("Phrase",),
        )
        figure = label_performance_chart(data)

        self.assertEqual(len(figure.data), 2)
        self.assertEqual(figure.data[0].name, "# of Ads (present)")
        self.assertEqual(figure.data[1].name, "Label Lift (%)")

    def test_details_chart_builders(self):
        aspect = categorical_lift_table(
            self.data,
            "aspect_ratio",
            "ROAS",
        )
        binary = binary_lift_table(
            self.data,
            "headline_has_numbers",
            "ROAS",
        )
        labels = label_table(self.data, "ROAS", min_ads=8).head(20)

        self.assertEqual(lift_bar_chart(aspect, "value").data[0].type, "bar")
        self.assertEqual(lift_bar_chart(binary, "value").data[0].type, "bar")
        self.assertEqual(circular_lift_chart(labels).data[0].type, "barpolar")
        self.assertEqual(word_cloud_chart(labels).data[0].mode, "text")


if __name__ == "__main__":
    unittest.main()
