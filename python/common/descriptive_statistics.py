"""Offline descriptive statistics with explicit method parameters.

This module implements the statistic names listed by Tahap 1. It intentionally
requires callers to choose ``ddof`` and ``percentile_method``; no unstated
scientific convention is selected for the operational pipeline.
"""

from __future__ import annotations

import math
import statistics
from typing import Iterable


class StatisticsError(ValueError):
    """Raised when statistics inputs or explicit method choices are invalid."""


def _values(values: Iterable[float]) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result:
        raise StatisticsError("values must not be empty")
    if any(not math.isfinite(value) for value in result):
        raise StatisticsError("values must be finite")
    return result


def percentile_linear(values: Iterable[float], percentile: float) -> float:
    """Return an explicitly requested linear-interpolation percentile."""

    data = tuple(sorted(_values(values)))
    q = float(percentile)
    if not math.isfinite(q) or not 0.0 <= q <= 100.0:
        raise StatisticsError("percentile must be finite and between 0 and 100")
    if len(data) == 1:
        return data[0]
    position = (len(data) - 1) * q / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return data[lower]
    fraction = position - lower
    return data[lower] + fraction * (data[upper] - data[lower])


def summary_statistics(
    values: Iterable[float], *, ddof: int, percentile_method: str
) -> dict[str, float | int]:
    """Return the configured speed-statistic fields for valid values.

    ``ddof`` is required because Tahap 1 does not silently choose population
    versus sample variance. At present the only implemented percentile method
    is the explicit ``linear`` interpolation method.
    """

    data = _values(values)
    if ddof not in (0, 1):
        raise StatisticsError("ddof must be explicitly set to 0 or 1")
    if len(data) <= ddof:
        raise StatisticsError("not enough values for the requested ddof")
    if percentile_method != "linear":
        raise StatisticsError("percentile_method must be explicitly set to 'linear'")

    average = math.fsum(data) / len(data)
    variance = math.fsum((value - average) ** 2 for value in data) / (len(data) - ddof)
    percentiles = {
        f"p{percentile:g}": percentile_linear(data, percentile)
        for percentile in (10, 25, 50, 75, 90, 95, 99)
    }
    return {
        "count": len(data),
        "mean": average,
        "min": min(data),
        "max": max(data),
        "median": statistics.median(data),
        "standard_deviation": math.sqrt(variance),
        "variance": variance,
        **percentiles,
    }
