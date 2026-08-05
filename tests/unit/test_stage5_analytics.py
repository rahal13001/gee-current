from __future__ import annotations

import unittest

import numpy as np

from python.analytics import (
    AnalyticsError,
    MINIMUM_VALID_AREA_FRACTION,
    _speed_bin_for_value,
    _speed_bin_definitions,
    _spatial_mean_vector,
    direction_sector_array,
    frame_statistics,
    resultant_direction_degrees,
    speed_array,
)


class Stage5AnalyticsTests(unittest.TestCase):
    def test_speed_preserves_joint_missing_mask(self) -> None:
        u = np.array([[3.0, np.nan], [0.0, 0.0]])
        v = np.array([[4.0, 2.0], [0.0, np.nan]])
        result = speed_array(u, v)
        self.assertEqual(float(result[0, 0]), 5.0)
        self.assertTrue(np.isnan(result[0, 1]))
        self.assertEqual(float(result[1, 0]), 0.0)
        self.assertTrue(np.isnan(result[1, 1]))

    def test_direction_sectors_wrap_north_and_zero_is_missing(self) -> None:
        u = np.array([[0.0, 1.0, 0.0, -1.0], [0.0, 0.0, 0.0, 0.0]])
        v = np.array([[1.0, 0.0, -1.0, 0.0], [0.0, 0.0, 0.0, 0.0]])
        result = direction_sector_array(u, v)
        self.assertEqual(result[0].tolist(), [0, 4, 8, 12])
        self.assertTrue(np.all(result[1] == -1))

    def test_frame_statistics_distinguishes_mean_and_resultant_speed(self) -> None:
        result = frame_statistics(
            np.array([1.0, 0.0]),
            np.array([0.0, 1.0]),
            ddof=0,
            percentile_method="linear",
        )
        self.assertEqual(result["valid_pixel_count"], 2)
        self.assertAlmostEqual(result["mean"], 1.0)
        self.assertAlmostEqual(result["resultant_speed"], 2**-0.5)
        self.assertAlmostEqual(result["persistence_index"], 2**-0.5)
        self.assertAlmostEqual(result["resultant_direction"], 45.0)
        self.assertEqual(result["dominant_direction_label"], "N")

    def test_zero_resultant_direction_is_null(self) -> None:
        self.assertIsNone(resultant_direction_degrees(0.0, 0.0))

    def test_shape_mismatch_fails_closed(self) -> None:
        with self.assertRaises(AnalyticsError):
            speed_array(np.zeros((2,)), np.zeros((1,)))

    def test_p90_equality_is_non_exceedance_and_bins_are_lower_inclusive(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0]
        threshold = 3.25
        definitions = _speed_bin_definitions(values, threshold, "linear")
        self.assertNotEqual(_speed_bin_for_value(threshold, definitions), "BIN_5")
        self.assertEqual(_speed_bin_for_value(0.0, definitions), "ZERO")

    def test_duplicate_quantiles_do_not_create_zero_width_bins(self) -> None:
        definitions = _speed_bin_definitions([1.0, 1.0, 1.0, 1.0], 1.0, "linear")
        for item in definitions:
            if item["lower"] is not None and item["upper"] is not None:
                self.assertLess(float(item["lower"]), float(item["upper"]))

    def test_area_fraction_rejects_unsupported_timestep(self) -> None:
        u = np.ones((2, 2))
        v = np.ones((2, 2))
        u[0, 0] = np.nan
        result = _spatial_mean_vector(u, v, np.ones((2, 2)), MINIMUM_VALID_AREA_FRACTION)
        self.assertFalse(result["accepted"])
        self.assertAlmostEqual(result["valid_area_fraction"], 0.75)


if __name__ == "__main__":
    unittest.main()
