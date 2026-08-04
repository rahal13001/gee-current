# Proposal Ekspansi AOI Perairan Indonesia Timur

Tanggal keputusan: 2026-08-05 (Asia/Jayapura)

## Status

`APPLIED_WITH_NOTES` — bbox regional sudah diterapkan pada AOI aktif; polygon
perairan, water mask, dan penggunaan operasional masih memerlukan validasi.

## Keputusan saat ini

- AOI aktif sekarang `eastern_indonesia_regional_001` pada
  `config/study_area.json`.
- `config/pilot_config.example.json` tetap `pilot_001` untuk baseline T2 dan
  tidak diganti oleh AOI regional.
- Asset pilot, periode pilot, asset root, dan keputusan dataset tetap tidak
  diubah.
- Belum ada download, upload, autentikasi, atau akses network untuk proposal
  ini.

## Cakupan regional yang diterapkan

Proposal ini mencakup perairan di sekitar Papua, Maluku, dan Maluku Utara.
Bounding box regional berikut diberikan langsung oleh pengguna pada
2026-08-05:

| Batas | Nilai |
|---|---:|
| North | `4.265137` |
| West | `122.986190` |
| South | `-12.191592` |
| East | `143.326183` |

Bounding box ini valid untuk `EPSG:4326` dan sudah diterapkan sebagai cakupan
aktif untuk preflight/dry-run regional. Polygon perairan dan water mask final
belum ditetapkan.

Koordinat di atas bukan hasil invent Codex. Bounding box besar tidak boleh
dianggap sebagai batas perairan Indonesia karena memasukkan daratan, wilayah
laut di luar kebutuhan, dan sel grid yang tidak relevan.

## Syarat sebelum penggunaan operasional

1. Pengguna menetapkan sumber batas wilayah yang sah dan dapat diaudit.
2. Polygon AOI dan CRS `EPSG:4326` disetujui bila analisis memerlukan batas
   perairan yang lebih presisi daripada bbox.
3. Water/land mask dan perlakuan sel pesisir ditetapkan.
4. AOI dipecah menjadi subwilayah bila ukuran file atau retry memerlukannya.
5. Dry-run lokal dan estimasi ukuran output selesai.
6. Download dan batch mendapat approval/change control eksplisit.

## Dampak terhadap Tahap 3

T3-014 tetap merupakan batch bulanan; jumlah temporal tetap 132 job, tetapi
ukuran setiap file meningkat bila AOI diperluas. T3-015 tetap terpisah untuk
33 job harian JFM. Bbox regional dapat digunakan untuk preflight/dry-run, tetapi
download aktual tetap menunggu syarat operasional di atas.

## Rujukan baseline

- AOI aktif regional: `config/study_area.json`
- Konfigurasi pilot T2: `config/pilot_config.example.json`
- Traceability: `docs/REQUIREMENTS_TRACEABILITY.md`
