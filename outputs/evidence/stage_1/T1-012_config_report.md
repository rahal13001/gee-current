# Tahap 1 Configuration Baseline Report

- Test ID: `T1-012`
- Status: `PASS_WITH_NOTES`
- Scope: offline configuration and schema baseline only
- AOI: `pilot_001`, user-provided bbox in `EPSG:4326`
- Asset root: `projects/ee-rahal13001/assets/glorys_current` (user-reported)
- Offline validator: `tools/validate_m1_config.ps1`
- Validator exit status: `0`
- Cross-file consistency: approved dataset IDs, timezone, period/JFM definition, depth-selection metadata, and statistic field lists are fail-closed validated.

## Artifacts

- `config/study_area.json`
- `config/analysis_period.json`
- `config/depth_selection.json`
- `config/statistics.json`
- `config/asset_naming.json`
- `config/pilot_config.schema.json`
- `config/local.example.json`
- `config/pilot_config.example.json`
- `python/common/scientific_formulas.py`
- `docs/methodology_formulas.md`
- `outputs/evidence/stage_1/T1_formula_validation.result.txt`
- `python/common/descriptive_statistics.py`
- `docs/methodology_statistics.md`
- `outputs/evidence/stage_1/T1_statistics_validation.result.txt`

## Gate status

The offline configuration and formula baseline was structurally ready for
review at the time of this historical report. The threshold list was empty/TBD
then, and no scientific value was invented. The typed loader,
constants/formula/statistics modules, data dictionary, architecture manifest,
and interactive limits baseline were present and locally validated.
Exact polygon/mask, benchmarking, the operational pilot, and Tahap 2 remain
downstream work. No network, authentication, asset existence check, upload, or
operational computation was performed.

## Amendment 2026-08-05

The original report is a historical Tahap 1 baseline. After the domain-expert
decision recorded in `docs/adr/ADR-011-threshold-current-rose.md`, the active
configuration was revalidated with exit status `0`. The literal threshold list
remains empty intentionally; T5-017 now derives global AOI P90 per
`analysis_plan_id`, and T5-019 uses the resolved 16-sector/current-rose
contract. Minimum valid area fraction is `0.95`. Formal ADR governance remains
`PROPOSED` until accepted through the M0 process.
