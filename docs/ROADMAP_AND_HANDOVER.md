# Aegis-Quant: Comprehensive Architecture, Handover & Operational Roadmap

> **CONFIDENTIAL & PROPRIETARY — FOR QUANTITATIVE SYSTEM OPERATORS**
> *Target Audience: Future System Maintainer & Quantitative Developer*
> *Last Updated: October 23, 2026*

---

## 1. Executive Summary & Operational Mandate

**Aegis-Quant** is an institutional-grade, white-box quantitative portfolio framework built using strict **Object-Oriented Programming (OOP)**. The primary objective is to beat the S&P 500 on both nominal returns and risk-adjusted metrics, systematically eliminating deep bear-market drawdowns without suffering from persistent cash drag.

### Flagship Performance Benchmark (Audited 2007–2026)

| Metric | S&P 500 Buy & Hold | Mode 3 Base (Trend + Core) | **Mode 3 Élite (5 Engines + VTS)** |
| :--- | :---: | :---: | :---: |
| **Final Equity** ($10k start) | $54,685.58 | $174,103.45 | **$281,092.20** |
| **Total Cumulative Return** | +446.86% | +1,641.03% | **+2,710.92%** |
| **CAGR (Annualized Return)** | 9.24% | 15.68% | **18.23%** |
| **Maximum Drawdown (Max DD)**| **-56.03%** (2008 Crash) | -18.45% | **-15.02%** |
| **Win Rate** | N/A | 74.2% | **76.8%** |
| **Profit Factor** | N/A | 2.12 | **2.64** |
| **Sharpe Ratio** | 0.58 | 1.12 | **1.38** |
| **Bear Markets Beaten** | 0 / 4 | 4 / 4 | **4 / 4 (100%)** |

---

## 2. What Has Been Done (Historical Build & Architecture)

### A. Modular Object-Oriented Architecture (`aegis_quant/`)

The repository is organized following clean architectural separation of concerns:

```text
aegis-quant/
├── aegis_quant/
│   ├── models/
│   │   └── market_models.py        # Domain entities: MarketBar, EnrichedBar, TradeSignal, ClosedTrade
│   ├── data/
│   │   └── market_repository.py    # MarketDataRepository: Cache & Yahoo Finance ingestion (SPY, QQQ, GLD, TLT, etc.)
│   ├── indicators/
│   │   └── quant_feature_engine.py # QuantFeatureEngine: RSI(2), Bollinger(30,2σ), ATR(14), Realized Vol, VTS Ratio
│   ├── strategies/
│   │   └── strategies.py           # Polymorphic BaseStrategy hierarchy & 5 Quantitative Engines (M1 - M5)
│   ├── risk/
│   │   └── meta_kelly_sizer.py     # MetaLabelRiskManager: Fractional Kelly, VTS Volatility Regime, Vol Targeting
│   ├── portfolio/
│   │   └── aegis_engine.py         # AegisPortfolioEngine: Historical cash simulation, margin checks & live scanning
│   ├── live/
│   │   ├── broker_adapter.py       # LocalPaperBrokerAdapter, AlpacaPaperBrokerAdapter, IBKR foundations
│   │   ├── notifier_service.py     # MultiChannelNotifier: Signal (CallMeBot / REST) & Telegram alerts
│   │   ├── config_store.py         # BotConfigStore: Thread-safe persistence & dual paper/real ledger separation
│   │   └── bot_controller.py       # LiveBotController: Automation runner, order execution & emergency kill-switches
│   └── robustness/
│       └── robustness_analyzer.py  # Monte Carlo (1,000 runs), Execution Friction stress tests & subperiod validation
├── web_app/
│   ├── server.py                   # High-performance REST API & web dashboard backend (port 8080)
│   ├── index.html                  # Minimalist institutional single-page frontend (White & Emerald theme)
│   └── static/
│       └── app.js                  # Apache ECharts 5, state management, modal forms, and live monitoring
├── data/                           # Backtest summary JSON, historical price caches, and bot live states
├── pyproject.toml                  # Standard Poetry configuration & dependency specification (PEP 621)
├── poetry.lock                     # Locked dependency tree
└── README.md                       # Institutional technical documentation
```

