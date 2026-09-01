"""Small deterministic tests for the isolated category experiment helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).with_name("train_category_poc.py")
SPEC = importlib.util.spec_from_file_location("train_category_poc", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CategoryExperimentHelperTests(unittest.TestCase):
    def test_utf7_header_decode(self) -> None:
        self.assertEqual(
            MODULE.decode_utf7_header("android.permission.ACCESS+AF8-FINE+AF8-LOCATION"),
            "android.permission.ACCESS_FINE_LOCATION",
        )

    def test_permission_header_matching_is_case_insensitive(self) -> None:
        match = MODULE.PERMISSION_HEADER_RE.fullmatch(
            "Android.permission.access_fine_location"
        )
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group(1).upper(), "ACCESS_FINE_LOCATION")

    def test_presence_parser_handles_numeric_boolean_and_blank(self) -> None:
        present, invalid = MODULE.parse_presence_column(
            pd.Series(["", "0", "1", "2.0", "True", "False", None])
        )
        self.assertEqual(invalid, 0)
        self.assertEqual(
            present.tolist(), [False, False, True, True, True, False, False]
        )

    def test_stable_downsample_is_repeatable_and_unique(self) -> None:
        positions = np.arange(20, dtype=np.int64)
        rows = np.arange(100, 120, dtype=np.int64)
        first = MODULE.stable_downsample(positions, rows, 7, "unit-test")
        second = MODULE.stable_downsample(positions, rows, 7, "unit-test")
        self.assertTrue(np.array_equal(first, second))
        self.assertEqual(len(first), 7)
        self.assertEqual(len(set(first.tolist())), 7)

    def test_group_capped_downsample_round_robins_and_caps(self) -> None:
        positions = np.arange(30, dtype=np.int64)
        rows = np.arange(100, 130, dtype=np.int64)
        groups = np.asarray(["large"] * 20 + [f"small-{i}" for i in range(10)])
        chosen = MODULE.stable_group_capped_downsample(
            positions,
            rows,
            groups,
            quota=12,
            salt="group-cap-test",
            max_rows_per_group=3,
        )
        selected_counts = pd.Series(groups[chosen]).value_counts()
        self.assertEqual(len(chosen), 12)
        self.assertLessEqual(int(selected_counts.max()), 3)

    def test_class_count_order_is_fixed(self) -> None:
        labels = np.asarray([4, 1, 3, 2, 4, 1], dtype=np.int8)
        self.assertEqual(list(MODULE.class_counts(labels)), MODULE.MODEL_CLASS_NAMES)


if __name__ == "__main__":
    unittest.main()
