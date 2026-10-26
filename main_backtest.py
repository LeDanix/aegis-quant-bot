"""
Punto de Entrada Principal Orientado a Objetos para el Backtest de Aegis-Quant (2007-2026).
Compara:
  - Modo 1: Táctico Conservador (Base de la Pirámide, 1.5% Riesgo)
  - Modo 2: Táctico Puro Scherman + Motor 5 VTS (2.5% Riesgo, sin Core pasivo)
  - Modo 3 Base: Core S&P 500 (SMA200) + 4 Motores Tácticos
  - Modo 3 Élite (Cúspide de la Pirámide): Core Dual-Momentum con Volatility Targeting,
    Rotación Defensiva en Crisis, Estructura Temporal VIX/VIX3M (Motor 5) y Meta-Labeling Kelly.
"""

import os
import json
from aegis_quant.data.market_repository import MarketDataRepository
from aegis_quant.indicators.quant_feature_engine import QuantFeatureEngine
from aegis_quant.portfolio.aegis_engine import AegisPortfolioEngine
from aegis_quant.robustness.robustness_analyzer import RobustnessAnalyzer
from aegis_quant.tax.spanish_tax_engine import compute_backtest_tax_waterfall


def run_aegis_backtest() -> dict:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")

    print("=" * 88)
    print("AEGIS-QUANT | MOTOR INSTITUCIONAL ORIENTADO A OBJETOS (2007 - 2026)")
    print("=" * 88)

    repo = MarketDataRepository(data_dir=data_dir)
    raw_universe = repo.load_universe(force_refresh=False, verbose=True)

    feature_engine = QuantFeatureEngine(
        vix_bars=raw_universe["VIX"],
        vix3m_bars=raw_universe["VIX3M"],
    )

    enriched_universe = {}
    for sym, bars in raw_universe.items():
        if sym in ("VIX", "VIX3M"):
            continue
        enriched_universe[sym] = feature_engine.enrich_series(bars)

    engine = AegisPortfolioEngine(enriched_universe=enriched_universe, start_date="2007-01-01")

    mode_1 = engine.simulate_mode(
        mode_id="MODO_1_BASE",
        mode_name="Modo 1: Tactico Conservador (Base Piramide, 1.5% Riesgo)",
        base_risk_pct=1.5,
        max_tactical_weight=0.65,
        max_slots=2,
        use_meta_confidence=False,
        include_motor5=False,
        core_type="NONE",
        overlay_scale=1.0,
    )

    mode_2 = engine.simulate_mode(
        mode_id="MODO_2_SCHERMAN",
        mode_name="Modo 2: Tactico Puro Scherman + VTS (2.5% Riesgo, 80% Liquidez)",
        base_risk_pct=2.5,
        max_tactical_weight=0.55,
        max_slots=3,
        use_meta_confidence=True,
        include_motor5=True,
        core_type="NONE",
        overlay_scale=1.0,
    )

    mode_3_base = engine.simulate_mode(
        mode_id="MODO_3_BASE",
        mode_name="Modo 3 Base: Core S&P 500 (Tendencia) + 4 Motores Tacticos",
        base_risk_pct=2.5,
        max_tactical_weight=0.55,
        max_slots=3,
        use_meta_confidence=False,
        include_motor5=False,
        core_type="SPY_SMA200",
        overlay_scale=1.0,
    )

    mode_3_elite = engine.simulate_mode(
        mode_id="MODO_3_ELITE",
        mode_name="Modo 3 Elite (6 Motores + Dual-Momentum + VolTarget + VIX/VIX3M + TOTM)",
        base_risk_pct=2.5,
        max_tactical_weight=0.55,
        max_slots=3,
        use_meta_confidence=True,
        include_motor5=True,
        core_type="ELITE_PYRAMID",
        overlay_scale=1.0,
        include_motor6=True,
    )

    live_scan = engine.scan_live_market()
    robustness = RobustnessAnalyzer(engine).generate_full_report(mode_3_elite)
    tax_analysis = compute_backtest_tax_waterfall(mode_3_elite)

    summary_payload = {
        "generated_at": live_scan["as_of_date"],
        "benchmark": {
            "name": "S&P 500 Buy & Hold (SPY)",
            "initial_capital": 10000.0,
            "final_equity": mode_3_elite["spy_final_equity"],
            "total_return_pct": mode_3_elite["spy_total_return_pct"],
            "cagr_pct": mode_3_elite["spy_cagr_pct"],
            "max_dd_pct": mode_3_elite["spy_max_dd_pct"],
        },
        "modes": {
            "MODO_1_BASE": mode_1,
            "MODO_2_SCHERMAN": mode_2,
            "MODO_3_BASE": mode_3_base,
            "MODO_3_ELITE": mode_3_elite,
        },
        "robustness": robustness,
        "live_scan": live_scan,
        "tax_analysis": tax_analysis,
    }

    out_path = os.path.join(data_dir, "aegis_backtest_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    print("\n" + "=" * 88)
    print("COMPARATIVA DE ARQUITECTURAS (2007 - 2026 | Capital Inicial: $10,000)")
    print("=" * 88)
    print(
        f"0. Benchmark S&P 500 Buy & Hold : ${mode_3_elite['spy_final_equity']:10,.2f} "
        f"({mode_3_elite['spy_total_return_pct']:+7.2f}%) | CAGR: {mode_3_elite['spy_cagr_pct']:5.2f}% | MaxDD: {mode_3_elite['spy_max_dd_pct']:6.2f}%"
    )
    for m in (mode_1, mode_2, mode_3_base, mode_3_elite):
        print(
            f"- {m['mode_name'][:46]:46s}: ${m['final_equity']:10,.2f} "
            f"({m['total_return_pct']:+8.2f}%) | CAGR: {m['cagr_pct']:5.2f}% | MaxDD: {m['max_dd_pct']:6.2f}% | "
            f"Sharpe: {m['sharpe']:4.2f} | Calmar: {m['calmar']:4.2f}"
        )

    print("\n" + "-" * 88)
    print("DESGLOSE POR MOTOR EN MODO 3 ELITE (5 MOTORES CUANTITATIVOS):")
    print("-" * 88)
    for eng_id, st in mode_3_elite["engine_breakdown"].items():
        print(
            f"  * {st['name']:50s} | Trades: {st['trades']:3d} | "
            f"WinRate: {st['win_rate']:5.1f}% | PF: {st['profit_factor']:4.2f}"
        )

    print("\n" + "-" * 88)
    print("RENDIMIENTO EN ANOS BAJISTAS DEL S&P 500 (CRISIS TEST):")
    print("-" * 88)
    for idx_y, y_el in enumerate(mode_3_elite["yearly"]):
        if y_el["spy_ret_pct"] < 0:
            y_b3 = mode_3_base["yearly"][idx_y]
            y_m2 = mode_2["yearly"][idx_y]
            print(
                f"  Ano {y_el['year']}: S&P 500 = {y_el['spy_ret_pct']:+6.2f}% | "
                f"Modo 2 Tactico = {y_m2['bot_ret_pct']:+6.2f}% | "
                f"Modo 3 Base = {y_b3['bot_ret_pct']:+6.2f}% | "
                f"Modo 3 Elite (Piramide) = {y_el['bot_ret_pct']:+6.2f}%"
            )

    print("\n" + "-" * 88)
    print("PRUEBAS DE ROBUSTEZ INSTITUCIONAL (MODO 3 ELITE):")
    print("-" * 88)
    mc = robustness["monte_carlo"]
    print(
        f"  [Monte Carlo 1,000 Sims | 8% Trades Perdidos] Prob. Batir S&P 500: {mc['prob_beat_sp500_pct']:.1f}% | "
        f"Mediana (P50): ${mc['p50_median']['final_equity']:,.2f} (CAGR {mc['p50_median']['cagr_pct']:.2f}%, DD {mc['p50_median']['median_dd_pct']:.2f}%) | "
        f"Peor 5% (P5): ${mc['p5_pessimistic']['final_equity']:,.2f} (CAGR {mc['p5_pessimistic']['cagr_pct']:.2f}%, DD P95 {mc['p5_pessimistic']['worst_dd_p95_pct']:.2f}%)"
    )
    for fr in robustness["friction_test"]:
        print(
            f"  [Friccion {fr['scenario']:38s}] Capital Final: ${fr['final_equity']:10,.2f} | "
            f"CAGR Neto: {fr['cagr_pct']:5.2f}%"
        )

    return summary_payload


if __name__ == "__main__":
    run_aegis_backtest()
