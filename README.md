# Aegis-Quant: Institutional Quantitative Trading Framework (OOP)

**Aegis-Quant** is an institutional-grade, white-box quantitative portfolio engine built with strict Object-Oriented Programming (OOP) design patterns. It integrates mean-reversion and cross-asset momentum principles with apex quantitative techniques: **Volatility Term Structure (VTS VIX/VIX3M) regime filtering**, **Target Volatility sizing**, **Cross-Asset Dual Momentum**, and **Meta-Labeling with Fractional Kelly risk management**.

The flagship configuration is **Mode 3 Élite**, an ensemble of 5 complementary tactical engines hedging equity drawdowns while maximizing risk-adjusted compound annual growth (CAGR 18.23% vs S&P 500 9.24%, Max DD -15.02% vs -56.03%, audited 2007–2026).

---

## Architecture & Directory Structure

```text
aegis-quant/
├── aegis_quant/
│   ├── models/
│   │   └── market_models.py        # Domain entities: MarketBar, EnrichedBar, TradeSignal, ClosedTrade
│   ├── data/
│   │   └── market_repository.py    # MarketDataRepository: Cache & Yahoo Finance ingestion (SPY, QQQ, GLD, TLT, etc.)
│   ├── indicators/
│   │   └── quant_feature_engine.py # QuantFeatureEngine: RSI(2), Bollinger Bands, ATR(14), Realized Vol, VTS Ratio
│   ├── strategies/
│   │   └── strategies.py           # Polymorphic BaseStrategy hierarchy & 5 Quantitative Engines (M1 - M5)
│   ├── risk/
│   │   └── meta_kelly_sizer.py     # MetaLabelRiskManager: Fractional Kelly, VTS Volatility Regime, Vol Targeting
│   ├── portfolio/
│   │   └── aegis_engine.py         # AegisPortfolioEngine: Historical cash simulation, margin checks & live scanning
│   ├── live/
│   │   ├── broker_adapter.py       # LocalPaperBrokerAdapter & AlpacaPaperBrokerAdapter (Polymorphic broker layer)
│   │   ├── notifier_service.py     # MultiChannelNotifier: Signal (CallMeBot/REST) & Telegram alerting
│   │   ├── config_store.py         # Thread-safe persistent configuration store (data/bot_config.json)
│   │   └── bot_controller.py       # LiveBotController: Automation runner, order execution & emergency kill-switches
│   └── robustness/
│       └── robustness_analyzer.py  # Monte Carlo (1,000 runs), Execution Friction stress tests & subperiod validation
├── web_app/
│   ├── server.py                   # High-performance REST API & web dashboard backend (port 8085)
│   ├── index.html                  # Minimalist institutional single-page frontend (White & Emerald theme)
│   └── static/
│       └── app.js                  # Apache ECharts 5, state management, modal forms, and live monitoring
├── data/                           # Backtest summary JSON, historical price caches, and bot live states
├── pyproject.toml                  # Standard Poetry configuration & dependency specification
├── poetry.lock                     # Locked dependency tree
└── README.md                       # Institutional technical documentation
```

---

## Getting Started with Poetry

### Prerequisites
- Python 3.10 or higher
- [Poetry](https://python-poetry.org/) installed (`pip install poetry` or `winget install Python.Poetry`)

### 1. Installation
Install project dependencies in a self-contained virtual environment:
```powershell
poetry install
```

### 2. Run the Web Command Center
Launch the integrated web server and REST control plane:
```powershell
poetry run aegis-server
```
Navigate to:
- **Web UI**: `http://localhost:8085` (or via private LAN / Tailscale VPN on mobile devices)
- **Live Status API**: `http://localhost:8085/api/live/status`
- **Quantitative Summary API**: `http://localhost:8085/api/summary`

### 3. CLI Scripts

- **Run Historical Backtest (2007–2026)**:
  ```powershell
  poetry run python main_backtest.py
  ```

- **Run Daily Live Market Scan**:
  ```powershell
  poetry run python daily_scanner.py
  ```

- **Regenerate Static Audit Dashboard**:
  ```powershell
  poetry run python build_dashboard.py
  ```

---

## Tactical Engine Roster (Mode 3 Élite)

1. **M1 Pullback Extreme**: Mean-reversion buyer on index panics ($RSI(2) < 10$, close below lower Bollinger band).
2. **M2 VIX Term Structure Divergence**: Counter-trend long on capitulation when VIX spikes while price forms a higher low.
3. **M3 Bear Crisis Short**: Hedging engine taking tactical short exposure when the market enters high-volatility backwardation ($VIX/VIX3M > 1.0$).
4. **M4 CTA Trend Follower**: Cross-asset trend rider investing in top-momentum defensive assets (GLD, TLT, commodities) during equities distress.
5. **M5 Volatility Crush**: Rapid mean-reversion engine capitalizing on acute implied volatility collapse following systemic panic events.

---

## Live Operations & Notifications

- **Local Paper Trading (`LocalPaperBrokerAdapter`)**: Runs real-time paper execution without requiring third-party credentials. Simulates order execution, slippage, and portfolio valuation.
- **Signal Mobile Alerts**: Native integration with CallMeBot Signal Gateway or self-hosted Signal CLI REST API. Delivers daily regime states, entry/exit orders, and emergency drawdown notifications directly to your phone.
- **Interactive Web Interface**: Minimalist institutional design displaying active portfolio allocations, pending signals, interactive equity curves with trade markers, and stress-test diagnostics.
