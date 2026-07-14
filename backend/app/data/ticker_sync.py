import asyncio
import logging
from datetime import datetime
from typing import Any

import requests
from app.database import get_session
from app.database.models import ListedTicker

logger = logging.getLogger(__name__)

SECTORS_API = "https://api.sectors.app/v1/listing/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://sectors.app/",
}


async def fetch_and_store_tickers():
    """Fetch ticker list from sectors.app and upsert into DB."""
    logger.info("Memulai sync ticker dari sectors.app")
    try:
        def _sync_request():
            resp = requests.get(SECTORS_API, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.json()

        data = await asyncio.to_thread(_sync_request)
        if not isinstance(data, list):
            logger.error("Response bukan list: %s", type(data))
            return

        async for session in get_session():
            for item in data:
                if not isinstance(item, dict):
                    continue
                ticker = (item.get("symbol") or item.get("ticker") or "").upper()
                if not ticker:
                    continue
                company_name = item.get("company_name") or item.get("name")
                sector = item.get("sector")
                ticker_obj = ListedTicker(
                    ticker=ticker,
                    company_name=company_name,
                    sector=sector,
                    is_active=1,
                    last_synced_at=datetime.utcnow(),
                )
                await session.merge(ticker_obj)
            await session.commit()
            break
        logger.info("Sync ticker selesai: %d entri", len(data))
    except Exception as e:
        logger.error("Gagal sync ticker: %s", e, exc_info=True)
        # Do not raise; keep old data


async def get_listed_tickers() -> list[str]:
    """Return active ticker list from DB (fallback to static if empty)."""
    try:
        async for session in get_session():
            result = await session.execute(
                "SELECT ticker FROM listed_tickers WHERE is_active = 1"
            )
            rows = result.fetchall()
            break
        tickers = [r[0] for r in rows]
        if tickers:
            return tickers
    except Exception as e:
        logger.warning("Gagal baca listed_tickers: %s", e)
    # Fallback to static whitelist
    from app.data.idx_stocks import VALID_TICKERS
    return list(VALID_TICKERS)
