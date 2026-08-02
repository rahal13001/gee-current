# ADR-008 — GEE Interaktif Dibatasi

- Status: `PROPOSED` (diwarisi dari PRD)
- Context: GEE memiliki batas memory, timeout, dan agregasi.
- Decision: interaktif dibatasi pada satu depth, satu AOI, periode kecil/native scale.
- Alternatives: pekerjaan berat dipindahkan ke batch/Python.
- Scientific impact: mencegah hasil parsial tanpa bukti.
- Technical impact: filter awal dan reducer terkontrol.
- Security/cost impact: mengurangi risiko EECU.
- Validation required: benchmark Tahap 2.
