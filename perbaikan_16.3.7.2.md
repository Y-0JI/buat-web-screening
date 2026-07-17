# Perbaikan 16.3.7.2 — Benahi Fitur Lupa/Reset Password

## Latar Belakang
Fitur lupa password & reset password di branch `fix/issue-105-login-register-ux` sudah berfungsi secara alur besar, tapi review menemukan beberapa hal yang perlu dibenahi sebelum digabung ke `main`: satu soal performa/stabilitas server, satu soal keamanan penyimpanan data, satu soal kesiapan untuk environment production, dan satu catatan kecil kebersihan kode.

## Tujuan
Memastikan fitur lupa/reset password aman dipakai di semua jenis environment (baik pakai SQLite maupun database production) dan tidak berisiko membuat server macet saat mengirim email.

## Ruang Lingkup

### 1. Pengiriman email reset password berpotensi bikin server macet (prioritas tertinggi)
Bagian yang mengirim email tautan reset password dijalankan langsung di alur permintaan utama server tanpa dipisah ke jalur tersendiri, padahal mengirim email itu proses jaringan yang bisa lambat atau nyangkut kalau server emailnya bermasalah/tidak responsif. Karena tidak ada juga batas waktu tunggu yang jelas, kalau proses kirim emailnya nyangkut, seluruh server bisa ikut macet untuk semua pengguna lain, bukan cuma pengguna yang lagi minta reset password.

**Yang perlu dilakukan:** pisahkan proses pengiriman email supaya tidak menahan alur utama server, dan pastikan ada batas waktu tunggu yang wajar (misal beberapa detik saja) sehingga kalau server email lambat/tidak responsif, permintaan pengguna tetap bisa selesai dengan wajar tanpa membuat bagian lain aplikasi ikut macet.

### 2. Token reset password sebaiknya tidak disimpan dalam bentuk aslinya
Saat ini kode rahasia untuk reset password disimpan di database persis apa adanya. Ini mirip seperti menyimpan password asli tanpa dienkripsi/di-hash — kalau suatu saat database bocor, kode reset yang masih aktif bisa langsung dipakai orang lain buat reset password akun siapa saja tanpa perlu tahu passwordnya.

**Yang perlu dilakukan:** simpan versi yang sudah diacak/di-hash dari kode reset tersebut di database (mirip cara password disimpan), lalu saat pengguna klik tautan resetnya, cocokkan dengan cara yang sama seperti verifikasi password, bukan membandingkan teks aslinya secara langsung.

### 3. Kolom database baru untuk fitur ini belum siap dipakai di environment production
Fitur ini menambah kolom baru di tabel pengguna. Saat ini, kolom baru itu cuma otomatis ditambahkan kalau memakai database SQLite (biasanya dipakai untuk pengembangan lokal). Kalau aplikasi dijalankan dengan database yang biasanya dipakai di production, kolom itu tidak akan pernah otomatis ditambahkan, sehingga fitur lupa/reset password akan gagal total di environment tersebut.

**Yang perlu dilakukan:** buat perubahan struktur database ini lewat mekanisme migrasi resmi yang sudah dipakai proyek ini (folder alembic yang sudah ada), bukan lewat penyesuaian manual yang cuma berlaku untuk SQLite. Dengan begitu, kolom baru ini akan ikut ter-update dengan benar di jenis database manapun yang dipakai.

### 4. Rapikan komentar yang sudah tidak sesuai (boleh sekaligus, dampak rendah)
Ada komentar di kode sisi frontend yang menyebut endpoint backend untuk fitur ini belum tersedia — padahal backend-nya sudah diimplementasi dalam perubahan yang sama. Perbarui atau hapus komentar itu supaya tidak membingungkan orang yang baca kode ini nanti.

## Kriteria Penerimaan
- Mengirim permintaan lupa password tidak membuat bagian lain aplikasi ikut lambat/macet, bahkan saat server email sedang lambat merespons atau tidak bisa dihubungi sama sekali.
- Kode reset password yang tersimpan di database tidak dalam bentuk yang bisa langsung dipakai walau database-nya dilihat langsung.
- Fitur lupa/reset password tetap berfungsi dengan benar baik di environment yang pakai SQLite maupun yang pakai database production, melalui mekanisme migrasi yang konsisten.
- Tidak ada komentar kode yang menyesatkan soal status ketersediaan endpoint.

## Verifikasi Wajib (harus benar-benar dijalankan, bukan hanya membaca kode)
1. Coba alur lupa password dari awal sampai akhir: minta reset, buka tautan yang didapat (lewat log kalau email belum dikonfigurasi, atau email asli kalau sudah), set password baru, lalu login pakai password barunya — pastikan semua berhasil.
2. Simulasikan kondisi server email lambat/tidak bisa dihubungi (misal alamat server email yang salah), lalu coba minta lupa password — pastikan permintaan tetap selesai dalam waktu wajar dan bagian lain aplikasi (misal buka halaman lain secara bersamaan) tetap responsif, tidak ikut macet.
3. Cek langsung isi tabel pengguna di database setelah minta reset password — pastikan kode reset yang tersimpan bukan teks yang sama persis dengan yang ada di tautan email/log.
4. Uji jalankan aplikasi dari kondisi database kosong sama sekali (bukan cuma SQLite yang sudah ada tabelnya), pastikan proses migrasi menyiapkan semua kolom yang dibutuhkan fitur ini dengan benar.
5. Laporkan hasil tiap poin verifikasi di atas (berhasil/gagal + detail singkat) sebagai bagian dari laporan penyelesaian.
