import streamlit as st
import requests
from streamlit_js_eval import get_geolocation

st.title("勤怠管理システム (GPS & 現場別リスト版)")

# 1. GPS取得の準備
# 画面を開いた瞬間に位置情報の取得を開始します
loc = get_geolocation()

# 2. 現場と所属ドライバーの定義（ここを最新にしました）
DATA_LIST = {
    "自販連": ["眞田", "山路"],
    "日通": ["小山"],
    "トナミ": ["A", "B", "C"]
}

# 3. 現場の選択
selected_station = st.selectbox("現場を選択してください", list(DATA_LIST.keys()))

# 4. 選んだ現場に対応する名前だけを表示
staff_options = DATA_LIST[selected_station]
selected_name = st.selectbox("名前を選択してください", staff_options)

# 出勤・退勤ボタンの配置
col1, col2 = st.columns(2)

with col1:
    if st.button("出勤する", use_container_width=True):
        if loc:
            lat = loc['coords']['latitude']
            lon = loc['coords']['longitude']
            # スプシでクリックするとGoogleマップが開くリンクを作成
            map_url = f"https://www.google.com/maps?q={lat},{lon}"
            
            data = {
                "token": st.secrets["MY_TOKEN"],
                "station": selected_station,
                "name": selected_name,
                "status": "出勤",
                "location": map_url
            }
            
            response = requests.post(st.secrets["GAS_URL"], json=data)
            if response.status_code == 200:
                st.success(f"【出勤】{selected_station}シートに場所付きで記録しました！")
            else:
                st.error("送信エラーが発生しました。")
        else:
            st.warning("GPSを取得中です。数秒待ってから押し直すか、ブラウザの位置情報許可を確認してください。")

with col2:
    if st.button("退勤する", use_container_width=True):
        if loc:
            lat = loc['coords']['latitude']
            lon = loc['coords']['longitude']
            map_url = f"https://www.google.com/maps?q={lat},{lon}"
            
            data = {
                "token": st.secrets["MY_TOKEN"],
                "station": selected_station,
                "name": selected_name,
                "status": "退勤",
                "location": map_url
            }
            
            response = requests.post(st.secrets["GAS_URL"], json=data)
            if response.status_code == 200:
                st.success(f"【退勤】{selected_station}シートに場所付きで記録しました！")
            else:
                st.error("送信エラーが発生しました。")
        else:
            st.warning("GPS取得中...")
