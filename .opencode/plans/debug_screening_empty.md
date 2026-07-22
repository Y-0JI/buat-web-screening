# Debug: Screening kosong ("Tidak ada data screening tersedia")

## Root cause (terbukti lewat analisis kode + config)

`GET /api/screen` (`backend/app/routers/screening.py:81-98`) saat cache
cold menjalankan `run_batch_scan(mode)` **synchronous di dalam request**
(screening.py:90). `run_batch_scan` (`scheduler.py:30-66`) memindai
**SELURUH universe** lewat `get_listed_tickers()` — DB punya **978 ticker
aktif** (cek sqlite: `listed_tickers` total 978, active 978).

Tiap `scan_one` memanggil `stock_service.get_price` yang di-throttle
`RequestScheduler` **60/menit** (`config.py:17`, `providers/scheduler.py:22`).
→ 978 ticker ÷ 60/menit ≈ **16 menit** untuk 1 kali cold scan.

Frontend `screenStocks` pakai axios **timeout 45 detik** (`frontend/src/lib/api.ts:5`).
Jadi request cold screen pasti **timeout** → `catch` di `screening-view.tsx:27`
→ `setItems([])` → tampilan "Tidak ada data screening tersedia."

Cache `screen` TTL **2 jam** (`cache/ttl.py:15`). Scheduler `run_daily_scan`
dijadwalkan 16:30 WIB (`main.py:104-117`) untuk pre-warm. Tapi screening cuma
isinya kalau: server hidup pas 16:30 **DAN** dalam 2 jam sejak scan terakhir.
Setelah restart / >2 jam idle → cache cold → load pertama selalu timeout → kosong.

Kode sendiri sudah menandai ini (screening.py:85-89): *"cold miss men-scan
SELURUH universe … jadikan background job bila latency cold-miss jadi masalah."*

## Bukti pendukung
- `listed_tickers`: 978 aktif → universe besar, bukan sample.
- `SCREEN_TTL = 7200` (2 jam) → cache bisa expired di luar window pre-warm.
- `rate_limit_per_minute = 60` → cold scan ~16 menit ≫ timeout 45s.
- Frontend: `catch { setItems([]) }` → empty state, bukan error visible.

## Kesimpulan
Bukan bug data/ticker — screening EMPTY karena request cold scan kehabisan
waktu (45s) sebelum 978 ticker selesai dipindai (~16 menit). Desain
synchronous in-request scan adalah akar masalahnya.

## Rencana fix (usulan, butuh pilihan user — lihat bawah)

### 1. Jangan scan di dalam request (wajib)
Di `screen()`, bila cache cold: jalankan `run_batch_scan` lewat
`fastapi.BackgroundTasks` (atau `asyncio.create_task`), **kembalikan cache
sekarang (boleh kosong) langsung** dengan flag `pending/generating` +
`generated_at=None`. Request selesai <1s, tidak timeout.

### 2. Pre-warm saat startup (direkomendasikan)
Di `lifespan` (`main.py`), panggil `run_daily_scan()` sebagai task
non-blocking saat boot supaya cache hangat beberapa menit setelah server
nyala (menutup kasus "baru restart").

### 3. Frontend "sedang diproses" (wajib kalau #1)
`screening-view.tsx`: bila `generated_at === undefined` / flag `pending`,
tampilkan "Screening sedang diproses, muat ulang dalam beberapa menit" —
bukan "Tidak ada data."

### 4. (Opsional) percepat cold scan
16 menit tetap lama walau background. Kalau mau data muncul lebih cepat:
naikkan `rate_limit_per_minute`, atau pakai endpoint screener bulk IDX
(`SCREENER_TTL`) daripada scan per-ticker. Perubahan lebih besar — tunda
kalau cukup dengan #1–#3.

## Verifikasi
- `curl "/api/screen?mode=BSJP"` balik <2s (langsung, bukan nunggu 16 menit),
  `success:true`, `data` mungkin `[]` sekali lalu terisi setelah background
  scan selesai.
- Reload beberapa menit → `data` terisi ratusan ticker.
- `npx tsc --noEmit` bersih.
- Dev server: ganti mode BSJP/BPJS tidak pernah timeout/empty lagi.
