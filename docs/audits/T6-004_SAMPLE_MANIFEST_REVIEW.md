# T6-004 — Review Manifest Sampel Source dan Derived

Tanggal: 6 Agustus 2026
Tahap: 6 — Publikasi aset GEE terpilih
Status: `PASS_WITH_NOTES`

## Ringkasan

Manifest sampel dibuat secara lokal dari evidence tervalidasi Stage 4/5:

- source daily JFM: `2015-01-01T00:00:00Z`, dua band `uo`/`vo`;
- derived `speed`: timestamp dan grid yang sama, satu band `speed`.

Artifact:

- `outputs/manifests/stage_6_t6_004/source_daily_jfm_20150101.json`;
- `outputs/manifests/stage_6_t6_004/derived_speed_daily_jfm_20150101.json`;
- `outputs/manifests/stage_6_t6_004/manifest_index.json`.

Generator: `python/12_create_t6_manifest.py` dengan logika pada
`python/gee_manifest.py`.

## Checks

| Check | Exit | Evidence |
|---|---:|---|
| `python3 -m unittest tests.unit.test_stage6_manifest -v` | 0 | 4 unit test lulus |
| Generator T6-004 dengan bucket sample eksplisit dan timestamp eksplisit | 0 | index mencatat 2 manifest |
| JSON Schema draft 2020-12 + `FormatChecker` untuk source | 0 | source manifest valid |
| JSON Schema draft 2020-12 + `FormatChecker` untuk derived | 0 | derived manifest valid |
| checksum source/derived terhadap manifest Stage 5 | 0 | checksum lokal cocok |
| source dan derived grid | 0 | CRS, transform, dan shape sama |
| `python3 -m pytest -q` | 1 | interpreter Linux tidak memiliki module `pytest`; tidak ada dependency dipasang |

## Kontrak yang diverifikasi

- Project ID dan asset root konsisten dengan `config/asset_naming.json`.
- Source memakai asset naming harian yang disetujui dan band `uo` index 0,
  `vo` index 1.
- Derived dibatasi pada produk `speed` dari `plan_name=daily_jfm`; pemilihan
  plan eksplisit karena timestamp yang sama juga muncul pada plan lain.
- `startTime`/`endTime` dan `period_end_inclusive=false` menunjukkan akhir
  periode eksklusif.
- Source checksum berasal dari Stage 5 conversion job; derived checksum berasal
  dari Stage 5 analytics product; source conversion manifest SHA-256 dan static
  expected-ocean mask checksum ikut dicatat.
- Tidak ada `upload_commands.txt` yang dibuat oleh generator.

## Batasan dan gate

- `t6-004-sample-bucket` adalah nama bucket sample, bukan bukti bucket GCS nyata.
  Keberadaan, ownership, lokasi, lifecycle, biaya, dan akses bucket belum dicek.
- Placeholder/sample URI tidak boleh dipakai untuk upload nyata.
- Tidak ada Earth Engine authentication, network, GCS check, upload, export,
  ACL mutation, atau Cloud task.
- Full suite pytest belum dapat dijalankan pada interpreter Linux ini; focused
  `unittest` T6-004 dan schema tetap lulus.
- T6-005 tetap menjadi gate upload sampel terkontrol dan memerlukan approval.
- `daily_full` tetap disabled; tidak ada keputusan ilmiah yang diubah.
