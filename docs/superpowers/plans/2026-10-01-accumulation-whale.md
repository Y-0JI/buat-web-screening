# Deteksi Akumulasi Pemain Besar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menambah tool AI yang menemukan saham IDX yang baru mulai diakumulasi pemain besar, hasil dari scan harian hemat kuota yang disimpan di DB dan dirender sebagai kartu.

**Architecture:** Scan harian funnel bertingkat (A: market-cap + screener → B: history untuk kandidat → C: broker untuk kandidat teratas) yang tunduk pada kuota `x-ratelimit-remaining`, hasil disimpan sebagai `accumulation_scans` + `accumulation_signals`. Agent tool & endpoint hanya membaca hasil tersimpan; frontend menampilkan kartu baru.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, httpx, pytest-style script test + `httpx.MockTransport`, Next.js 15 / React 19 / Tailwind, lightweight-charts (tidak berubah).

## Global Constraints

- Kuota: header `x-ratelimit-remaining` = sumber kebenaran; penghitung lokal hanya cadangan.
- Idempotent per tanggal data; skip akhir pekan/libur bursa (dari tanggal data, bukan kalender).
- `POST /api/accumulation/scan` wajib secret token + single-flight lock.
- Simpan komponen mentah sinyal untuk re-skor.
- Backtest tanpa look-ahead.
- `flow=F` = "arus asing", JANGAN dilabeli "institusi" di UI/reasons.
- Tanpa dependency baru; tanpa provider baru; tanpa data palsu di jalur produksi.
- Jalur eksekusi berhenti (STOP) setelah Task 0 untuk laporan ke pengguna.

---

### Task 0: Tahap 0 — Verifikasi respons API nyata (CHECKPOINT, WAJIB LAPOR DULU)

**Files:**
- Create (sementara, tidak di-commit): `/tmp/opencode/tahap0_probe.py`

**Interfaces:**
- Consumes: `app.config.settings`, `app.providers.idx_edge_provider.IdxEdgeProvider`.
- Produces: laporan ke pengguna (respons terpotong + `x-ratelimit-remaining` sebelum/sesudah + kriteria A→B).

- [ ] **Step 1: Tulis skrip probe**

Buat `/tmp/opencode/tahap0_probe.py` yang (a) membaca `settings` dari `backend/.env`,
(b) memakai `httpx` langsung ke `settings.idx_edge_base_url` dengan header
`X-API-Key`, (c) mencetak `status`, header `x-ratelimit-remaining`/`x-ratelimit-limit`,
dan potongan JSON, untuk:

1. `GET /api/history/BBCA?frame=daily&limit=1000` → hitung `len(rows)`, cek kunci
   `f_buy`, `f_sell`, `n_foreign`, `avg` pada baris pertama/terakhir.
2. `GET /api/broker-accumulation/BBCA` → cetak kunci top-level + contoh `series[0]`,
   `top_buyers[0]`, `top_sellers[0]`.
3. `GET /api/broker-summary/BBCA?start_date=<30 hari lalu>&end_date=<hari ini>&net=true`
   → cetak jumlah `brokers`, `broker_levels`, rentang tanggal.
4. `GET /api/screener/latest` → cetak kunci top-level + contoh 1 baris + set `bucket`.
5. `GET /api/market-cap?page=1&per_page=50` → cetak kunci baris + cek field turnover/likuiditas.

Jalankan dari `backend/` memakai venv: `./.venv/bin/python /tmp/opencode/tahap0_probe.py`.

- [ ] **Step 2: Jalankan & kumpulkan bukti**

Catat `x-ratelimit-remaining` **sebelum** dan **sesudah** kelima panggilan.

- [ ] **Step 3: Tetapkan kriteria Tahap A→B**

Berdasarkan field nyata dari market-cap + screener, tulis kriteria eksplisit
(market-cap tidak memuat pergerakan harga):
- seed: semua baris `screener/latest` (bucket vendor = penanda kandidat, bukan skor);
- universe: `turnover_ratio` bersifat relatif (jangan urutkan desc mentah),
  pakai batas bawah `market_cap`, stratifikasi + rotasi irisan antar-hari agar
  seluruh emiten terjangkau;
