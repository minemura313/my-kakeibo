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
    [data-testid="stMetric"] {
        background-color: #ffffff; padding: 20px;
        border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }
    [data-testid="stMetricValue"] { color: #007bff !important; font-size: 36px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 ポケ家計簿")

# --- スプレッドシート接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl=0) 
        if df is None or df.empty:
            return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])
        df.columns = df.columns.str.strip()
        df = df[["日付", "カテゴリー", "金額"]].dropna(how='all')
        df["日付"] = pd.to_datetime(df["日付"], errors='coerce', format='mixed')
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0).astype(int)
        return df.dropna(subset=["日付"])
    except Exception as e:
        return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])

def save_data(df_to_save):
    try:
        df_clean = df_to_save.drop(columns=['年月'], errors='ignore')
        df_clean["日付"] = df_clean["日付"].dt.strftime('%Y-%m-%d')
        conn.update(worksheet="Sheet1", data=df_clean)
        st.success("スプレッドシートに保存しました！")
    except Exception as e:
        st.error(f"保存エラー: {e}")

# データの読み込み
df = load_data()

# --- 集計・表示 ---
if not df.empty:
    df['年月'] = df['日付'].dt.strftime('%Y-%m')
    current_month = datetime.date.today().strftime('%Y-%m')
    monthly_total = int(df[df['年月'] == current_month]['金額'].sum())
    st.metric(f"{current_month} の支出合計", f"{monthly_total:,} 円")
else:
    st.info("データがありません。入力を開始しましょう！")

# --- タブ ---
tab_input, tab_chart, tab_history = st.tabs(["＋ 入力", "📊 分析", "📜 履歴"])

with tab_input:
    st.subheader("クイック入力")
    date = st.date_input("日付", datetime.date.today())
    # ジムを追加したカテゴリー
    category = st.radio("カテゴリー", ["食費", "日用品", "趣味", "交通費", "通信費", "ジム", "その他"], horizontal=True)
    amount = st.number_input("金額 (円)", min_value=0, step=100, value=None, placeholder="金額を入力...")
    
    if st.button("記録を保存する"):
        if amount is not None and amount > 0:
            new_row = pd.DataFrame([[pd.to_datetime(date), category, int(amount)]], 
                                    columns=["日付", "カテゴリー", "金額"])
            df_updated = pd.concat([df, new_row], ignore_index=True)
            save_data(df_updated)
            st.rerun()

with tab_chart:
    if not df.empty:
        st.subheader("カテゴリー別支出")
        category_sum = df.groupby("カテゴリー")["金額"].sum().reset_index()
        
        # グラフ作成
        fig = px.pie(
            category_sum, 
            values='金額', 
            names='カテゴリー', 
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        
        # 【修正ポイント】textinfoを 'label+value' にして金額を表示
        fig.update_traces(
            textinfo='label+value', 
            texttemplate='%{label}<br>%{value:,}円', # ラベルとカンマ区切り金額
            textfont_size=14
        )
        
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("データがありません")

with tab_history:
    if not df.empty:
        st.dataframe(df.sort_values("日付", ascending=False), use_container_width=True)
        st.divider()
        edit_idx = st.selectbox("削除するデータを選択", df.index, 
                                format_func=lambda i: f"{df.loc[i, '日付'].strftime('%m/%d')} - {df.loc[i, 'カテゴリー']} ({int(df.loc[i, '金額']):,}円)")
        if st.button("選択したデータを削除"):
            save_data(df.drop(edit_idx))
            st.rerun()

with st.sidebar:
    if st.button("全データをリセット"):
        save_data(pd.DataFrame(columns=["日付", "カテゴリー", "金額"]))
        st.rerun()
