# T6-006 — Runtime Validation dan Koreksi Kontrak Band

Tanggal: 7 Agustus 2026  
Tahap: 6 — Publikasi aset GEE terpilih  
Status: `PASS_WITH_NOTES`

## Ringkasan

Validasi runtime terhadap aset hasil ingest awal menemukan ketidaksesuaian nama
band: source terbaca sebagai `b1`/`b2` dan derived sebagai `b1`, sedangkan
kontrak manifest mengharuskan `uo`/`vo` dan `speed`. Nilai raster, waktu, grid,
mask, dan rumus derived tetap dapat direkonsiliasi secara positional.

Perbaikan dilakukan dalam dua tahap. Dua aset sementara bersuffix `_fixed`
dibuat dan divalidasi terlebih dahulu. Setelah user memberi persetujuan
eksplisit, dua ID kanonis yang salah dihapus dan dibuat ulang dari asset
`_fixed` tervalidasi melalui `Export.image.toAsset`. Asset `_fixed`
dipertahankan sebagai rollback/evidence.

## Asset kanonis setelah rekreasi

- Source: `projects/ee-rahal13001/assets/glorys_current/surface_0p494025m/daily_jfm_2015_2025/glorys12v1_d_20150101_d0p494025m`
- Derived: `projects/ee-rahal13001/assets/glorys_current/derived/speed/glorys12v1_speed_20150101_d0p494025m`
- Rollback/evidence source: suffix `_fixed` pada ID source di atas.
- Rollback/evidence derived: suffix `_fixed` pada ID derived di atas.

Script repository:

- `tools/gee_export_t6_006_corrected_assets.js`
- `tools/gee_validate_t6_006_corrected_assets.js`
- `tools/gee_replace_t6_006_original_assets.js`
- `tools/gee_validate_t6_006_recreated_assets.js`

## Evidence runtime

| Check | Result |
|---|---|
| Task Manager export source | `completed` — `t6_006_source_recreated_original_id` |
| Task Manager export derived | `completed` — `t6_006_derived_recreated_original_id` |
| Source bands | `["uo", "vo"]` |
| Derived bands | `["speed"]` |
| Source/derived time | `1420070400000` sampai `1420156800000`; keduanya sama |
| CRS | `EPSG:4326` pada source dan derived |
| Transform | sama: `0.0833282470703125, 0, 122.95833587646484, 0, -0.08333331346511841, 4.291666656732559` |
| Nominal scale | `9276.34002252204 m` pada keduanya |
| Grid equality | `crs_equal=true`, `transform_equal=true`, selisih scale `0` |
| Unmasked `-9999` | source `uo=0`, `vo=0`; derived `speed=0` |
| Valid-mask mean | source `0.8169675725855516`; derived `0.8169675725855516` |
| Speed formula | `max abs(speed - sqrt(uo^2 + vo^2)) = 5.959572346725395e-8` |
| Visual evidence | `outputs/evidence/stage_6/T6-006_recreated_original_runtime.png` (captured from the same browser session) |
| Console evidence | `outputs/evidence/stage_6/T6-006_recreated_console_fullregion.txt` |
| Task evidence | `outputs/evidence/stage_6/T6-006_recreated_task_manager.txt` |

## Offline evidence

| Command | Exit | Result |
|---|---:|---|
| `python3 -m unittest tests.unit.test_stage6_manifest -v` | 0 | 4 test lulus |
| `python3 -m unittest tests.unit.test_gee_asset_schemas -v` | 0 | 5 test lulus |
| `git diff --check` | 0 | tidak ada whitespace error |

## Keputusan dan batasan

- Manifest T6-004 dan generator kini menunjuk ke ID kanonis tanpa suffix.
- ID kanonis lama yang salah telah dihapus setelah konfirmasi exact asset ID,
  lalu dibuat ulang dari `_fixed` tervalidasi. Hanya dua asset tersebut yang
  disentuh; asset `_fixed` tidak dihapus dan menjadi rollback/evidence.
- Validasi dilakukan pada sampel `2015-01-01` saja; belum merupakan validasi
  seluruh koleksi Stage 5 atau batch `daily_full`.
- Task Manager dan Console GEE digunakan melalui browser yang sudah login oleh
  user. Tidak ada credential yang dibaca atau disimpan oleh repository.
- Pemeriksaan Earth Engine Python API lokal tidak tersedia karena environment
  Linux tidak memiliki module `ee` dan `geemap`; ini tidak membatalkan evidence
  runtime browser, tetapi membatasi replikasi lewat Python lokal.
- Warning/error UI lama pada Console berasal dari script validasi sebelum
  koreksi dan layer legacy; hasil scientific yang digunakan di sini hanya entry
  berlabel `T6-006 recreated` dan status task rekreasi.
- `daily_full`, batch upload, ACL mutation, dan publikasi aset tambahan tetap
  berada di luar scope.
