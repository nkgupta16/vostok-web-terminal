"""
╔══════════════════════════════════════════════════════════════════════╗
║   VOSTOK WEB TERMINAL  –  Quantitative MOEX Trading Dashboard      ║
║   Streamlit Cloud-Ready  •  24/7 Deployment  •  Electric Blue UI   ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import io
import os
import time
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Page Config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Vostok Web Terminal",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Vostok Web Terminal — MOEX Quantitative Dashboard"},
)

# ── Service Imports ──────────────────────────────────────────────────
from services.auth import get_invest_token, render_sidebar_auth
from services.market import (
    get_tickers,
    get_selected_tickers,
    save_tickers,
    scan_market,
    scan_squeeze,
    fetch_all_moex_shares,
    DEFAULT_TICKERS,
)
from services.portfolio import (
    fetch_portfolio,
    fetch_dividends,
    sandbox_init,
    sandbox_deposit,
    sandbox_buy,
)
from services.indicators import (
    get_signal_label,
    SIGNAL_SORT_ORDER,
    calculate_position_size,
)

# ═════════════════════════════════════════════════════════════════════
# LOGGING SYSTEM
# ═════════════════════════════════════════════════════════════════════
_LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(_LOGS_DIR, exist_ok=True)

if "app_logs" not in st.session_state:
    st.session_state["app_logs"] = []


def log(msg: str, level: str = "INFO"):
    """Append a timestamped log entry."""
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] [{level}] {msg}"
    st.session_state["app_logs"].append(entry)
    # Keep last 500 lines
    if len(st.session_state["app_logs"]) > 500:
        st.session_state["app_logs"] = st.session_state["app_logs"][-500:]


def get_log_text() -> str:
    return "\n".join(st.session_state["app_logs"])


# ═════════════════════════════════════════════════════════════════════
# COPY-TABLE HELPER
# ═════════════════════════════════════════════════════════════════════
def df_to_tsv(df: pd.DataFrame) -> str:
    """Convert DataFrame to tab-separated string for clipboard."""
    buf = io.StringIO()
    df.to_csv(buf, sep="\t", index=False)
    return buf.getvalue()


# ═════════════════════════════════════════════════════════════════════
# GLOBAL CSS — Electric Blue dark theme (compact header)
# ═════════════════════════════════════════════════════════════════════
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root {
    --accent: #00e5ff; --accent-dim: #007a8a;
    --bg-primary: #0a0e12; --bg-card: #111820; --bg-card-hover: #162030;
    --border: #1c2838; --text-primary: #e0e4ea; --text-secondary: #7a8a9e;
    --green: #00e676; --red: #ff5252; --amber: #ffab40;
}
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif !important; color: var(--text-primary);
}
/* Reduce Streamlit default top padding */
.stMainBlockContainer { padding-top: 1rem !important; }
header[data-testid="stHeader"] { display: none !important; }

/* Metric Cards */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, var(--bg-card) 0%, #0d1520 100%);
    border: 1px solid var(--border); border-radius: 12px; padding: 14px 18px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(0,229,255,0.10); }
[data-testid="stMetricLabel"] { color: var(--text-secondary) !important; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; font-weight: 600; color: var(--accent) !important; }
[data-testid="stMetricDelta"] > div { font-family: 'JetBrains Mono', monospace !important; }

/* Tabs */
[data-testid="stTabs"] > div > div > button {
    font-weight: 600; font-size: 0.85rem; letter-spacing: 0.02em;
    border-radius: 8px 8px 0 0; padding: 8px 16px; transition: background 0.15s ease;
}
[data-testid="stTabs"] > div > div > button[aria-selected="true"] { border-bottom: 3px solid var(--accent); color: var(--accent); }
[data-testid="stTabs"] > div > div > button:hover { background: var(--bg-card-hover); }

/* DataFrames */
[data-testid="stDataFrame"] table { font-family: 'JetBrains Mono', monospace !important; font-size: 0.82rem; }
[data-testid="stDataFrame"] th { background: var(--bg-card) !important; color: var(--accent) !important; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 2px solid var(--accent) !important; }
[data-testid="stDataFrame"] td { border-color: var(--border) !important; }

/* Sidebar */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0c1018 0%, #0a0e12 100%) !important; border-right: 1px solid var(--border); }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: var(--accent) !important; }

/* Buttons */
.stButton > button { border-radius: 8px; font-weight: 600; transition: all 0.15s ease; border: 1px solid var(--border); }
.stButton > button:hover { border-color: var(--accent); box-shadow: 0 0 12px rgba(0,229,255,0.15); }

/* Plotly */
.js-plotly-plot .plotly .modebar-group { background: var(--bg-card) !important; border-radius: 6px; }

/* Header line */
.header-glow { background: linear-gradient(90deg, transparent, rgba(0,229,255,0.15), transparent); height: 2px; margin-bottom: 8px; border-radius: 1px; }

/* Squeeze animation */
@keyframes pulse-glow { 0%{box-shadow:0 0 4px var(--green)} 50%{box-shadow:0 0 16px var(--green)} 100%{box-shadow:0 0 4px var(--green)} }
.breakout-pulse { animation: pulse-glow 1.2s infinite; border-radius: 6px; padding: 2px 10px; display: inline-block; font-weight: 700; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════
st.sidebar.markdown(
    '<div style="text-align:center; padding:6px 0 2px 0;">'
    '<span style="font-size:2rem;">🚀</span><br>'
    '<span style="font-size:1.2rem; font-weight:700; color:#00e5ff; letter-spacing:0.08em;">VOSTOK WEB</span><br>'
    '<span style="font-size:0.7rem; color:#7a8a9e; letter-spacing:0.12em;">QUANTITATIVE TERMINAL</span>'
    "</div>",
    unsafe_allow_html=True,
)

render_sidebar_auth()

# ── Auto-Scan (10s – 300s + custom) ──
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Auto-Scan")
auto_scan = st.sidebar.toggle("Enable Auto-Refresh", value=False, key="auto_scan")

scan_mode = st.sidebar.radio(
    "Interval Mode", ["Preset", "Custom"], horizontal=True, key="scan_mode", label_visibility="collapsed"
)
if scan_mode == "Preset":
    scan_interval = st.sidebar.select_slider(
        "Interval (sec)",
        options=[10, 15, 20, 30, 60, 120, 300],
        value=60,
        key="scan_interval",
        disabled=not auto_scan,
    )
else:
    scan_interval = st.sidebar.number_input(
        "Custom Interval (sec)",
        min_value=5,
        max_value=3600,
        value=45,
        step=5,
        key="scan_interval_custom",
        disabled=not auto_scan,
    )

# ── Ticker Manager ──
st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Ticker Universe")

all_tickers = get_tickers()
current_selected = get_selected_tickers()

# Quick select/deselect
tc1, tc2 = st.sidebar.columns(2)
if tc1.button("✅ All", key="sel_all", use_container_width=True):
    st.session_state["selected_tickers"] = list(all_tickers.keys())
    st.rerun()
if tc2.button("❌ None", key="sel_none", use_container_width=True):
    st.session_state["selected_tickers"] = []
    st.rerun()

# Multiselect for active tickers
selected = st.sidebar.multiselect(
    "Active Tickers",
    options=sorted(all_tickers.keys()),
    default=sorted([t for t in current_selected if t in all_tickers]),
    key="ticker_multiselect",
    label_visibility="collapsed",
)
st.session_state["selected_tickers"] = selected

st.sidebar.caption(f"{len(selected)}/{len(all_tickers)} tickers active")

# Add / Remove tickers
with st.sidebar.expander("➕ Add / Remove Tickers"):
    new_ticker = st.text_input("Ticker Symbol", key="new_ticker_input", placeholder="e.g. MGNT")
    new_uid = st.text_input("Instrument UID", key="new_uid_input", placeholder="UID from T-Bank")

    ac1, ac2 = st.columns(2)
    if ac1.button("➕ Add", key="add_ticker", use_container_width=True):
        t = new_ticker.strip().upper()
        u = new_uid.strip()
        if t and u:
            all_tickers[t] = u
            st.session_state["tickers"] = all_tickers
            if t not in st.session_state["selected_tickers"]:
                st.session_state["selected_tickers"].append(t)
            save_tickers(all_tickers)
            log(f"Added ticker {t} ({u})")
            st.success(f"Added {t}")
            st.rerun()
        else:
            st.warning("Enter both ticker and UID.")

    remove_ticker = st.selectbox("Remove Ticker", options=[""] + sorted(all_tickers.keys()), key="rm_ticker")
    if ac2.button("🗑️ Remove", key="rm_btn", use_container_width=True):
        if remove_ticker and remove_ticker in all_tickers:
            del all_tickers[remove_ticker]
            st.session_state["tickers"] = all_tickers
            if remove_ticker in st.session_state["selected_tickers"]:
                st.session_state["selected_tickers"].remove(remove_ticker)
            save_tickers(all_tickers)
            log(f"Removed ticker {remove_ticker}")
            st.success(f"Removed {remove_ticker}")
            st.rerun()

    if st.button("🔄 Reset to Defaults", key="reset_tickers"):
        from services.market import DEFAULT_TICKERS
        st.session_state["tickers"] = dict(DEFAULT_TICKERS)
        st.session_state["selected_tickers"] = list(DEFAULT_TICKERS.keys())
        save_tickers(dict(DEFAULT_TICKERS))
        log("Reset tickers to defaults")
        st.rerun()


# ═════════════════════════════════════════════════════════════════════
# HEADER (compact)
# ═════════════════════════════════════════════════════════════════════
st.markdown('<div class="header-glow"></div>', unsafe_allow_html=True)
hcol1, hcol2 = st.columns([5, 1])
with hcol1:
    st.markdown(
        "<h1 style='margin:0; font-size:1.4rem; letter-spacing:0.04em;'>"
        "🚀 VOSTOK WEB TERMINAL</h1>"
        "<p style='color:#7a8a9e; margin:0 0 4px 0; font-size:0.78rem;'>"
        "MOEX Quantitative Dashboard · Real-time Dip & Squeeze Scanner</p>",
        unsafe_allow_html=True,
    )
with hcol2:
    st.markdown(
        f"<p style='text-align:right; color:#7a8a9e; font-size:0.72rem; margin-top:8px;'>"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}</p>",
        unsafe_allow_html=True,
    )

# ═════════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════════
tab_dash, tab_squeeze, tab_port, tab_divs, tab_sandbox, tab_strat, tab_logs = st.tabs([
    "📈 Dashboard", "💥 Squeeze", "💼 Portfolio", "📅 Dividends",
    "🎮 Sandbox", "🧠 Strategy", "📜 Logs",
])

token = get_invest_token()
tickers = get_tickers()
selected_tickers = {t: tickers[t] for t in selected if t in tickers}
tickers_tuple = tuple(sorted(selected_tickers.items()))

log(f"Session start — {len(selected_tickers)} tickers selected, token={'set' if token else 'none'}")


# ═════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ═════════════════════════════════════════════════════════════════════
with tab_dash:
    if not token:
        st.warning("⚠️ Connect your T-Bank API token in the sidebar to begin scanning.")
        st.stop()

    if not selected_tickers:
        st.warning("⚠️ Select at least one ticker in the sidebar.")
        st.stop()

    with st.spinner(f"🔍 Scanning {len(selected_tickers)} tickers…"):
        data = scan_market(token, tickers_tuple)
        st.session_state["market_data"] = data

    if not data:
        st.error("No data returned. Check your token or network connection.")
        log("Dashboard scan returned empty", "ERROR")
    else:
        log(f"Dashboard scan complete — {len(data)} tickers")
        buy_count = sum(1 for d in data.values() if d["label"] == "BUY")
        watch_count = sum(1 for d in data.values() if d["label"] == "WATCH")
        avg_rsi = np.mean([d["rsi"] for d in data.values()])
        strongest = max(data.items(), key=lambda x: x[1]["confidence"])

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("🟢 BUY Signals", buy_count)
        mc2.metric("👁 WATCH Signals", watch_count)
        mc3.metric("📊 Avg RSI", f"{avg_rsi:.1f}")
        mc4.metric("🏆 Top Signal", f"{strongest[0]} ({strongest[1]['confidence']:.0f}%)")

        # Build DataFrame
        rows = []
        for ticker, d in data.items():
            rows.append({
                "Ticker": ticker,
                "Price (RUB)": round(d["price"], 2),
                "RSI": round(d["rsi"], 1),
                "vs BB (%)": round(d["price_to_bb"], 1),
                "Vol %": round(d["volume_ratio"], 0),
                "MACD Δ (%)": round(d["macd_change"], 1),
                "Confidence": round(d["confidence"], 1),
                "Signal": d["label"],
                "_sort": SIGNAL_SORT_ORDER.get(d["label"], 9),
            })

        df_display = pd.DataFrame(rows)
        df_display.sort_values(["_sort", "Confidence"], ascending=[True, False], inplace=True)
        df_display.drop(columns=["_sort"], inplace=True)
        df_display.reset_index(drop=True, inplace=True)

        st.dataframe(
            df_display,
            column_config={
                "Confidence": st.column_config.ProgressColumn(
                    "Confidence %", help="Weighted quantitative score (0-100)",
                    format="%.0f%%", min_value=0, max_value=100,
                ),
            },
            use_container_width=True, hide_index=True,
            height=min(600, 40 + 35 * len(df_display)),
        )

        # Copy button
        st.download_button(
            "📋 Copy Dashboard Data (TSV)", df_to_tsv(df_display),
            file_name=f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M')}.tsv",
            mime="text/tab-separated-values", key="copy_dash",
        )

        # Chart for selected ticker
        st.markdown("---")
        chart_ticker = st.selectbox("📊 Select Ticker for Chart", options=list(data.keys()), index=0, key="chart_ticker")

        if chart_ticker and chart_ticker in data:
            td = data[chart_ticker]
            chart_df = td["df"]

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=list(range(len(chart_df))),
                open=chart_df["open"], high=chart_df["high"],
                low=chart_df["low"], close=chart_df["close"],
                name="OHLC", increasing_line_color="#00e676", decreasing_line_color="#ff5252",
            ))
            fig.add_trace(go.Scatter(x=list(range(len(chart_df))), y=chart_df["BB_UPPER"], name="BB Upper", line=dict(color="#ff5252", width=1, dash="dot")))
            fig.add_trace(go.Scatter(x=list(range(len(chart_df))), y=chart_df["BB_LOWER"], name="BB Lower", line=dict(color="#00e5ff", width=1, dash="dot"), fill="tonexty", fillcolor="rgba(0,229,255,0.04)"))
            fig.update_layout(
                title=f"{chart_ticker} — Price + Bollinger Bands", template="plotly_dark",
                paper_bgcolor="#0a0e12", plot_bgcolor="#0d1520", height=380,
                xaxis_rangeslider_visible=False, margin=dict(l=40, r=20, t=40, b=30),
                font=dict(family="Inter, sans-serif", size=12, color="#e0e4ea"),
            )
            st.plotly_chart(fig, use_container_width=True)

            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=list(range(len(chart_df))), y=chart_df["RSI"], name="RSI", line=dict(color="#00e5ff", width=2)))
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="#ff5252", annotation_text="Oversold (30)")
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="#ff5252", annotation_text="Overbought (70)")
            fig_rsi.update_layout(
                title="RSI (14)", template="plotly_dark",
                paper_bgcolor="#0a0e12", plot_bgcolor="#0d1520", height=200,
                yaxis=dict(range=[0, 100]), margin=dict(l=40, r=20, t=40, b=30),
                font=dict(family="Inter, sans-serif", size=12, color="#e0e4ea"),
            )
            st.plotly_chart(fig_rsi, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════
# TAB 2 — SQUEEZE
# ═════════════════════════════════════════════════════════════════════
with tab_squeeze:
    if not token:
        st.warning("⚠️ Connect your T-Bank API token to enable Squeeze detection.")
    elif not selected_tickers:
        st.warning("⚠️ Select at least one ticker.")
    else:
        with st.spinner(f"🔍 Scanning {len(selected_tickers)} tickers for squeezes…"):
            sq_data = scan_squeeze(token, tickers_tuple)
            log(f"Squeeze scan complete — {len(sq_data)} tickers")

        if not sq_data:
            st.info("No squeeze data returned.")
        else:
            sorted_sq = sorted(sq_data.items(), key=lambda x: x[1]["metrics"]["score"])
            breakouts = [t for t, d in sorted_sq if d["metrics"]["is_breakout"]]
            if breakouts:
                for b in breakouts:
                    st.toast(f"🚀 BREAKOUT: **{b}**", icon="🚀")
                    log(f"BREAKOUT detected: {b}", "ALERT")

            rows_sq = []
            for ticker, d in sorted_sq:
                m = d["metrics"]
                if m["is_breakout"]:
                    status = "🚀 BREAKOUT"
                elif m["is_squeeze"]:
                    status = "🔥 SQUEEZE"
                else:
                    status = "—"

                rows_sq.append({
                    "Ticker": ticker,
                    "Price": round(d["price"], 2),
                    "BB Width %ile": round(m["score"], 1),
                    "OBV Trend": f"{m['obv_trend']:+,.0f}",
                    "ATR Ratio": round(m["atr_ratio"], 3),
                    "Days in Squeeze": m["days_in_squeeze"],
                    "Alert": status,
                })

            df_sq = pd.DataFrame(rows_sq)
            st.dataframe(df_sq, use_container_width=True, hide_index=True, height=min(600, 40 + 35 * len(df_sq)))

            st.download_button(
                "📋 Copy Squeeze Data (TSV)", df_to_tsv(df_sq),
                file_name=f"squeeze_{datetime.now().strftime('%Y%m%d_%H%M')}.tsv",
                mime="text/tab-separated-values", key="copy_squeeze",
            )

# ═════════════════════════════════════════════════════════════════════
# TAB 3 — PORTFOLIO
# ═════════════════════════════════════════════════════════════════════
with tab_port:
    if not token:
        st.warning("⚠️ Connect your T-Bank API token to view portfolio.")
    else:
        with st.spinner("📂 Loading portfolio…"):
            pf = fetch_portfolio(token)
            log(f"Portfolio loaded — {len(pf.get('positions', []))} positions")

        if pf.get("error"):
            st.error(pf["error"])
        else:
            pc1, pc2, pc3, pc4 = st.columns(4)
            pc1.metric("Total Value", f"₽ {pf['total_value']:,.0f}")
            pc2.metric("Total P&L", f"₽ {pf['total_pnl']:,.0f}", delta=f"{pf['total_pnl']:+,.0f}")
            pc3.metric("Day P&L", f"₽ {pf['day_pnl']:,.0f}", delta=f"{pf['day_pnl']:+,.0f}")
            pc4.metric("Cash", f"₽ {pf['cash']:,.0f}")

            st.markdown("#### 📊 Current Positions")
            if pf["positions"]:
                df_pos = pd.DataFrame(pf["positions"])
                df_pos.columns = ["Ticker", "Qty", "Avg Price", "Last Price", "Value", "P&L", "P&L %", "Day P&L", "Day P&L %"]

                def _style_pos(df):
                    styles = pd.DataFrame("", index=df.index, columns=df.columns)
                    for idx, row in df.iterrows():
                        c = "color: #00e676" if row["P&L"] >= 0 else "color: #ff5252"
                        styles.loc[idx, "P&L"] = c + "; font-weight: 600"
                        styles.loc[idx, "P&L %"] = c
                        dc = "color: #00e676" if row["Day P&L"] >= 0 else "color: #ff5252"
                        styles.loc[idx, "Day P&L"] = dc
                        styles.loc[idx, "Day P&L %"] = dc
                    return styles

                st.dataframe(
                    df_pos.style.apply(_style_pos, axis=None).format({
                        "Avg Price": "₽ {:.2f}", "Last Price": "₽ {:.2f}", "Value": "₽ {:,.0f}",
                        "P&L": "₽ {:+,.0f}", "P&L %": "{:+.2f}%",
                        "Day P&L": "₽ {:+,.0f}", "Day P&L %": "{:+.2f}%", "Qty": "{:.0f}",
                    }),
                    use_container_width=True, hide_index=True,
                )
                st.download_button("📋 Copy Positions (TSV)", df_to_tsv(df_pos), file_name="positions.tsv", mime="text/tab-separated-values", key="copy_pos")
            else:
                st.info("No open positions.")

            st.markdown("#### 📜 Recent Operations")
            if pf["operations"]:
                df_ops = pd.DataFrame(pf["operations"])
                df_ops.columns = ["Date", "Ticker", "Type", "Qty", "Price", "Amount"]
                st.dataframe(
                    df_ops.style.format({"Price": "₽ {:.2f}", "Amount": "₽ {:+,.0f}", "Qty": "{:.0f}"}),
                    use_container_width=True, hide_index=True,
                )
                st.download_button("📋 Copy Operations (TSV)", df_to_tsv(df_ops), file_name="operations.tsv", mime="text/tab-separated-values", key="copy_ops")
            else:
                st.info("No recent operations.")


# ═════════════════════════════════════════════════════════════════════
# TAB 4 — DIVIDENDS
# ═════════════════════════════════════════════════════════════════════
with tab_divs:
    if not token:
        st.warning("⚠️ Connect your T-Bank API token to view dividends.")
    else:
        pf_for_divs = fetch_portfolio(token)
        portfolio_map = {p["ticker"]: p for p in pf_for_divs.get("positions", [])}

        with st.spinner("📅 Fetching dividend calendar…"):
            divs = fetch_dividends(token, tickers_tuple, portfolio_map)
            log(f"Dividend calendar — {len(divs)} upcoming events")

        if not divs:
            st.info("No upcoming dividends in the next 6 months.")
        else:
            rows_div = []
            for d in divs:
                price = None
                mkt = st.session_state.get("market_data", {})
                if mkt and d["ticker"] in mkt:
                    price = mkt[d["ticker"]]["price"]
                yld = (d["div_per_share"] / price * 100) if price and price > 0 else None

                rows_div.append({
                    "Ticker": d["ticker"],
                    "Shares Owned": int(d["shares_owned"]),
                    "Div/Share (₽)": round(d["div_per_share"], 2),
                    "Expected Payout (₽)": round(d["expected_payout"], 2),
                    "Yield est. %": round(yld, 2) if yld else None,
                    "Date": d["date"].strftime("%Y-%m-%d"),
                    "Days to Cutoff": d["days_left"],
                })

            df_div = pd.DataFrame(rows_div)

            def _style_divs(df):
                styles = pd.DataFrame("", index=df.index, columns=df.columns)
                for idx, row in df.iterrows():
                    days = row["Days to Cutoff"]
                    if days <= 14:
                        styles.loc[idx, "Days to Cutoff"] = "color: #ff5252; font-weight: 700"
                    elif days <= 60:
                        styles.loc[idx, "Days to Cutoff"] = "color: #ffab40"
                    else:
                        styles.loc[idx, "Days to Cutoff"] = "color: #00e676"
                    payout = row["Expected Payout (₽)"]
                    if payout and payout > 0:
                        styles.loc[idx, "Expected Payout (₽)"] = "color: #00e676; font-weight: 600"
                return styles

            st.dataframe(
                df_div.style.apply(_style_divs, axis=None).format({
                    "Div/Share (₽)": "₽ {:.2f}", "Expected Payout (₽)": "₽ {:,.2f}", "Yield est. %": "{:.2f}%",
                }),
                use_container_width=True, hide_index=True,
            )
            st.download_button("📋 Copy Dividends (TSV)", df_to_tsv(df_div), file_name="dividends.tsv", mime="text/tab-separated-values", key="copy_divs")


# ═════════════════════════════════════════════════════════════════════
# TAB 5 — SANDBOX
# ═════════════════════════════════════════════════════════════════════
with tab_sandbox:
    if not token:
        st.warning("⚠️ Connect your T-Bank API token for Sandbox mode.")
    else:
        st.markdown(
            '<div style="background:linear-gradient(135deg,#111820,#162030); border:1px solid #1c2838;'
            'border-radius:12px; padding:16px; margin-bottom:12px;">'
            '<h3 style="color:#00e5ff; margin:0;">🎮 Virtual Sandbox</h3>'
            '<p style="color:#7a8a9e; margin:4px 0 0 0; font-size:0.85rem;">Paper trading with T-Bank Sandbox API. No real money at risk.</p>'
            "</div>",
            unsafe_allow_html=True,
        )

        sc1, sc2, sc3 = st.columns(3)

        with sc1:
            if st.button("🏗️ Initialize Sandbox", type="primary", key="sb_init"):
                try:
                    acc_id = sandbox_init(token)
                    st.session_state["sandbox_account_id"] = acc_id
                    st.success(f"Created: `{acc_id}`")
                    log(f"Sandbox created: {acc_id}")
                except Exception as e:
                    st.error(f"Error: {e}")
                    log(f"Sandbox init error: {e}", "ERROR")

        with sc2:
            if st.button("💰 Deposit 100K RUB", key="sb_deposit"):
                acc_id = st.session_state.get("sandbox_account_id")
                if not acc_id:
                    st.warning("Initialize sandbox first!")
                else:
                    try:
                        sandbox_deposit(token, acc_id)
                        st.success("Deposited ₽100,000")
                        log(f"Sandbox deposit: 100K RUB → {acc_id}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                        log(f"Sandbox deposit error: {e}", "ERROR")

        with sc3:
            sandbox_status = st.session_state.get("sandbox_account_id")
            if sandbox_status:
                st.markdown(f"**Account:** `{sandbox_status}` — 🟢 Active")
            else:
                st.markdown("**Status:** 🔴 Inactive")

        # Paper-trade BUY signals
        st.markdown("#### 📋 Paper Trade BUY Signals")
        mkt_data = st.session_state.get("market_data", {})
        if not mkt_data:
            st.info("Run Dashboard scan first to see BUY signals here.")
        else:
            buy_signals = {t: d for t, d in mkt_data.items() if d["label"] == "BUY"}
            if not buy_signals:
                st.info("No active BUY signals to paper-trade.")
            else:
                for ticker, d in buy_signals.items():
                    with st.expander(f"🟢 {ticker} — ₽{d['price']:.2f}  (Confidence: {d['confidence']:.0f}%)"):
                        pos = calculate_position_size(50_000, 0.01, 0.02, d["price"], d["lot_size"])
                        st.markdown(f"**Lots:** {pos['lots']} · **Shares:** {pos['shares']} · **Value:** ₽{pos['position_value']:,.0f}")
                        if st.button(f"🚀 Paper BUY {ticker}", key=f"sb_buy_{ticker}", disabled=not sandbox_status):
                            try:
                                uid = selected_tickers.get(ticker)
                                order_id = sandbox_buy(token, sandbox_status, uid, pos["lots"])
                                st.success(f"Order placed! ID: `{order_id}`")
                                log(f"Sandbox BUY: {ticker} × {pos['lots']} lots — order {order_id}")
                                if "sandbox_orders" not in st.session_state:
                                    st.session_state["sandbox_orders"] = []
                                st.session_state["sandbox_orders"].append({
                                    "ticker": ticker, "lots": pos["lots"], "price": d["price"],
                                    "order_id": order_id, "time": datetime.now().strftime("%H:%M:%S"),
                                })
                            except Exception as e:
                                st.error(f"Order failed: {e}")
                                log(f"Sandbox BUY error ({ticker}): {e}", "ERROR")

        if st.session_state.get("sandbox_orders"):
            st.markdown("#### 📜 Order History")
            df_sb = pd.DataFrame(st.session_state["sandbox_orders"])
            st.dataframe(df_sb, use_container_width=True, hide_index=True)
            st.download_button("📋 Copy Orders (TSV)", df_to_tsv(df_sb), file_name="sandbox_orders.tsv", mime="text/tab-separated-values", key="copy_sb")


# ═════════════════════════════════════════════════════════════════════
# TAB 6 — STRATEGY
# ═════════════════════════════════════════════════════════════════════
with tab_strat:
    st.markdown(
        '<div style="background:linear-gradient(135deg,#111820,#162030); border:1px solid #1c2838;'
        'border-radius:12px; padding:16px; margin-bottom:12px;">'
        '<h3 style="color:#00e5ff; margin:0;">🧠 Strategy Backtest Analytics</h3>'
        '<p style="color:#7a8a9e; margin:4px 0 0 0; font-size:0.85rem;">Simulated equity curves and drawdown analysis.</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    s1, s2 = st.columns([2, 1])
    with s1:
        strategy = st.selectbox("Select Strategy", ["Buy The Dip", "Volatility Squeeze"], key="strat_sel")
    with s2:
        run_bt = st.button("▶ Run Backtest", type="primary", key="run_bt")

    if run_bt or st.session_state.get("backtest_ran"):
        st.session_state["backtest_ran"] = True
        np.random.seed(42 if strategy == "Buy The Dip" else 7)
        days = 252
        if strategy == "Buy The Dip":
            returns = np.random.normal(0.001, 0.015, days)
        else:
            returns = np.random.normal(-0.0005, 0.005, days)
            for _ in range(5):
                returns[np.random.randint(0, days)] += 0.05

        equity = 100_000 * np.cumprod(1 + returns)
        peak = np.maximum.accumulate(equity)
        drawdown = ((equity - peak) / peak) * 100

        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(y=equity, name="Equity", line=dict(color="#00e5ff", width=2.5), fill="tozeroy", fillcolor="rgba(0,229,255,0.06)"))
        fig_eq.update_layout(title=f"{strategy} — Equity Curve", template="plotly_dark", paper_bgcolor="#0a0e12", plot_bgcolor="#0d1520", height=320, margin=dict(l=40, r=20, t=50, b=30), font=dict(family="Inter", size=12, color="#e0e4ea"), yaxis_title="₽")
        st.plotly_chart(fig_eq, use_container_width=True)

        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(y=drawdown, name="Drawdown", line=dict(color="#ff5252", width=2), fill="tozeroy", fillcolor="rgba(255,82,82,0.12)"))
        fig_dd.update_layout(title="Drawdown (%)", template="plotly_dark", paper_bgcolor="#0a0e12", plot_bgcolor="#0d1520", height=200, margin=dict(l=40, r=20, t=40, b=30), font=dict(family="Inter", size=12, color="#e0e4ea"), yaxis_title="%")
        st.plotly_chart(fig_dd, use_container_width=True)

        total_ret = ((equity[-1] / 100_000) - 1) * 100
        max_dd = np.min(drawdown)
        sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Total Return", f"{total_ret:+.2f}%")
        s2.metric("Max Drawdown", f"{max_dd:.2f}%")
        s3.metric("Sharpe Ratio", f"{sharpe:.2f}")
        s4.metric("Final Value", f"₽ {equity[-1]:,.0f}")
        log(f"Backtest: {strategy} — Ret={total_ret:.2f}% DD={max_dd:.2f}%")


# ═════════════════════════════════════════════════════════════════════
# TAB 7 — LOGS
# ═════════════════════════════════════════════════════════════════════
with tab_logs:
    st.markdown(
        '<div style="background:linear-gradient(135deg,#111820,#162030); border:1px solid #1c2838;'
        'border-radius:12px; padding:16px; margin-bottom:12px;">'
        '<h3 style="color:#00e5ff; margin:0;">📜 Application Logs</h3>'
        '<p style="color:#7a8a9e; margin:4px 0 0 0; font-size:0.85rem;">Real-time diagnostic output. Copy or save locally.</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    log_text = get_log_text()

    lc1, lc2, lc3 = st.columns(3)
    with lc1:
        st.download_button(
            "📋 Copy Logs", log_text,
            file_name=f"vostok_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            mime="text/plain", key="copy_logs",
        )
    with lc2:
        if st.button("💾 Save to Logs Folder", key="save_logs"):
            fname = f"vostok_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            fpath = os.path.join(_LOGS_DIR, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(log_text)
            st.success(f"Saved: `logs/{fname}`")
            log(f"Logs saved to {fpath}")
    with lc3:
        if st.button("🗑️ Clear Logs", key="clear_logs"):
            st.session_state["app_logs"] = []
            st.rerun()

    # Display log content
    st.code(log_text if log_text else "(no logs yet)", language="log")


# ═════════════════════════════════════════════════════════════════════
# AUTO-SCAN LOOP
# ═════════════════════════════════════════════════════════════════════
if auto_scan and token and selected_tickers:
    placeholder = st.empty()
    placeholder.info(f"⚡ Auto-refresh active — next scan in {scan_interval}s")
    log(f"Auto-scan sleeping {scan_interval}s")
    time.sleep(scan_interval)
    st.cache_data.clear()
    st.rerun()
