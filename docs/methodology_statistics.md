# Approved descriptive-statistics baseline

The statistic names below are taken from the Tahap 1 design and
`config/statistics.json`. The implementation is
`python/common/descriptive_statistics.py`.

The operational pipeline must provide both parameters explicitly:

- `ddof`: `0` for population or `1` for sample variance;
- `percentile_method`: currently implemented option `linear`.

Neither parameter is silently selected in the project config. The current
local Stage 5 baseline records `ddof=0` and percentile method `linear`.
Threshold exceedance is implemented separately in `python/analytics.py` using
the approved global AOI P90 decision; it is a relative research threshold,
not a safety or operational limit.

Implemented fields: `count`, `mean`, `min`, `max`, `median`,
`standard_deviation`, `variance`, `p10`, `p25`, `p50`, `p75`, `p90`, `p95`,
and `p99`.
