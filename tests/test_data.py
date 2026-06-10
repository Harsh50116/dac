"""Tests for dashboard dataset ingestion and normalization."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from dashboard.data import (
    DataValidationError,
    calendar_months,
    load_dataset,
    normalize_dataset,
    parse_labels,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE_ONE_DATA = (
    PROJECT_ROOT
    / "data"
    / "ads-monthly_v1_2026-06-06_2023-01_2025-01.csv"
)


class DataLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_dataset(PHASE_ONE_DATA)

    def test_phase_one_dataset_contract(self):
        self.assertEqual(len(self.data), 2650)
        self.assertEqual(self.data["ad_id"].nunique(), 2650)
        self.assertFalse(self.data.isna().any().any())
        self.assertEqual(self.data["date"].min(), pd.Timestamp("2023-01-01"))
        self.assertEqual(self.data["date"].max(), pd.Timestamp("2025-01-01"))

    def test_complete_calendar_preserves_empty_months(self):
        months = calendar_months(self.data)
        observed = set(self.data["date"])
        empty = [month for month in months if month not in observed]

        self.assertEqual(len(months), 25)
        self.assertEqual(
            empty,
            [
                pd.Timestamp("2023-02-01"),
                pd.Timestamp("2023-09-01"),
                pd.Timestamp("2024-02-01"),
                pd.Timestamp("2024-09-01"),
                pd.Timestamp("2024-10-01"),
            ],
        )

    def test_labels_and_copy_flags_are_derived(self):
        first = self.data.iloc[0]

        self.assertEqual(
            first["label_pairs"],
            (("img_cap", "Image"), ("cap", "Noun"), ("train", "Verb")),
        )
        self.assertEqual(first["label_tokens"], ("img_cap", "cap", "train"))
        self.assertEqual(first["label_types"], ("Image", "Noun", "Verb"))
        self.assertTrue(first["headline_has_numbers"])
        self.assertTrue(first["body_has_numbers"])
        self.assertFalse(first["has_punctuation"])

    def test_csv_parquet_and_excel_are_supported(self):
        sample = pd.read_csv(PHASE_ONE_DATA, nrows=150)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [
                root / "sample.csv",
                root / "sample.parquet",
                root / "sample.xlsx",
            ]
            sample.to_csv(paths[0], index=False)
            sample.to_parquet(paths[1], index=False)
            sample.to_excel(paths[2], index=False)

            for path in paths:
                with self.subTest(path=path.suffix):
                    self.assertEqual(len(load_dataset(path)), 150)


class DataValidationTests(unittest.TestCase):
    def test_missing_column_is_rejected(self):
        with self.assertRaisesRegex(
            DataValidationError, "Missing required columns: labels"
        ):
            normalize_dataset(pd.DataFrame(columns=REQUIRED_WITHOUT_LABELS))

    def test_malformed_label_is_rejected(self):
        with self.assertRaisesRegex(DataValidationError, "Malformed label"):
            parse_labels("missing_type")

    def test_unsupported_file_type_is_rejected(self):
        with self.assertRaisesRegex(DataValidationError, "Unsupported file type"):
            load_dataset(Path("dataset.json"))


REQUIRED_WITHOUT_LABELS = [
    "ad_id",
    "date",
    "spend",
    "revenue",
    "impressions",
    "clicks",
    "purchases",
    "headline",
    "body",
    "media_type",
    "aspect_ratio",
    "category",
]


if __name__ == "__main__":
    unittest.main()