- likuiditas absolut diukur di Tahap B dari kolom `value` history.
Sertakan kriteria ke dalam laporan.

- [ ] **Step 4: Laporkan & STOP**

Tempel ringkasan respons nyata (terpotong) + sisa kuota + kriteria A→B. Nyatakan
komponen yang tidak tersedia (dilewati, tanpa mengarang). **Berhenti dan minta
konfirmasi sebelum lanjut ke Task 1.**

---

### Task 1: Config + method provider baru

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/providers/idx_edge_provider.py`
- Test: `backend/test_idx_edge_provider.py` (tambah kasus)

**Interfaces:**
- Produces:
  - `settings.accumulation_*` (lihat spec §4).
  - `IdxEdgeProvider.fetch_broker_accumulation(code: str) -> Optional[dict]`
  - `IdxEdgeProvider.fetch_market_cap_all(max_pages: int = 25) -> list[dict]`
  - `IdxEdgeProvider.calls_today` (properti) dan `IdxEdgeProvider.reset_quota()`
  - `IdxEdgeProvider.last_ratelimit_remaining` (dari header, bila ada)

- [ ] **Step 1: Tambah setting** ke `config.py` sesuai spec §4.
- [ ] **Step 2: Simpan header kuota** di `_get_json`: set `self.last_ratelimit_remaining`
  dari `resp.headers.get("x-ratelimit-remaining")` (int bila bisa).
- [ ] **Step 3: `fetch_broker_accumulation`** ikut pola `_get_json` → `/api/broker-accumulation/{code}`.
- [ ] **Step 4: `fetch_market_cap_all`** loop halaman sampai `total_pages` atau `max_pages`,
  gabungkan `data`. Hentikan bila provider nonaktif / `None`.
- [ ] **Step 5: Test** dengan `httpx.MockTransport` (tipe respons + header kuota),
  jalankan `./.venv/bin/python test_idx_edge_provider.py`.
- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/app/providers/idx_edge_provider.py backend/test_idx_edge_provider.py
git commit -m "feat(accumulation): config + provider broker-accumulation & market-cap paginasi"
```

---

### Task 2: Tabel DB + migrasi + repository

**Files:**
- Modify: `backend/app/database/models.py` (tambah `AccumulationScan`, `AccumulationSignal`)
- Create: `backend/alembic/versions/<rev>_add_accumulation_tables.py`
- Create: `backend/app/repositories/accumulation_repository.py`
- Test: `backend/test_accumulation_repository.py`

**Interfaces:**
- Produces (repository, dict polos):
  - `save_scan(scan_date, status, counts, requests_used, quota_remaining, note, signals) -> int`
  - `get_scan_by_date(scan_date) -> Optional[dict]`
  - `get_latest_scan() -> Optional[dict]` (scan + signals)
  - `get_signal(ticker) -> Optional[dict]`
  - `list_signals(scan_id, limit) -> list[dict]`
  - `forward_returns(ticker, date) -> ...` (untuk backtest, baca komponen mentah)

- [ ] **Step 1: Model ORM** sesuai spec §5 (JSON `components`, `reasons` Text).
- [ ] **Step 2: Migrasi Alembic** idempoten (cek `inspect(bind).get_table_names()`),
  `down_revision` = revisi terakhir.
- [ ] **Step 3: Repository** mengikuti pola `chat_repository` (async_session, dict polos).
- [ ] **Step 4: Test** repository (SQLite sementara) → simpan & baca kembali; jalankan
  `./.venv/bin/python test_accumulation_repository.py`.
- [ ] **Step 5: Commit**

```bash
git add backend/app/database/models.py backend/alembic/versions backend/app/repositories/accumulation_repository.py backend/test_accumulation_repository.py
git commit -m "feat(accumulation): tabel scans/signals + migrasi + repository"
```

---

### Task 3: Modul sinyal & skor (murni)

**Files:**
- Create: `backend/app/analysis/__init__.py`
- Create: `backend/app/analysis/accumulation.py`
- Test: `backend/test_accumulation_signals.py`

