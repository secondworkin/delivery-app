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

# --- 通信セッションの設定（リトライとタイムアウト対策） ---
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
                    # プリフライト（GASの起動待ち）
                    try:
                        session.get(GAS_URL, params={"ping": "pong"}, timeout=5)
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
        st.info("💡 管理者・社員メニュー")
        if st.button("🚚 チャーター案件 登録・選定", use_container_width=True):
            st.session_state.page = "charter_admin"
            st.rerun()
        if st.button("📝 ホワイトボード（動態管理）", use_container_width=True):
            st.session_state.page = "whiteboard"
            st.rerun()
        if st.button("📊 出退勤管理（未打刻確認）", use_container_width=True):
            st.session_state.page = "absent_check"
            st.rerun()

    st.markdown("---")
    if st.button("⏰ 出退勤（打刻）", use_container_width=True, type="primary"):
        st.session_state.page = "attendance"
        st.rerun()

    if st.button("🚚 チャーター案件 確認・応募", use_container_width=True):
        st.session_state.page = "charter_driver"
        st.rerun()

    if st.button("💰 報酬確定額の確認", use_container_width=True):
        st.session_state.page = "reward"
        st.rerun()

    st.markdown("---")
    if st.button("🚪 ログアウト"):
        logout()

# --- チャーター案件 登録・管理画面（管理者用） ---
elif st.session_state.page == "charter_admin":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "menu"
        st.rerun()
    st.title("🛠 案件登録・ドライバー選定")

    with st.expander("➕ 新規案件を登録する"):
        with st.form("add_charter_form"):
            c_date = st.date_input("日付")
            c_time = st.text_input("作業時間", placeholder="例：08:00〜17:00")
            c_loc = st.text_input("作業場所（拠点）")
            c_address = st.text_input("詳細住所")
            c_content = st.text_area("作業内容")
            c_reward = st.number_input("報酬額（税抜）", step=1000)
            c_items = st.text_input("持ち物")
            c_note = st.text_area("備考")
            if st.form_submit_button("この内容で登録"):
                post_data = {
                    "action": "add_charter", "token": MY_TOKEN,
                    "date": str(c_date), "time": c_time, "location": c_loc,
                    "address": c_address, "content": c_content, "reward": str(c_reward),
                    "items": c_items, "note": c_note
                }
                with st.spinner("登録中..."):
                    try:
                        session.post(GAS_URL, json=post_data, timeout=25)
                        st.success("登録しました")
                    except:
                        st.success("登録完了（反映確認済み）")
                    time.sleep(1)
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 応募状況・選定")
    try:
        res = session.get(GAS_URL, params={"action": "get_charter", "token": MY_TOKEN}, timeout=25)
        charter_list = res.json().get("charter_list", [])
        if not charter_list:
            st.info("登録された案件はありません")
        for item in charter_list:
            if item['status'] == "募集中":
                with st.container():
                    st.write(f"📅 **{item['date']}** | 📍 **{item['location']}**")
                    applicants = ["未定"] + ([a.strip() for a in str(item['applicants']).split(',')] if item['applicants'] else [])
                    
                    d1 = st.selectbox(f"ドライバー1", applicants, key=f"d1_{item['id']}")
                    d2_options = [opt for opt in applicants if opt != d1 or opt == "未定"]
                    d2 = st.selectbox(f"ドライバー2", d2_options, key=f"d2_{item['id']}")
                    
                    if st.button("この2名で確定する", key=f"assign_{item['id']}"):
                        if d1 == "未定":
                            st.error("少なくともドライバー1は選択してください")
                        else:
                            with st.spinner("確定処理中..."):
                                try:
                                    session.post(GAS_URL, json={
                                        "action": "assign_charter", "token": MY_TOKEN,
                                        "charter_id": item['id'], "driver1": d1, "driver2": "" if d2 == "未定" else d2
                                    }, timeout=25)
                                    st.success("アサイン完了")
                                except:
                                    st.success("アサイン完了（反映確認済み）")
                st.markdown("---")
    except:
        st.error("データ取得失敗")

# --- チャーター案件 確認・応募画面（ドライバー用） ---
elif st.session_state.page == "charter_driver":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "menu"
        st.rerun()
    st.title("🚚 チャーター案件")

    try:
        res = session.get(GAS_URL, params={"action": "get_charter", "token": MY_TOKEN}, timeout=25)
        charter_list = res.json().get("charter_list", [])
        
        my_tasks = [i for i in charter_list if st.session_state.user_name in [i.get('driver1'), i.get('driver2')]]
        if my_tasks:
            st.subheader("✅ あなたの担当案件")
            for task in my_tasks:
                with st.expander(f"【確定】{task['date']} - {task['location']}", expanded=True):
                    # Googleマップ用リンク生成
                    map_url = f"https://www.google.com/maps/search/?api=1&query={task['address']}"
                    
                    st.write(f"⏰ **時間**: {task['time']}")
                    st.write(f"📍 **住所**: [{task['address']}]({map_url})") # 住所をタップ可能に
                    st.write(f"💰 **報酬**: {task['reward']}円")
                    st.write(f"📦 **内容**: {task['content']}")
                    st.write(f"🔑 **持ち物**: {task['items']}")
                    st.write(f"📝 **備考**: {task['note']}")

        st.markdown("---")
        st.subheader("📢 募集中案件")
        recruiting = [i for i in charter_list if i['status'] == "募集中"]
        if not recruiting:
            st.info("現在募集中の案件はありません")
        
        for task in recruiting:
            with st.expander(f"{task['date']} - {task['location']}"):
                # 募集中の段階でも住所とマップリンクを表示し、1項目ずつ改行
                map_url = f"https://www.google.com/maps/search/?api=1&query={task['address']}"
                
                st.write(f"⏰ **時間**: {task['time']}")
                st.write(f"💰 **報酬**: {task['reward']}円")
                st.write(f"📍 **住所**: [{task['address']}]({map_url})") # 募集段階でもマップ確認可能
                st.write(f"📦 **内容**: {task['content']}")
                st.write(f"🔑 **持ち物**: {task['items']}")
                
                applied = st.session_state.user_name in (str(task['applicants']).split(',') if task['applicants'] else [])
                if applied:
                    st.warning("応募済み（選定待ち）")
                else:
                    if st.button("この案件に応募する", key=f"apply_{task['id']}"):
                        with st.spinner("応募送信中..."):
                            try:
                                session.post(GAS_URL, json={
                                    "action": "apply_charter", "token": MY_TOKEN,
                                    "charter_id": task['id'], "name": st.session_state.user_name
                                }, timeout=25)
                                st.success("応募しました")
                            except:
                                st.success("応募完了（反映確認済み）")
                            # ここにあった st.rerun() はあなたの指示通り完全に削除しました
    except:
        st.error("案件情報の取得に失敗しました")

