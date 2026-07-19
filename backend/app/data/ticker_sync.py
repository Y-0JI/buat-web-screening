import asyncio
import logging
from datetime import datetime

from curl_cffi import requests as curl_requests
from sqlalchemy import text

from app.config import settings
from app.database import get_session
from app.database.models import SyncStatus

logger = logging.getLogger(__name__)

# -------- Konfigurasi sumber eksternal ----------
# 1️⃣ Sectors.app (memang memerlukan API key berbayar)
SECTORS_API_KEY = settings.sectors_api_key  # ← tambah env var SECTORS_API_KEY
SECTORS_ENDPOINTS = [
    "https://api.sectors.app/v1/index/idx30/",
    "https://api.sectors.app/v1/index/idx80/",
    "https://api.sectors.app/v1/index/kompas100/",
]  # ← sesuaikan dengan endpoint yang benar di docs.sectors.app

SECTORS_HEADERS = {"Authorization": SECTORS_API_KEY} if SECTORS_API_KEY else {}

# 2️⃣ IDX.co.id (publik, tapi harus pakai header browser‑like)
IDX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}
# URL publik daftar emiten (JSON) – lebih ringan dan peluang lebih besar lolos Cloudflare
IDX_JSON_URL = "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles"

# -------- Fungsi fetch ----------
async def fetch_and_store_tickers():
    """Sync tickers dari sumber eksternal ke DB.
    Jika semua sumber gagal, tidak overwrite DB (fallback statis dihilangkan) dan
    catat kegagalan sync. Jika data anomali (penurunan drastis), juga tidak overwrite.
    """
    logger.info("Memulai sync ticker...")
    tickers_data = await _fetch_from_sources()

    if not tickers_data:
        logger.error(
            "SYNC GAGAL TOTAL: semua sumber eksternal (Sectors.app, IDX) tidak "
            "mengembalikan data. DB TIDAK diubah, data lama tetap dipakai."
        )
        await _record_sync_failure()
        return  # <-- JANGAN overwrite DB dengan static fallback

    # Sanity check: tolak kalau jumlah data anjlok drastis (indikasi response
    # rusak / salah parse, bukan penurunan emiten beneran)
    current_count = await _get_current_ticker_count()
    if current_count > 0 and len(tickers_data) < current_count * 0.9:
        logger.error(
            "SYNC DITOLAK: hasil fetch baru (%d ticker) anjlok >10%% dari data "
            "lama (%d ticker). Kemungkinan response rusak. DB tidak diubah.",
            len(tickers_data), current_count,
        )
        await _record_sync_failure()
        return

    try:
        async for session in get_session():
            # Upsert per ticker pakai SQL langsung (INSERT OR REPLACE)
            # supaya update-by-ticker jalan benar (bukan by id internal).
            for item in tickers_data:
                ticker = str(item.get("ticker") or "").upper()
                if not ticker:
                    continue
                await session.execute(
                    text("""
                        INSERT INTO listed_tickers (ticker, company_name, sector, is_active, last_synced_at)
                        VALUES (:ticker, :company_name, :sector, 1, :last_synced_at)
                        ON CONFLICT(ticker) DO UPDATE SET
                            company_name = excluded.company_name,
                            sector = excluded.sector,
                            is_active = 1,
                            last_synced_at = excluded.last_synced_at
                    """),
                    {
                        "ticker": ticker,
                        "company_name": item.get("company_name") or item.get("name"),
                        "sector": item.get("sector"),
                        "last_synced_at": datetime.utcnow(),
                    },
                )
            await session.commit()
            break
        await _record_sync_success(len(tickers_data))
        logger.info("Sync ticker selesai: %d entri", len(tickers_data))
    except Exception as e:
        logger.error("Gagal simpan ticker ke DB: %s", e, exc_info=True)
        await _record_sync_failure()


def _static_tickers():
    from app.data.idx_stocks import VALID_TICKERS
    return list(VALID_TICKERS)


