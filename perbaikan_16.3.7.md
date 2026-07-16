# Perbaikan 16.3.7 --- Peningkatan UX Login & Registrasi

## Latar Belakang

Halaman Login dan Registrasi masih dapat ditingkatkan agar lebih nyaman
digunakan serta mengikuti standar pengalaman pengguna pada aplikasi
modern.

## Tujuan

Meningkatkan kemudahan penggunaan halaman Login dan Registrasi tanpa
mengubah alur autentikasi yang sudah ada.

## Ruang Lingkup

-   Tambahkan fitur Show/Hide Password (ikon mata) pada seluruh field
    password.
-   Pastikan pengguna dapat menampilkan atau menyembunyikan password
    tanpa mengubah isi input.
-   Tambahkan tautan **Lupa Password** pada halaman Login.
-   Implementasikan alur Forgot Password yang sesuai dengan mekanisme
    autentikasi aplikasi.
-   Berikan pesan yang jelas apabila proses reset password berhasil
    maupun gagal.
-   Pastikan pengalaman penggunaan konsisten pada desktop dan mobile.
-   Pertahankan konsistensi tampilan dengan Design System aplikasi.

## Kriteria Penerimaan

-   Password dapat ditampilkan dan disembunyikan melalui ikon mata.
-   Status ikon berubah sesuai kondisi Show/Hide.
-   Isi password tetap tersimpan saat fitur digunakan.
-   Halaman Login memiliki tautan Lupa Password.
-   Pengguna dapat memulai proses reset password dengan alur yang jelas.
-   Tampilan responsif dan konsisten.
-   Tidak ada regresi pada proses Login maupun Registrasi.

## Catatan

Fokus utama perbaikan ini adalah meningkatkan pengalaman pengguna tanpa
mengubah alur autentikasi yang sudah berjalan.
