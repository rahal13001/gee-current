# ADR-004 — Arsitektur Hibrida Python–GEE

- Status: `PROPOSED` (diwarisi dari PRD)
- Context: Komputasi berat tidak cocok dijalankan ulang pada setiap interaksi GEE.
- Decision: Python/xarray menangani ingestion, validasi, analytics berat, dan prahitung; GEE menangani aset terpilih, peta, dan analisis ringan.
- Alternatives: seluruh workflow di GEE atau seluruhnya lokal.
- Scientific impact: hasil berat memiliki referensi Python yang dapat diaudit.
- Technical impact: membutuhkan metadata lintas platform.
- Security/cost impact: mengurangi komputasi interaktif dan risiko biaya.
- Validation required: pilot dan perbandingan Python–GeoTIFF–GEE.
