"""Test resolusi .env relatif ke lokasi file config (cwd-independent).

Jalan: ./.venv/bin/python test_config_env.py
"""

import sys
from pathlib import Path

from app.config import BASE_DIR, Settings


def test_env_file_menunjuk_backend_dir():
    env_file = Settings.model_config.get("env_file")
    p = Path(str(env_file))
    assert p.is_absolute(), env_file
    assert p.parent == BASE_DIR, (p.parent, BASE_DIR)
    assert p.name == ".env", p.name


def main():
    test_env_file_menunjuk_backend_dir()
    print("OK: test_config_env lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
