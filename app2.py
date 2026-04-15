import streamlit as st

import requests

from streamlit_js_eval import get_geolocation



# --- 設定 ---

GAS_URL = st.secrets["GAS_URL"]

MY_TOKEN = st.secrets["MY_TOKEN"]



st.set_page_config(page_title="勤怠管理システム", layout="centered")

st.title("勤怠管理システム")



# 1. ログイン・名前固定ロジック

if "user_name" not in st.session_state:

    st.session_state.user_name = st.query_params.get("user_name", "")



if not st.session_state.user_name:

    st.subheader("🔑 ログイン")

    name_input = st.text_input("お名前を入力してください（フルネーム）")

    if st.button("ログイン"):

        if name_input:

            st.session_state.user_name = name_input

            st.query_params["user_name"] = name_input

            st.rerun()

    st.stop()



# 2. GPS取得

loc = get_geolocation()



# 3. 担当現場リストを取得

@st.cache_data(ttl=600)

def get_my_stations(name):

    try:

        response = requests.get(f"{GAS_URL}?name={name}&token={MY_TOKEN}")

        if response.status_code == 200:

            return response.json()["stations"]

        return []

    except:

        return []



my_stations = get_my_stations(st.session_state.user_name)



# 現場が見つからない場合の処理

if not my_stations:

    st.error(f"「{st.session_state.user_name}」さんの担当現場が登録されていません。")

    if st.button("ログアウトして別の名前で試す"):

        st.query_params.clear()

        st.session_state.user_name = ""

        st.rerun()

    st.stop()



# 4. 画面表示と現場選択

st.write(f"利用者： **{st.session_state.user_name}** さん")



if len(my_stations) > 1:

    selected_station = st.selectbox("本日の現場を選択してください", my_stations)

else:

    selected_station = my_stations[0]

    st.info(f"現場： **{selected_station}**")



# 5. 出退勤ボタン

col1, col2 = st.columns(2)



# 送信共通ロジック

def send_data(status):

    if loc:

        lat = loc['coords']['latitude']

        lon = loc['coords']['longitude']

        map_url = f"https://www.google.com/maps?q={lat},{lon}"

        

        data = {

            "token": MY_TOKEN,

            "station": selected_station,

            "name": st.session_state.user_name, # ログイン名を使用

            "status": status,

            "location": map_url

        }

        

        with st.spinner(f"{status}を送信中..."):

            response = requests.post(GAS_URL, json=data)

            if response.status_code == 200:

                st.success(f"【{status}】{selected_station}に記録しました！")

                st.balloons()

            else:

                st.error(f"送信エラー: {response.text}")

    else:

        st.warning("GPS取得中... 数秒待ってから押し直してください。")



with col1:

    if st.button("出勤する", use_container_width=True, type="primary"):

        send_data("出勤")



with col2:

    if st.button("退勤する", use_container_width=True):

        send_data("退勤")



# 画面下部にログアウトオプション

st.divider()

if st.button("ログアウト (別の名前で入る)", key="logout"):

    st.query_params.clear()

    st.session_state.user_name = ""

    st.rerun()