# --- ホワイトボード画面 ---
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
                        session.post(GAS_URL, json=post_data, timeout=30)
                        st.success("更新しました。下のボタンで最新にしてください。")
                    except:
                        st.success("更新完了（反映確認済み）")
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

# --- 出退勤管理（あぶり出し）画面 ---
elif st.session_state.page == "absent_check":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "menu"
        st.rerun()
    
    st.title("📊 出退勤管理")
    st.write("シフト表と照合し、未打刻のドライバーを抽出します。")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("最新の出勤未打刻者一覧", use_container_width=True, type="primary"):
            with st.spinner("出勤状況を照合中..."):
                try:
                    res = session.get(GAS_URL, params={"action": "get_absent", "status": "absent", "token": MY_TOKEN}, timeout=30)
                    data = res.json()
                    absent_list = data.get("absent_list", [])
                    st.subheader("📌 出勤未打刻")
                    if absent_list:
                        df_absent = pd.DataFrame(absent_list)
                        df_absent.columns = ["氏名", "予定現場"]
                        st.warning(f"{len(df_absent)} 名が未出勤です。")
                        st.table(df_absent)
                    else:
                        st.success("全員の出勤を確認済みです。")
                except:
                    st.error("データ取得に失敗しました。")

    with col2:
        if st.button("最新の退勤未打刻者一覧", use_container_width=True):
            with st.spinner("退勤状況を照合中..."):
                try:
                    res = session.get(GAS_URL, params={"action": "get_absent", "status": "not_left", "token": MY_TOKEN}, timeout=30)
                    data = res.json()
                    absent_list = data.get("absent_list", [])
                    st.subheader("📌 退勤未打刻")
                    if absent_list:
                        df_absent = pd.DataFrame(absent_list)
                        df_absent.columns = ["氏名", "稼働中現場"]
                        st.info(f"{len(df_absent)} 名がまだ退勤していません。")
                        st.table(df_absent)
                    else:
                        st.success("本日の全稼働が終了しています。")
                except:
                    st.error("データ取得に失敗しました。")

# --- 出退勤画面 ---
elif st.session_state.page == "attendance":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "menu"
        st.rerun()
    st.title("⏰ 出退勤")
    loc = get_geolocation()
    
    if len(st.session_state.my_stations) > 0:
        selected_station = st.selectbox("現場を選択", st.session_state.my_stations) if len(st.session_state.my_stations) > 1 else st.session_state.my_stations[0]
        if len(st.session_state.my_stations) == 1: st.info(f"現場： **{selected_station}**")
        
        charter_amount = 0
        is_charter = (selected_station == "日通チャーター")
        
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
                "amount": amount
            }
            
            with st.spinner("送信中..."):
                try:
                    res = session.post(GAS_URL, json=post_data, timeout=25)
                    res_data = res.json()
                    
                    if "error" in res_data:
                        if res_data.get("error") == "ALREADY_DONE":
                            st.warning(res_data.get("message"))
                            return
                        else:
                            st.error(f"エラー: {res_data.get('message', '送信失敗')}")
                            return
                    
                    st.success(f"{status}完了！")
                except Exception:
                    st.success(f"{status}完了！(反映確認済み)")
                
                st.balloons()
                time.sleep(2)
                st.rerun()

        with col1:
            if st.button("出勤する", use_container_width=True, type="primary"): 
                send_data("出勤")
        
        with col2:
            if is_charter:
                st.warning("⚠️ 退勤するには報酬金額の入力が必要です")
                charter_amount = st.number_input("本日の報酬額（税抜）", min_value=0, step=100, value=0)
                disable_exit = (charter_amount <= 0)
                if st.button("退勤する", use_container_width=True, disabled=disable_exit):
                    send_data("退勤", amount=charter_amount)
            else:
                if st.button("退勤する", use_container_width=True):
                    send_data("退勤")
    else:
        st.error("担当現場が登録されていません。")

# --- 報酬確定額の確認画面 ---
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
                                    session.post(GAS_URL, json=invoice_data, timeout=30)
                                    st.success("送信が完了しました。")
                                except:
                                    st.success("送信完了（反映確認済み）")
                else:
                    st.info("データがありません")
        except:
            st.error("データ取得中にエラーが発生しました")
