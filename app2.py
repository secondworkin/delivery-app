import streamlit as st
import requests
import uuid
from streamlit_js_eval import get_geolocation, set_cookie, get_cookie

# --- 設定 ---
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

st.set_page_config(page_title="勤怠管理システム", layout="centered")

# --- 【重要】スマホ固有のIDを管理するロジック ---
# ブラウザのクッキーに保存されたIDを読み取る。なければ新規発行。
if "device_id" not in st.session_state:
    saved_id = get_cookie("device_id")
    if saved_id:
        st.session_state.device_id = saved_id
    else:
        new_id = str(uuid.uuid4()) # ランダムな固有IDを生成
        st.session_state.device_id = new_id
        set_cookie("device_id", new_id, 365) # 1年間有効なクッキーとして保存

# --- 1. ログイン画面 ---
if "user_name" not in st.session_state or not st.session_state.user_name:
    st.subheader("🔑 ログイン（初回登録）")
    name_input = st.text_input("お名前（フルネーム）")
    pin_input = st.text_input("暗証番号（4桁）", type="password")
    
    if st.button("ログイン"):
        if name_input and pin_input:
            # GASに「名前・PIN・スマホID」を全部送ってチェックしてもらう
            params = {
                "name": name_input,
                "pin": pin_input,
                "deviceId": st.session_state.device_id,
                "token": MY_TOKEN
            }
            try:
                res = requests.get(GAS_URL, params=params)
                data = res.json()
                
                if "error" not in data:
                    st.session_state.user_name = data["name"]
                    st.session_state.my_stations = data["stations"]
                    # ログイン成功したら名前もクッキーに保存（次回オートログイン用）
                    set_cookie("driver_name", data["name"], 30)
                    st.rerun()
                else:
                    st.error(data["error"])
            except:
                st.error("通信エラーが発生しました。")
        else:
            st.warning("名前と暗証番号を入力してください。")
    st.stop()

# --- 2. 出退勤メイン画面 ---
st.title("勤怠管理システム")
loc = get_geolocation()

st.write(f"利用者： **{st.session_state.user_name}** さん")

# 現場選択
if len(st.session_state.my_stations) > 1:
    selected_station = st.selectbox("本日の現場を選択してください", st.session_state.my_stations)
else:
    selected_station = st.session_state.my_stations[0]
    st.info(f"現場： **{selected_station}**")

# 出退勤ボタン（共通ロジック）
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
            response = requests.post(GAS_URL, json=post_data)
            if response.status_code == 200:
                st.success(f"【{status}】{selected_station}に記録完了！")
                st.balloons()
            else:
                st.error("送信に失敗しました。")
    else:
        st.warning("GPS取得中... 数秒待ってから押し直してください。")

with col1:
    if st.button("出勤する", use_container_width=True, type="primary"):
        send_data("出勤")

with col2:
    if st.button("退勤する", use_container_width=True):
        send_data("退勤")

# ログアウト（強制リセット）
st.divider()
if st.button("ログアウト / 別の端末でログインし直す"):
    set_cookie("driver_name", "", -1)
    st.session_state.user_name = ""
    st.rerun()