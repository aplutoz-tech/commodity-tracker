"""
📊 全球大宗商品價格追蹤儀表板
================================
資料來源：Yahoo Finance（免費）
使用技術：Streamlit + yfinance + Plotly
"""

import time
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(
    page_title="大宗商品追蹤儀表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

COMMODITIES = {
    "⚡ 能源": [
        {"name": "WTI 原油",   "ticker": "CL=F",  "unit": "USD / 桶"},
        {"name": "布倫特原油", "ticker": "BZ=F",  "unit": "USD / 桶"},
        {"name": "天然氣",     "ticker": "NG=F",  "unit": "USD / MMBtu"},
    ],
    "🥇 金屬": [
        {"name": "黃金",  "ticker": "GC=F",  "unit": "USD / 盎司"},
        {"name": "白銀",  "ticker": "SI=F",  "unit": "USD / 盎司"},
        {"name": "銅",    "ticker": "HG=F",  "unit": "USD / 磅"},
        {"name": "鋁",    "ticker": "ALI=F", "unit": "USD / 磅"},
        {"name": "鉑金",  "ticker": "PL=F",  "unit": "USD / 盎司"},
    ],
}

TIME_PERIODS = {
    "1 週":   "7d",
    "1 個月": "1mo",
    "3 個月": "3mo",
    "6 個月": "6mo",
    "1 年":   "1y",
    "2 年":   "2y",
}

@st.cache_data(ttl=300)
def get_current_price(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        current = info.last_price
        prev    = info.previous_close
        if current and prev and prev > 0:
            change = current - prev
            pct    = (change / prev) * 100
            return {"price": current, "change": change, "pct": pct, "ok": True}
    except Exception:
        pass
    return {"price": None, "change": None, "pct": None, "ok": False}


@st.cache_data(ttl=300)
def get_history(ticker: str, period: str) -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        return df
    except Exception:
        return pd.DataFrame()


def main():
    col_title, col_time = st.columns([3, 1])
    with col_title:
        st.title("📊 全球大宗商品追蹤儀表板")
    with col_time:
        st.markdown(
            f"<p style='text-align:right; color:#888; margin-top:1.5rem;'>"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>",
            unsafe_allow_html=True,
        )
    st.caption("資料來源：Yahoo Finance（免費）｜期貨合約報價，僅供參考")
    st.divider()

    with st.sidebar:
        st.header("⚙️ 設定")
        selected_period = st.selectbox(
            "📅 歷史走勢時間範圍",
            options=list(TIME_PERIODS.keys()),
            index=1,
        )
        selected_categories = st.multiselect(
            "🏷️ 顯示類別",
            options=list(COMMODITIES.keys()),
            default=list(COMMODITIES.keys()),
        )
        show_raw = st.checkbox("📋 顯示原始數據表", value=False)
        auto_refresh = st.toggle("🔄 自動更新（每 5 分鐘）", value=False)
        if st.button("🔃 立即重新整理", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.info(
            "**💡 使用說明**\n\n"
            "- 資料快取 **5 分鐘**更新一次\n"
            "- 走勢圖使用**相對漲跌幅**便於比較\n"
            "- 點選圖例可隱藏/顯示個別商品"
        )

    st.subheader("💹 即時報價")
    for category, items in COMMODITIES.items():
        if category not in selected_categories:
            continue
        st.markdown(f"### {category}")
        cols = st.columns(len(items))
        for col, item in zip(cols, items):
            with col:
                data = get_current_price(item["ticker"])
                if data["ok"]:
                    arrow = "▲" if data["change"] >= 0 else "▼"
                    delta_str = f"{arrow} {abs(data['change']):.2f}  ({data['pct']:+.2f}%)"
                    st.metric(
                        label=item["name"],
                        value=f"$ {data['price']:,.2f}",
                        delta=delta_str,
                    )
                else:
                    st.metric(label=item["name"], value="—")
                    st.caption("⚠️ 無法取得")
                st.caption(f"📌 {item['unit']}")

    st.divider()

    st.subheader("📈 歷史走勢比較")
    st.caption("以選定期間第一天收盤價為基準（= 0%），顯示相對漲跌幅")

    all_items = [
        item
        for cat, items in COMMODITIES.items()
        if cat in selected_categories
        for item in items
    ]
    if not all_items:
        st.warning("請在左側選擇至少一個類別。")
        return

    item_names = [item["name"] for item in all_items]
    selected_names = st.multiselect(
        "選擇要比較的商品（可多選）",
        options=item_names,
        default=item_names[:4],
    )
    if not selected_names:
        st.info("請至少選擇一個商品。")
        return

    period_code = TIME_PERIODS[selected_period]
    fig = go.Figure()
    raw_data = {}

    with st.spinner("載入歷史資料中…"):
        for item in all_items:
            if item["name"] not in selected_names:
                continue
            df = get_history(item["ticker"], period_code)
            if df.empty:
                st.warning(f"⚠️ 無法取得「{item['name']}」的歷史資料")
                continue
            close = df["Close"].squeeze()
            if len(close) < 2:
                continue
            normalized = (close / close.iloc[0] - 1) * 100
            raw_data[item["name"]] = close.rename(item["name"])
            fig.add_trace(go.Scatter(
                x=df.index,
                y=normalized,
                mode="lines",
                name=item["name"],
                line=dict(width=2),
                hovertemplate=(
                    f"<b>{item['name']}</b><br>"
                    "日期：%{x|%Y-%m-%d}<br>"
                    "相對漲跌幅：%{y:.2f}%<br>"
                    "<extra></extra>"
                ),
            ))

    fig.update_layout(
        xaxis_title="日期",
        yaxis_title="相對漲跌幅（%）",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500,
        yaxis=dict(ticksuffix="%"),
    )
    fig.add_hline(y=0, line_dash="dot", line_color="#666", opacity=0.7)
    st.plotly_chart(fig, use_container_width=True)

    if show_raw and raw_data:
        st.divider()
        st.subheader("📋 原始收盤價")
        combined = pd.concat(raw_data.values(), axis=1)
        combined.index = combined.index.strftime("%Y-%m-%d")
        combined = combined.sort_index(ascending=False)
        st.dataframe(combined.style.format("${:,.2f}"), use_container_width=True, height=300)
        csv = combined.to_csv(encoding="utf-8-sig")
        st.download_button(
            label="⬇️ 下載 CSV",
            data=csv,
            file_name=f"commodity_prices_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

    if auto_refresh:
        time.sleep(300)
        st.cache_data.clear()
        st.rerun()


if __name__ == "__main__":
    main()
