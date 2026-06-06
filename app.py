import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yaml
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader

st.set_page_config(
    page_title="超市銷售儀表板",
    page_icon="🏪",
    layout="wide",
)

# 載入帳號設定：本機用 config.yaml，雲端用 Streamlit Secrets
import os
if os.path.exists("config.yaml"):
    with open("config.yaml") as f:
        config = yaml.load(f, Loader=SafeLoader)
else:
    config = yaml.safe_load(st.secrets["config_yaml"])

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

authenticator.login()

if st.session_state["authentication_status"] is False:
    st.error("帳號或密碼錯誤，請重試")
    st.stop()

if st.session_state["authentication_status"] is None:
    st.warning("請輸入帳號與密碼")
    st.stop()

# ── 登入成功，以下為儀表板 ────────────────────────────────────────────

@st.cache_data
def load_data():
    df = pd.read_csv("supermarket_sales.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    return df

df = load_data()

# 側邊欄：篩選器 + 登出
with st.sidebar:
    st.markdown(f"**登入身份：** {st.session_state['name']}")
    authenticator.logout("登出", "sidebar")
    st.divider()

    branches = ["全部"] + sorted(df["Branch"].unique().tolist())
    selected_branch = st.selectbox("選擇分店", branches)

    product_lines = ["全部"] + sorted(df["Product line"].unique().tolist())
    selected_product = st.selectbox("選擇商品類別", product_lines)

    date_min = df["Date"].min().date()
    date_max = df["Date"].max().date()
    date_range = st.date_input("日期範圍", value=(date_min, date_max), min_value=date_min, max_value=date_max)

# 套用篩選
filtered = df.copy()
if selected_branch != "全部":
    filtered = filtered[filtered["Branch"] == selected_branch]
if selected_product != "全部":
    filtered = filtered[filtered["Product line"] == selected_product]
if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["Date"].dt.date >= start) & (filtered["Date"].dt.date <= end)]

# ── 頁面標題
st.title("🏪 超市銷售儀表板")
st.caption(f"資料範圍：{filtered['Date'].min().strftime('%Y/%m/%d')} ～ {filtered['Date'].max().strftime('%Y/%m/%d')}　共 {len(filtered):,} 筆交易")

# ── KPI 卡片
k1, k2, k3, k4 = st.columns(4)
k1.metric("總收入", f"${filtered['Total'].sum():,.0f}")
k2.metric("總毛利", f"${filtered['gross income'].sum():,.0f}")
k3.metric("平均評分", f"{filtered['Rating'].mean():.2f} / 10")
k4.metric("交易筆數", f"{len(filtered):,}")

st.divider()

# ── 第一行圖表
col1, col2 = st.columns(2)

with col1:
    branch_sales = filtered.groupby("Branch")["Total"].sum().reset_index()
    branch_sales.columns = ["分店", "總銷售額"]
    fig = px.bar(branch_sales, x="分店", y="總銷售額", title="各分店銷售額",
                 color="分店", text_auto=".2s", color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    product_sales = filtered.groupby("Product line")["Total"].sum().reset_index()
    product_sales.columns = ["商品類別", "銷售額"]
    fig = px.pie(product_sales, names="商品類別", values="銷售額", title="商品類別銷售占比",
                 hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig, use_container_width=True)

# ── 第二行圖表
col3, col4 = st.columns(2)

with col3:
    daily = filtered.groupby("Date")["Total"].sum().reset_index()
    daily.columns = ["日期", "每日銷售額"]
    fig = px.line(daily, x="日期", y="每日銷售額", title="每日銷售趨勢",
                  markers=True, color_discrete_sequence=["#636EFA"])
    st.plotly_chart(fig, use_container_width=True)

with col4:
    payment_counts = filtered["Payment"].value_counts().reset_index()
    payment_counts.columns = ["付款方式", "筆數"]
    fig = px.bar(payment_counts, x="筆數", y="付款方式", title="付款方式分布",
                 orientation="h", color="付款方式", text_auto=True,
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ── 第三行圖表
col5, col6 = st.columns(2)

with col5:
    fig = px.histogram(filtered, x="Rating", nbins=10, title="顧客評分分布",
                       color_discrete_sequence=["#EF553B"])
    fig.update_layout(bargap=0.1)
    st.plotly_chart(fig, use_container_width=True)

with col6:
    gender_sales = filtered.groupby(["Gender", "Product line"])["Total"].sum().reset_index()
    gender_sales.columns = ["性別", "商品類別", "銷售額"]
    fig = px.bar(gender_sales, x="商品類別", y="銷售額", color="性別",
                 title="各商品類別性別消費比較", barmode="group",
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_xaxes(tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

# ── 明細資料表
with st.expander("查看原始資料"):
    st.dataframe(
        filtered[["Invoice ID", "Branch", "City", "Product line", "Total", "Payment", "Date", "Rating"]],
        use_container_width=True,
    )