**Interfaces:**
- Produces:
  - `hv_signals(points: list[dict]) -> dict` — OBV, A/D, CMF, absorption, basing, vwap_pos, runup.
  - `foreign_signal(points: list[dict]) -> dict` — net asing konsisten.
  - `broker_signals(payload: dict) -> dict` — konsentrasi, avg pembeli vs harga, persistensi.
  - `score(components: dict, weights: dict) -> tuple[float, str, list[str]]` — (skor, depth, reasons).
  - `depth_label(has_hv, has_foreign, has_broker) -> str`.

- [ ] **Step 1: Tulis test** dengan OHLCV sintetis deterministik (mis. pola akumulasi
  vs distribusi) yang mengassert arah sinyal, bukan angka ajaib.
- [ ] **Step 2: Implementasi** rumus OBV/A-D/CMF/VWAP/absorption/basing/runup + foreign + broker.
- [ ] **Step 3: Implementasi `score`** (bobot dari settings) + `depth_label` + reasons.
  Pastikan reasons TIDAK memakai kata "institusi" untuk `flow=F` (pakai "arus asing").
- [ ] **Step 4: Jalankan** `./.venv/bin/python test_accumulation_signals.py`.
- [ ] **Step 5: Commit**

```bash
git add backend/app/analysis backend/test_accumulation_signals.py
git commit -m "feat(accumulation): sinyal harga-volume/asing/broker + skor"
```

---

### Task 4: Orkestrator funnel + trigger endpoint (token + lock)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/accumulation_scan.py`
- Create: `backend/app/routers/accumulation.py`
- Modify: `backend/app/main.py` (daftarkan router)
- Test: `backend/test_accumulation_scan.py`

**Interfaces:**
- Produces:
  - `async run_scan(force: bool = False) -> dict` — menjalankan funnel, idempotent per
    tanggal data, skip libur, jaga kuota (pakai `x-ratelimit-remaining` bila ada,
    else `calls_today`), simpan complete/partial.
  - `router` dengan `POST /api/accumulation/scan` (header `X-Scan-Token`), `GET /latest`,
    `GET /{ticker}`.
  - Lock single-flight: module-level `asyncio.Lock`; panggilan kedua → 409/`{"success": false, "busy": true}`.
  - Rotasi universe: pilih irisan berdasarkan strata market cap + ticker yang paling
    lama tidak dicek (`last_checked`), disimpan per ticker (kolom/tabel pendukung).
  - Validasi parameter sebelum request (limit history ≤ `accumulation_max_history_limit`).
  - Freshness: bandingkan tanggal bar history terbaru dengan tanggal data bursa;
    tandai `stale` bila basi.

- [ ] **Step 1: Test** funnel dengan provider bermock (MockTransport) → pastikan
  A→B→C dipanggil, batas kandidat dihormati, hasil partial saat kuota menipis.
- [ ] **Step 2: Implementasi `run_scan`** (funnel + quota guard + idempotensi + skip libur).
- [ ] **Step 3: Implementasi router** (token check `hmac.compare_digest`, lock, JSON).
- [ ] **Step 4: Daftarkan router** di `main.py`.
- [ ] **Step 5: Jalankan** `./.venv/bin/python test_accumulation_scan.py`.
- [ ] **Step 6: Commit**

```bash
git add backend/app/services backend/app/routers/accumulation.py backend/app/main.py backend/test_accumulation_scan.py
git commit -m "feat(accumulation): orkestrator funnel + endpoint scan (token + single-flight)"
```

---

### Task 5: Tool agent + event SSE + kartu frontend

**Files:**
- Modify: `backend/app/ai/agent.py` (TOOL_SPECS + event `accumulation` + system prompt)
- Modify: `frontend/src/lib/chat.ts` (tipe + `ChatEvent` + fetch)
- Create: `frontend/src/components/chat/accumulation.tsx`
- Modify: `frontend/src/components/chat/types.ts` (`UIMessage.accumulations`)
- Modify: `frontend/src/components/chat/message.tsx`
- Modify: `frontend/src/components/chat/chat-app.tsx` (event + replay)

**Interfaces:**
- Consumes: `accumulation_repository.get_latest_scan()`, `GET /api/accumulation/latest`.
- Produces: tool `get_accumulation_candidates(limit?)`, SSE `{type:"accumulation", scan_date, status, candidates}`, komponen `AccumulationCard`.

