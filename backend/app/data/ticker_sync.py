import asyncio
import io
import logging
from datetime import datetime
from typing import Any

import pandas as pd
import requests
from sqlalchemy import text

from app.config import settings
from app.database import get_session
from app.database.models import ListedTicker

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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/vnd.ms-excel, text/csv, */*",
}
# URL publik daftar emiten (Excel) – hanya bisa diakses lewat browser biasa (User-Agent)
IDX_EXCEL_URL = "https://www.idx.co.id/umbraco/Surface/ListedCompany/GetListedCompany?format=excel"

# -------- Fungsi fetch ----------
async def fetch_and_store_tickers():
    """Sync tickers dari sumber eksternal ke DB; fallback ke whitelist statis."""
    logger.info("Memulai sync ticker...")
    tickers_data = await _fetch_from_sources()
    if not tickers_data:
        logger.warning("Semua sumber eksternal gagal; fallback ke whitelist statis.")
        tickers_data = [{"ticker": t} for t in _static_tickers()]

    try:
        async for session in get_session():
            for item in tickers_data:
                ticker = str(item.get("ticker") or "").upper()
                if not ticker:
                    continue
                session.merge(
                    ListedTicker(
                        ticker=ticker,
                        company_name=item.get("company_name") or item.get("name"),
                        sector=item.get("sector"),
                        is_active=1,
                        last_synced_at=datetime.utcnow(),
                    )
                )
            await session.commit()
            break
        logger.info("Sync ticker selesai: %d entri", len(tickers_data))
    except Exception as e:
        logger.error("Gagal simpan ticker ke DB: %s", e, exc_info=True)


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
    # ② IDX.co.id publik (Excel/CSV)
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
                resp = requests.get(url, headers=SECTORS_HEADERS, timeout=15)
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
                continue
        return out
    return await asyncio.to_thread(_sync)


async def _fetch_idx():
    """Fetch tickers dari idx.co.id (Excel/CSV publik)."""
    def _sync():
        try:
            resp = requests.get(IDX_EXCEL_URL, headers=IDX_HEADERS, timeout=15)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if "excel" in content_type or resp.content[:4] == b"PK\x03\x04":  # xlsx signature
                df = pd.read_excel(io.BytesIO(resp.content), engine="openpyxl")
            elif "csv" in content_type:
                df = pd.read_csv(io.BytesIO(resp.content))
            else:  # fallback: coba excel engine selain CSV
                df = pd.read_excel(io.BytesIO(resp.content), engine="openpyxl")
            logger.debug("Parsed %d rows from %s", len(df), IDX_EXCEL_URL)

            # Buat mapping kolom (biasanya kode ticker & nama perusahaan)
            cols = {c.lower(): c for c in df.columns}
            ticker_col = cols.get("kode") or cols.get("ticker") or cols.get("kode emiten") or (df.columns[0] if len(df.columns) > 0 else None)
            name_col = cols.get("nama") or cols.get("company_name") or cols.get("company") or cols.get("name") or ("" if len(df.columns) <= 1 else df.columns[1] if len(df.columns) > 1 else None)
            sector_col = cols.get("sektor") or cols.get("sector") or cols.get("industry") or cols.get("industri") or (df.columns[2] if len(df.columns) > 2 else None)

            out = []
            for _, row in df.iterrows():
                out.append({
                    "ticker": str(row[ticker_col]).strip().upper(),
                    "company_name": str(row[name_col]).strip() if name_col else None,
                    "sector": str(row[sector_col]).strip() if sector_col else None,
                })
            return out
        except Exception as e:
            logger.warning("Error parsing idx.co.id response: %s", e)
            return []
    return await asyncio.to_thread(_sync)


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