# T6-007/T6-008 — Offline Publish Manifest Review

Tanggal: 7 Agustus 2026  
Status: `PASS_WITH_NOTES`  
Scope: seleksi publish-on-demand lokal; tidak termasuk upload.

## Keputusan seleksi

Manifest memilih set inti yang dapat langsung mendukung implementasi reader
source dan reader produk prahitung:

| Kelompok | Jumlah | Keputusan |
|---|---:|---|
| Source `monthly_all` | 132 | Dipilih seluruhnya untuk koleksi bulanan 2015–2025 |
| Source `daily_jfm` | 993 | Dipilih seluruhnya untuk MVP JFM yang disetujui |
| Derived `speed` | 1.125 | Dipilih seluruhnya untuk reader speed prahitung |
| Derived monthly climatology | 12 | Dipilih seluruhnya untuk ringkasan bulanan |
| Derived JFM climatology | 1 | Dipilih untuk ringkasan JFM |
| **Total source** | **1.125** |  |
| **Total derived** | **1.138** |  |

`speed_anomaly` (1.125) dan `exploratory_trend_slope` (1) tetap lokal.
Keduanya tidak dihapus atau diubah; keduanya ditunda sampai kontrak reader/UI
GEE dan keputusan publish produk tersebut disetujui. Dua static expected-ocean
mask juga tetap menjadi artefak QC lokal.

Target asset derived `speed` diberi namespace `daily_jfm` atau `monthly_all`
untuk mencegah benturan ID pada tanggal yang sama. Dua ID kanonis sampel
T6-006 tetap merupakan alias legacy yang sudah divalidasi dan tidak diubah oleh
manifest ini. Setiap source dan derived `speed` juga membawa `startTime` dan
`endTime` UTC dengan batas akhir eksklusif; derived `speed` harus memakai window
waktu yang sama dengan source terkait.

## Evidence dan pemeriksaan

Manifest: `outputs/manifests/stage_6_publish/t6_007_t6_008_publish_manifest.json`  
SHA-256 manifest: `8c459823fd687af0483e5058f7be889d8011dd8af965c4922e6ceafee2427113`

Command generator:

```text
python3 python/13_create_t6_publish_manifest.py --root . --created-utc 2026-08-07T00:00:00Z --output-dir outputs/manifests/stage_6_publish
exit 0
```

Output generator mencatat `PASS_WITH_NOTES`, `selected_source_count=1125`,
dan `selected_derived_count=1138`.

Unit/schema test:

```text
python3 -m unittest tests.unit.test_stage6_publish_manifest -v
exit 0
Ran 4 tests in 274.165s — OK
```

Pemeriksaan tersebut memverifikasi bahwa:

- seluruh path aset terpilih ada di repository dan tetap berada di root;
- checksum lokal seluruh aset terpilih cocok dengan manifest Stage 5;
- source tetap dua band `uo`/`vo`, `float32`, `EPSG:4326`, NoData `-9999`,
  dan resampling `none`;
- setiap speed mempunyai source path yang cocok;
- setiap source dan derived `speed` mempunyai window `startTime`/`endTime` UTC
  end-exclusive yang konsisten; April 2015 diverifikasi sebagai
  `2015-04-01T00:00:00Z` sampai `2015-05-01T00:00:00Z`;
- schema publish mewajibkan window waktu untuk source dan derived `speed`,
  serta test negatif memastikan field tersebut tidak boleh hilang;
- seluruh target asset ID unik;
- input evidence Stage 5 berstatus `PASS_WITH_NOTES` dan cakupannya adalah
  165 job, 1.125 frame, serta 2.264 derived products;
- schema `config/gee_publish_selection.schema.json` lulus dengan
  `Draft202012Validator` dan `FormatChecker`;
- generator menolak overwrite artifact yang sudah ada.

## Limitasi dan gate berikutnya

- Manifest ini tidak memeriksa keberadaan bucket atau asset Earth Engine.
- Tidak ada login, pembacaan credential, network, GCS, upload, export,
  perubahan ACL/IAM, atau cloud task.
- Bucket GCS belum dikonfigurasi dan perintah upload sengaja tidak dibuat.
- T6-009/T6-010 baru boleh dimulai setelah ada keputusan staging/bucket dan
  approval upload; T6-011/T6-012 tetap downstream.
- `daily_full` tetap disabled.
