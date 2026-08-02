# ADR-007 — Produk 11 Tahun Diprahitungkan

- Status: `PROPOSED` (diwarisi dari PRD)
- Context: Seri panjang tidak aman dihitung ulang di UI.
- Decision: produk 11 tahun diprahitungkan di Python atau batch.
- Alternatives: komputasi penuh per klik ditolak.
- Scientific impact: formula dan provenance produk harus tersimpan.
- Technical impact: GEE membaca derived assets/tables.
- Security/cost impact: mengendalikan EECU dan timeout.
- Validation required: benchmark dan rekonsiliasi nilai.