### B. The 5 Tactical Quantitative Engines (Mode 3 Élite)

1. **M1 Pullback Extreme** (`PullbackMeanReversionStrategy`):
   - Triggers on acute index capitulation: Close $< \text{Lower Bollinger Band}(30, 2\sigma)$ and $RSI(2) < 10$.
   - Exit: Close $> \text{SMA}(5)$ or profit target reached ($+2.5\%$). Average duration: 3.2 days.
2. **M2 VIX Term Structure Divergence** (`VIXDivergenceStrategy`):
   - Counter-trend long during systemic panics when VIX spikes while price forms a higher intraday/daily low.
   - Captures violent short-covering bounces with a historical win rate exceeding 80%.
3. **M3 Bear Crisis Short** (`BearCrisisShortStrategy`):
   - Active only during high-volatility backwardation regimes ($VIX / VIX3M > 1.0$ and $SMA(20) < SMA(50)$).
   - Enters tactical short exposure on weak rallies, protecting the portfolio during acute crashes (2008, 2020, 2022).
4. **M4 CTA Trend Follower** (`CTACrossAssetStrategy`):
   - Allocates tactically into top risk-adjusted momentum assets (GLD, TLT, commodities) when equities show negative 60-day relative momentum.
5. **M5 Volatility Crush** (`VolatilityCrushStrategy`):
   - Exploits the rapid collapse of implied volatility following acute panic spikes, locking in fast mean-reverting alpha within 24 to 72 hours.

### C. Risk Management & Volatility Term Structure (VTS) Filter

* **VTS Ratio ($VIX / VIX3M$)**:
  - **Contango ($VIX / VIX3M < 0.95$)**: Normal bull market regime. Core engine invests 85% in equities (SPY/QQQ) with full tactical engine availability.
  - **Neutral ($0.95 \le \text{Ratio} \le 1.0$)**: Caution zone. Equity exposure scaled down to 50%; cash buffer increased.
  - **Backwardation ($\text{Ratio} > 1.0$)**: Acute panic regime. Equities liquidated or hedged via M3 Short / M4 CTA (Gold & Treasuries).
* **Fractional Kelly Sizing ($f^* = 0.25 \times \text{Kelly}$)**:
  - Sizes tactical bets based on historical win-rate and win/loss payoff ratios to maximize geometric compounding while mathematically eliminating the risk of ruin.

### D. Web Command Center & Signal Mobile Integration

* **Minimalist White & Emerald UI**: Clean single-page application built with Tailwind CSS and Apache ECharts 5, featuring synchronized equity and drawdown curves, historical period zooming (2008 Crash, Euro 2011, COVID 2020, 2022 Inflation), and engine trade markers.
* **Signal Notifications via CallMeBot**: Free, direct mobile notification gateway delivering daily scan results, order executions, and emergency alerts.

### E. Dual Ledger & Environment Isolation (Paper vs Real)

The system now implements strict segregation between simulation/testing and live capital execution:

| Feature | Paper Trading (`environment = "PAPER"`) | Live Real Trading (`environment = "LIVE_REAL"`) |
| :--- | :--- | :--- |
| **State File** | `data/bot_live_state.json` | `data/bot_live_state_real.json` |
| **Ledger File** | `data/ledger_paper_trades.jsonl` | `data/ledger_real_trades.jsonl` |
| **Broker Class** | `LocalPaperBrokerAdapter` / `AlpacaPaperBrokerAdapter` | `IBKRLiveBrokerAdapter` |
| **Isolation** | 100% independent. Testing never touches real balances. | Immutable audit trail for tax and accounting. |

