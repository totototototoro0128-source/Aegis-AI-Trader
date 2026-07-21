import streamlit as st

from modules.database import init_db
from modules.watchlist import (
    add_stock,
    get_stocks,
    delete_stock,
)

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

        col1, col2 = st.columns([8, 1])

        with col1:
            st.write(f"**{code}**　{company}")

        with col2:

            if st.button("🗑", key=stock_id):

                delete_stock(stock_id)

                st.rerun()