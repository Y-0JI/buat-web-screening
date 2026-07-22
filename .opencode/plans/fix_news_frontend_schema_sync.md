# Plan — Sinkron Frontend News ke Schema Backend (16.4.4 E2E)

## Hasil Verifikasi E2E (read-only)

Pipeline backend **sudah benar** (bukti live test 16.4.4 + smoke test):
- Provider: IDX `GetProfileAnnouncement` live 200 + items; RSS 100 items; Yahoo
  kadang kosong (.JK, normal). ✅
- Normalisasi: 7 field kanonik terisi (`headline`, `publisher`,
  `published_date`, `summary`, `url`, `related_ticker`, `source`),
  `related_ticker`/`source` konsisten. ✅
- Endpoint `GET /api/stock/{ticker}/news` → `data: NewsItem[]` berisi headline
  nyata (bukan item kosong). ✅

**Root cause konten kosong = frontend tidak sinkron schema** (bukan backend):
- `frontend/src/lib/api.ts:322` `NewsItem` = `title`/`link`/`published` (lama).
- `frontend/src/components/renderers/stock-report.tsx:46,55-57,86,91-92` mapping
  & render `n.title`/`n.link`/`n.published` → `undefined` di response baru →
  card ke-render tapi isinya kosong.

## Fix (minimal — 2 file frontend, backend tidak diubah)

### 1. `frontend/src/lib/api.ts` — update `NewsItem`
Ganti ke field kanonik backend:
```ts
export interface NewsItem {
  headline: string;
  publisher: string;
  published_date: string;
  summary?: string;
  url: string;
  related_ticker: string;
  source: string;
}
```

### 2. `frontend/src/components/renderers/stock-report.tsx` — `NewsSection`
- `useState` type → `Array<NewsItem>` (import dari `api`) atau inline field baru.
- Mapping (baris 55-57): `res.data.map(n => ({ headline: n.headline,
  publisher: n.publisher, url: n.url, published_date: n.published_date,
  source: n.source }))`.
- Render (baris 84-93): `href={n.url}`, judul `{n.headline}`, subtitle
  `{n.publisher} · {n.source} · {n.published_date}`.

## Verifikasi (saat eksekusi, di luar plan mode)
- `cd frontend && npx tsc --noEmit` (atau `bun run build`) → tidak ada type error.
- Jalankan dev, buka halaman riset sebuah emitter (mis. BBCA) → NewsSection
  menampilkan ≥1 berita dengan headline + sumber + tanggal, link bisa diklik.
- Konfirmasi backend tetap return headline (sudah terbukti; cukup curl
  `GET /api/stock/BBCA/news` untuk pastikan `data[0].headline` terisi).

## Scope
- Tidak ubah backend (sudah benar & lolos test 16.4.4).
- Tanpa dependensi baru.
- Ini menjembatani sebagian 16.4.6 (wiring field di NewsSection yg ada), bukan
  bikin News Card baru. Bila mau card 16.4.6 penuh, kerjakan terpisah.
