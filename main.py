import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- UI設定 ---
st.set_page_config(page_title="ポケ家計簿", layout="centered")

# スマホ向けカスタムCSS
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #212529; }
    div.stButton > button {
        width: 100%; height: 3.5em; font-weight: bold;
        border-radius: 12px; background-color: #007bff;
        color: white; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 ポケ家計簿")

# --- スプレッドシート接続 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"接続設定自体にミスがあります: {e}")

def load_data():
    try:
        # スプレッドシートを読み込む
        df = conn.read(ttl=0) 
        
        # 【デバッグ用】読み込めた列名を画面に出す（後で消します）
        if df is not None:
            st.write("🔍 デバッグ情報: スプレッドシートから読み取った列名:", df.columns.tolist())
        
        if df is None or df.empty:
            return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])
            
        df.columns = df.columns.str.strip()
        
        # 必要な列があるかチェック
        required = ["日付", "カテゴリー", "金額"]
        for col in required:
            if col not in df.columns:
                st.warning(f"スプレッドシートに『{col}』という列が見つかりません。")
                return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])

        df = df[required].dropna(how='all')
        df["日付"] = pd.to_datetime(df["日付"])
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"読み込みエラーが発生しました: {e}")
        return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])

def save_data(df_to_save):
    try:
        df_clean = df_to_save.drop(columns=['年月'], errors='ignore')
        # シート名を明示的に指定して更新
        conn.update(worksheet="Sheet1", data=df_clean)
        st.success("スプレッドシートを更新しました！")
    except Exception as e:
        st.error(f"保存エラーが発生しました: {e}")

# データの読み込み
df = load_data()

# --- メイン画面 ---
if not df.empty:
    df['年月'] = df['日付'].dt.strftime('%Y-%m')
    current_month = datetime.date.today().strftime('%Y-%m')
    monthly_total = int(df[df['年月'] == current_month]['金額'].sum())
    st.metric(f"{current_month} の支出合計", f"{monthly_total:,} 円")
else:
    st.info("データがありません。スプレッドシートの1行目と列名が合っているか確認してください。")

# 入力フォーム
with st.expander("＋ 新しく入力する", expanded=True):
    date = st.date_input("日付", datetime.date.today())
    category = st.selectbox("カテゴリー", ["食費", "日用品", "趣味", "交通費", "通信費", "その他"])
    amount = st.number_input("金額 (円)", min_value=0, step=100, value=None, placeholder="金額を入力...")
    
    if st.button("記録を保存する"):
        if amount is not None and amount > 0:
            new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), category, int(amount)]], 
                                    columns=["日付", "カテゴリー", "金額"])
            df_updated = pd.concat([df.drop(columns=['年月'], errors='ignore'), new_row], ignore_index=True)
            save_data(df_updated)
            st.rerun()

# 履歴表示
if not df.empty:
    st.subheader("履歴")
    st.dataframe(df.sort_values("日付", ascending=False), use_container_width=True)
