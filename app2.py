import streamlit as st
import requests
import json

# ★GASのウェブアプリURL
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

st.set_page_config(page_title="配送DXプロトタイプ", layout="centered")
st.title("🚚 配送現場DXアプリ")

name = st.text_input("名前を入力してください", value="")

col1, col2 = st.columns(2)

with col1:
    if st.button("🔴 出勤する", use_container_width=True):
        payload = {
            "name": name,
            "status": "出勤",
            "location": "金沢拠点",
            "token": MY_TOKEN 
        }
        response = requests.post(
            GAS_URL, 
            data=json.dumps(payload), 
            headers={'Content-Type': 'application/json'}
        )
        # 結果の判定
        if "成功" in response.text:
            st.success(f"{response.text}")
        else:
            st.error(f"エラー: {response.text}")

with col2:
    if st.button("🔵 退勤する", use_container_width=True):
        payload = {
            "name": name,
            "status": "退勤",
            "location": "金沢拠点",
            "token": MY_TOKEN
        }
        response = requests.post(
            GAS_URL, 
            data=json.dumps(payload), 
            headers={'Content-Type': 'application/json'}
        )
        if "成功" in response.text:
            st.info(f"{response.text}")
        else:
            st.error(f"エラー: {response.text}")