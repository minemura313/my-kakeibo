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
    button[data-baseweb="tab"] { font-size: 18px !important; font-weight: bold; }
    .stNumberInput, .stDateInput, .stSelectbox { background-color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 ポケ家計簿")

# --- スプレッドシート接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # ttl=0 でキャッシュを無効化し、常に最新のスプレッドシートを読み込む
        df = conn.read(ttl=0) 
        
        if df is None or df.empty:
            return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])
            
        # 列名の前後の空白を削除
        df.columns = df.columns.str.strip()
        
        # 必要な列だけを抽出（余計な空列を無視）
        df = df[["日付", "カテゴリー", "金額"]].dropna(how='all')
        
        # 型のクリーンアップ
        df["日付"] = pd.to_datetime(df["日付"])
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0).astype(int)
        
        return df
    except Exception as e:
        # 接続エラー時は空のデータを返す
        return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])

def save_data(df_to_save):
    # 年月などの計算用列を除外して保存
    df_clean = df_to_save.drop(columns=['年月'], errors='ignore')
    # Sheet1 というシート名に対して上書き保存
    conn.update(worksheet="Sheet1", data=df_clean)

# データの読み込み
df = load_data()

# --- 集計表示（今月の合計） ---
if not df.empty:
    df['年月'] = df['日付'].dt.strftime('%Y-%m')
    current_month = datetime.date.today().strftime('%Y-%m')
    monthly_total = int(df[df['年月'] == current_month]['金額'].sum())
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
    # 0を表示させない設定
    amount = st.number_input("金額 (円)", min_value=0, step=100, format="%d", value=None, placeholder="金額を入力...")
    
    if st.button("記録を保存する"):
        if amount is not None and amount > 0:
            # 新しい行を作成
            new_row = pd.DataFrame([[date.strftime('%Y-%m-%d'), category, int(amount)]], 
                                    columns=["日付", "カテゴリー", "金額"])
            
            # 既存データに結合（年月列は除く）
            df_for_concat = df.drop(columns=['年月'], errors='ignore')
            df_updated = pd.concat([df_for_concat, new_row], ignore_index=True)
            
            # 保存
            save_data(df_updated)
            st.success("保存しました！")
            # 画面を更新して最新データを反映
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
        # 最新順に表示
        st.dataframe(df.sort_values("日付", ascending=False), use_container_width=True)
        
        st.divider()
        edit_idx = st.selectbox(
            "削除するデータを選択", 
            df.index, 
            format_func=lambda i: f"{df.loc[i, '日付'].strftime('%m/%d')} - {df.loc[i, 'カテゴリー']} ({int(df.loc[i, '金額']):,}円)"
        )
        
        if st.button("選択したデータを削除"):
            df_remaining = df.drop(edit_idx)
            save_data(df_remaining)
            st.success("削除しました")
            st.rerun()
    else:
        st.write("履歴はありません")

with st.sidebar:
    st.subheader("設定")
    if st.button("全データをリセット"):
        # 見出しのみの空のデータで上書き
        reset_df = pd.DataFrame(columns=["日付", "カテゴリー", "金額"])
        save_data(reset_df)
        st.rerun()
