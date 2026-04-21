import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px

# --- 設定 ---
DATA_FILE = "kakeibo_data.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE, parse_dates=["日付"])
            return df.dropna(how='all')
        except:
            return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])
    else:
        return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- UI設定 ---
st.set_page_config(page_title="ポケ家計簿", layout="centered")

# スマホで見やすくするための明るいデザインカスタム
st.markdown("""
    <style>
    /* 全体の背景を白、文字を黒に近く */
    .stApp {
        background-color: #f8f9fa;
        color: #212529;
    }
    /* ボタンを青色にして押しやすく */
    div.stButton > button {
        width: 100%;
        height: 3.5em;
        font-weight: bold;
        border-radius: 12px;
        background-color: #007bff;
        color: white;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    /* 今月の支出（メトリック）をカード風に目立たせる */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }
    [data-testid="stMetricValue"] {
        color: #007bff !important;
        font-size: 36px !important;
    }
    /* タブのデザインをスマホに最適化 */
    button[data-baseweb="tab"] {
        font-size: 18px !important;
        font-weight: bold;
    }
    /* 入力エリアの背景 */
    .stNumberInput, .stDateInput, .stSelectbox {
        background-color: white;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 ポケ家計簿")

df = load_data()

# --- タブ管理 ---
tab_input, tab_chart, tab_history = st.tabs(["＋ 入力", "📊 分析", "📜 履歴"])

with tab_input:
    st.subheader("クイック入力")
    date = st.date_input("日付", datetime.date.today())
    category = st.radio(
        "カテゴリー", 
        ["食費", "日用品", "趣味", "交通費", "通信費", "その他"],
        horizontal=True
    )
    amount = st.number_input("金額 (円)", min_value=0, step=100, format="%d")
    
    if st.button("記録を保存する"):
        if amount > 0:
            new_data = pd.DataFrame([[pd.to_datetime(date), category, amount]], 
                                    columns=["日付", "カテゴリー", "金額"])
            df = pd.concat([df, new_data], ignore_index=True)
            save_data(df)
            st.success("保存しました！")
            st.rerun()
        else:
            st.warning("金額を入力してください")

with tab_chart:
    if not df.empty:
        # 今月の集計
        df['年月'] = df['日付'].dt.strftime('%Y-%m')
        current_month = datetime.date.today().strftime('%Y-%m')
        monthly_total = df[df['年月'] == current_month]['金額'].sum()
        
        st.metric(f"{current_month} の支出額", f"{monthly_total:,} 円")
        
        # 円グラフ
        category_sum = df.groupby("カテゴリー")["金額"].sum().reset_index()
        fig = px.pie(
            category_sum, 
            values='金額', 
            names='カテゴリー', 
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Safe # 見やすい色合い
        )
        fig.update_traces(textinfo='label+value', textfont_size=14)
        fig.update_layout(
            showlegend=False, 
            margin=dict(t=30, b=30, l=30, r=30),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, width="stretch")
        
        st.table(category_sum.set_index("カテゴリー")["金額"].map("{:,}円".format))
    else:
        st.info("まだデータがありません")

with tab_history:
    st.header("履歴の編集")
    if not df.empty:
        st.dataframe(df.sort_values("日付", ascending=False), width="stretch")
        
        st.divider()
        edit_idx = st.selectbox(
            "削除するデータを選択", 
            df.index, 
            format_func=lambda i: f"{df.loc[i, '日付'].strftime('%m/%d')} - {df.loc[i, 'カテゴリー']} ({df.loc[i, '金額']}円)"
        )
        
        if st.button("選択したデータを削除"):
            df = df.drop(edit_idx)
            save_data(df)
            st.success("削除しました")
            st.rerun()
    else:
        st.write("履歴はありません")

with st.sidebar:
    st.subheader("設定")
    if st.button("全データをリセット"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.rerun()
