# T6-002/T6-003 — Review Schema Asset Source dan Derived

Tanggal: 6 Agustus 2026  
Tahap: 6 — Publikasi aset GEE terpilih  
Status: `PASS_WITH_NOTES`

## Ringkasan

Kontrak offline untuk dua jenis manifest asset telah difinalisasi:

- `config/gee_source_asset.schema.json` untuk source asset dua band `uo`/`vo`;
- `config/gee_derived_asset.schema.json` untuk satu-band precomputed product.

Keduanya menggunakan struktur manifest yang sudah dicontohkan pada Tahap 2:
`name`, `tilesets`, `bands`, `properties`, `startTime`, dan `endTime`.
`startTime`/`endTime` adalah representasi manifest untuk `system:time_start` dan
`system:time_end`; `period_end_inclusive` diwajibkan `false`.

## Keputusan kontrak

### T6-002 — Source

- Project ID dan asset path harus mengikuti pola `projects/.../assets/...`.
- Tileset source menerima URI `gs://` dan tidak mengklaim bahwa URI tersebut
  sudah tersedia.
- Band harus tepat dua dan berurutan: `uo` pada index 0, `vo` pada index 1.
- Kedua band memakai `MEAN` dan missing value `-9999`.
- Metadata wajib mencakup Product ID, Dataset ID, version/part, model,
  processing type, resolusi waktu, period, depth `0.494025`, label lapisan,
  unit, konvensi arah, CRS/grid, conversion/pipeline/config hash, filename,
  source checksum, nodata/mask policy, status, AOI, limitations, dan waktu
  pembuatan.
- Daily JFM dan monthly all dipisahkan melalui Dataset ID, `temporal_resolution`,
  dan `period_type`; keduanya tidak boleh tercampur dalam satu manifest.

### T6-003 — Derived

- Asset derived harus tepat satu band dan tetap menggunakan missing value
  `-9999` serta `MEAN`.
- Product type dibatasi pada lima tipe yang ada di manifest analytics lokal:
  `monthly_climatology_speed`, `jfm_climatology_speed`, `speed`,
  `speed_anomaly`, dan `exploratory_trend_slope`.
- Provenance wajib mencakup analytics version, source conversion manifest dan
  SHA-256-nya, source config hash, reference period, period, depth, unit,
  CRS/grid, mask method/checksum, AOI, status, limitation, dan timestamp.
- Produk per-frame wajib membawa source time/path/checksum dan job/plan.
- Tren hanya boleh membawa method `ordinary_least_squares_per_pixel` dan
  interpretation eksploratif tanpa klaim inferensial/kausal.

## Evidence offline

| Command | Exit | Hasil |
|---|---:|---|
| `python3 -m unittest tests.unit.test_gee_asset_schemas -v` | 0 | 5 test schema contract lulus |
| `Draft202012Validator.check_schema` pada dua file | 0 | dua dokumen valid sebagai JSON Schema draft 2020-12 |
| fixture source daily JFM dan derived monthly climatology dengan `FormatChecker` | 0 | tidak ada validation error |

Test unit menggunakan standard library dan memeriksa shape, required fields,
band order, fixed scientific identifiers, branch daily/monthly, product enum,
dan provenance requirements. Pemeriksaan validator formal dijalankan dari
interpreter lokal yang sudah memiliki `jsonschema`; dependency tidak dipasang
atau diubah oleh task ini.

## Batasan dan gate berikutnya

- Tidak ada login, credential read, network, Earth Engine runtime, GCS check,
  upload, export, ACL mutation, atau Cloud task.
- Schema belum membuktikan bahwa manifest diterima oleh Earth Engine atau bahwa
  asset/GCS path benar-benar ada.
- T6-004 tetap wajib membuat manifest sampel konkret dan memvalidasi sintaksnya.
- T6-005/T6-006 tetap memerlukan approval dan operasi cloud terpisah.
- `daily_full` tetap disabled; tidak ada keputusan ilmiah yang diubah.
