import streamlit as st
import requests
from streamlit_js_eval import get_geolocation
import pandas as pd
import base64
from datetime import datetime

# --- 設定 ---
GAS_URL = st.secrets["GAS_URL"]
MY_TOKEN = st.secrets["MY_TOKEN"]

st.set_page_config(page_title="勤怠管理システム", layout="centered")

# セッション状態の初期化
if "page" not in st.session_state:
    st.session_state.page = "login"

# --- 1. ログイン管理 ---
if "user_name" not in st.session_state:
    st.title("🔑 ログイン")
    user_id = st.text_input("割り当てられたIDを入力してください", key="login_id")
    
    if st.button("ログイン"):
        if user_id:
            try:
                # GAS側のIDチェック（doGet）
                res = requests.get(GAS_URL, params={"id": user_id, "token": MY_TOKEN}, timeout=10)
                data = res.json()
                if "error" not in data:
                    st.session_state.user_name = data["name"]
                    st.session_state.my_stations = data["stations"]
                    st.session_state.page = "menu"
                    st.rerun()
                else:
                    st.error("IDが正しくありません")
            except Exception as e:
                st.error("通信エラー: GASのURLが正しいか確認してください")
        else:
            st.warning("IDを入力してください")
    st.stop()

# --- 2. 共通メニュー・ログアウト処理 ---
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
    st.write(f"利用者： **{st.session_state.user_name}** さん")

    loc = get_geolocation()

    if len(st.session_state.my_stations) > 0:
        if len(st.session_state.my_stations) > 1:
            selected_station = st.selectbox("現場を選択", st.session_state.my_stations)
        else:
            selected_station = st.session_state.my_stations[0]
            st.info(f"現場： **{selected_station}**")
        
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
                    requests.post(GAS_URL, json=post_data, timeout=10)
                    st.success(f"{status}完了！")
                    st.balloons()
                except:
                    st.error("送信に失敗しました")

        with col1:
            if st.button("出勤する", use_container_width=True, type="primary"):
                send_data("出勤")
        with col2:
            if st.button("退勤する", use_container_width=True):
                send_data("退勤")
    else:
        st.error("担当現場が登録されていません。")

# --- 5. 報酬確定額の確認画面 ---
elif st.session_state.page == "reward":
    if st.button("⬅️ メニューに戻る"):
        st.session_state.page = "menu"
        st.rerun()

    st.title("💰 報酬確定額")
    st.write(f"対象者： **{st.session_state.user_name}** さん")

    # --- 📅 月選択メニューの追加 ---
    now = datetime.now()
    month_options = []
    for i in range(5): # 直近5ヶ月分を選択肢に
        m = (now.month - i - 1) % 12 + 1
        y = now.year + (now.month - i - 1) // 12
        month_options.append(f"{y}/{m:02d}")
    
    selected_month = st.selectbox("表示する月を選択してください", month_options)

    with st.spinner("データを集計中..."):
        try:
            stations_str = ",".join(st.session_state.my_stations)
            res = requests.get(GAS_URL, params={
                "token": MY_TOKEN, 
                "action": "get_logs", 
                "stations": stations_str
            }, timeout=10)
            
            logs = res.json().get("logs", [])
            
            if logs:
                df = pd.DataFrame(logs, columns=["日時", "名前", "状態", "グループ", "金額", "場所"])
                
                # 日付型に変換
                df["日時_dt"] = pd.to_datetime(df["日時"])
                # 選択された月でフィルタリング
                target_y, target_m = map(int, selected_month.split("/"))
                my_df = df[
                    (df["名前"] == st.session_state.user_name) & 
                    (df["金額"] != "") &
                    (df["日時_dt"].dt.year == target_y) &
                    (df["日時_dt"].dt.month == target_m)
                ].copy()
                
                if not my_df.empty:
                    my_df["現場"] = my_df["グループ"].apply(lambda x: str(x)[:-1])
                    total_reward = pd.to_numeric(my_df["金額"]).sum()
                    
                    st.metric(f"{selected_month} の合計報酬（概算）", f"{total_reward:,} 円")
                    
                    st.write("### 稼働履歴")
                    my_df["日時_表示"] = my_df["日時_dt"].dt.strftime('%m/%d %H:%M')
                    display_df = my_df[["日時_表示", "現場", "金額"]]
                    st.dataframe(display_df, use_container_width=True, hide_index=True)

                    # --- 📝 請求書PDF発行フォーム ---
                    st.markdown("---")
                    st.subheader("📄 請求書の発行")
                    st.caption("※以下の情報はPDF作成時のみ使用され、クラウドには保存されません。")
                    
                    zip_code = st.text_input("郵便番号", placeholder="123-4567")
                    address = st.text_input("住所", placeholder="石川県金沢市...")
                    bank_info = st.text_input("振込先口座", placeholder="〇〇銀行 〇〇支店 普通 1234567")
                    
                    if st.button("請求書PDFを作成する", use_container_width=True, type="primary"):
                        if not zip_code or not address or not bank_info:
                            st.warning("すべての情報を入力してください。")
                        else:
                            invoice_data = {
                                "action": "create_pdf",
                                "token": MY_TOKEN,
                                "name": st.session_state.user_name,
                                "zip": zip_code,
                                "address": address,
                                "bank": bank_info,
                                # フィルタリング済みのデータを送る
                                "logs": my_df[["日時", "現場", "金額"]].to_dict(orient="records")
                            }
                            
                            with st.spinner("PDFを生成中..."):
                                try:
                                    res_pdf = requests.post(GAS_URL, json=invoice_data, timeout=30)
                                    res_json = res_pdf.json()
                                    
                                    if res_json.get("status") == "success":
                                        # Base64をデコードしてダウンロードボタンを表示
                                        pdf_bytes = base64.b64decode(res_json["pdfData"])
                                        st.success("PDFの作成が完了しました！")
                                        st.download_button(
                                            label="📥 PDFをダウンロード",
                                            data=pdf_bytes,
                                            file_name=res_json["fileName"],
                                            mime="application/pdf",
                                            use_container_width=True
                                        )
                                    else:
                                        st.error(f"エラー: {res_json.get('message')}")
                                except Exception as e:
                                    st.error(f"PDFの生成に失敗しました: {e}")

                else:
                    st.info(f"{selected_month} の集計対象データが見つかりませんでした。")
            else:
                st.info("ログデータがありません。")
        except Exception as e:
            st.error(f"データ取得エラー: {e}")