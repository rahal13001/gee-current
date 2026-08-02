# Copernicus Marine Metadata Read-only Check

Status: `PASS_WITH_NOTES`

Tanggal pemeriksaan: 2026-08-02

## Scope

Pemeriksaan ini hanya membaca katalog metadata Copernicus Marine menggunakan
`copernicusmarine describe`. Tidak ada operasi `get`, `subset`, download,
upload, atau perubahan asset.

Product yang diperiksa:

```text
GLOBAL_MULTIYEAR_PHY_001_030
```

Dataset yang diperiksa:

```text
cmems_mod_glo_phy_my_0.083deg_P1D-m
cmems_mod_glo_phy_my_0.083deg_P1M-m
```

Versi metadata yang dikembalikan katalog: `202311`.

## Evidence

| Check | Result |
|---|---|
| Product ID | Cocok dengan `GLOBAL_MULTIYEAR_PHY_001_030` |
| Daily dataset ID | Cocok |
| Monthly dataset ID | Cocok |
| Variables | `uo` dan `vo` tersedia |
| Units | `m s-1` untuk `uo` dan `vo` |
| Depth | Nilai katalog `0.49402499198913574 m`, cocok dengan keputusan `0.494025 m` dalam toleransi numerik |
| Daily temporal representation | `1993-01-01` sampai `2026-06-23`, step 1 hari |
| Monthly temporal representation | `1993-01-01` sampai `2026-05-01`; 132 timestep pada periode proyek |
| Project period | `2015-01-01` inklusif sampai `2026-01-01` eksklusif |
| Daily JFM count | 993 timestep, dihitung dari step harian dan periode proyek |
| Monthly count | 132 timestep |

## Notes and limits

- Daily metadata menggunakan `minimum_value`, `maximum_value`, dan `step`
  untuk koordinat waktu; katalog tidak mengembalikan seluruh daftar waktu pada
  field tersebut.
- Nilai 993 daily JFM adalah kalkulasi deterministik dari rentang proyek,
  step satu hari, dan bulan Januari–Maret. Ini bukan hasil pengunduhan data.
- Pemeriksaan ini tidak membuktikan integritas nilai numerik pada file data,
  checksum, AOI, atau hasil subset. Pemeriksaan tersebut memerlukan tahap
  validasi data tersendiri.
- GLORYS12V1 tetap diperlakukan sebagai reanalisis model untuk pendidikan dan
  penelitian nonkomersial; hasil ini bukan validasi operasional, navigasi,
  keselamatan, desain teknik, atau komersial.

## Reproducibility command

Command yang digunakan setelah membaca `copernicusmarine describe --help`:

```powershell
& .\.venv\Scripts\copernicusmarine.exe describe `
  --dataset-id cmems_mod_glo_phy_my_0.083deg_P1D-m `
  --return-fields all `
  --disable-progress-bar `
  --max-concurrent-requests 0 `
  --log-level ERROR `
  --raise-on-error
```

Command yang sama dijalankan untuk dataset bulanan dengan mengganti
`--dataset-id`.

