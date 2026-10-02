# Dashboard Utama — AI Copilot di Kanan, Chart di Kiri

## Tujuan
Ubah halaman utama (`/`) jadi dashboard ala Google Finance (lihat `aicopilot.png`):
panel AI chat pindah ke **kanan**, area **kiri/atas** berisi chart saham ala
`dashboard.png` dengan popup setting ala `dashsetting.png`.

## Layout
- Kiri/utama: header saham + chart candlestick + pemilih periode.
- Kanan: panel AI chat (pindahan dari tampilan chat sekarang).
- Tidak ada sidebar kiri. Daftar percakapan (thread) dipindah jadi menu/tombol
  di dalam panel AI.

## Chart (lihat `dashboard.png`)
- Default tampilkan **IHSG**. Di atas chart ada **kotak cari ticker** untuk ganti saham.
- Tampilkan: nama + kode saham, harga terakhir, perubahan + persen, info
  "Past <periode>", Lot, Val, baris OHLCV (O/H/L/C/Vol), chart candlestick,
  tombol periode `1D 1W 1M 3M YTD 1Y` (3Y/5Y dinonaktifkan karena batas API).
- **Jangan** tampilkan: tombol Alert, Following, Buy.

## Popup Setting (lihat `dashsetting.png`)
- Tombol roda gigi di chart membuka popup berisi:
  - **Show Indicator** (centang nyala/mati): MA, EMA, BOLL, Volume, Value,
    RSI, MACD, KDJ.
  - **Chart Type** (pilih satu): Candlestick, Line.
- Pilihan tersimpan (refresh tidak hilang). Parameter indikator pakai nilai
  standar, tidak perlu submenu pengaturan.

## Panel AI
- Isi dan perilaku chat tetap sama seperti sekarang (kirim pesan, streaming,
  ganti model, riwayat percakapan).
- Tambah tombol **minimize** (panel menciut jadi bar kecil, chat tetap jalan)
  dan **fullscreen** (panel menutupi seluruh layar, bisa dikembalikan).

## Backend (yang perlu ditambah)
- Endpoint baru `GET /api/quote/{ticker}`: harga terakhir, perubahan, persen,
  OHLC, volume, value, freq, nama saham.
- Endpoint history (`/api/history/{ticker}`): dukung periode `1W, 1M, 3M, YTD,
  1Y` dan sertakan field `value` dan `freq` di tiap baris.
- Kalau IHSG ternyata tidak didukung API, pakai BBCA sebagai default.

## Kriteria Selesai
1. Buka `/`: chart IHSG tampil dengan header lengkap, AI tampil di kanan.
2. Cari ticker lain (mis. BBCA): header dan chart ikut berubah.
3. Semua tombol periode berfungsi; 3Y/5Y nonaktif.
4. Popup setting: tiap indikator bisa dinyalakan/dimatikan, ganti
   Candlestick/Line berfungsi, pilihan tersimpan setelah refresh.
5. Panel AI: minimize dan fullscreen berfungsi, chat tetap bisa dipakai di
   semua mode, riwayat percakapan bisa dibuka dari dalam panel.
6. `bun run build` dan seluruh test lolos tanpa error.

## Batasan
- Jangan tambah library/dependensi baru.
- Jangan ubah perilaku chat/AI yang sudah ada selain posisi dan tombol
  minimize/fullscreen.
- Tag saham dan jumlah followers tidak tersedia di API, jadi tidak ditampilkan.
