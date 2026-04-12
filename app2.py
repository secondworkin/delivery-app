import streamlit as st
import requests
import uuid
from streamlit_js_eval import get_geolocation, streamlit_js_eval

# --- 設定 ---
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

st.set_page_config(page_title="勤怠管理システム", layout="centered")

# --- 1. エラーに強いLocalStorage読み書き機能 ---
def get_local_storage(key):
    try:
        # ブラウザの準備ができるまで待機しつつ読み込む
        return streamlit_js_eval(f"localStorage.getItem('{key}')", key=f"get_{key}")
    except:
        return None

def set_local_storage(key, value):
    try:
        streamlit_js_eval(f"localStorage.setItem('{key}', '{value}')", key=f"set_{key}_{value}")
    except:
        pass

# --- 2. 起動時のデータ取得（重要） ---
# 読み込みが完了するまで「None」が返るため、ここで一旦止める
saved_id = get_local_storage("device_id")
saved_name = get_local_storage("user_name")

if saved_id is None:
    st.info("システム準備中...（数秒お待ちください）")
    st.stop()

# デバイスIDが未発行なら新規作成して保存
if not saved_id:
    device_id = str(uuid.uuid4())
    set_local_storage("device_id", device_id)
else:
    device_id = saved_id

# 名前が保存されていればセッションに入れる
if "user_name" not in st.session_state:
    st.session_state.user_name = saved_name if saved_name else ""

# --- 3. ログイン画面（名前が不明な場合） ---
if not st.session_state.user_name:
    st.subheader("🔑 初回ログイン登録")
    name_input = st.text_input("お名前（フルネーム）")
    pin_input = st.text_input("暗証番号（4桁）", type="password")
    
    if st.button("登録してログイン"):
        if name_input and pin_input:
            params = {
                "name": name_input, "pin": pin_input,
                "deviceId": device_id, "token": MY_TOKEN
            }
            try:
                res = requests.get(GAS_URL, params=params)
                data = res.json()
                if "error" not in data:
                    st.session_state.user_name = data["name"]
                    st.session_state.my_stations = data["stations"]
                    set_local_storage("user_name", data["name"])
                    st.rerun()
                else:
                    st.error(data["error"])
            except:
                st.error("通信エラーが発生しました。")
    st.stop()

# --- 4. 暗証番号認証画面（名前は覚えているが、未認証の場合） ---
if "authenticated" not in st.session_state:
    st.subheader(f"お疲れ様です、{st.session_state.user_name} さん")
    pin_check = st.text_input("暗証番号を入力してください", type="password")
    
    if st.button("ログイン"):
        params = {
            "name": st.session_state.user_name, "pin": pin_check,
            "deviceId": device_id, "token": MY_TOKEN
        }
        try:
            res = requests.get(GAS_URL, params=params)
            data = res.json()
            if "error" not in data:
                st.session_state.authenticated = True
                st.session_state.my_stations = data["stations"]
                st.rerun()
            else:
                st.error("暗証番号が正しくありません。")
        except:
            st.error("通信エラーが発生しました。")
    
    if st.button("別の名前でログインし直す"):
        set_local_storage("user_name", "")
        st.session_state.user_name = ""
        st.rerun()
    st.stop()

# --- 5. メイン画面（出退勤） ---
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