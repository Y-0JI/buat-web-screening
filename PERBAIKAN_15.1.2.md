# PERBAIKAN 15.1.2 — Perbaikan Regresi: Pengambilan Data IDX JSON Tidak Pernah Benar-benar Jalan

## Kenapa dokumen ini dibuat

Ini regresi baru yang muncul dari perbaikan sebelumnya (PERBAIKAN 15.1). Bagian kode yang
seharusnya mengambil daftar ticker dari endpoint JSON resmi IDX ternyata salah cara
penulisannya, sehingga proses pengambilan datanya **tidak pernah benar-benar dijalankan**
sama sekali — bukan gagal karena diblokir Cloudflare, tapi gagal karena bagian ini
tidak pernah dieksekusi isinya.

## Masalah

**File terkait:** `backend/app/data/ticker_sync.py`, bagian fungsi yang mengambil data dari
endpoint JSON IDX.

Fungsi ini dijalankan di thread terpisah (supaya tidak memblokir proses lain selagi
menunggu request internet selesai). Tapi cara fungsi bagian dalamnya ditulis salah tipe —
seharusnya fungsi biasa, malah ditulis sebagai fungsi asynchronous. Akibatnya, ketika
dijalankan di thread terpisah, isi fungsinya (request ke internet, ambil data, susun hasil)
tidak pernah benar-benar dieksekusi. Yang dikembalikan bukan hasil data, tapi semacam
"janji proses" yang belum pernah ditepati.

Efeknya: proses sync ticker dari sumber IDX JSON akan selalu gagal (atau error), walaupun
endpoint-nya sendiri sebenarnya bisa diakses dengan lancar tanpa halangan apa pun. Ini bikin
seolah-olah "IDX masih diblokir", padahal masalahnya ada di cara pemanggilan fungsinya
sendiri, bukan di jaringan/Cloudflare.

## Target hasil

Bagian kode yang mengambil data dari endpoint JSON IDX (request ke internet lewat
`curl_cffi`, lalu susun hasilnya jadi daftar ticker) harus benar-benar dieksekusi
sepenuhnya saat dipanggil, dan mengembalikan daftar ticker asli (list berisi dict ticker),
bukan objek "janji proses" yang belum jalan.

Cara paling aman: pastikan fungsi-fungsi kecil di dalam bagian ini (yang melakukan request
dan yang menyusun hasil parsing) ditulis sebagai fungsi biasa/synchronous, bukan
asynchronous — karena proses di dalamnya (request internet lewat `curl_cffi`, susun dict)
memang tidak butuh ditunggu secara asynchronous, dan memang dirancang untuk dijalankan di
thread terpisah sebagai satu kesatuan.

## Verifikasi wajib

- Panggil manual fungsi pengambil data IDX JSON ini sendirian (bukan lewat seluruh alur
  sync), dan print/log hasilnya. Hasilnya harus berupa daftar/list berisi data ticker
  (atau list kosong kalau memang gagal terhubung/ditolak server) — **bukan** objek jenis
  lain yang bukan list.
- Pastikan tidak ada warning semacam "coroutine was never awaited" di log setelah
  pemanggilan fungsi ini.
- Jalankan proses sync ticker penuh (`fetch_and_store_tickers`) sekali secara manual, cek
  log akhir: kalau endpoint IDX memang bisa diakses, harus tercatat sebagai sync berhasil
  dengan jumlah ticker yang masuk akal (bukan langsung gagal seperti sebelumnya). Kalau
  memang endpoint IDX kebetulan diblokir/error di sisi server, itu wajar dan boleh tetap
  tercatat gagal — yang penting kegagalannya sekarang benar-benar berasal dari koneksi,
  bukan dari bug penulisan kode ini lagi.
- Cek juga bagian lain di file yang sama dan file sejenis (`backend/app/data/fetcher.py`)
  untuk memastikan tidak ada pola serupa (fungsi asynchronous yang dijalankan di thread
  terpisah) yang kelewat — kalau ketemu, samakan perbaikannya.
