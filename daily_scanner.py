"""
Escáner Diario en Vivo de Aegis-Quant (daily_scanner.py).
Evalúa el estado actual de la Estructura Temporal de Volatilidad (VIX / VIX3M),
el régimen macroeconómico de cada activo, los pesos recomendados del Core Élite
y las señales tácticas activas hoy en los 5 Motores.
"""

import os

from aegis_quant.data.market_repository import MarketDataRepository
from aegis_quant.indicators.quant_feature_engine import QuantFeatureEngine
from aegis_quant.portfolio.aegis_engine import AegisPortfolioEngine


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")

    repo = MarketDataRepository(data_dir=data_dir)
    raw_universe = repo.load_universe(force_refresh=False, verbose=False)

    feature_engine = QuantFeatureEngine(
        vix_bars=raw_universe["VIX"],
        vix3m_bars=raw_universe["VIX3M"],
    )
    enriched_universe = {
        sym: feature_engine.enrich_series(bars) for sym, bars in raw_universe.items() if sym not in ("VIX", "VIX3M")
    }

    engine = AegisPortfolioEngine(enriched_universe=enriched_universe)
    scan = engine.scan_live_market()

    print("=" * 84)
    print(f"AEGIS-QUANT | ESCANER DE MERCADO EN VIVO (Fecha: {scan['as_of_date']})")
    print("=" * 84)
    print(f"Regimen Macro Detectado : {scan['regime']}")
    print(
        f"Estructura VIX / VIX3M  : VIX={scan['vix_close']:.2f} | VIX3M={scan['vix3m_close']:.2f} | "
        f"Ratio VTS={scan['vts_ratio']:.3f} -> {scan['vts_state']}"
    )
    print("-" * 84)
    print("ASIGNACION RECOMENDADA DEL CORE ADAPTATIVO (MODO 3 ELITE):")
    for sym, w_pct in scan["core_allocation"].items():
        print(f"  * {sym:5s}: {w_pct:5.1f}% del capital")
    print("-" * 84)
    print("ESTADO TECNICO DEL UNIVERSO MULTI-ACTIVO:")
    for a in scan["assets"]:
        print(
            f"  {a['symbol']:4s} | Close: {a['close']:7.2f} | SMA200: {a['sma200']:7.2f} ({a['trend']:7s}) | "
            f"RSI(2): {a['rsi2']:4.1f} | Vol20d: {a['realized_vol20']:4.1f}% | Mom60Adj: {a['mom60_vol_adj']:+5.2f} | "
            f"Peso Core: {a['core_weight_pct']:4.1f}%"
        )
    print("-" * 84)
    if scan["active_signals"]:
        print(f"SENALES TACTICAS ACTIVAS HOY ({len(scan['active_signals'])}):")
        for s in scan["active_signals"]:
            print(
                f"  >>> [{s['engine_name']}] {s['direction']} en {s['symbol']} @ {s['entry_price']} | "
                f"Stop: {s['stop_price']} ({s['stop_distance_pct']}%) | Meta-Conf: {s['meta_confidence']}x"
            )
            print(f"      Motivo: {s['reason']}")
            print(f"      Target: {s['target_description']}")
    else:
        print("SENALES TACTICAS ACTIVAS HOY: Ninguna. Mantener asignacion del Core Adaptativo.")
    print("=" * 84)


if __name__ == "__main__":
    main()
