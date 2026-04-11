import streamlit as st
import requests
import json

# 設定データ（ここを増やせば現場や名前を自由に追加できます！）
LIST_DATA = {
    "自販連": ["眞田", "山路"],
    "日通": ["小山"],
    "トナミ": ["ドライバーA", "ドライバーB", "ドライバーC"]
}

GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

st.set_page_config(page_title="配送現場DXアプリ", layout="centered")
st.title("🚚 配送現場DXアプリ")

# 1. 現場を選択させる
selected_location = st.selectbox("現場（拠点）を選択してください", list(LIST_DATA.keys()))

# 2. 選択された現場に応じて名前のリストを切り替える
name_options = LIST_DATA[selected_location]
selected_name = st.selectbox("名前を選択してください", name_options)

st.write(f"現在は **{selected_location}** の **{selected_name}** さんとして入力します。")

col1, col2 = st.columns(2)

with col1:
    if st.button("🔴 出勤する", use_container_width=True):
        payload = {
            "name": selected_name,
            "status": "出勤",
            "location": selected_location,
            "token": MY_TOKEN
        }
        response = requests.post(GAS_URL, data=json.dumps(payload))
        st.info(response.text)

with col2:
    if st.button("🔵 退勤する", use_container_width=True):
        payload = {
            "name": selected_name,
            "status": "退勤",
            "location": selected_location,
            "token": MY_TOKEN
        }
        response = requests.post(GAS_URL, data=json.dumps(payload))
        st.info(response.text)