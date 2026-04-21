import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px

# --- 設定 ---
DATA_FILE = "kakeibo_data.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, parse_dates=["日付"])
        return df.dropna(how='all')
    else:
        return pd.DataFrame(columns=["日付", "カテゴリー", "金額"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- メイン UI ---
st.set_page_config(page_title="ポケ家計簿", layout="centered") # スマホで見やすい中央寄せ

# スマホで押しやすいようにCSSでボタンを大きくする
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        height: 3em;
        font-size: 18px !important;
        font-weight: bold;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .stMetric {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 ポケ家計簿")

df = load_data()

# --- メイン画面をタブで管理（スマホの親指操作を意識） ---
tab_input, tab_chart, tab_history = st.tabs(["＋ 入力", "📊 分析", "📜 履歴"])

with tab_input:
    st.header("クイック入力")
    date = st.date_input("日付", datetime.date.today())
    category = st.radio(
        "カテゴリー", 
        ["食費", "日用品", "趣味・娯楽", "交通費", "通信費", "その他"],
        horizontal=True # スマホで選択しやすい横並び
    )
    amount = st.number_input("金額 (円)", min_value=0, step=100, format="%d")
    
    if st.button("記録する"):
        new_data = pd.DataFrame([[pd.to_datetime(date), category, amount]], 
                                columns=["日付", "カテゴリー", "金額"])
        df = pd.concat([df, new_data], ignore_index=True)
        save_data(df)
        st.success("保存しました！")
        st.rerun()

with tab_chart:
    if not df.empty:
        # サマリー
        df['年月'] = df['日付'].dt.strftime('%Y-%m')
        current_month = datetime.date.today().strftime('%Y-%m')
        monthly_total = df[df['年月'] == current_month]['金額'].sum()
        
        st.metric(f"{current_month} の支出", f"{monthly_total:,} 円")
        
        # 円グラフ
        category_sum = df.groupby("カテゴリー")["金額"].sum().reset_index()
        fig = px.pie(category_sum, values='金額', names='カテゴリー', color='カテゴリー', hole=0.5)
        fig.update_traces(textposition='inside', textinfo='label+value')
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, width="stretch")
        
        st.table(category_sum.set_index("カテゴリー")["金額"].map("{:,}円".format))
    else:
        st.info("データがありません")

with tab_history:
    st.header("履歴の編集")
    if not df.empty:
        # 修正・削除
        edit_idx = st.selectbox(
            "修正するデータを選択", 
            df.index, 
            format_func=lambda i: f"{df.loc[i, '日付'].strftime('%m/%d')} - {df.loc[i, 'カテゴリー']} ({df.loc[i, '金額']}円)"
        )
        
        with st.expander("選択中のデータを編集"):
            row = df.loc[edit_idx]
            new_date = st.date_input("日付修正", row["日付"], key="ed")
            new_cat = st.selectbox("カテゴリ修正", ["食費", "日用品", "趣味・娯楽", "交通費", "通信費", "その他"], 
                                   index=["食費", "日用品", "趣味・娯楽", "交通費", "通信費", "その他"].index(row["カテゴリー"]), key="ec")
            new_amount = st.number_input("金額修正", value=int(row["金額"]), min_value=0, step=10, key="ea")
            
            if st.button("更新"):
                df.at[edit_idx, "日付"] = pd.to_datetime(new_date)
                df.at[edit_idx, "カテゴリー"] = new_cat
                df.at[edit_idx, "金額"] = new_amount
                save_data(df)
                st.rerun()
            
            if st.button("このデータを削除"):
                df = df.drop(edit_idx)
                save_data(df)
                st.rerun()
        
        st.divider()
        st.dataframe(df.sort_values("日付", ascending=False), width="stretch")
    else:
        st.write("データがありません")

# サイドバーは設定用として残す
with st.sidebar:
    st.subheader("設定")
    if st.button("全データをリセット"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.rerun()
