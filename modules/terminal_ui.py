"""Aegis 市場ターミナルの共通 UI。"""

import streamlit as st


def show_terminal_header():
    st.markdown(
        """
        <div style="display:flex;justify-content:space-between;align-items:center;
             border:1px solid #1d4658;background:#081017;padding:10px 14px;
             font-family:Consolas,monospace;color:#74d9ff">
          <strong>AEGIS // MARKET TERMINAL</strong>
          <span style="color:#62e6ac">● DATA LINK ACTIVE</span>
          <span>JP EQUITIES · FX · METALS</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
