# Perbaikan 16.3.7.1 — Penyempurnaan Alur Forgot Password

## Latar Belakang

Setelah implementasi peningkatan UX Login & Registrasi, ditemukan bahwa fitur Forgot Password belum berjalan sesuai harapan. Meskipun akun pengguna telah terdaftar, proses reset password belum dapat mengenali akun secara konsisten.

---

## Tujuan

Memastikan alur Forgot Password berjalan dengan benar, konsisten dengan sistem autentikasi, dan memberikan pengalaman pengguna yang jelas.

---

## Ruang Lingkup

- Verifikasi kembali alur Forgot Password dari awal hingga akhir.
- Pastikan proses pencarian akun menggunakan mekanisme yang sama dengan Login.
- Pastikan email yang telah terdaftar dapat dikenali oleh sistem.
- Berikan pesan yang jelas untuk kondisi berhasil maupun gagal.
- Pastikan proses reset password terhubung dengan backend yang benar.
- Lakukan pengujian end-to-end terhadap seluruh alur reset password.

---

## Kriteria Penerimaan

- Email yang telah terdaftar dapat dikenali.
- Pengguna dapat memulai proses reset password tanpa error.
- Pesan kesalahan hanya muncul apabila email benar-benar tidak terdaftar.
- Alur Forgot Password konsisten dengan Login dan Registrasi.
- Tidak ada regresi pada sistem autentikasi.

---

## Catatan

Prioritaskan stabilitas dan konsistensi proses autentikasi. Pastikan seluruh alur Login, Registrasi, dan Forgot Password menggunakan mekanisme validasi yang sama sehingga pengalaman pengguna tetap konsisten.
