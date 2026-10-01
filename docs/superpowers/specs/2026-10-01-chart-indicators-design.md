# Desain: Indikator Chart Interaktif (gaya TradingView)

Tanggal: 2026-10-01
Status: Menunggu implementasi
Pendekatan: Hitung indikator di frontend, toggle per-chart, state diingat di localStorage

## 1. Latar Belakang

Chart candlestick di chat (`frontend/src/components/chat/chart.tsx`) memakai
`lightweight-charts` v5.2.1 dan hanya menampilkan candle + volume. Data OHLCV
sudah tersedia dari backend (`UIChart.series`, hasil tool `get_price_history`).

Pengguna ingin indikator teknikal yang bisa dinyalakan/dimatikan seperti
TradingView, tanpa memuat ulang chart.

## 2. Tujuan & Non-Tujuan

Tujuan:
- Menambah indikator overlay (di atas candle) dan panel bawah (oscillator).
- Tombol toggle di header chart untuk aktif/nonaktif tiap indikator.
- Pilihan diingat di `localStorage` dan dipakai untuk chart-chart berikutnya.

Non-tujuan:
- Tidak mengubah backend, API, atau kontrak `UIChart`.
- Tidak menambah fitur ubah parameter indikator (pakai nilai standar).
- Tidak menambah toolbar gambar/drawing seperti TradingView penuh.
- Tidak menambah AI agar menyebut angka indikator.

## 3. Set Indikator

| Indikator | Jenis | Parameter standar | Pane |
|---|---|---|---|
| EMA13 | Overlay | 13 | utama |
| EMA21 | Overlay | 21 | utama |
| EMA100 | Overlay | 100 | utama |
| EMA200 | Overlay | 200 | utama |
| Bollinger Bands | Overlay | 20, 2 | utama |
| Volume | Panel | — | bawah |
| Stochastic | Panel | 14, 3, 3 | bawah |
| RSI | Panel | 14 | bawah |
| MACD | Panel | 12, 26, 9 | bawah |

Kondisi awal:

- Aktif: Volume, Stochastic, EMA13, EMA21, EMA100, EMA200.
- Non-aktif: Bollinger Bands, RSI, MACD.

## 4. Arsitektur & Komponen

### 4.1 File baru: `frontend/src/lib/indicators.ts`

Kumpulan fungsi murni (tanpa dependensi baru). Input `HistoryPoint[]` + periode,
output array `LineData[]` atau `HistogramData[]` (`{ time, value }`) dengan
`time` = `point.date` agar sejajar dengan seri candle.

Fungsi yang disediakan:

- `ema(points, period): LineData[]`
- `sma(values, period): (number | null)[]` (pembantu Bollinger)
- `bollinger(points, period = 20, mult = 2): { upper, middle, lower }` — tiga `LineData[]`
- `rsi(points, period = 14): LineData[]`
- `macd(points, fast = 12, slow = 26, signal = 9): { macd, signal, histogram }`
- `stochastic(points, kPeriod = 14, kSmooth = 3, dPeriod = 3): { k, d }`

Aturan umum: nilai yang belum cukup data (indeks < periode) dilewati (tidak
dimasukkan ke array), sehingga garis mulai saat data cukup. Tidak crash untuk
data pendek.

### 4.2 Perubahan: `frontend/src/components/chat/chart.tsx`

- Definisi `IndicatorId` dan metadata (label, jenis overlay/panel, warna default).
- State `active: IndicatorId[]`, diinisialisasi dari `localStorage`
  (`idx_chart_indicators`), fallback ke daftar default bila kosong/rusak.
- Bar toggle berupa pill button di header chart; klik = toggle, lalu simpan ke
  `localStorage`.
- Overlay: satu `LineSeries` per EMA dan tiga `LineSeries` untuk Bollinger
  (upper/middle/lower), semuanya di pane utama.
- Panel bawah: tiap indikator panel memakai `chart.addSeries(..., paneIndex)`
  pada pane hasil `chart.addPane()`, dan `panes()[i].setHeight(80)`.
  Saat toggle off, `chart.removeSeries(...)`; pane kosong otomatis hilang
  (`preserveEmptyPane` default `false`).
- Tinggi chart dinamis: `256 + 80 × jumlah panel bawah aktif`.
- Setelah perubahan toggle: `setData` ulang seri terkait, lalu
  `timeScale().fitContent()`.

Urutan pane tetap: **Volume, Stochastic, RSI, MACD**. Pane hanya "bergeser"
saat salah satu dimatikan, dan pemetaan dihitung ulang dari daftar aktif
sebelum membuat seri, sehingga indeks pane selalu konsisten.

Warna default overlay: EMA13 `#22d3ee`, EMA21 `#f59e0b`, EMA100 `#a78bfa`,
EMA200 `#f472b6`; Bollinger upper/lower `#71717a`, middle `#a1a1aa` (putus-putus).

## 5. Alur Data

```
chart.series (OHLCV) ──► indicators.ts (hitung) ──► setData() seri indikator
        │
        └── active (localStorage) ──► menentukan seri/pane mana yang dibuat
```

Tidak ada request backend tambahan; semua dihitung dari data yang sudah ada.

## 6. Penanganan Error & Edge Case

- **Data pendek**: indikator tampil sebagian atau garis kosong; tidak error.
- **localStorage kosong/rusak**: fallback ke daftar default.
- **Resize**: `ResizeObserver` yang ada tetap dipakai; tinggi mengikuti jumlah pane.
- **Toggle cepat berulang**: buat/hapus seri secara idempoten berdasarkan state.
- **Bollinger deviasi 0**: hindari pembagian nol; hasil garis lurus di harga tengah.

## 7. Verifikasi

- `bun run build` (typecheck + build) sukses.
- Manual di browser:
  1. Toggle tiap indikator on/off; seri/pane muncul dan hilang tanpa error.
  2. Nilai EMA/RSI/MACD/Stochastic tampak wajar.
  3. Refresh halaman → pilihan toggle tersimpan.
  4. Buka chart dengan data pendek (< 200 bar) → tidak crash.
- Repository tidak punya test runner frontend; tidak menambah unit test
  (YAGNI). Fungsi murni `indicators.ts` bisa diverifikasi dengan skrip cepat
  bila diperlukan.

## 8. Risiko

- Pengelolaan indeks pane saat toggle on/off bisa keliru bila urutan tidak
  dijaga; dimitigasi dengan urutan pane tetap.
- Chart terlalu padat bila semua panel aktif; tinggi dinamis menangani ini.
