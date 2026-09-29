import logging
from datetime import datetime

from sqlalchemy import text

from app.database import get_session
from app.database.models import SyncStatus

logger = logging.getLogger(__name__)


# -------- Sumber daftar ticker: IDX Edge PRO --------
def _edge_provider():
    """Pabrik provider IDX Edge PRO — dapat diganti pada test."""
    from app.providers.idx_edge_provider import IdxEdgeProvider

    return IdxEdgeProvider()


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
    """Ambil seluruh daftar emiten dari IDX Edge PRO (market-cap, paginasi)."""
    provider = _edge_provider()
    if not provider.enabled:
        logger.warning("IDX_EDGE_API_KEY kosong — sync ticker dilewati")
        return []
    out: list[dict] = []
    page = 1
    while True:
        data = await provider.fetch_market_cap(page=page, per_page=50)
        if not data or not data.get("data"):
            break
        for row in data["data"]:
            code = str(row.get("code") or "").strip().upper()
            if code:
                out.append({
                    "ticker": code,
                    "company_name": row.get("name"),
                    "sector": None,
                })
        total_pages = data.get("total_pages") or page
        if page >= total_pages:
            break
        page += 1
    return out


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
