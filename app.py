from __future__ import annotations

import truststore

truststore.inject_into_ssl()

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src.backtest import run_backtest
from src.binance_client import BinanceDataError, fetch_closed_klines, fetch_live_price
from src.indicators import add_indicators
from src.market_context import MarketContext, context_conflicts, fetch_market_context
from src.news import NewsDataError, NewsSummary, fetch_crypto_news
from src.risk import build_trade_plan
from src.signals import add_signal_scores, latest_signal


st.set_page_config(
    page_title="BTC & ETH Hourly Trading Assistant",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(ttl=55, show_spinner=False)
def load_market(symbol: str, product: str, limit: int = 1000) -> pd.DataFrame:
    return fetch_closed_klines(symbol=symbol, interval="1h", limit=limit, product=product)


@st.cache_data(ttl=300, show_spinner=False)
def load_news() -> NewsSummary:
    return fetch_crypto_news(max_records=25)


@st.cache_data(ttl=300, show_spinner=False)
def load_context(symbol: str, product: str) -> MarketContext:
    return fetch_market_context(symbol=symbol, product=product)


def price_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    view = df.tail(180)
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=view.index,
            open=view["open"],
            high=view["high"],
            low=view["low"],
            close=view["close"],
            name="Price",
        )
    )
    fig.add_trace(go.Scatter(x=view.index, y=view["ema20"], name="EMA 20", line=dict(width=1.5)))
    fig.add_trace(go.Scatter(x=view.index, y=view["ema50"], name="EMA 50", line=dict(width=1.5)))
    fig.update_layout(
        title=f"{symbol} — closed 1-hour candles",
        xaxis_rangeslider_visible=False,
        height=520,
        margin=dict(l=10, r=10, t=55, b=10),
        legend=dict(orientation="h"),
    )
    return fig


def fmt_price(value: float) -> str:
    return f"${value:,.2f}"


def fmt_large(value: float) -> str:
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    return f"${value:,.0f}"


st.title("BTC & ETH Hourly Trading Assistant")
st.caption("Continuous monitoring • manual orders • Spot, Isolated Margin and USDⓈ-M Futures")
st.warning(
    "This is a decision-support and educational tool—not a promise of profit. "
    "Crypto can fall sharply. Verify every order in Binance and never risk money you cannot afford to lose."
)

with st.sidebar:
    st.header("Account guardrails")
    account_size = st.number_input("Capital (USDT, hard maximum $100)", min_value=10.0, max_value=100.0, value=100.0, step=10.0)
    mode = st.selectbox("Trading mode", ["Spot", "Isolated Margin", "USDⓈ-M Futures"])
    allow_short = mode != "Spot"
    product = "futures" if mode == "USDⓈ-M Futures" else "spot"
    leverage = 1 if mode == "Spot" else st.slider("Leverage", min_value=2, max_value=5, value=2, step=1)
    risk_pct = st.slider("Maximum risk per trade", 0.25, 1.00, 0.50, 0.25)
    max_allocation_pct = st.slider("Maximum capital/collateral allocation", 10, 30, 25, 5)
    fee_pct = st.number_input("Estimated fee per side (%)", 0.0, 1.0, 0.10, 0.01)
    slippage_pct = st.number_input("Estimated slippage per side (%)", 0.0, 1.0, 0.05, 0.01)
    st.info(
        f"Current risk cap: **${account_size * risk_pct / 100:,.2f}** per trade. "
        f"Daily stop: **${account_size * 0.02:,.2f}**. Capital ceiling: **$100**."
    )
    if leverage > 1:
        st.warning(
            f"At {leverage}×, the selected {max_allocation_pct}% collateral cap can create up to "
            f"${account_size * max_allocation_pct / 100 * leverage:,.2f} of market exposure."
        )
    monitor_on = st.toggle("Continuous monitoring", value=True)
    refresh_seconds = st.select_slider("Refresh interval", options=[30, 60, 120, 300], value=60, format_func=lambda x: f"{x} seconds")
    refresh = st.button("Refresh now", type="primary", use_container_width=True)
    if refresh:
        st.cache_data.clear()

if monitor_on:
    refresh_count = st_autorefresh(interval=refresh_seconds * 1000, key="continuous_market_monitor")
else:
    refresh_count = 0

