import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import plotly.express as px

# --- UI設定 ---
st.set_page_config(page_title="ポケ家計簿", layout="centered")

# スマホ向けカスタムCSS（元のデザインを維持）
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
    button[data-baseweb="tab"] { font-size: 18px !important; font-weight: bold; }
    .stNumberInput, .stDateInput, .stSelectbox { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 ポケ家計簿")

# --- スプレッドシート接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # スプレッドシートから読み込み（キャッシュを無効化して常に最新を取得）
        df = conn.read(ttl=0)
        # 日付列を日時型に変換
        if not df.empty:
            df["日付"] = pd.to_datetime(df["日付"])
        return df
    except:
        return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])

def save_data(df):
    # スプレッドシートを更新
    conn.update(data=df)

df = load_data()

# --- アプリ起動時にすぐ見える集計表示 ---
if not df.empty:
    df['年月'] = df['日付'].dt.strftime('%Y-%m')
    current_month = datetime.date.today().strftime('%Y-%m')
    monthly_total = df[df['年月'] == current_month]['金額'].sum()
    st.metric(f"{current_month} の支出合計", f"{monthly_total:,} 円")
    st.write("")
else:
    st.info("データがありません。下の「入力」から記録を始めましょう！")

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
            # 新しい行を作成（日付を文字列に変換して保存）
            new_data = pd.DataFrame([[date.strftime('%Y-%m-%d'), category, amount]], 
                                    columns=["日付", "カテゴリー", "金額"])
            # 既存のデータに結合
            df_to_save = pd.concat([df.drop(columns=['年月'], errors='ignore'), new_data], ignore_index=True)
            save_data(df_to_save)
            st.success("スプレッドシートに保存しました！")
            st.rerun()
        else:
            st.warning("金額を入力してください")

with tab_chart:
    if not df.empty:
        category_sum = df.groupby("カテゴリー")["金額"].sum().reset_index()
        fig = px.pie(
            category_sum, 
            values='金額', 
            names='カテゴリー', 
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig.update_traces(textinfo='label+value', textfont_size=14)
        fig.update_layout(
            showlegend=False, 
            margin=dict(t=30, b=30, l=30, r=30),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
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
            df_to_save = df.drop(edit_idx).drop(columns=['年月'], errors='ignore')
            save_data(df_to_save)
            st.success("削除しました")
            st.rerun()
    else:
        st.write("履歴はありません")

with st.sidebar:
    st.subheader("設定")
    if st.button("全データをリセット"):
        # 空のデータフレームで上書き
        reset_df = pd.DataFrame(columns=["日付", "カテゴリー", "金額"])
        save_data(reset_df)
        st.rerun()
