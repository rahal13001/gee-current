# Tahap 1 Architecture Manifest

The project uses the approved hybrid Python/Google Earth Engine architecture.

## Responsibility split

- Python/xarray/NetCDF: metadata, raw-data validation, heavy statistics,
  long current-rose and percentile work, and batch preparation.
- Earth Engine: selected asset storage, bounded AOI filtering, lightweight
  statistics, map preview, and constrained teaching interactions.
- Full daily 2015–2025 computation remains disabled by design.

## Asset boundary

The user-reported Earth Engine root is:

```text
projects/ee-rahal13001/assets/glorys_current
```

No asset was created, uploaded, or verified by Codex in this stage. Derived
collections remain prohibited until source data and the Tahap 2 pilot pass.

## Gate state

This manifest is an offline design artifact. `tileScale`, `parallelScale`,
export sizing, and task strategy remain subject to Tahap 2 benchmarking.
