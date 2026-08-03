# GEEMu Foundation Run Note

Status: `READ_ONLY` dengan user-reported runtime smoke; bukan Earth Engine analysis, export, asset, atau batch run.

## Research Design

| Decision | Choice | Suggested by local knowledge | Reason | Needs confirmation |
|---|---|---|---|---|
| Study area | `pilot_001`, user-defined bbox di `EPSG:4326` | Tidak dipilih otomatis | AOI ditetapkan langsung oleh pengguna; exact polygon/water mask tetap downstream | Tidak untuk pilot bbox |
| Analysis scale | native sekitar 1/12°; nilai final harus mengikuti metadata aktif | Jangan gunakan resolusi lebih halus sebagai akurasi | Menjaga makna grid model | Ya, setelah metadata aktif |
| Output target | Python validation/products lalu GEE selected assets/light visualization | Hibrida Python–GEE | Sesuai PRD/ADR-004 | Ya |

## Parameter ledger

| Item | Chosen value | Evidence |
|---|---|---|
| Product ID | `GLOBAL_MULTIYEAR_PHY_001_030` | `docs/audits/COPERNICUS_METADATA_READONLY_CHECK.md`; user reports metadata target verified |
| Daily dataset | `cmems_mod_glo_phy_my_0.083deg_P1D-m` | read-only metadata audit; user reports target verified |
| Monthly dataset | `cmems_mod_glo_phy_my_0.083deg_P1M-m` | read-only metadata audit; user reports target verified |
| Bands | `uo`, `vo` | Keputusan ilmiah pengguna |
| Units | `m s-1` | Keputusan ilmiah pengguna |
| Depth | `0.494025 m` | metadata catalog `0.49402499198913574 m`, reconciled within tolerance |
| Period | 2015-01-01 inclusive to 2026-01-01 exclusive | Keputusan ilmiah pengguna |
| Core data | 132 monthly + 993 daily JFM | read-only metadata audit and user report; no download claim |

## Boundary/performance

Project ID: `ee-rahal13001` (user-reported). Noncommercial registration: user-reported completed.
AOI pilot bbox sudah ditetapkan user; exact polygon/water mask, export target, exact Earth Engine tier, IAM, billing,
asset existence/write access, and EECU target remain `UNKNOWN/OPEN`.
No GEE code, export, asset upload, or batch task was run by Codex. The only runtime evidence is the
user-reported smoke test `ee.Initialize(project='ee-rahal13001')` plus `ee.Number(1).getInfo()` returning `1`.

## Read-only evidence reconciliation

- Copernicus metadata target: `docs/audits/COPERNICUS_METADATA_READONLY_CHECK.md`.
- Reported Copernicus Marine version: `2.4.1`; no login or credential check was repeated by Codex.
- Reported Earth Engine API package: `1.7.37`; no OAuth or credential file was inspected by Codex.
- Daily JFM count: `993`; monthly count: `132`; this does not prove downloaded-file integrity,
  checksum, NetCDF decoding, AOI validity, GEE asset state, or scientific acceptance.