status_cols = st.columns([2, 2, 3])
status_cols[0].success("● MONITORING" if monitor_on else "○ PAUSED")
status_cols[1].metric("Automatic refresh", f"Every {refresh_seconds}s" if monitor_on else "Off")
status_cols[2].caption(f"Last application check: {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC")

if mode != "Spot":
    st.error(
        f"HIGH-RISK MODE: {mode} at {leverage}×. Short positions can lose when price rises, and leveraged positions can be liquidated. "
        "This app provides manual calculations only and its simplified danger price is not Binance's official liquidation price."
    )

try:
    news_summary = load_news()
except NewsDataError:
    news_summary = None

tabs = st.tabs(["Hourly signals", "News & market trends", "Strategy evidence", "Paper-trade journal", "How to use"])

market_frames: dict[str, pd.DataFrame] = {}
market_contexts: dict[str, MarketContext] = {}

with tabs[0]:
    cols = st.columns(2)
    for col, symbol in zip(cols, ["BTCUSDT", "ETHUSDT"]):
        with col:
            try:
                raw = load_market(symbol, product)
                data = add_signal_scores(add_indicators(raw))
                market_frames[symbol] = data
                signal = latest_signal(data, allow_short=allow_short)
                plan = None
                if signal.direction in {"LONG", "SHORT"}:
                    plan = build_trade_plan(
                        signal,
                        account_size=account_size,
                        risk_pct=risk_pct,
                        max_allocation_pct=max_allocation_pct,
                        leverage=leverage,
                    )
            except BinanceDataError as exc:
                st.error(f"{symbol}: {exc}")
                continue
            except Exception as exc:
                st.error(f"{symbol}: calculation failed safely ({exc}). No signal was produced.")
                continue

            try:
                live_price = fetch_live_price(symbol, product=product)
                live_price_verified = True
            except BinanceDataError:
                live_price = signal.close
                live_price_verified = False

            try:
                market_contexts[symbol] = load_context(symbol, product)
            except BinanceDataError:
                pass

            st.subheader(symbol.replace("USDT", "/USDT"))
            p1, p2 = st.columns(2)
            p1.metric("Live price" if live_price_verified else "Live price unavailable", fmt_price(live_price))
            p2.metric("Last closed price", fmt_price(signal.close), signal.one_hour_change_label)
            if not live_price_verified:
                st.warning("Live ticker verification failed. The displayed fallback is the last closed price; do not use it to place an order.")
            st.markdown(f"### {signal.decision}")
            st.caption(f"Candle closed: {signal.timestamp:%Y-%m-%d %H:%M} UTC • score {signal.score:+d}/4")

            if plan is not None:
                if not live_price_verified:
                    st.warning("SETUP UNVERIFIED — wait until the live ticker reconnects.")
                elif plan.min_valid_entry <= live_price <= plan.max_valid_entry:
                    st.success("SETUP CURRENTLY VALID — live price remains within the permitted entry range. Manual confirmation is still required.")
                elif (plan.direction == "LONG" and live_price <= plan.stop) or (plan.direction == "SHORT" and live_price >= plan.stop):
                    st.error("SETUP INVALIDATED — live price has crossed the planned stop level. Do not enter.")
                else:
                    st.warning("SETUP OUTSIDE ENTRY BAND — do not chase the move. Wait for a new closed-candle signal.")
            elif signal.decision == "EXIT / AVOID":
                st.error("Conditions are weak. Do not open a new long position from this signal.")
            else:
                st.info("No qualified new entry. Waiting is a valid trading decision.")

            context = market_contexts.get(symbol)
            if signal.direction in {"LONG", "SHORT"} and context is not None:
                if context_conflicts(signal.direction, context):
                    st.warning(
                        f"TREND CONFLICT — the setup is {signal.direction}, but the combined 1h/4h/1d context is {context.overall_trend}."
                    )
                else:
                    st.caption(f"Multi-timeframe context: {context.overall_trend}; no direct higher-timeframe conflict detected.")
            if signal.direction in {"LONG", "SHORT"} and news_summary is not None and news_summary.risk_gate:
                st.warning("NEWS CAUTION — recent high-impact negative headlines require manual verification before acting on this setup.")

            if plan is not None:
                m1, m2 = st.columns(2)
                m1.metric("Entry reference", fmt_price(plan.entry))
                m2.metric("Valid entry band", f"{fmt_price(plan.min_valid_entry)}–{fmt_price(plan.max_valid_entry)}")
                m1.metric("Stop-loss", fmt_price(plan.stop))
                m2.metric("Target", fmt_price(plan.target))
                m1.metric("Market exposure", f"${plan.notional_value:,.2f}")
                m2.metric("Capital/collateral used", f"${plan.margin_required:,.2f}")
                m1.metric("Planned loss", f"${plan.planned_loss:,.2f}")
                m2.metric("Leverage", f"{plan.leverage}×")
                st.caption(f"Approximate quantity for manual entry: {plan.quantity:.8f} {symbol.replace('USDT', '')}")
                if plan.danger_price is not None:
                    st.warning(
                        f"Simplified leverage-exhaustion danger price: {fmt_price(plan.danger_price)}. "
                        "Actual Binance liquidation depends on maintenance margin, fees, account mode and other positions."
                    )

            with st.expander("Why this signal?", expanded=True):
                for reason in signal.reasons:
                    st.write(f"• {reason}")
                st.write(f"• RSI(14): {signal.rsi:.1f}")
                st.write(f"• Volume versus 20-hour average: {signal.volume_ratio:.2f}×")
                st.write(f"• ATR volatility: {signal.atr_pct:.2f}% of price")

    selected_symbol = st.radio("Chart", ["BTCUSDT", "ETHUSDT"], horizontal=True)
    if selected_symbol in market_frames:
        st.plotly_chart(price_chart(market_frames[selected_symbol], selected_symbol), use_container_width=True)

