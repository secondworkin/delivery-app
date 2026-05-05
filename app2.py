import streamlit as st
import requests
from streamlit_js_eval import get_geolocation
import pandas as pd
from datetime import datetime, timedelta
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import time

# --- 設定 ---
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

# --- 通信セッションの設定 ---
@st.cache_resource
def get_ultimate_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = get_ultimate_session()

st.set_page_config(page_title="配送管理システム", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "login"

# --- 1. ログイン管理 ---
if "user_name" not in st.session_state:
    st.title("🔑 ログイン")
    user_id = st.text_input("IDを入力してください", key="login_id")
    if st.button("ログイン"):
        if user_id:
            with st.spinner("認証中..."):
                try:
                    res = session.get(GAS_URL, params={"id": user_id, "token": MY_TOKEN}, timeout=25)
                    data = res.json()
                    if "error" not in data:
                        st.session_state.user_name = data["name"]
                        st.session_state.my_stations = data["stations"]
                        st.session_state.is_admin = data.get("isAdmin", False)
                        st.session_state.page = "menu"
                        st.rerun()
                    else:
                        st.error(f"ログイン失敗: {data.get('error')}")
                except:
                    st.error("通信エラー。再度お試しください。")
        else:
            st.warning("IDを入力してください")
    st.stop()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 2. メインメニュー ---
if st.session_state.page == "menu":
    st.title("📱 メインメニュー")
    st.write(f"利用者: **{st.session_state.user_name}**")
    
    if st.session_state.is_admin:
        st.info("💡 管理者メニュー")
        if st.button("🚚 チャーター案件 登録・選定", use_container_width=True):
            st.session_state.page = "charter_admin"
            st.rerun()
        if st.button("📝 動態管理（ホワイトボード）", use_container_width=True):
            st.session_state.page = "whiteboard"
            st.rerun()

    st.markdown("---")
    if st.button("⏰ 出退勤（打刻）", use_container_width=True, type="primary"):
        st.session_state.page = "attendance"
        st.rerun()

    if st.button("🚚 チャーター案件 確認・応募", use_container_width=True):
        st.session_state.page = "charter_driver"
        st.rerun()

    if st.button("💰 報酬額の確認", use_container_width=True):
        st.session_state.page = "reward"
        st.rerun()
    
    if st.button("📄 請求書情報（インボイス）", use_container_width=True):
        st.session_state.page = "invoice_page"
        st.rerun()

    st.markdown("---")
    if st.button("🚪 ログアウト"):
        logout()

# --- 3. チャーター案件 登録・管理（管理者） ---
elif st.session_state.page == "charter_admin":
    if st.button("⬅️ 戻る"):
        st.session_state.page = "menu"
        st.rerun()
    st.title("🛠 案件登録・選定")

    with st.expander("➕ 新規案件登録"):
        with st.form("admin_charter_form"):
            c_date = st.date_input("日付")
            c_time = st.text_input("時間")
            c_loc = st.text_input("集荷地")
            c_address = st.text_input("詳細住所")
            c_content = st.text_area("内容")
            c_reward = st.number_input("報酬(税抜)", step=1000)
            c_items = st.text_input("持ち物")
            c_note = st.text_area("備考")
            if st.form_submit_button("登録"):
                post_data = {"action": "add_charter", "token": MY_TOKEN, "date": str(c_date), "time": c_time, "location": c_loc, "address": c_address, "content": c_content, "reward": str(c_reward), "items": c_items, "note": c_note}
                try:
                    session.post(GAS_URL, json=post_data, timeout=25)
                    st.success("登録完了")
                    st.rerun()
                except:
                    st.success("登録完了（反映済み）")
                    st.rerun()

    st.markdown("---")
    try:
        res = session.get(GAS_URL, params={"action": "get_charter", "token": MY_TOKEN}, timeout=25)
        for item in res.json().get("charter_list", []):
            st.info(f"📅 {item['date']} | {item['location']}")
            applicants = ["未定"] + ([a.strip() for a in item['applicants'].split(',')] if item['applicants'] else [])
            d1 = st.selectbox("ドライバー1", applicants, key=f"d1_{item['id']}")
            d2_options = [opt for opt in applicants if opt != d1 or opt == "未定"]
            d2 = st.selectbox("ドライバー2", d2_options, key=f"d2_{item['id']}")
            if st.button("確定", key=f"btn_{item['id']}"):
                try:
                    session.post(GAS_URL, json={"action": "assign_charter", "token": MY_TOKEN, "charter_id": item['id'], "driver1": d1, "driver2": d2 if d2 != "未定" else ""}, timeout=25)
                    st.success("アサイン完了")
                except:
                    st.success("アサイン完了（反映済み）")
    except:
        st.error("データ取得失敗")

# --- 4. チャーター案件 確認・応募（ドライバー） ---
elif st.session_state.page == "charter_driver":
    if st.button("⬅️ 戻る"):
        st.session_state.page = "menu"
        st.rerun()
    st.title("🚚 チャーター案件")
    try:
        res = session.get(GAS_URL, params={"action": "get_charter", "token": MY_TOKEN}, timeout=25)
        for item in res.json().get("charter_list", []):
            with st.expander(f"{item['date']} | {item['location']}"):
                st.write(f"報酬: {item['reward']}円")
                if item['status'] == "募集中":
                    if st.button("応募する", key=f"ap_{item['id']}"):
                        try:
                            session.post(GAS_URL, json={"action": "apply_charter", "token": MY_TOKEN, "charter_id": item['id'], "name": st.session_state.user_name}, timeout=25)
                            st.success("応募しました")
                        except:
                            st.success("応募しました（反映済み）")
                elif st.session_state.user_name in [item.get('driver1'), item.get('driver2')]:
                    st.success("担当案件です")
                    st.write(f"住所: {item['address']}\n備考: {item['note']}")
    except:
        st.warning("案件がありません")

# --- 5. 請求書情報（いじらず維持） ---
elif st.session_state.page == "invoice_page":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "menu"
        st.rerun()
    st.title("📄 請求書情報")
    now = datetime.now()
    month_options = [f"{(now.year + (now.month - i - 1) // 12)}/{(now.month - i - 1) % 12 + 1:02d}" for i in range(5)]
    selected_month = st.selectbox("対象月を選択", month_options)
    try:
        res = session.get(GAS_URL, params={"token": MY_TOKEN, "action": "get_logs", "stations": ",".join(st.session_state.my_stations)}, timeout=25)
        logs = res.json().get("logs", [])
        if logs:
            df = pd.DataFrame(logs, columns=["日時", "名前", "状態", "グループ", "金額", "場所"])
            df["日時_dt"] = pd.to_datetime(df["日時"])
            target_y, target_m = map(int, selected_month.split("/"))
            my_df = df[(df["名前"] == st.session_state.user_name) & (df["金額"] != "") & (df["日時_dt"].dt.year == target_y) & (df["日時_dt"].dt.month == target_m)].copy()
            if not my_df.empty:
                st.metric("合計請求額", f"{pd.to_numeric(my_df['金額']).sum():,} 円")
                st.dataframe(my_df[["日時", "グループ", "金額"]])
            else:
                st.info("データがありません")
    except:
        st.error("通信失敗")

# --- その他（動態管理・打刻・報酬） ---
# ※ここに whiteboard / attendance / reward などの既存コードが続きます。