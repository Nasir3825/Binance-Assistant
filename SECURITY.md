# Security policy

Version 3 intentionally uses public Binance Spot and USDⓈ-M Futures market-data endpoints plus public news retrieval. It does not request, store, or transmit a Binance API key and cannot place Spot, Margin, or Futures orders.

Do not add real credentials to source files, screenshots, GitHub, or Streamlit configuration committed to Git. If order automation is developed later:

- begin with the applicable Binance Spot or USDⓈ-M Futures test environment;
- create a separate API key for the bot;
- enable only the minimum trading permission required;
- never enable withdrawals;
- restrict the key to the deployment server's IP address where supported;
- keep secrets in environment variables or the host's secret manager;
- add daily-loss, stale-data, duplicate-order, and emergency-stop controls;
- enforce isolated rather than cross margin for the beginner configuration;
- verify leverage, margin mode, position side, reduce-only exits, maintenance-margin tiers, funding, interest and liquidation calculations directly against Binance before enabling orders;
- rotate the key immediately if it may have been exposed.

Report a suspected credential exposure by revoking the affected key in Binance first, then reviewing account and order history.
