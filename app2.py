import streamlit as st
import requests
import uuid
from streamlit_js_eval import get_geolocation

# --- 設定 ---
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

st.set_page_config(page_title="勤怠管理システム", layout="centered")

# --- ブラウザに刻み込む記憶ロジック (JavaScript使用) ---
def get_local_storage(key):
    """ブラウザのLocalStorageから値を読み出す"""
    from streamlit_js_eval import streamlit_js_eval
    return streamlit_js_eval(f"localStorage.getItem('{key}')", key=f"get_{key}")

def set_local_storage(key, value):
    """ブラウザのLocalStorageに値を書き込む"""
    from streamlit_js_eval import streamlit_js_eval
    streamlit_js_eval(f"localStorage.setItem('{key}', '{value}')", key=f"set_{key}_{value}")

# 1. デバイスIDの取得/発行
if "device_id" not in st.session_state:
    saved_id = get_local_storage("device_id")
    if saved_id:
        st.session_state.device_id = saved_id
    else:
        new_id = str(uuid.uuid4())
        st.session_state.device_id = new_id
        set_local_storage("device_id", new_id)

# 2. 登録済み氏名の取得
if "user_name" not in st.session_state:
    saved_name = get_local_storage("user_name")
    st.session_state.user_name = saved_name if saved_name else ""

# --- A. ログイン画面 ---
if not st.session_state.user_name:
    st.subheader("🔑 初回ログイン登録")
    name_input = st.text_input("お名前（フルネーム）")
    pin_input = st.text_input("暗証番号（4桁）", type="password")
    
    if st.button("登録してログイン"):
        if name_input and pin_input:
            params = {
                "name": name_input, "pin": pin_input,
                "deviceId": st.session_state.device_id, "token": MY_TOKEN
            }
            res = requests.get(GAS_URL, params=params)
            data = res.json()
            if "error" not in data:
                st.session_state.user_name = data["name"]
                st.session_state.my_stations = data["stations"]
                set_local_storage("user_name", data["name"]) # 名前をスマホに記憶
                st.rerun()
            else:
                st.error(data["error"])
    st.stop()

# --- B. PIN認証画面（2回目以降） ---
if "authenticated" not in st.session_state:
    st.subheader(f"お疲れ様です、{st.session_state.user_name} さん")
    pin_check = st.text_input("暗証番号を入力してください", type="password")
    
    if st.button("認証"):
        params = {
            "name": st.session_state.user_name, "pin": pin_check,
            "deviceId": st.session_state.device_id, "token": MY_TOKEN
        }
        res = requests.get(GAS_URL, params=params)
        data = res.json()
        if "error" not in data:
            st.session_state.authenticated = True
            st.session_state.my_stations = data["stations"]
            st.rerun()
        else:
            st.error("暗証番号が正しくありません。")
    
    if st.button("別の名前でログインし直す"):
        set_local_storage("user_name", "")
        st.session_state.user_name = ""
        st.rerun()
    st.stop()

# --- C. メイン機能（出退勤） ---
st.title("勤怠管理システム")
loc = get_geolocation()
st.write(f"ログイン中： **{st.session_state.user_name}**")

# 現場選択
if len(st.session_state.my_stations) > 1:
    selected_station = st.selectbox("現場を選択", st.session_state.my_stations)
else:
    selected_station = st.session_state.my_stations[0]
    st.info(f"現場： **{selected_station}**")

col1, col2 = st.columns(2)

def send_data(status):
    if loc:
        lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
        map_url = f"https://www.google.com/maps?q={lat},{lon}"
        post_data = {
            "token": MY_TOKEN, "station": selected_station,
            "name": st.session_state.user_name, "status": status, "location": map_url
        }
        with st.spinner("送信中..."):
            requests.post(GAS_URL, json=post_data)
            st.success(f"{status}完了！")
            st.balloons()
    else:
        st.warning("GPS取得中... 数秒待ってから押し直してください。")

with col1:
    if st.button("出勤する", use_container_width=True, type="primary"):
        send_data("出勤")
with col2:
    if st.button("退勤する", use_container_width=True):
        send_data("退勤")