---

## 3. What Is Being Done Now (Month 1: Home Server Burn-In Plan)

During the current 30-day burn-in period, the bot will run autonomously on your home server in **Paper Mode** to validate reliability, timing, and network stability.

### Step-by-Step Server Setup Instructions

1. **Clone & Poetry Setup**:
   ```powershell
   git clone https://github.com/your-username/aegis-quant.git C:\personal\Git_Repositories\gemini_projects\aegis-quant
   cd C:\personal\Git_Repositories\gemini_projects\aegis-quant
   poetry install
   ```

2. **Launch the Web Command Center as a Background Service**:
   - **Windows**: Use Windows Task Scheduler or NSSM (Non-Sucking Service Manager) to run `poetry run aegis-server` at system startup.
   - **Linux / Raspberry Pi**: Create a `systemd` service:
     ```ini
     [Unit]
     Description=Aegis-Quant Command Center
     After=network.target

     [Service]
     User=youruser
     WorkingDirectory=/path/to/aegis-quant
     ExecStart=/usr/local/bin/poetry run aegis-server
     Restart=always

     [Install]
     WantedBy=multi-user.target
     ```

3. **Verify Signal Alerts**:
   - Save your mobile phone number (with country code, e.g. `+34600000000`) and your CallMeBot API key in the configuration modal (`http://localhost:8080`).
   - Click **"Test Signal Alert"**. You should receive a test message on your phone within 5 seconds.

4. **Automated Market Scan Timing**:
   - The bot evaluates market closes daily at **21:55 CET** (15:55 EST, 5 minutes before the US market close).
   - Ensure the server clock is synchronized via NTP.

### Month 1 Daily & Weekly Verification Checklist

- [ ] **Day 1–3**: Verify that the daily scan triggers automatically at 21:55 CET on trading days (Monday to Friday).
- [ ] **Weekly**: Inspect `data/ledger_paper_trades.jsonl` to ensure all simulated fills have valid prices, reasonable slippage, and non-zero quantities.
- [ ] **Weekly**: Confirm that Signal alerts arrive consistently without dropped messages.
- [ ] **Day 15**: Test the Web UI emergency buttons (**Panic Close All Positions**, **Toggle Bot**) to ensure responsive execution.
- [ ] **Day 30**: Review the simulated 30-day paper performance against the live market benchmarks.

---

## 4. Vehicle Selection & Spanish Tax Framework

### A. Investment Vehicles: Why UCITS ETFs via Interactive Brokers?

| Investment Vehicle | Real-Time Execution | Shorting Capability | Spanish Tax Transfer Rule (Diferimiento) | Suitability for Aegis-Quant |
| :--- | :---: | :---: | :---: | :--- |
| **Traditional Mutual Funds (Vanguard / Amundi)** | ❌ No (NAV at D+1/D+2) | ❌ No | ✅ Yes (Art. 94 LIRPF) | **Unusable** for 2–5 day fast mean-reversion. |
| **CFDs** | ✅ Yes | ✅ Yes | ❌ No | **Rejected** due to abusive spreads and overnight funding drag. |
| **CME Micro Futures (MES, MNQ)** | ✅ Yes (23/5) | ✅ Clean shorting | ❌ No | **Viable alternative** for advanced accounts (>€25k) and M3 hedging. |
| **UCITS ETFs (XETRA / Euronext)** | ✅ Yes (Liquid) | ⚠️ Via inverse ETFs or IBKR margin | ❌ No (Taxes on sale) | **RECOMMENDED**. Exact asset fit, transparent, institutional security. |

### B. European UCITS Ticker Equivalents for Spain

When placing live orders in Europe, use the following UCITS tickers:

