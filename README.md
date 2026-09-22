# BTC & ETH Leveraged Trading Assistant

A continuously monitoring, manual-decision Streamlit application for a beginner with a **hard capital ceiling of $100**. It covers Binance Spot, Isolated Margin and USDⓈ-M Futures for BTC/USDT and ETH/USDT. It checks prices every 60 seconds by default and recalculates signals after each completed one-hour candle. It does **not** connect to a Binance account or place orders.

## Important limitation

No strategy or bot can guarantee profit. Historical performance can fail in live markets. This project is educational decision support; the user remains responsible for every order and loss.

## Complete build guide

For the full Windows, VS Code, modeling, backtesting, deployment and worked-example instructions, open [`docs/STEP_BY_STEP_BUILD_GUIDE.md`](docs/STEP_BY_STEP_BUILD_GUIDE.md).

## Version 3 features

- public Binance Spot and USDⓈ-M Futures candles; no API key
- BTC/USDT and ETH/USDT only
- continuous live-price monitoring with selectable 30–300 second refresh
- current English-language Bitcoin, Ethereum and crypto-market headlines
- transparent headline sentiment and high-impact news-risk warnings
- 1-hour, 4-hour and daily trend alignment
- 24-hour price change and quote volume
- public USDⓈ-M Futures funding-rate and open-interest context
- completed 1-hour candles only
- EMA 20/50 trend, RSI, MACD, volume confirmation and ATR volatility
- `LONG SETUP`, `SHORT SETUP`, `NEUTRAL / WAIT`, and `EXIT / AVOID` decisions
- Spot long-only, plus manual Isolated Margin and USDⓈ-M Futures long/short analysis
- leverage selectable from 2× to 5× in leveraged modes
- separate collateral, market exposure, stop-loss, target and planned-loss calculations
- historical simulation with next-candle entry, long/short logic, fees, slippage and leverage
- in-session paper-trade journal and CSV download
- $100 capital ceiling, one-position workflow, 1% per-trade maximum and 2% daily stop

## Windows installation using Command Prompt

Python 3.11 is recommended.

1. Extract the project ZIP.
2. Open the extracted folder in VS Code.
3. Open **Terminal > New Terminal** and make sure the terminal profile is Command Prompt.
4. Create a virtual environment:

```cmd
py -3.11 -m venv .venv
```

5. Activate it:

```cmd
.venv\Scripts\activate
```

6. Install the application:

```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

7. Start it:

```cmd
python -m streamlit run app.py
```

8. Open the local URL shown in Command Prompt, normally `http://localhost:8501`.

## Test the calculations

```cmd
pip install -r requirements-dev.txt
python -m pytest -q
```

The expected result is eight passing tests.

## Continuous-monitoring routine

1. Keep the app running with **Continuous monitoring** enabled.
2. Select `Spot`, `Isolated Margin`, or `USDⓈ-M Futures`. Leveraged modes are capped at 5×.
3. Review the News & market trends tab for high-impact headlines and higher-timeframe conflicts.
4. Do nothing unless the decision is `LONG SETUP` or `SHORT SETUP` and its live status is `SETUP CURRENTLY VALID`.
5. Match the displayed direction, leverage, market exposure and collateral in Binance. Never use Cross Margin for this beginner workflow.
6. If proceeding, use only the displayed capital/collateral amount.
7. Set the displayed stop-loss immediately; never widen it.
8. Stop for the day if realized losses reach 2% of the account.
9. Paper trade at least 30–50 signals in each selected mode before committing real funds.

News scoring is a transparent keyword-based context indicator, not a factual-verification engine or trading signal. Funding and open interest describe positioning and can indicate either conviction or crowding; they do not guarantee direction.

The local version monitors only while the app and computer remain running with an internet connection. A cloud deployment monitors only while its host is active; free hosting services may sleep. Version 3 does not send push, email, or Telegram notifications.

## How the signal works

Long and short setups are scored independently. One point is awarded for each direction-specific condition:

- bullish or bearish EMA structure;
- RSI in the preferred long zone (50–68) or short zone (32–50);
- MACD aligned with the direction;
- volume at or above its 20-hour average.

A setup needs at least three points. Longs are blocked when RSI is 70 or higher; shorts are blocked when RSI is 30 or lower. Stops use 1.5 ATR with a minimum distance, and targets use two times planned risk. A signal is a screening rule, not proof of direction.

## Understanding the $100 ceiling

The app never accepts capital above $100. In leveraged modes, **collateral** and **market exposure** are different. For example, $25 collateral at 3× controls $75 of exposure. This does not mean the account contains $75 extra cash; it means gains, losses and liquidation risk are magnified. The displayed danger price is a simplified leverage-exhaustion illustration—not Binance's official liquidation price.

## Backtest limitations

The simulation is deliberately conservative when both the stop and target fall inside one candle: it assumes the stop was hit first. It cannot reproduce order-book liquidity, outages, market gaps, taxes, maintenance-margin tiers, liquidation, margin interest, futures funding, changing fees, emotional execution or future market regimes. The included history is limited by the API request, so results are diagnostic—not a forecast.

## Before any future automation

Automation is a separate phase. First require a meaningful forward-tested sample for each trading mode, stable after-cost results, acceptable drawdown, and successful Binance test-environment operation. Any future key must have withdrawals disabled and minimum permissions. Never reuse a personal all-purpose API key.
