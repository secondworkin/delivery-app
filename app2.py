import streamlit as st
import requests
from streamlit_js_eval import get_geolocation
import pandas as pd
from datetime import datetime, timedelta
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import time

# --- 設定 ---
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

# --- 通信セッションの設定 ---
@st.cache_resource
def get_ultimate_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = get_ultimate_session()

st.set_page_config(page_title="勤怠管理システム", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "login"

# --- 共通関数：日本時間への整形 ---
def format_date_jp(x):
    try:
        if not x or x == "": return ""
        dt = pd.to_datetime(x)
        if dt.tzinfo is None or "Z" in str(x):
             if dt.hour < 9:
                 dt = dt + timedelta(hours=9)
        return dt.strftime('%m/%d %H:%M')
    except:
        return x

# --- 1. ログイン管理 ---
if "user_name" not in st.session_state:
    st.title("🔑 ログイン")
    user_id = st.text_input("割り当てられたIDを入力してください", key="login_id")
    if st.button("ログイン"):
        if user_id:
            with st.spinner("認証情報を確認しています..."):
                try:
                    try:
                        session.get(GAS_URL, params={"ping": "pong"}, timeout=3)
                    except:
                        pass
                    
                    time.sleep(1)
                    
                    res = session.get(GAS_URL, params={"id": user_id, "token": MY_TOKEN}, timeout=25)
                    data = res.json()
                    
                    if "error" not in data:
                        st.session_state.user_name = data["name"]
                        st.session_state.my_stations = data["stations"]
                        st.session_state.is_admin = data.get("isAdmin", False)
                        st.session_state.page = "menu"
                        st.rerun()
                    else:
                        st.error(f"ログイン失敗: {data.get('error')}")
                except Exception as e:
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
    
    if st.session_state.is_admin:
        st.info("💡 管理者・社員メニューが利用可能です")
        if st.button("📝 ホワイトボード（動態管理）", use_container_width=True):
            st.session_state.page = "whiteboard"
            st.rerun()

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

# --- 4. ホワイトボード画面 ---
elif st.session_state.page == "whiteboard":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "menu"
        st.rerun()
    
    st.title("📝 ホワイトボード")
    
    with st.expander("自分の動きを更新する", expanded=True):
        new_content = st.text_input("現在の業務内容を入力", placeholder="例：〇〇で営業 16時帰社予定")
        if st.button("ホワイトボードを更新"):
            if new_content:
                with st.spinner("送信中..."):
                    try:
                        post_data = {
                            "action": "update_whiteboard",
                            "token": MY_TOKEN,
                            "name": st.session_state.user_name,
                            "content": new_content
                        }
                        res = session.post(GAS_URL, json=post_data, timeout=40)
                        if res.json().get("status") == "success":
                            st.success("更新しました。下のボタンで表を最新にしてください。")
                        else:
                            st.error("更新に失敗しました。")
                    except:
                        st.error("通信エラーが発生しました。")
            else:
                st.warning("内容を入力してください")

    st.markdown("---")
    st.subheader("現在の社員の動き")
    
    if st.button("🔄 最新の状態に更新", use_container_width=True):
        st.rerun()

    with st.spinner("最新情報を取得中..."):
        try:
            res = session.get(GAS_URL, params={"action": "get_whiteboard", "token": MY_TOKEN}, timeout=30)
            board_data = res.json().get("board", [])
            if board_data:
                df_wb = pd.DataFrame(board_data, columns=["氏名", "業務内容", "最終更新"])
                df_wb["最終更新"] = df_wb["最終更新"].apply(format_date_jp)
                st.table(df_wb)
            else:
                st.info("掲示板にデータがありません")
        except:
            st.error("データの読み込みに失敗しました。")

# --- 5. 出退勤画面 ---
elif st.session_state.page == "attendance":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "menu"
        st.rerun()
    st.title("⏰ 出退勤")
    loc = get_geolocation()
    
    if len(st.session_state.my_stations) > 0:
        selected_station = st.selectbox("現場を選択", st.session_state.my_stations) if len(st.session_state.my_stations) > 1 else st.session_state.my_stations[0]
        if len(st.session_state.my_stations) == 1: st.info(f"現場： **{selected_station}**")
        
        # --- チャーター報酬入力ロジック (追加) ---
        charter_amount = 0
        is_charter = (selected_station == "日通チャーター")
        
        if is_charter:
            st.warning("⚠️ 日通チャーターは退勤時に金額入力が必要です")
            charter_amount = st.number_input("本日のチャーター報酬額（税抜）を入力してください", min_value=0, step=100, value=0)
        
        col1, col2 = st.columns(2)
        
        def send_data(status, amount=None):
            location_data = "GPS取得失敗"
            if loc:
                lat, lon = loc['coords']['latitude'], loc['coords']['longitude']
                location_data = f"http://maps.google.com/?q={lat},{lon}"
            
            post_data = {
                "token": MY_TOKEN, 
                "station": selected_station, 
                "name": st.session_state.user_name, 
                "status": status, 
                "location": location_data,
                "amount": amount  # 金額を送る（チャーター以外はNone）
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
                        time.sleep(2)
                        st.rerun()
                except:
                    st.error("通信エラーが発生しました。もう一度お試しください。")

        with col1:
            if st.button("出勤する", use_container_width=True, type="primary"): 
                send_data("出勤")
        
        with col2:
            # チャーター時は金額が0ならボタンを無効化（案A）
            disable_exit = is_charter and (charter_amount <= 0)
            if st.button("退勤する", use_container_width=True, disabled=disable_exit):
                send_data("退勤", amount=charter_amount if is_charter else None)
            
            if disable_exit:
                st.caption("※金額を入力すると退勤ボタンが押せます")

    else:
        st.error("担当現場が登録されていません。")

# --- 6. 報酬確定額の確認画面 ---
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
                    # グループ名から現場名を抽出するロジック（適宜調整）
                    my_df["現場"] = my_df["グループ"].apply(lambda x: str(x)[:-1] if x else "チャーター")
                    st.metric(f"{selected_month} の合計報酬", f"{pd.to_numeric(my_df['金額']).sum():,} 円")
                    st.dataframe(my_df[["日時", "現場", "金額"]].assign(日時=my_df["日時_dt"].dt.strftime('%m/%d %H:%M')), use_container_width=True, hide_index=True)

                    st.markdown("---")
                    st.subheader("📄 請求書情報の申請")
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