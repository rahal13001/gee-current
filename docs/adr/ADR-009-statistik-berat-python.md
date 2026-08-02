# ADR-009 — Statistik Berat di Python

- Status: `PROPOSED` (diwarisi dari PRD)
- Context: current rose, percentile panjang, dan tabel zonal besar memerlukan kontrol lokal.
- Decision: statistik berat dilakukan di Python atau batch; GEE hanya membaca produk/ringkasan.
- Alternatives: reducer interaktif massal ditolak.
- Scientific impact: metode numerik dapat diuji dengan fixture sintetis.
- Technical impact: membutuhkan output prahitung dan manifest.
- Security/cost impact: biaya cloud lebih terkendali.
- Validation required: unit/synthetic tests dan cross-platform comparison.
