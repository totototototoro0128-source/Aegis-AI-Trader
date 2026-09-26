"""ローカル開発と公開サイトのデータ保存範囲を判定する。"""

import os
from datetime import datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import streamlit as st


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def now_jst():
    """保存済みの時刻形式と互換のある日本時間を返す。"""

    return datetime.now(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)


def is_public_site():
    """公開サイトでは訪問者ごとのセッション状態を使う。"""

    scope = os.getenv("AEGIS_DEMO_SCOPE", "").strip().lower()
    if scope == "session":
        return True
    if scope == "local":
        return False
    try:
        host = urlsplit(st.context.url).hostname
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False
    return bool(host and host not in LOCAL_HOSTS)
