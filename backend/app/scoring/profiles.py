BSJP_PROFILE = {
    "name": "BSJP",
    "label": "Beli Sore Jual Pagi",
    "veto": {
        "min_avg_volume": 1_000_000,
        "description": "Likuiditas cukup, buang saham suspen/ARB",
    },
    "layers": [
        {"name": "Likuiditas", "weight": 0.25},
        {"name": "ClosingStrength", "weight": 0.25},
        {"name": "Momentum", "weight": 0.15},
        {"name": "Volume", "weight": 0.20},
        {"name": "Struktur", "weight": 0.15},
    ],
    "confluence": {
        "buy_conditions": ["uptrend_or_strong_close", "volume_confirmed", "no_veto"],
        "sell_conditions": ["downtrend_or_reject", "volume_confirmed"],
    },
}

BPJS_PROFILE = {
    "name": "BPJS",
    "label": "Beli Pagi Jual Sore (Intraday)",
    "veto": {
        "min_avg_volume": 5_000_000,
        "description": "Likuiditas tinggi, buang saham dekat ARA",
    },
    "layers": [
        {"name": "Likuiditas", "weight": 0.35},
        {"name": "GapClassification", "weight": 0.20},
        {"name": "Momentum", "weight": 0.10},
        {"name": "Volume", "weight": 0.20},
        {"name": "VwapBias", "weight": 0.15},
    ],
    "confluence": {
        "buy_conditions": ["gap_continuation", "volume_confirmed", "no_veto"],
        "sell_conditions": ["gap_exhaustion", "volume_confirmed"],
    },
}


def get_profile(mode: str) -> dict:
    if mode.upper() == "BPJS":
        return BPJS_PROFILE
    return BSJP_PROFILE
