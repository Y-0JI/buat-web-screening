import asyncio
import logging
import re
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.stock import ResearchRequest, ResearchResponse
from app.services import (
    stock_service,
    company_profile_service,
    news_service,
    fundamentals_service,
)
from app.utils.errors import AppError
from app.repositories.technical_cache import calculate_score_cached
from app.ai.orchestrator import enhance_with_ai
from app.database import get_session
from app.database.models import User, ScanHistory
from app.routers.auth import get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["research"])

# Filter kata umum bahasa Indonesia yang bukan ticker saham
_TICKER_STOP_WORDS = frozenset({
    "ADA", "AKAN", "ALSO", "AND", "APA", "API", "ARE", "ATAU", "BADAN", "BAIK",
    "BAGI", "BAHAYA", "BAIK", "BAKAL", "BANK", "BANYAK", "BEBERAPA", "BELI",
    "BENAR", "BENTUK", "BERAPA", "BERAT", "BERDASARKAN", "BERIKUT", "BISA",
    "BISA", "BISNIS", "BUKAN", "BURUK", "BUTUH", "CARA", "CUKUP", "DALAM",
    "DAN", "DAPAT", "DARI", "DATA", "DAFTAR", "DELAPAN", "DEMI", "DENGAN",
    "DEPT", "DERMA", "DIA", "DIBAWAH", "DIBELI", "DIBUTUHKAN", "DIDIK",
    "DIMANA", "DIMULAI", "DINI", "DIRI", "DULU", "DUA", "DUIT", "DUNIA",
    "EKONOMI", "EMA", "ENAM", "FIVE", "FOR", "FOUR", "FUND", "GAMBAR",
    "GENERAL", "GLOBAL", "GRATIS", "GULA", "HAL", "HANYA", "HARAP", "HARGA",
    "HARIAN", "HASIL", "HEBAT", "HOLD", "HUTANG", "INI", "INGIN", "INVEST",
    "INVESTASI", "ITU", "JADI", "JALAN", "JANGAN", "JENIS", "JUAL", "JUGA",
    "JULI", "JUMAT", "JUNI", "KABAR", "KALI", "KAMI", "KAPAN", "KARENA",
    "KASUS", "KECUALI", "KEBUTUHAN", "KEHIDUPAN", "KEKURANGAN", "KELAS",
    "KELOMPOK", "KEMAMPUAN", "KEMBALI", "KEMUDIAN", "KENAIKAN", "KENAPA",
    "KEPADA", "KERJA", "KITA", "KOMISI", "KONDISI", "KREDIT", "KURANG",
    "LAGI", "LAIN", "LAINNYA", "LALU", "LAMA", "LANGKAH", "LAPORAN", "LARIS",
    "LEBIH", "LIMIT", "LIMA", "LIPAT", "MAKAN", "MAKA", "MAKSIMAL", "MALAH",
    "MANA", "MANAGER", "MANFAAT", "MAMPU", "MARCH", "MASIH", "MASA", "MASALAH",
    "MAU", "MAY", "MEDIA", "MEI", "MEMBELI", "MEMILIKI", "MEMPUNYAI", "MENANG",
    "MENDAPAT", "MENGAPA", "MENGHASILKAN", "MENIT", "MENTERI", "MERAH",
    "MERUGI", "MESKI", "MILIK", "MINAT", "MINIM", "MINTA", "MISAL", "MODE",
    "MODAL", "MULAI", "MUNGKIN", "NAIK", "NAMA", "NANTI", "NILAI", "NING",
    "NOMOR", "NOVEMBER", "NUANSA", "NEGARA", "OBAT", "OKTOBER", "OLAH",
    "OMSET", "ONE", "ONLINE", "ORANG", "PAGI", "PAKAI", "PALING", "PASAR",
    "PASCA", "PEDULI", "PEGAWAI", "PEKERJA", "PELUANG", "PEMBAYARAN",
    "PEMERINTAH", "PENAWARAN", "PENCAPAIAN", "PENDAPAT", "PENDAPATAN",
    "PENELITIAN", "PENGALAMAN", "PENGELOLAAN", "PENGGUNA", "PENJUALAN",
    "PENTING", "PENURUNAN", "PER", "PERBANKAN", "PERBEDAAN", "PERDAGANGAN",
    "PERNAH", "PERLU", "PERMINTAAN", "PERUSAHAAN", "PERTAMA", "PERTUMBUHAN",
    "PERUBAHAN", "POKOK", "POSISI", "POTENSI", "PREDIKSI", "PRIBADI", "PRODUK",
    "PROFIT", "PROGRAM", "PT", "PUBLIK", "PUNYA", "PUSAT", "RATA", "RENDAH",
    "RESIKO", "RUGI", "RUMAH", "RUPIAH", "SAAT", "SABAR", "SAHAM", "SAJA",
    "SAKING", "SALAH", "SALDO", "SAMA", "SANGAT", "SAPI", "SARAN", "SASARAN",
    "SATU", "SAYA", "SEBAGAI", "SEBAGIAN", "SEBAIK", "SEBELUM", "SEBESAR",
    "SEBUAH", "SEDANG", "SEDIKIT", "SEHARUSNYA", "SEHINGGA", "SEJAK", "SEKARANG",
    "SEKITOR", "SEKOLAH", "SEKTOR", "SELALU", "SELAMA", "SELAMAT", "SELASA",
    "SELURUH", "SEMAKIN", "SEMUA", "SENIN", "SENTUH", "SEOLAH", "SEPERTI",
    "SEPTEMBER", "SERAGAM", "SERIUS", "SERTA", "SETELAH", "SETIAP", "SIFAT",
    "SIGNAL", "SIH", "SIKLUS", "SILAHKAN", "SIMPAN", "SIMPULAN", "SINYAL",
    "SISTEM", "SITUASI", "SIAPA", "SOLUSI", "SPEKULASI", "SUDAH", "SUKSES",
    "SUMBER", "SUNGGUH", "SUPAYA", "SURYA", "SUSUN", "TABEL", "TABUNGAN",
    "TAMBAH", "TAMPIL", "TANDA", "TANGGAL", "TANPA", "TARGET", "TATA", "TAHU",
    "TAHUN", "TELAH", "TELAT", "TEMAN", "TEMPAT", "TENGAH", "TENTANG", "TEPAT",
    "TERBAIK", "TERBALIK", "TERBANYAK", "TERBATAS", "TERBUKA", "TERIMA",
    "TERJADI", "TERLALU", "TERMASUK", "TERSEDIA", "TERUS", "TERUS", "TETAP",
    "TIDAK", "TIGA", "TINGGI", "TINGKAT", "TIPE", "TIAP", "TOBAT", "TOTAL",
    "TRADING", "TREN", "TRIWULAN", "TUJUAN", "TUKAR", "TULIS", "TUNGGU", "TURUN",
    "UANG", "UBAH", "UGD", "UKURAN", "UMUM", "UMPAN", "UNTUK", "UNTUNG",
    "USAHA", "USAI", "UTAMA", "VALUE", "VERSI", "VS", "WAJAR", "WAKTU", "WALAU",
    "WALAUPUN", "WANI", "WARGA", "WARNA", "WILAYAH", "WALI", "YANG",
})


