# Aegis-Quant: Framework Institucional de Trading Cuantitativo (OOP)

**Aegis-Quant** es un sistema cuantitativo multi-estrategia y multi-activo de "Caja Blanca" (*White-Box*) construido con **Programación Orientada a Objetos (OOP)**. Combina los principios de reversión a la media e intermercado de campeones mundiales de trading (como **Iván Scherman**) con técnicas institucionales de la **Cúspide de la Pirámide Cuantitativa** (*Volatility Term Structure VIX/VIX3M*, *Volatility Targeting*, *Cross-Asset Dual Momentum* y *Meta-Labeling con Kelly Fraccional*).

## Estructura Orientada a Objetos

```text
C:\personal\Git_Repositories\gemini_projects\aegis-quant\
├── aegis_quant/
│   ├── models/
│   │   └── market_models.py        # Dataclasses de dominio: MarketBar, EnrichedBar, TradeSignal, ClosedTrade
│   ├── data/
│   │   └── market_repository.py    # MarketDataRepository: Descarga y caché de SPY, QQQ, VIX, VIX3M, GLD, TLT, USO, ZS
│   ├── indicators/
│   │   └── quant_feature_engine.py # QuantFeatureEngine: RSI(2), Bollinger(30,2σ), ATR(14), Vol20d, Mom60Adj y Ratio VIX/VIX3M
│   ├── strategies/
│   │   └── strategies.py           # Jerarquía polimórfica BaseStrategy y los 5 Motores Cuantitativos (M1 a M5)
│   ├── risk/
│   │   └── meta_kelly_sizer.py     # MetaLabelRiskManager: Kelly Fraccional, Filtro de Régimen VTS y Volatility Targeting
│   ├── portfolio/
│   │   └── aegis_engine.py         # AegisPortfolioEngine: Simulación histórica sin apalancamiento oculto y escáner diario
│   └── robustness/
│       └── robustness_analyzer.py  # RobustnessAnalyzer: Monte Carlo (1,000 sims), Estrés de Fricción, Walk-Forward y Sensibilidad
├── data/                           # Caché JSON histórica (2006-2026) y resumen auditado del backtest
├── main_backtest.py                # Ejecuta la comparativa histórica (Modos 1, 2, 3 Base y 3 Élite vs S&P 500)
├── daily_scanner.py                # Escáner diario en vivo de régimen VIX/VIX3M, pesos del Core y señales tácticas
├── build_dashboard.py              # Compila el panel interactivo HTML (dashboard.html)
└── dashboard.html                  # Panel visual interactivo
```

## Comandos de Uso

1. **Ejecutar el Backtest Completo (2007–2026)**:
   ```powershell
   python C:\personal\Git_Repositories\gemini_projects\aegis-quant\main_backtest.py
   ```
2. **Ejecutar el Escáner Diario en Vivo**:
   ```powershell
   python C:\personal\Git_Repositories\gemini_projects\aegis-quant\daily_scanner.py
   ```
3. **Regenerar el Dashboard Interactivo**:
   ```powershell
   python C:\personal\Git_Repositories\gemini_projects\aegis-quant\build_dashboard.py
   ```
