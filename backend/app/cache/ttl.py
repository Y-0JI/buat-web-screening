"""Konstanta TTL terpusat untuk Smart Cache (16.4.5).

Satu sumber kebenaran untuk time-to-live setiap kategori data. Semua
repository/provider/scheduler mengambil TTL dari sini supaya konsisten dan
mudah di-audit.
"""

PROFILE_TTL = 7 * 24 * 3600      # Company Profile — 7 hari
FUNDAMENTAL_TTL = 24 * 3600      # Fundamental & Financial — 24 jam
NEWS_TTL = 3600                  # News — 1 jam
PRICE_TTL = 3600                 # Price/History — 1 jam
VERIFY_TTL = 300                 # Verify ticker — 5 menit
TECHNICAL_TTL = 60              # Technical/scoring — 1 menit
SCREENER_TTL = 6 * 3600          # IDX stock-screener (semua emiten) — 6 jam
SCREEN_TTL = 7200                # Hasil batch screening — 2 jam

# Market Intelligence (16.5) — durasi mengikuti seberapa sering data berubah.
DIVIDEND_TTL = 7 * 24 * 3600     # Dividend — jarang berubah, mingguan
CORP_ACTION_TTL = 7 * 24 * 3600  # Corporate Action (split/right) — mingguan
FOREIGN_FLOW_TTL = 24 * 3600     # Foreign Flow — berubah tiap hari bursa
BROKER_TTL = 24 * 3600           # Broker Summary — berubah tiap hari bursa
EARNINGS_TTL = 7 * 24 * 3600     # Earnings — jarang berubah, mingguan
PRICE_TARGET_TTL = 7 * 24 * 3600  # Price Target/Recommendation — mingguan

TTL_BY_CATEGORY = {
    "profile": PROFILE_TTL,
    "fundamental": FUNDAMENTAL_TTL,
    "news": NEWS_TTL,
    "price": PRICE_TTL,
    "verify": VERIFY_TTL,
    "technical": TECHNICAL_TTL,
    "screener": SCREENER_TTL,
    "screen": SCREEN_TTL,
    "dividend": DIVIDEND_TTL,
    "corp_action": CORP_ACTION_TTL,
    "foreign_flow": FOREIGN_FLOW_TTL,
    "broker_summary": BROKER_TTL,
    "earnings": EARNINGS_TTL,
    "price_target": PRICE_TARGET_TTL,
}
