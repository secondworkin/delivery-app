import streamlit as st
import requests
from streamlit_js_eval import get_geolocation
import pandas as pd
from datetime import datetime
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

# --- 設定 ---
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

# --- 通信セッションの強化（リトライ5回・待機時間増量） ---
@st.cache_resource
def get_ultimate_session():
    session = requests.Session()
    retries = Retry(
        total=5,               # 最大5回まで粘り強くリトライ
        backoff_factor=2,      # 失敗するごとに待機時間を 2s, 4s, 8s... と増やしてGASの起動を待つ
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = get_ultimate_session()

st.set_page_config(page_title="勤怠管理システム", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "login"

# --- 1. ログイン管理 ---
if "user_name" not in st.session_state:
    st.title("🔑 ログイン")
    user_id = st.text_input("割り当てられたIDを入力してください", key="login_id")
    if st.button("ログイン"):
        if user_id:
            with st.spinner("サーバーを呼び出しています... (最大15秒)"):
                try:
                    res = session.get(GAS_URL, params={"id": user_id, "token": MY_TOKEN}, timeout=20)
                    data = res.json()
                    if "error" not in data:
                        st.session_state.user_name = data["name"]
                        st.session_state.my_stations = data["stations"]
                        st.session_state.page = "menu"
                        st.rerun()
                    else:
                        st.error("IDが正しくありません")
                except:
                    st.error("通信がタイムアウトしました。もう一度ログインを押してください。")
        else:
            st.warning("IDを入力してください")
    st.stop()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 3. メインメニュー画面 ---
if st.session_state.page == "menu":
    st.title("📱 メインメニュー")
    st.write(f"こんにちは、 **{st.session_state.user_name}** さん")
    st.markdown("---")
    if st.button("⏰ 出退勤（打刻）", use_container_width=True, type="primary"):
        st.session_state.page = "attendance"
        st.rerun()
    if st.button("💰 報酬確定額の確認", use_container_width=True):
        st.session_state.page = "reward"
        st.rerun()
    st.markdown("---")
    if st.button("🚪 ログアウト"):
        logout()

# --- 4. 出退勤画面 ---
elif st.session_state.page == "attendance":
    if st.button("⬅️ メニューに戻る"):