from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    env: str = "development"
    ai_api_key: str = ""
    ai_model: str = "coba9router"
    ai_base_url: str = "http://localhost:20128/v1"
    database_url: str = "sqlite+aiosqlite:///./bsjp.db"
    # Pembatas laju request global untuk provider IDX Edge PRO.
    rate_limit_per_minute: int = 60
    cors_origins: str = "http://localhost:3000"
    idx_edge_api_key: str = ""
    idx_edge_base_url: str = "https://stock.arjum.com"
    idx_edge_timeout: int = 20
    idx_edge_daily_quota: int = 1000

    # --- Deteksi akumulasi pemain besar (screening hemat kuota) ---
    accumulation_enabled: bool = True
    # Token wajib untuk POST /api/accumulation/scan; kosong = endpoint nonaktif.
    accumulation_scan_token: str = ""
    accumulation_lookback_days: int = 20
    # Batas kandidat Tahap B (history) dan Tahap C (broker).
    accumulation_history_limit: int = 150
    accumulation_broker_limit: int = 40
    # Tahap A: batas bawah market cap (turnover_ratio relatif, bukan likuiditas absolut).
    accumulation_market_cap_min: float = 1e11
    # Tahap B: likuiditas absolut minimum dari kolom `value` history.
    accumulation_min_daily_value: float = 5e9
    # Validasi limit history sebelum request (API menolak > 500 dengan 422).
    accumulation_max_history_limit: int = 250
    # Jumlah bar history yang diminta per kandidat di Tahap B (<= max_history_limit).
    accumulation_history_bars: int = 80
    # Jumlah strata market cap untuk rotasi irisan universe antar-hari.
    accumulation_rotation_strata: int = 3
    # Buang saham yang sudah naik lebih dari ini dalam N hari (belum lari).
    accumulation_max_runpct: float = 0.15
    # Sisa kuota yang selalu disisakan untuk chat ad-hoc.
    accumulation_quota_reserve: int = 50
    # Plafon skor bila BELUM ada konfirmasi broker (depth hv/foreign).
    accumulation_score_cap_no_broker: float = 60.0
    # Daftar kode broker asing (opsional, dipisah koma).
    accumulation_foreign_broker_codes: str = ""
    # Bobot komponen skor (di satu tempat).
    accumulation_weights: dict = {
        "obv": 0.15,
        "ad": 0.10,
        "cmf": 0.10,
        "absorption": 0.15,
        "basing": 0.10,
        "vwap": 0.10,
        "foreign": 0.15,
        "broker": 0.15,
    }


    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("database_url")
    @classmethod
    def resolve_sqlite_path(cls, v: str) -> str:
        # Resolve relative SQLite paths to an absolute path anchored at the
        # backend directory so every process (regardless of CWD) reads/writes
        # the SAME physical database.
        if not v.startswith("sqlite"):
            return v
        # Format: sqlite+driver:///path
        prefix, _, dbpath = v.partition(":///")
        p = Path(dbpath)
        if not p.is_absolute():
            p = (BASE_DIR / p).resolve()
        return f"{prefix}:///{p}"


settings = Settings()
