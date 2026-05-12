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
        # キャッシュなしで読み込み
        df = conn.read(ttl=0) 
        if df is None or df.empty:
            return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])
        
        # 列名のクリーンアップ
        df.columns = df.columns.str.strip()
        df = df[["日付", "カテゴリー", "金額"]].dropna(how='all')
        
        # 日付と金額の型変換
        df["日付"] = pd.to_datetime(df["日付"], errors='coerce', format='mixed')
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0).astype(int)
        df = df.dropna(subset=["日付"])
        
        # 【新機能】フィルタリング用に「年月」列を作成
        df['年月'] = df['日付'].dt.strftime('%Y-%m')
        return df
    except Exception as e:
        return pd.DataFrame(columns=["日付", "カテゴリー", "金額", "年月"])

def save_data(df_to_save):
    try:
        # 保存時は計算用の「年月」列を削除
        df_clean = df_to_save.drop(columns=['年月'], errors='ignore')
        df_clean["日付"] = df_clean["日付"].dt.strftime('%Y-%m-%d')
        conn.update(worksheet="Sheet1", data=df_clean)
        st.success("データを更新しました！")
    except Exception as e:
        st.error(f"保存エラー: {e}")

# データの読み込み
df = load_data()

# --- サイドバー：月選択機能 ---
with st.sidebar:
    st.header("表示設定")
    if not df.empty:
        # スプレッドシートにある年月を重複なく取得し、新しい順に並べる
        month_list = sorted(df['年月'].unique(), reverse=True)
        
        # 今月（今日の日付の年月）を初期選択にする。なければリストの先頭。
        this_month = datetime.date.today().strftime('%Y-%m')
        default_idx = month_list.index(this_month) if this_month in month_list else 0
        
        selected_month = st.selectbox("表示する月を選択", month_list, index=default_idx)
        
        # 選択された月のデータだけに絞り込む
        display_df = df[df['年月'] == selected_month]
    else:
        st.info("データがまだありません")
        display_df = df
        selected_month = datetime.date.today().strftime('%Y-%m')

    st.divider()
    if st.button("全データをリセット"):
        save_data(pd.DataFrame(columns=["日付", "カテゴリー", "金額"]))
        st.rerun()

# --- メイン画面の表示 ---
if not display_df.empty:
    monthly_total = int(display_df['金額'].sum())
    st.metric(f"{selected_month} の支出合計", f"{monthly_total:,} 円")
else:
    st.info(f"{selected_month} のデータはまだ登録されていません。")

# --- タブ ---
tab_input, tab_chart, tab_history = st.tabs(["＋ 入力", "📊 分析", "📜 履歴"])

with tab_input:
    st.subheader("クイック入力")
    date = st.date_input("日付", datetime.date.today())
    category = st.radio("カテゴリー", ["食費", "日用品", "趣味", "交通費", "通信費", "ジム", "その他"], horizontal=True)
    amount = st.number_input("金額 (円)", min_value=0, step=100, value=None, placeholder="金額を入力...")
    
    if st.button("記録を保存する"):
        if amount is not None and amount > 0:
            new_row = pd.DataFrame([[pd.to_datetime(date), category, int(amount)]], 
                                    columns=["日付", "カテゴリー", "金額"])
            # 保存時は年月列を除いた全データと結合
            df_for_save = df.drop(columns=['年月'], errors='ignore')
            df_updated = pd.concat([df_for_save, new_row], ignore_index=True)
            save_data(df_updated)
            st.rerun()

with tab_chart:
    if not display_df.empty:
        st.subheader(f"{selected_month} のカテゴリー別支出")
        category_sum = display_df.groupby("カテゴリー")["金額"].sum().reset_index()
        fig = px.pie(category_sum, values='金額', names='カテゴリー', hole=0.5)
        fig.update_traces(
            textinfo='label+value', 
            texttemplate='%{label}<br>%{value:,}円',
            textfont_size=14
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("表示するデータがありません")

with tab_history:
    if not display_df.empty:
        st.subheader(f"{selected_month} の履歴")
        # 選択した月のデータを日付順に表示
        st.dataframe(display_df.sort_values("日付", ascending=False)[["日付", "カテゴリー", "金額"]], use_container_width=True)
        
        st.divider()
        # 削除機能も表示中の月のデータから選択
        edit_idx = st.selectbox(
            "削除するデータを選択", 
            display_df.index, 
            format_func=lambda i: f"{display_df.loc[i, '日付'].strftime('%m/%d')} - {display_df.loc[i, 'カテゴリー']} ({int(display_df.loc[i, '金額']):,}円)"
        )
        if st.button("選択したデータを削除"):
            save_data(df.drop(edit_idx))
            st.rerun()
    else:
        st.write("履歴はありません")