with tabs[1]:
    st.subheader("News and broader market context")
    st.caption(
        "This layer assists the technical model but never creates an order by itself. News coverage may be delayed, duplicated or misclassified."
    )
    if news_summary is None:
        st.warning("Current news could not be verified. Technical signals remain available, but do not assume there are no market-moving headlines.")
    else:
        n1, n2, n3 = st.columns(3)
        n1.metric("News context", news_summary.label)
        n2.metric("Headline score", f"{news_summary.average_score:+.1f}")
        n3.metric("High-impact headlines", news_summary.high_impact_count)
        if news_summary.risk_gate:
            st.error("NEWS RISK GATE ACTIVE — pause and verify the underlying high-impact stories before considering a manual trade.")
        news_df = pd.DataFrame(
            [
                {
                    "Headline": item.title,
                    "Source": item.domain,
                    "Seen": item.seen_date,
                    "Score": item.score,
                    "Impact": item.impact,
                    "Link": item.url,
                }
                for item in news_summary.items
            ]
        )
        st.dataframe(
            news_df,
            use_container_width=True,
            hide_index=True,
            column_config={"Link": st.column_config.LinkColumn("Article")},
        )

    st.markdown("### Multi-timeframe market trends")
    context_cols = st.columns(2)
    for col, symbol in zip(context_cols, ["BTCUSDT", "ETHUSDT"]):
        with col:
            context = market_contexts.get(symbol)
            if context is None:
                try:
                    context = load_context(symbol, product)
                    market_contexts[symbol] = context
                except BinanceDataError as exc:
                    st.error(f"{symbol}: market context unavailable ({exc})")
                    continue
            st.markdown(f"#### {symbol.replace('USDT', '/USDT')}")
            a, b = st.columns(2)
            a.metric("Overall trend", context.overall_trend)
            b.metric("24h change", f"{context.price_change_24h_pct:+.2f}%")
            a.metric("24h quote volume", fmt_large(context.quote_volume_24h))
            if context.funding_rate_pct is None:
                b.metric("Futures funding", "Unavailable")
            else:
                b.metric("Futures funding", f"{context.funding_rate_pct:+.4f}%")
            if context.open_interest is not None:
                st.metric("Futures open interest", f"{context.open_interest:,.2f} {symbol.replace('USDT', '')}")
            trend_df = pd.DataFrame(
                [{"Timeframe": timeframe, "Trend": trend} for timeframe, trend in context.trends.items()]
            )
            st.dataframe(trend_df, use_container_width=True, hide_index=True)
    st.info(
        "Funding and open interest describe positioning, not guaranteed direction. Positive funding can indicate long demand or crowded longs; "
        "negative funding can indicate short demand or crowded shorts. Interpret them with price structure and risk controls."
    )

