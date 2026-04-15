import streamlit as st
import requests
from streamlit_js_eval import get_geolocation
from datetime import datetime
import pandas as pd

# --- 設定 ---
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

st.set_page_config(page_title="勤怠管理システム", layout="centered")

# --- セッション状態の初期化 ---
if "page" not in st.session_state:
    st.session_state.page = "home"  # 最初はホーム画面

# 1. ログイン・名前固定ロジック
if "user_name" not in st.session_state:
    st.session_state.user_name = st.query_params.get("user_name", "")

if not st.session_state.user_name:
    st.title("勤怠管理システム")
    st.subheader("🔑 ログイン")
    name_input = st.text_input("お名前を入力してください（フルネーム）")
    if st.button("ログイン"):
        if name_input:
            st.session_state.user_name = name_input
            st.query_params["user_name"] = name_input
            st.rerun()
    st.stop()

# --- 関数：報酬データの取得 ---
def get_monthly_rewards(name):
    try:
        response = requests.get(f"{GAS_URL}?name={name}&token={MY_TOKEN}&action=get_logs")
        if response.status_code == 200:
            all_logs = response.json()["logs"]
            current_month = datetime.now().strftime("%Y/%m")
            monthly_data = []
            total_amount = 0
            for log in all_logs:
                # [日時, 名前, 状態, 報酬グループ, 報酬額, 場所] の形式を想定
                if log[1] == name and log[2] == "退勤" and log[0].startswith(current_month):
                    log_station = str(log[3])
                    display_station = log_station[:-1] if log_station else ""
                    monthly_data.append({
                        "日付": log[0].split(" ")[0],
                        "現場名": display_station,
                        "報酬額": f"¥{int(log[4]):,}"
                    })
                    total_amount += int(log[4])
            return monthly_data, total_amount
    except:
        return [], 0
    return [], 0

# 2. GPS取得
loc = get_geolocation()

# ---------------------------------------------------------
# 🏠 ホーム画面（メニュー）
# ---------------------------------------------------------
if st.session_state.page == "home":
    st.title("📱 メインメニュー")
    st.write(f"こんにちは、**{st.session_state.user_name}** さん")
    st.divider()

    # 大きなボタンを配置
    if st.button("⏰ 出退勤（打刻）", use_container_width=True, type="primary"):
        st.session_state.page = "dakoku"
        st.rerun()

    st.write("") # スペース空け

    if st.button("💰 報酬確定額の確認", use_container_width=True):
        st.session_state.page = "reward"
        st.rerun()

    st.divider()
    if st.button("🚪 ログアウト", key="logout"):
        st.query_params.clear()
        st.session_state.user_name = ""
        st.rerun()

# ---------------------------------------------------------
# ⏰ 出退勤ページ
# ---------------------------------------------------------
elif st.session_state.page == "dakoku":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "home"
        st.rerun()
    
    st.title("⏰ 出退勤")
    
    # 担当現場リストを取得
    @st.cache_data(ttl=600)
    def get_my_stations(name):
        try:
            response = requests.get(f"{GAS_URL}?name={name}&token={MY_TOKEN}")
            if response.status_code == 200: return response.json()["stations"]
            return []
        except: return []

    my_stations = get_my_stations(st.session_state.user_name)

    if not my_stations:
        st.error("担当現場が登録されていません。")
        st.stop()

    if len(my_stations) > 1:
        selected_station = st.selectbox("本日の現場を選択", my_stations)
    else:
        selected_station = my_stations[0]
        st.info(f"現場： **{selected_station}**")

    col1, col2 = st.columns(2)

    def send_data(status):
        if loc:
            lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
            map_url = f"https://www.google.com/maps?q={lat},{lon}"
            data = {"token": MY_TOKEN, "station": selected_station, "name": st.session_state.user_name, "status": status, "location": map_url}
            with st.spinner(f"{status}送信中..."):
                res = requests.post(GAS_URL, json=data)
                if res.status_code == 200:
                    st.success(f"【{status}】完了！")
                    st.balloons()
                else: st.error(f"エラー: {res.text}")
        else: st.warning("GPS取得中...")

    with col1:
        if st.button("出勤する", use_container_width=True, type="primary"): send_data("出勤")
    with col2:
        if st.button("退勤する", use_container_width=True): send_data("退勤")

# ---------------------------------------------------------
# 💰 報酬確認ページ
# ---------------------------------------------------------
elif st.session_state.page == "reward":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "home"
        st.rerun()

    st.title("💰 報酬確定額")
    with st.spinner("集計中..."):
        rewards_list, total = get_monthly_rewards(st.session_state.user_name)
    
    st.metric(label=f"{datetime.now().month}月の合計報酬（暫定）", value=f"¥{total:,}")
    
    if rewards_list:
        st.subheader("🗓️ 稼働内訳")
        st.table(pd.DataFrame(rewards_list))
    else:
        st.info("今月の実績はまだありません。")