# ADR-011 — Threshold Relatif dan Current Rose Penelitian

## Context

T5-017 dan T5-019 memerlukan definisi statistik yang tidak boleh ditebak oleh
pipeline. Konfigurasi awal sengaja membiarkan threshold dan speed bins kosong.
Keputusan domain expert yang diterima pada 2026-08-05 menetapkan definisi
operasional untuk analisis lokal Stage 5.

## Decision

1. T5-017 menggunakan `relative_high_current_threshold_global_p90`:
   `T = P90(S_A(t))`, dengan `S_A(t)` sebagai kecepatan resultan dari vektor
   `u`/`v` rata-rata spasial berbobot luas pada seluruh AOI.
2. Threshold dihitung terpisah untuk `daily_jfm` dan `monthly_all`, berlaku
   hanya pada AOI, periode, depth, dataset, dan agregasi temporal asalnya.
3. Exceedance menggunakan `speed > threshold`; nilai sama dengan threshold
   adalah non-exceedance. Missing pair `uo`/`vo` dikeluarkan.
4. Timestep diterima bila valid-area fraction minimal `0.95` terhadap static
   expected-ocean mask. Missing tidak diisi nol atau diinterpolasi.
5. T5-019 menghasilkan current rose untuk AOI (zona hanya bila ID dan geometri
   valid), dengan 16 sektor `towards`, 0° utara sejati, searah jarum jam.
6. Speed bins global AOI menggunakan P25/P50/P75/P90 dari seri `S_A(t)` yang
   sama; `P90` sama dengan threshold T5-017. `S <= 1e-6 m s-1` adalah ZERO dan
   tidak diberi arah.
7. Frekuensi current rose menggunakan seluruh timestep valid sebagai
   denominator, termasuk ZERO. Missing tetap dilaporkan terpisah.

Keputusan ini adalah metodologi penelitian dan bukan ambang keselamatan,
bahaya, atau operasional. Rujukan prinsip QARTOD dicatat sebagai dasar
metodologis yang disediakan oleh domain expert; proyek menggunakan reanalisis
GLORYS12V1, bukan observasi ADCP real-time.

## Alternatives

- Threshold fisik universal: ditolak karena tidak kontekstual.
- Threshold berbeda per zona: ditolak sebagai threshold utama karena merusak
  keterbandingan antarzona.
- Current rose per pixel: ditunda dari MVP karena ukuran dan interpretasi;
  produk raster/vektor menangani detail spasial.

## Scientific impact

Hasil mewakili kondisi relatif tinggi terhadap distribusi masing-masing
analysis plan, bukan klaim bahaya atau keselamatan. Zona dan polygon air yang
belum tersedia tetap menjadi keterbatasan yang harus ditampilkan.

## Technical impact

Analytics menghasilkan tabel threshold, tabel current-rose long/summary,
figure SVG AOI, dan static expected-ocean mask per analysis plan. Semua metode,
metadata dataset T4, config hash lengkap, checksum, dan aturan missing dicatat
di manifest Stage 5.

## Security/cost impact

Tidak ada network, authentication, upload, layanan cloud, atau dependency baru.

## Validation required

Unit test threshold/bin/missing/zero/area fraction, full local run untuk 1.125
timestep, audit checksum/schema/metadata, dan verifikasi frekuensi harus lulus.
Output zona memerlukan geometri zona yang disediakan pengguna.

## Status

`PROPOSED` — keputusan ahli telah diimplementasikan untuk local analytics dengan
status `PASS_WITH_NOTES`; penerimaan ADR formal tetap mengikuti governance M0.
