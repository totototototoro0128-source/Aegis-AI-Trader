import streamlit as st

st.set_page_config(
    page_title="AI Investment Assistant",
    page_icon="📈",
    layout="wide"
)

st.title("📈 AI Investment Assistant")

st.write("ようこそ！")

st.success("システム起動成功")
from modules.database import init_db

init_db()