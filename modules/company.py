import yfinance as yf

from modules.yfinance_config import configure_yfinance_cache


configure_yfinance_cache()


def get_company_name(code):

    try:

        ticker = yf.Ticker(f"{code}.T")

        info = ticker.info

        return info.get("longName")

    except:

        return None
