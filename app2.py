import streamlit as st
import requests
from streamlit_js_eval import get_geolocation

# --- 設定 ---
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

st.set_page_config(page_title="勤怠管理システム", layout="centered")

# --- 1. ログイン画面 ---
if "user_name" not in st.session_state:
    st.title("🔑 ログイン")
    st.write("配車係から指定された【ID】を入力してください。")
    user_id = st.text_input("IDを入力", key="login_id")
    
    if st.button("ログイン"):
        if user_id:
            params = {"id": user_id, "token": MY_TOKEN}
            try:
                res = requests.get(GAS_URL, params=params)
                data = res.json()
                if "error" not in data:
                    st.session_state.user_name = data["name"]
                    st.session_state.my_stations = data["stations"]
                    st.rerun()
                else:
                    st.error("IDが正しくないか、登録されていません。")
            except:
                st.error("通信エラーが発生しました。GASのURL等を確認してください。")
        else:
            st.warning("IDを入力してください。")
    st.stop()

# --- 2. 出退勤メイン画面 ---
st.title("勤怠管理システム")
# ここでGPSを取得（許可ダイアログが出ます）
loc = get_geolocation()

st.write(f"利用者： **{st.session_state.user_name}** さん")

# 現場選択
if len(st.session_state.my_stations) > 1:
    selected_station = st.selectbox("本日の現場を選択", st.session_state.my_stations)
else:
    selected_station = st.session_state.my_stations[0]
    st.info(f"現場： **{selected_station}**")

col1, col2 = st.columns(2)

def send_data(status):
    if loc:
        lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
        map_url = f"https://www.google.com/maps?q={lat},{lon}"
        
        post_data = {
            "token": MY_TOKEN,
            "station": selected_station,
            "name": st.session_state.user_name,
            "status": status,
            "location": map_url
        }
        with st.spinner(f"{status}を送信中..."):
            requests.post(GAS_URL, json=post_data)
            st.success(f"【{status}】完了！")
            st.balloons()
    else:
        st.warning("GPS取得中... 数秒待ってから押し直してください。")
        st.info("※ブラウザの「位置情報サービス」がオフの場合、記録できません。")

with col1:
    if st.button("出勤", use_container_width=True, type="primary"):
        send_data("出勤")

with col2:
    if st.button("退勤", use_container_width=True):
        send_data("退勤")

st.divider()
if st.button("ログアウト"):
    del st.session_state.user_name
    st.rerun()