- [ ] **Step 1: Tool agent** baca hasil tersimpan; deskripsi menyebut keterbatasan
  (bukan institusi; kedalaman data).
- [ ] **Step 2: Event SSE** `accumulation` dikirim saat tool sukses.
- [ ] **Step 3: Tipe & fetch frontend**; `AccumulationCard` menampilkan skor, alasan,
  `scan_date`, `depth`, dan status partial; pesan kosong/error jelas.
- [ ] **Step 4: Render + replay** di `message.tsx` & `chat-app.tsx`.
- [ ] **Step 5: Verifikasi** `cd frontend && bunx tsc --noEmit && bun run build`.
- [ ] **Step 6: Commit**

```bash
git add backend/app/ai/agent.py frontend/src/lib/chat.ts frontend/src/components/chat
git commit -m "feat(accumulation): tool agent, event SSE, dan kartu frontend"
```

---

### Task 6: Penjadwalan (cron/systemd)

**Files:**
- Create: `backend/scripts/run_accumulation_scan.sh`
- Create: `backend/scripts/accumulation-scan.service` (contoh)
- Create: `backend/scripts/accumulation-scan.timer` (contoh)
- Create: `backend/scripts/README.md` (cara pakai)

- [ ] **Step 1: Skrip** memanggil `POST /api/accumulation/scan` dengan header
  `X-Scan-Token` (dari env), cetak hasil.
- [ ] **Step 2: Unit systemd** (service+timer) contoh setelah pasar tutup; sebutkan
  alternatif cron.
- [ ] **Step 3: Commit**

```bash
git add backend/scripts
git commit -m "chore(accumulation): skrip + unit systemd/cron untuk scan harian"
```

---

### Task 7: Backtest (tanpa look-ahead)

**Files:**
- Create: `backend/scripts/backtest_accumulation.py`
- Test: `backend/test_accumulation_backtest.py`

**Interfaces:**
- Consumes: `accumulation_repository` + provider `fetch_history` (dicache).
- Produces: laporan return 5/10/20 hari vs rata-rata sampel pasar.

- [ ] **Step 1: Implementasi** hanya memakai data ≤ tanggal sinyal untuk skor; return
  masa depan untuk evaluasi saja. Batasi request history + quota guard.
- [ ] **Step 2: Test** dengan data sintetis memastikan tidak ada look-ahead.
- [ ] **Step 3: Jalankan & commit**

```bash
git add backend/scripts/backtest_accumulation.py backend/test_accumulation_backtest.py
git commit -m "feat(accumulation): skrip backtest tanpa look-ahead"
```

---

### Task 8: Verifikasi menyeluruh

- [ ] **Step 1:** Jalankan semua test backend (`.venv/bin/python test_*.py`) & tempel output.
- [ ] **Step 2:** `cd frontend && bun run build` & tempel output.
- [ ] **Step 3:** Trigger `POST /api/accumulation/scan` (token) → tempel jumlah request
  siklus + sisa kuota + status complete/partial.
- [ ] **Step 4:** Tunjukkan ≥3 saham nyata (likuid, kurang likuid, sudah lari) + rincian;
  bukti kartu tampil di UI.
- [ ] **Step 5:** Laporkan jujur komponen yang tidak bisa dikerjakan + alasan.

---

## Self-Review

- Spec §3 kuota (header = kebenaran) → Task 1 (simpan header) + Task 4 (guard).
- Spec §4 config → Task 1. §5 DB → Task 2. §6 sinyal → Task 3. §7 skor/re-skor → Task 2 (JSON) + Task 3.
- §8 funnel + idempotent + skip libur + single-flight → Task 4. §9 integrasi → Task 5. §10 cron → Task 6.
- §11 Tahap 0 → Task 0 (gated STOP). §12 backtest tanpa look-ahead → Task 7.
- Tambahan wajib: token+lock (Task 4), kuota header (Task 1), kriteria A→B dilaporkan (Task 0),
  idempotent+skip libur (Task 4), simpan komponen mentah (Task 2), flow=F bukan institusi (Task 3).
- Placeholder: Task 0 detail cukup; Task 1–7 berisi interface konkret; kode rinci
  sinyal/orkestrasi difinalkan setelah Task 0 sesuai instruksi "verifikasi dulu".