with tabs[2]:
    st.subheader("Walk-forward-style historical check")
    st.caption(
        "Signals are calculated from information available at each candle. Entries occur on the next candle open. "
        "Results include the selected fee and slippage assumptions and do not guarantee future performance."
    )
    if mode == "Isolated Margin":
        st.warning("The historical check does not include changing borrowing availability or margin interest. Enter your current Binance interest cost separately before acting.")
    elif mode == "USDⓈ-M Futures":
        st.warning("The historical check does not include funding payments, maintenance-margin tiers or liquidation execution. It is not a liquidation simulator.")
    evidence_cols = st.columns(2)
    for col, symbol in zip(evidence_cols, ["BTCUSDT", "ETHUSDT"]):
        with col:
            if symbol not in market_frames:
                try:
                    market_frames[symbol] = add_signal_scores(add_indicators(load_market(symbol, product)))
                except Exception as exc:
                    st.error(f"{symbol}: evidence unavailable ({exc})")
                    continue
            result = run_backtest(
                market_frames[symbol],
                fee_pct=fee_pct,
                slippage_pct=slippage_pct,
                allocation_pct=max_allocation_pct,
                leverage=leverage,
                allow_short=allow_short,
            )
            st.markdown(f"#### {symbol.replace('USDT', '/USDT')}")
            a, b = st.columns(2)
            a.metric("Completed trades", result.trades)
            b.metric("Win rate", f"{result.win_rate:.1f}%")
            a.metric("Net strategy return", f"{result.net_return_pct:.2f}%")
            b.metric("Maximum drawdown", f"{result.max_drawdown_pct:.2f}%")
            a.metric("Profit factor", result.profit_factor_label)
            b.metric("Average trade", f"{result.average_trade_pct:.3f}%")
            if result.trades < 20:
                st.warning("Small sample: do not treat these statistics as reliable evidence yet.")
            if not result.equity_curve.empty:
                st.line_chart(result.equity_curve.rename("Strategy equity"), height=220)

with tabs[3]:
    st.subheader("Manual paper-trade journal")
    st.caption("Record simulated trades before risking real funds. Entries remain in this browser session; download the CSV before closing it.")
    if "journal" not in st.session_state:
        st.session_state.journal = []
    with st.form("paper_trade"):
        c1, c2, c3 = st.columns(3)
        journal_symbol = c1.selectbox("Pair", ["BTCUSDT", "ETHUSDT"])
        journal_action = c2.selectbox("Action", ["LONG OPEN", "LONG CLOSE", "SHORT OPEN", "SHORT COVER", "SKIPPED"])
        journal_price = c3.number_input("Price", min_value=0.0, step=1.0)
        note = st.text_input("Reason or observation")
        submitted = st.form_submit_button("Add journal entry")
        if submitted:
            st.session_state.journal.append(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "symbol": journal_symbol,
                    "mode": mode,
                    "leverage": leverage,
                    "action": journal_action,
                    "price": journal_price,
                    "note": note,
                }
            )
    journal_df = pd.DataFrame(st.session_state.journal)
    if journal_df.empty:
        st.info("No paper trades recorded yet.")
    else:
        st.dataframe(journal_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download journal CSV",
            journal_df.to_csv(index=False).encode("utf-8"),
            file_name="paper_trade_journal.csv",
            mime="text/csv",
        )

with tabs[4]:
    st.subheader("Continuous-monitoring routine")
    st.markdown(
        """
1. Keep the app open with **Continuous monitoring** enabled, or deploy it on an always-on host.
2. The screen refreshes automatically; the strategy changes only after a completed hourly candle.
3. Review **News & market trends** for high-impact headlines and 1h/4h/1d conflicts.
4. If the decision is **NEUTRAL / WAIT** or **EXIT / AVOID**, do not open a position.
5. For a **LONG SETUP** or **SHORT SETUP**, act only while the app says **SETUP CURRENTLY VALID**.
6. Match the selected mode, leverage, exposure and collateral in Binance; never substitute Cross Margin for Isolated Margin.
7. Set the displayed stop-loss immediately. Do not widen it after entry.
8. Stop trading for the day when total realized losses reach 2% of the account.
9. Record the result in the paper journal. Review at least 30–50 paper trades before using real money.
        """
    )
    st.warning("Closing the local app, shutting down the computer, losing internet access, or a cloud host going to sleep stops monitoring. Version 3 does not send background notifications.")
    st.error("For a $100 account, never deposit additional money to rescue a losing leveraged position. Do not average down, widen the stop, or use Cross Margin.")
