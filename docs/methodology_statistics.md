# Approved descriptive-statistics baseline

The statistic names below are taken from the Tahap 1 design and
`config/statistics.json`. The implementation is
`python/common/descriptive_statistics.py`.

The operational pipeline must provide both parameters explicitly:

- `ddof`: `0` for population or `1` for sample variance;
- `percentile_method`: currently implemented option `linear`.

Neither parameter is silently selected in the project config. The choice must
be approved before using real GLORYS outputs. Threshold exceedance remains
TBD and is deliberately not implemented here.

Implemented fields: `count`, `mean`, `min`, `max`, `median`,
`standard_deviation`, `variance`, `p10`, `p25`, `p50`, `p75`, `p90`, `p95`,
and `p99`.