async def _fetch_from_sources():
    # ① Sectors.app dengan (opsional) API key
    if SECTORS_API_KEY:
        try:
            data = await _fetch_sectors()
            if data:
                return data
        except Exception as e:
            logger.warning("Sectors.app gagal: %s", e)
    # ② IDX.co.id publik (JSON)
    try:
        data = await _fetch_idx()
        if data:
            return data
    except Exception as e:
        logger.warning("IDX.co.id gagal: %s", e)
    return []


async def _fetch_sectors():
    """Fetch tickers dari satu atau beberapa endpoint Sectors.app."""
    def _sync():
        out = []
        for url in SECTORS_ENDPOINTS:
            try:
                resp = curl_requests.get(url, headers=SECTORS_HEADERS, timeout=15)
                resp.raise_for_status()
                json_data = resp.json()
                if isinstance(json_data, list):
                    for item in json_data:
                        out.append({
                            "ticker": item.get("symbol") or item.get("ticker"),
                            "company_name": item.get("company_name") or item.get("name"),
                            "sector": item.get("sector"),
                        })
            except Exception:
                continue  # Skip this URL if any error occurs
        return out
    
    # Since main function is async, wrap in asyncio.to_thread
    return await asyncio.to_thread(_sync)


async def _fetch_idx():
    """Fetch tickers dari idx.co.id (JSON endpoint)."""
    def _parse_rows(rows):
        out = []
        for row in rows:
            out.append({
                "ticker": str(row.get("KodeEmiten") or row.get("Kode") or "").strip().upper(),
                "company_name": row.get("NamaEmiten") or row.get("Nama") or "",
                "sector": row.get("Sektor") or "",
            })
        return out

    def _sync():
        try:
            resp = curl_requests.get(
                IDX_JSON_URL,
                params={"emitenType": "s", "start": 0, "length": 9999},
                headers=IDX_HEADERS,
                impersonate="chrome124",
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, dict) and "data" in data:
                raw_rows = data["data"]
            elif isinstance(data, list):
                raw_rows = data
            else:
                raw_rows = data if isinstance(data, list) else []

            parsed = _parse_rows(raw_rows)
            return [r for r in parsed if r["ticker"]]
        except Exception as e:
            logger.warning("IDX JSON endpoint gagal: %s", e)
            return []
    return await asyncio.to_thread(_sync)


async def _get_current_ticker_count() -> int:
    async for session in get_session():
        result = await session.execute(text("SELECT COUNT(*) FROM listed_tickers WHERE is_active = 1"))
        row = result.fetchone()
        return row[0] if row else 0
    return 0


async def _record_sync_failure():
    """Catat kegagalan sync biar bisa dipantau, tanpa mengubah data ticker."""
    async for session in get_session():
        status = await session.get(SyncStatus, 1)
        if status is None:
            status = SyncStatus(id=1, consecutive_failures=0)
            session.add(status)
        last_attempt = datetime.utcnow()
        status.last_attempt_at = last_attempt
        status.consecutive_failures += 1
        await session.commit()
        if status.consecutive_failures >= 3:
            logger.error(
                "PERINGATAN: sync ticker gagal %d kali berturut-turut. "
                "Cek koneksi ke IDX/Sectors.app secara manual.",
                status.consecutive_failures,
            )
        break


async def _record_sync_success(count: int):
    """Catat keberhasilan sync."""
    async for session in get_session():
        status = await session.get(SyncStatus, 1)
        if status is None:
            status = SyncStatus(id=1)
            session.add(status)
        now = datetime.utcnow()
        status.last_attempt_at = now
        status.last_success_at = now
        status.consecutive_failures = 0
        status.last_ticker_count = count
        await session.commit()
        break


async def get_listed_tickers() -> list[str]:
    """Return active ticker list from DB (fallback to static whitelist)."""
    try:
        async for session in get_session():
            result = await session.execute(
                text("SELECT ticker FROM listed_tickers WHERE is_active = 1")
            )
            rows = result.fetchall()
            break
        tickers = [r[0] for r in rows]
        if tickers:
            return tickers
    except Exception as e:
        logger.warning("Gagal baca listed_tickers: %s", e)

    logger.debug("Fallback visual ke whitelist statis")
    return _static_tickers()
