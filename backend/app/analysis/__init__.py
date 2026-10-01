"""Analisis akumulasi pemain besar — murni, tanpa I/O & tanpa jaringan.

Semua perhitungan bekerja pada deret OHLCV yang sudah diurutkan naik dan
difilter `as_of` (siap backtest: tidak memakai data setelah `as_of`).

Kaidah penting:
- `flow=F` / arus asing BUKAN "institusi" — sebut "arus asing".
- Data kotor/kurang -> "tidak dinilai" beserta alasan, bukan skor.
"""
