# Penjadwalan Scan Akumulasi

Script `run_accumulation_scan.sh` memicu `POST /api/accumulation/scan`, lalu
menunggu scan selesai dan mencatat ringkasan: `scan_date`, `status`,
`requests_used`, `quota_remaining`, jumlah sinyal.

## Prasyarat

1. Backend berjalan dan `ACCUMULATION_SCAN_TOKEN` diset di `.env` backend.
2. Token yang sama diletakkan di file environment **di luar repo**, mis.
   `/etc/idx-accumulation.env` (jangan commit ke git):

   ```ini
   ACCUMULATION_SCAN_TOKEN=ganti-dengan-token-acak
   ACCUMULATION_API_URL=http://localhost:8000
   ACCUMULATION_MAX_RETRIES=5
   ACCUMULATION_RETRY_DELAY=900
   ```

   Lindungi file: `chmod 600 /etc/idx-accumulation.env`.

## Uji manual

```bash
set -a; . /etc/idx-accumulation.env; set +a
/opt/idx-copilot/backend/scripts/run_accumulation_scan.sh
```

Keluar **0** bila sukses/skip wajar; **non-nol** saat gagal (token salah,
koneksi gagal, atau tetap "data tidak berubah" setelah semua percobaan).

## systemd (disarankan, mendukung Persistent)

```bash
sudo cp backend/scripts/accumulation-scan.service /etc/systemd/system/
sudo cp backend/scripts/accumulation-scan.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now accumulation-scan.timer
systemctl list-timers accumulation-scan.timer
journalctl -u accumulation-scan.service -n 50
```

Timer: Senin-Jumat 19:30 `Asia/Jakarta` (setelah pasar tutup), `Persistent=true`.

## cron (alternatif, tanpa Persistent)

```bash
sudo cp backend/scripts/accumulation-scan.cron /etc/cron.d/accumulation-scan
sudo chmod 644 /etc/cron.d/accumulation-scan
```

Log ke `/var/log/accumulation-scan.log`. Bila cron tidak mendukung `CRON_TZ`,
jalankan pada `12:30` UTC.

## Perilaku retry

Bila respons `200` dengan alasan "data tidak berubah" (mis. data belum terbit /
libur bursa) dan hari ini **bukan** Sabtu/Minggu, script mengulang hingga
`ACCUMULATION_MAX_RETRIES` kali dengan jeda `ACCUMULATION_RETRY_DELAY` detik,
lalu menyerah dengan log jelas (exit 2).

## Catatan keamanan

- **Tidak ada secret di repo.** Token hanya dibaca dari environment.
- Endpoint scan menolak dengan **403** bila token backend kosong atau salah.

## Ukuran kuota

Satu siklus penuh (setelan default) ≈ **212 request** (market-cap ~20 + screener
1 + history ≤150 + broker ≤40 + probe), meninggalkan cadangan
`ACCUMULATION_QUOTA_RESERVE` untuk chat. Scan idempotent per tanggal data: bila
data belum berubah, tidak ada scan ulang.
