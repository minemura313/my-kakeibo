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
st.set_page_config(page_title="シンプル家計簿", layout="wide")
st.title("💰 家計簿アプリ")

df = load_data()

# --- サイドバー ---
with st.sidebar:
    tab1, tab2 = st.tabs(["新規入力", "データの編集"])
    
    with tab1:
        st.header("新規入力")
        date = st.date_input("日付", datetime.date.today(), key="add_date")
        category = st.selectbox("カテゴリー", ["食費", "日用品", "趣味・娯楽", "交通費", "通信費", "その他"], key="add_cat")
        amount = st.number_input("金額 (円)", min_value=0, step=10, key="add_amount")
        
        if st.button("追加"):
            new_data = pd.DataFrame([[pd.to_datetime(date), category, amount]], 
                                    columns=["日付", "カテゴリー", "金額"])
            df = pd.concat([df, new_data], ignore_index=True)
            save_data(df)
            st.success("追加しました！")
            st.rerun()

    with tab2:
        st.header("データの修正・削除")
        if not df.empty:
            edit_idx = st.selectbox(
                "修正するデータを選択", 
                df.index, 
                format_func=lambda i: f"{df.loc[i, '日付'].strftime('%m/%d')} - {df.loc[i, 'カテゴリー']} ({df.loc[i, '金額']}円)"
            )
            
            row = df.loc[edit_idx]
            new_date = st.date_input("日付を変更", row["日付"], key="edit_date")
            new_cat = st.selectbox(
                "カテゴリーを変更", 
                ["食費", "日用品", "趣味・娯楽", "交通費", "通信費", "その他"], 
                index=["食費", "日用品", "趣味・娯楽", "交通費", "通信費", "その他"].index(row["カテゴリー"]), 
                key="edit_cat"
            )
            new_amount = st.number_input("金額を変更", value=int(row["金額"]), min_value=0, step=10, key="edit_amount")
            
            col_u, col_d = st.columns(2)
            if col_u.button("更新"):
                df.at[edit_idx, "日付"] = pd.to_datetime(new_date)
                df.at[edit_idx, "カテゴリー"] = new_cat
                df.at[edit_idx, "金額"] = new_amount
                save_data(df)
                st.success("更新しました！")
                st.rerun()
            
            if col_d.button("この行を削除"):
                df = df.drop(edit_idx)
                save_data(df)
                st.warning("削除しました。")
                st.rerun()
        else:
            st.write("データがありません")

# --- メインエリア ---
if not df.empty:
    # データの加工
    df['年月'] = df['日付'].dt.strftime('%Y-%m')
    current_month = datetime.date.today().strftime('%Y-%m')
    
    monthly_total = df[df['年月'] == current_month]['金額'].sum()
    total_spent = df["金額"].sum()

    # サマリー表示
    st.subheader("📊 収支サマリー")
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.metric(f"今月 ({current_month}) の支出", f"{monthly_total:,} 円")
    with m_col2:
        st.metric("累計の総支出", f"{total_spent:,} 円")
    
    st.divider()

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 履歴")
        st.dataframe(df.sort_values("日付", ascending=False), width="stretch")

    with col2:
        st.subheader("🏷️ 種類別の合計")
        category_sum = df.groupby("カテゴリー")["金額"].sum().reset_index()
        
        # 表の表示
        st.table(category_sum.set_index("カテゴリー")["金額"].map("{:,}円".format))
        
        # 円グラフの作成（金額表示＋真ん中に合計）
        fig = px.pie(
            category_sum, 
            values='金額', 
            names='カテゴリー', 
            color='カテゴリー',
            hole=0.5
        )
        
        # 表示設定：パーセントではなく「ラベル＋金額」を表示
        fig.update_traces(
            textposition='inside', 
            textinfo='label+value',
            hovertemplate='%{label}<br>%{value:,}円'
        )
        
        # グラフの真ん中に合計金額を表示
        fig.add_annotation(
            text=f"累計合計<br><b>{total_spent:,}円</b>",
            showarrow=False,
            font_size=18
        )

        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        
        # 最新の書き方 width="stretch"
        st.plotly_chart(fig, width="stretch")

    st.divider()
    if st.button("全データを削除（リセット）"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.rerun()
else:
    st.info("まだデータがありません。サイドバーから入力してください。")