# GEEMu Foundation Run Note

Status: `READ_ONLY`, bukan Earth Engine run.

## Research Design

| Decision | Choice | Suggested by local knowledge | Reason | Needs confirmation |
|---|---|---|---|---|
| Study area | Perairan Sorong dan sekitarnya; AOI/bbox belum disahkan | Tidak dipilih otomatis | Tahap 2 melarang AOI tebakan | Ya |
| Analysis scale | native sekitar 1/12°; nilai final harus mengikuti metadata aktif | Jangan gunakan resolusi lebih halus sebagai akurasi | Menjaga makna grid model | Ya, setelah metadata aktif |
| Output target | Python validation/products lalu GEE selected assets/light visualization | Hibrida Python–GEE | Sesuai PRD/ADR-004 | Ya |

## Parameter ledger

| Item | Chosen value | Evidence |
|---|---|---|
| Product ID | `GLOBAL_MULTIYEAR_PHY_001_030` | PRD/Tahap 0; metadata aktif belum dicek network |
| Daily dataset | `cmems_mod_glo_phy_my_0.083deg_P1D-m` | PRD/Tahap 0; metadata aktif belum dicek network |
| Monthly dataset | `cmems_mod_glo_phy_my_0.083deg_P1M-m` | PRD/Tahap 0; metadata aktif belum dicek network |
| Bands | `uo`, `vo` | Keputusan ilmiah pengguna |
| Units | `m s-1` | Keputusan ilmiah pengguna |
| Depth | `0.494025 m` | Keputusan ilmiah pengguna |
| Period | 2015-01-01 inclusive to 2026-01-01 exclusive | Keputusan ilmiah pengguna |
| Core data | 132 monthly + 993 daily JFM | Keputusan ilmiah pengguna |

## Boundary/performance

AOI, export target, Project ID, tier, and EECU target are `UNKNOWN/OPEN`. No GEE code, export, or task was run.
