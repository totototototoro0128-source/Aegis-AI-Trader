"""yfinance の実行環境設定。"""

from pathlib import Path

import yfinance as yf


def configure_yfinance_cache():
    """プロジェクト内の書き込み可能な場所に yfinance のキャッシュを置く。"""

    project_root = Path(__file__).resolve().parent.parent
    cache_dir = project_root / "database" / "yfinance_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    yf.set_tz_cache_location(str(cache_dir))