async def extract_ticker(text: str) -> str | None:
    raw = re.findall(r"\b([A-Z]{2,5})\b", text.upper())
    candidates = [c for c in raw if c not in _TICKER_STOP_WORDS]
    if not candidates:
        return None
    # Cek local VALID_TICKERS dulu sebelum hit network
    try:
        from app.data.idx_stocks import VALID_TICKERS
        for c in candidates:
            if c in VALID_TICKERS:
                return c
    except ImportError:
        pass
    results = await asyncio.gather(*[stock_service.verify_ticker(c) for c in candidates], return_exceptions=True)
    for candidate, result in zip(candidates, results):
        if result is True:
            return candidate
    return None


@router.post("/research", response_model=ResearchResponse)
async def research(
    req: ResearchRequest,
    user: Optional[User] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
):
    ticker = req.ticker or await extract_ticker(req.query)
    if not ticker:
        return ResearchResponse(success=False, error="Tidak ada ticker saham ditemukan")

    df, is_simulated = await stock_service.get_price(ticker)
    if df is None or df.empty:
        return ResearchResponse(
            success=False, error=f"Data untuk {ticker} tidak ditemukan"
        )

    info = await company_profile_service.get_profile(ticker)
    mode = (req.mode or "BSJP").upper()
    report = await calculate_score_cached(df, ticker, mode, is_simulated=is_simulated)
    report.company_name = info.get("name", ticker)
    report.mode = mode

    if user:
        session.add(ScanHistory(
            user_id=user.id, ticker=ticker.upper(),
            score=report.score, verdict=report.verdict.value,
        ))
        await session.commit()

    try:
        news_data = await news_service.get_news(ticker, limit=10)
        report.news = [item.model_dump() for item in news_data.items]
    except AppError:
        report.news = None
    try:
        report.fundamentals = await fundamentals_service.get_fundamentals(ticker)
    except AppError:
        report.fundamentals = None

    try:
        report = await enhance_with_ai(report)
    except Exception as e:
        logger.error("AI enhancement gagal untuk %s: %s", ticker, e, exc_info=True)
        report.ai_available = False
        report.summary += " | Insight AI sedang tidak tersedia, silakan coba lagi."

    return ResearchResponse(success=True, data=report)


@router.post("/resolve-tickers")
async def resolve_tickers(req: dict):
    text_in = req.get("text", "")
    raw = re.findall(r"\b([A-Z]{2,5})\b", text_in.upper())
    candidates = [c for c in raw if c not in _TICKER_STOP_WORDS]
    valid = []
    try:
        from app.data.idx_stocks import VALID_TICKERS
        for c in candidates:
            if c in VALID_TICKERS:
                valid.append(c)
    except ImportError:
        pass
    remaining = [c for c in candidates if c not in valid]
    if remaining:
        results = await asyncio.gather(*[stock_service.verify_ticker(c) for c in remaining], return_exceptions=True)
        for c, ok in zip(remaining, results):
            if ok is True and c not in valid:
                valid.append(c)
    return {"tickers": valid[:5]}


@router.get("/health")
async def health():
    return {"status": "ok"}