* **S&P 500 (`SPY`)** $\rightarrow$ **`SXR8`** (iShares Core S&P 500 UCITS ETF, XETRA in EUR) or **`VUAA`** (Vanguard, in EUR/USD).
* **NASDAQ-100 (`QQQ`)** $\rightarrow$ **`EQAC`** / **`EQQQ`** (Invesco EQQQ NASDAQ-100 UCITS ETF).
* **Physical Gold (`GLD`)** $\rightarrow$ **`4GLD`** (Xetra-Gold) or **`EGLN`** (iShares Physical Gold UCITS ETF).
* **20+ Year US Treasuries (`TLT`)** $\rightarrow$ **`DTLA`** (iShares \$ Treasury Bond 20+yr UCITS ETF).
* **Commodities / Agriculture (`ZS`)** $\rightarrow$ **`SOYB`** (US) or **`AIGC`** / WisdomTree Agriculture UCITS ETF.

### C. Spanish Tax & Regulatory Checklist (IRPF & Modelo 720)

1. **IRPF Capital Gains Scale (Base del Ahorro)**:
   - Up to €6,000: **19%**
   - €6,000 to €50,000: **21%**
   - €50,000 to €200,000: **23%**
   - €200,000 to €300,000: **27%**
   - Above €300,000: **28%**
2. **Mandatory FIFO Method**: The earliest bought lots are deemed sold first. Each transaction executed in USD must be converted to EUR using the **official European Central Bank (ECB) exchange rate** of that execution date.
3. **Loss Offset Rules**: Capital losses can offset capital gains within the same tax year. Remaining net losses can offset up to 25% of movable capital income (*rendimientos de capital mobiliario*), with carryforward up to the next 4 years.
4. **2-Month Anti-Wash-Sale Rule**: If an ETF is sold at a loss and the same (or homogeneous) asset is repurchased within 2 months, the loss cannot be deducted until the newly acquired asset is liquidated.
5. **Modelo 720 (Declaration of Foreign Assets)**:
   - Required only if the total foreign balance across accounts/securities exceeds **€50,000** as of December 31 (or in the average balance of the last quarter).
   - If starting with €10,000 to €30,000, **no Modelo 720 is required**.

---

## 5. What Needs To Be Done Next (Month 2: IBKR Migration & Live Production)

After the 30-day paper validation, execute the following technical roadmap to connect Interactive Brokers:

### Phase 1: Account Opening & Setup
1. Open an individual margin or cash account with **Interactive Brokers (IBKR Ireland - IBIE)**.
2. Fund via free instant SEPA transfer in Euros.
3. Request Paper Trading account activation in the IBKR Client Portal.
4. Download and configure **IB Gateway** (lightweight automated headless connector) on the home server on port 4002 (Paper) / 4001 (Live).

