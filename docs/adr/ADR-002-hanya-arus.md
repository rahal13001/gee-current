# ADR-002 — Ruang Lingkup Hanya Arus

- Status: `PROPOSED` (diwarisi dari PRD)
- Context: Fokus ilmiah proyek adalah komponen arus laut.
- Decision: Hanya `uo` dan `vo`; gelombang dan pasut lokal bukan scope inti.
- Alternatives: menambah gelombang memerlukan PRD/change control baru.
- Scientific impact: scope tetap terukur dan tidak mencampur fenomena.
- Technical impact: validator dan analytics fokus pada dua komponen.
- Security/cost impact: tidak ada perubahan.
- Validation required: cek variabel metadata aktif.
