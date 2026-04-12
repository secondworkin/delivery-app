import streamlit as st
import requests
from streamlit_js_eval import get_geolocation

# --- 設定 ---
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

st.set_page_config(page_title="勤怠管理システム", layout="centered")

# --- 1. ログイン管理 ---
if "user_name" not in st.session_state:
    st.title("🔑 ログイン")
    user_id = st.text_input("割り当てられたIDを入力してください", key="login_id")
    
    if st.button("ログイン"):
        if user_id:
            try:
                res = requests.get(GAS_URL, params={"id": user_id, "token": MY_TOKEN}, timeout=10)
                data = res.json()
                if "error" not in data:
                    st.session_state.user_name = data["name"]
                    st.session_state.my_stations = data["stations"]
                    st.rerun()
                else:
                    st.error("IDが正しくありません")
            except Exception as e:
                st.error(f"通信エラー: GASのURLが正しいか確認してください")
        else:
            st.warning("IDを入力してください")
    st.stop()

# --- 2. メイン画面 ---
st.title("勤怠管理システム")
st.write(f"利用者： **{st.session_state.user_name}** さん")

# GPS取得（メイン画面に入ってから取得を開始する）
loc = get_geolocation()

if len(st.session_state.my_stations) > 1:
    selected_station = st.selectbox("現場を選択", st.session_state.my_stations)
else:
    selected_station = st.session_state.my_stations[0]
    st.info(f"現場： **{selected_station}**")

col1, col2 = st.columns(2)

def send_data(status):
    # GPSが取れていればURL、取れていなければテキストを送る
    location_data = "GPS取得失敗"
    if loc:
        lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
        location_data = f"https://www.google.com/maps?q={lat},{lon}"
    
    post_data = {
        "token": MY_TOKEN,
        "station": selected_station,
        "name": st.session_state.user_name,
        "status": status,
        "location": location_data
    }
    
    with st.spinner("送信中..."):
        try:
            requests.post(GAS_URL, json=post_data, timeout=10)
            st.success(f"{status}完了！")
            st.balloons()
        except:
            st.error("送信に失敗しました")

with col1:
    if st.button("出勤する", use_container_width=True, type="primary"):
        send_data("出勤")

with col2:
    if st.button("退勤する", use_container_width=True):
        send_data("退勤")

if st.button("ログアウト"):
    del st.session_state.user_name
    st.rerun()