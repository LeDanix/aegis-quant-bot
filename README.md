# Aegis-Quant: Institutional Quantitative Trading Framework (OOP)

**Aegis-Quant** is an institutional-grade, white-box quantitative portfolio engine built with strict Object-Oriented Programming (OOP) design patterns. It integrates mean-reversion and cross-asset momentum principles with apex quantitative techniques: **Volatility Term Structure (VTS VIX/VIX3M) regime filtering**, **Target Volatility sizing**, **Cross-Asset Dual Momentum**, and **Meta-Labeling with Fractional Kelly risk management**.

The flagship configuration is **Mode 3 Élite**, an ensemble of 6 complementary tactical engines (`M1`–`M6`) hedging equity drawdowns while maximizing risk-adjusted compound annual growth (audited 2007–2026: CAGR 19.54% vs S&P 500 9.24%, Max DD -14.86% vs -56.03%, Sharpe 1.61, Calmar 1.31).

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
6. **M6 TOTM Flow (Turn-of-the-Month)**: Institutional liquidity harvester capturing end-of-month and beginning-of-month pension/payroll rebalancing flows under Contango regime.

---

## Live Operations & Notifications

- **Local Paper Trading (`LocalPaperBrokerAdapter`)**: Runs real-time paper execution without requiring third-party credentials. Simulates order execution, slippage, and portfolio valuation.
- **Signal Mobile Alerts**: Native integration with CallMeBot Signal Gateway or self-hosted Signal CLI REST API. Delivers daily regime states, entry/exit orders, and emergency drawdown notifications directly to your phone.
- **Interactive Web Interface**: Minimalist institutional design displaying active portfolio allocations, pending signals, interactive equity curves with trade markers, and stress-test diagnostics.
- **Automated Spanish Tax Engine (AEAT / IRPF)**: Built-in FIFO lot tracking, official daily ECB EUR/USD exchange rates, 2-month wash sale rule detection (Art. 33.5.f LIRPF), 4-year loss carryforward, and direct Renta WEB Box 0326–0335 CSV export.

---

## Technical & Operational Documentation (`docs/`)

All exhaustive architectural, operational, and regulatory documentation is centralized in [`docs/`](docs/):

- **[MANUAL_DE_USO.md](docs/MANUAL_DE_USO.md)**: Manual oficial exhaustivo de la plataforma web/móvil (Inicio, Cartera, ETFs, Análisis, Sistema y Configuración), rutina diaria de las 21:55 CET, operativa en Euros en Tradegate y auditoría fiscal.
- **[REQUISITOS_Y_TESTS_FIABILIDAD.md](docs/REQUISITOS_Y_TESTS_FIABILIDAD.md)**: Especificación formal de los 12 requisitos de fiabilidad operativa y UX (hot-swapping de motores, botón de pánico, persistencia atómica, cortafuegos de drawdown -8%, modo copiloto y resiliencia), verificados por 71 tests automatizados.
- **[OPERATIONAL_FAQ_AND_DECISIONS.md](docs/OPERATIONAL_FAQ_AND_DECISIONS.md)**: Registro histórico y vivo de decisiones cuantitativas, operativa en Tradegate en EUR con órdenes Limit, selección de ETFs UCITS (`SPYL`, `EQQQ`, `4GLD`, etc.) y descarte de productos apalancados x3.
- **[AUDIT_AND_PROPOSALS.md](docs/AUDIT_AND_PROPOSALS.md)**: Auditoría cuantitativa independiente 2007–2026, pruebas de ablación (*leave-one-out*), evaluación empírica de candidatos M6–M9 y dictamen de robustez.
- **[ROADMAP_AND_HANDOVER.md](docs/ROADMAP_AND_HANDOVER.md)**: Manual de traspaso técnico, fórmulas matemáticas, gestión de liquidez y protocolo de paso a dinero real.
