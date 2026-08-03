# Tahap 1 Configuration Baseline Report

- Test ID: `T1-012`
- Status: `PASS_WITH_NOTES`
- Scope: offline configuration and schema baseline only
- AOI: `pilot_001`, user-provided bbox in `EPSG:4326`
- Asset root: `projects/ee-rahal13001/assets/glorys_current` (user-reported)
- Offline validator: `tools/validate_m1_config.ps1`
- Validator exit status: `0`

## Artifacts

- `config/study_area.json`
- `config/analysis_period.json`
- `config/depth_selection.json`
- `config/statistics.json`
- `config/asset_naming.json`
- `config/pilot_config.schema.json`
- `config/local.example.json`
- `config/pilot_config.example.json`

## Gate status

The offline configuration baseline is structurally ready for review. Thresholds
remain empty/TBD and no scientific value was invented. The typed loader,
constants module, data dictionary, architecture manifest, and interactive
limits baseline are present and locally validated. Exact polygon/mask,
benchmarking, the operational pilot, and Tahap 2 remain downstream work. No
network, authentication, asset existence check, upload, or operational
computation was performed.
