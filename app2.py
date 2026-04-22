import streamlit as st
import requests
from streamlit_js_eval import get_geolocation
import pandas as pd
from datetime import datetime
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import time

# --- 設定 ---
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

# --- 通信セッションの最強設定（キャッシュ化） ---
@st.cache_resource
def get_ultimate_session():
    session = requests.Session()
    retries = Retry(
        total=5,                # 最大5回まで粘る
        backoff_factor=1,       # 待機時間を1s, 2s, 4s...と増やしてGASの起動を待つ
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"], # GETもPOSTもしっかりリトライ
        raise_on_status=False
    )
    # 接続・読み取りの両方にリトライを適用
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = get_ultimate_session()

st.set_page_config(page_title="勤怠管理システム", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "login"

# --- 1. ログイン管理 ---
if "user_name" not in st.session_state:
    st.title("🔑 ログイン")
    user_id = st.text_input("割り当てられたIDを入力してください", key="login_id")
    if st.button("ログイン"):
        if user_id:
            with st.spinner("サーバーを叩き起こしています..."):
                try:
                    # 【重要】本番通信の前に、GASを「起こす」ための挨拶を1回投げる
                    try:
                        session.get(GAS_URL, params={"ping": "pong"}, timeout=3)
                    except:
                        pass # ここでのエラーは無視して本番へ進む
                    
                    time.sleep(1) # 1秒だけ待ってから本番
                    
                    # 本番の認証通信
                    res = session.get(GAS_URL, params={"id": user_id, "token": MY_TOKEN}, timeout=25)
                    data = res.json()
                    
                    if "error" not in data:
                        st.session_state.user_name = data["name"]
                        st.session_state.my_stations = data["stations"]
                        st.session_state.page = "menu"
                        st.rerun()
                    else:
                        st.error(f"ログイン失敗: {data.get('error')}")
                except Exception as e:
                    # 3秒で切れる現象対策：エラーになっても「もう一度だけ」を促す
                    st.error("通信が一時的に遮断されました。もう一度「ログイン」を押してください。")
                    st.info("※GASの起動に時間がかかっています。2回目以降はスムーズに入れます。")
        else:
            st.warning("IDを入力してください")
    st.stop()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 3. メインメニュー画面 ---
if st.session_state.page == "menu":
    st.title("📱 メインメニュー")
    st.write(f"こんにちは、 **{st.session_state.user_name}** さん")
    st.markdown("---")
    if st.button("⏰ 出退勤（打刻）", use_container_width=True, type="primary"):
        st.session_state.page = "attendance"
        st.rerun()
    if st.button("💰 報酬確定額の確認", use_container_width=True):
        st.session_state.page = "reward"
        st.rerun()
    st.markdown("---")
    if st.button("🚪 ログアウト"):
        logout()

# --- 4. 出退勤画面 ---
elif st.session_state.page == "attendance":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "menu"
        st.rerun()
    st.title("⏰ 出退勤")
    loc = get_geolocation()
    if len(st.session_state.my_stations) > 0:
        selected_station = st.selectbox("現場を選択", st.session_state.my_stations) if len(st.session_state.my_stations) > 1 else st.session_state.my_stations[0]
        if len(st.session_state.my_stations) == 1: st.info(f"現場： **{selected_station}**")
        
        col1, col2 = st.columns(2)
        
        def send_data(status):
            location_data = "GPS取得失敗"
            if loc:
                lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
                location_data = f"http://maps.google.com/?q={lat},{lon}"
            
            post_data = {
                "token": MY_TOKEN, 
                "station": selected_station, 
                "name": st.session_state.user_name, 
                "status": status, 
                "location": location_data
            }
            
            with st.spinner("送信中..."):
                try:
                    res = session.post(GAS_URL, json=post_data, timeout=25)
                    res_data = res.json()
                    
                    if "error" in res_data:
                        if res_data.get("error") == "ALREADY_DONE":
                            st.warning(res_data.get("message"))
                        else:
                            st.error(f"エラー: {res_data.get('message', '送信失敗')}")
                    else:
                        st.success(f"{status}完了！")
                        st.balloons()
                except:
                    st.error("通信エラーが発生しました。もう一度お試しください。")

        with col1:
            if st.button("出勤する", use_container_width=True, type="primary"): send_data("出勤")
        with col2:
            if st.button("退勤する", use_container_width=True): send_data("退勤")
    else:
        st.error("担当現場が登録されていません。")

# --- 5. 報酬確定額の確認画面 ---
elif st.session_state.page == "reward":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "menu"
        st.rerun()
    st.title("💰 報酬確定額")
    
    now = datetime.now()
    month_options = [f"{(now.year + (now.month - i - 1) // 12)}/{(now.month - i - 1) % 12 + 1:02d}" for i in range(5)]
    selected_month = st.selectbox("表示する月を選択", month_options)

    with st.spinner("データを集計中..."):
        try:
            res = session.get(GAS_URL, params={"token": MY_TOKEN, "action": "get_logs", "stations": ",".join(st.session_state.my_stations)}, timeout=25)
            logs = res.json().get("logs", [])
            if logs:
                df = pd.DataFrame(logs, columns=["日時", "名前", "状態", "グループ", "金額", "場所"])
                df["日時_dt"] = pd.to_datetime(df["日時"])
                target_y, target_m = map(int, selected_month.split("/"))
                my_df = df[(df["名前"] == st.session_state.user_name) & (df["金額"] != "") & (df["日時_dt"].dt.year == target_y) & (df["日時_dt"].dt.month == target_m)].copy()
                
                if not my_df.empty:
                    my_df["現場"] = my_df["グループ"].apply(lambda x: str(x)[:-1])
                    st.metric(f"{selected_month} の合計報酬", f"{pd.to_numeric(my_df['金額']).sum():,} 円")
                    st.dataframe(my_df[["日時", "現場", "金額"]].assign(日時=my_df["日時_dt"].dt.strftime('%m/%d %H:%M')), use_container_width=True, hide_index=True)

                    st.markdown("---")
                    st.subheader("📄 請求書情報の申請")
                    st.caption("以下の情報を入力して送信してください。")
                    zip_code = st.text_input("郵便番号", placeholder="123-4567")
                    address = st.text_input("住所", placeholder="石川県金沢市...")
                    bank_info = st.text_input("振込先口座", placeholder="〇〇銀行 支店 普通 1234567")
                    
                    if st.button("請求書データを送信する", use_container_width=True, type="primary"):
                        if not zip_code or not address or not bank_info:
                            st.warning("情報を入力してください")
                        else:
                            invoice_data = {"action": "create_pdf", "token": MY_TOKEN, "name": st.session_state.user_name, "zip": zip_code, "address": address, "bank": bank_info, "logs": my_df[["日時", "現場", "金額"]].to_dict(orient="records")}
                            with st.spinner("送信中..."):
                                try:
                                    res_upd = session.post(GAS_URL, json=invoice_data, timeout=30)
                                    if res_upd.json().get("status") == "success":
                                        st.success("送信が完了しました。")
                                    else:
                                        st.error("送信に失敗しました。")
                                except:
                                    st.error("通信エラーが発生しました。")
                else:
                    st.info("データがありません")
        except:
            st.error("データ取得中にエラーが発生しました")