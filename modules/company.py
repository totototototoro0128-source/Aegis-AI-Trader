import yfinance as yf


def get_company_name(code):

    try:

        ticker = yf.Ticker(f"{code}.T")

        info = ticker.info

        return info.get("longName")

    except:

        return None