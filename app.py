import streamlit as st

from modules.database import init_db
from modules.watchlist import (
    
    add_stock,
    get_stocks,
    delete_stock,
)
from modules.stock import get_stock_price

# データベース初期化
init_db()

st.set_page_config(
    page_title="AI Investment Assistant",
    page_icon="📈",
    layout="wide",
)

st.title("📈 AI Investment Assistant")

st.divider()

st.subheader("➕ 銘柄追加")

code = st.text_input("銘柄コード")

company = st.text_input("会社名")

if st.button("追加"):

    if code and company:
        add_stock(code, company)
        st.success("追加しました")
        st.rerun()

    else:
        st.warning("銘柄コードと会社名を入力してください")

st.divider()

st.subheader("📋 監視銘柄")

stocks = get_stocks()

if len(stocks) == 0:

    st.info("まだ登録されていません")

else:

    for stock in stocks:

        stock_id, code, company = stock

        stock_info = get_stock_price(code)

        col1, col2 = st.columns([8, 1])

        with col1:

            st.subheader(f"{code}　{company}")

            if stock_info:

                price = stock_info["price"]
                previous = stock_info["previous_close"]

                if price and previous:

                    diff = price - previous
                    rate = diff / previous * 100

                    st.write(f"現在価格：{price:.2f} 円")

                    if diff >= 0:
                        st.success(f"前日比：+{diff:.2f} 円 ({rate:.2f}%)")
                    else:
                        st.error(f"前日比：{diff:.2f} 円 ({rate:.2f}%)")

                else:
                    st.warning("株価取得失敗")

            else:
                st.warning("株価取得失敗")

        with col2:

            if st.button("🗑", key=stock_id):
                delete_stock(stock_id)
                st.rerun()

        st.divider()