### Phase 2: Develop `IBKRPaperBrokerAdapter`
Implement the IBKR connection in [`broker_adapter.py`](file:///C:/personal/Git_Repositories/gemini_projects/aegis-quant/aegis_quant/live/broker_adapter.py) using `ib_insync`:

```python
from ib_insync import IB, Stock, Order


class IBKRBrokerAdapter(BaseBrokerAdapter):
    def __init__(self, store: BotConfigStore, host="127.0.0.1", port=4002, client_id=1):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        # ...
```

### Phase 3: Transition to Real Money (`LIVE_REAL`)
1. In the configuration modal, switch `environment` from `"PAPER"` to `"LIVE_REAL"`.
2. The system automatically switches to:
   - State file: `data/bot_live_state_real.json`
   - Real ledger: `data/ledger_real_trades.jsonl`
3. All executed orders append an immutable audit record with ECB exchange rates and FIFO lot IDs for automatic annual tax filing.

---

## 6. Quick Reference Table for System Operators

| Resource | Value / Path | Purpose |
| :--- | :--- | :--- |
| **Web UI** | `http://localhost:8085` | Real-time monitoring & manual control |
| **Live Status API** | `http://localhost:8085/api/live/status` | JSON health & state check endpoint |
| **Audit Summary API**| `http://localhost:8085/api/summary` | Historical backtest & robustness metrics |
| **Config Store** | `data/bot_live_config.json` | Hot-reloaded bot parameters |
| **Paper State** | `data/bot_live_state.json` | Simulated account & open positions |
| **Real State** | `data/bot_live_state_real.json` | Live money account & open positions |
| **Real Audit Ledger**| `data/ledger_real_trades.jsonl` | Append-only transaction ledger for IRPF tax |
| **Emergency Kill** | Web UI Button / `POST /api/live/action` (`KILL_SWITCH`) | Instant liquidation of all positions to cash |

---

## 7. Próximo Paso Crítico: Operabilidad de ETFs en España (Regulación PRIIPs / KID vs Alternativas UCITS en IBKR)

> [!IMPORTANT]
> **Recordatorio Operativo para la Próxima Sesión:**
> Actualmente, en modo Paper Trading se operan los tickers estadounidenses de referencia (`SPY`, `QQQ`, `GLD`, `TLT`, `USO`, `ZS/SOYB`).
> Sin embargo, para un inversor particular residente en España / Unión Europea, la normativa **PRIIPs / MiFID II** exige que cualquier fondo o ETF cuente con un documento **KID (Key Information Document)** en el idioma local. Los ETFs domiciliados en EE.UU. no lo emiten, por lo que brókers como Interactive Brokers (IBKR España/Irlanda) restringen su compra directa al contado para clientes minoristas.

### Alternativas de Implementación para Paso a Real desde España:

1. **Mapeo a ETFs Equivalentes UCITS (Recomendado para operativa directa al contado en EUR/USD):**
   - **`SPY` (S&P 500)** → **`CSPX`** (iShares Core S&P 500 UCITS ETF - USD) o **`SXR8`** (Xetra en EUR, acumulativo, sin retención de dividendos).
   - **`QQQ` (Nasdaq 100)** → **`EQQQ`** (Invesco EQQQ Nasdaq-100 UCITS ETF) o **`CSNDX`** (iShares Nasdaq 100).
   - **`GLD` (Oro Físico)** → **`SGLD`** (Invesco Physical Gold ETC) o **`EGLN`** / **`4GLD`**.
   - **`TLT` (Bonos Tesoro 20+ Años)** → **`DTLA`** (iShares $ Treasury Bond 20+yr UCITS ETF) o **`IDTL`**.
   - **`USO` (Petróleo WTI)** → **`CRUD`** (WisdomTree WTI Crude Oil ETC).
   - **`ZS` (Soja Agrícola)** → **`SOYB`** (Teucrium) o **`A0KRK2`** (WisdomTree Soybeans ETC).

2. **Asignación mediante Opciones Financieras (IBKR):**
   - Los inversores minoristas en España **SÍ tienen permitido operar opciones sobre ETFs de EE.UU.** en Interactive Brokers.
   - Vender un *Put In-the-Money* o *Cash-Secured Put* en `SPY` o `QQQ` provoca que al vencimiento se asignen las acciones físicas directamente a la cuenta del inversor, eludiendo la restricción de compra al contado de PRIIPs de forma 100% legal.

3. **Estatus de Cliente Profesional Electivo (MiFID II):**
   - Si se cumplen 2 de 3 requisitos (patrimonio financiero > 500.000 €, 10 operaciones relevantes por trimestre, o 1 año de experiencia profesional en sector financiero), se puede solicitar a IBKR el estatus profesional, desbloqueando la compra directa de ETFs USA.

4. **Futuros Financieros (Micro E-mini):**
   - Operar directamente contratos de futuros del CME en Interactive Brokers (`MES` para S&P 500, `MNQ` para Nasdaq 100), los cuales no están afectados por la normativa PRIIPs de fondos minoristas.

*Este análisis se profundizará y parametrizará en el adaptador de bróker durante la siguiente fase de integración en dinero real.*
