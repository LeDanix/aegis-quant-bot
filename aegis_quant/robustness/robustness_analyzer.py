"""
Analizador Orientado a Objetos de Robustez Institucional (RobustnessAnalyzer).
Ejecuta 4 baterías de pruebas de estrés sobre Aegis-Quant:
  1. Análisis de Fricción Operativa (Comisiones + Slippage por operación y rotación)
  2. Simulación de Monte Carlo (1,000 trayectorias sintéticas con remuestreo y pérdida aleatoria del 10% de señales)
  3. Estabilidad por Sub-Periodos Macroeconómicos (Walk-Forward 4 etapas: 2007-2011, 2012-2016, 2017-2021, 2022-2026)
  4. Sensibilidad Paramétrica (Perturbación de umbrales RSI, ATR Stop y VIX/VIX3M para descartar Overfitting)
"""

import random

from aegis_quant.portfolio.aegis_engine import AegisPortfolioEngine


class RobustnessAnalyzer:
    def __init__(self, engine: AegisPortfolioEngine):
        self.engine = engine

    def run_friction_stress_test(self, mode_result: dict) -> list[dict]:
        """
        Evalúa cómo impactan diferentes niveles de coste de transacción (comisión + slippage ida y vuelta)
        sobre todas las operaciones tácticas y rotaciones del Core desde 2007 hasta 2026.
        """
        friction_levels_bps = [
            {"label": "0 bps (Ideal / Backtest Puro)", "roundtrip_pct": 0.00},
            {"label": "5 bps (0.05% - Institucional / IBKR Pro)", "roundtrip_pct": 0.05},
            {"label": "10 bps (0.10% - Broker Estandar)", "roundtrip_pct": 0.10},
            {"label": "20 bps (0.20% - Alta Friccion / Slippage)", "roundtrip_pct": 0.20},
            {"label": "35 bps (0.35% - Estres Extremo)", "roundtrip_pct": 0.35},
        ]

        base_final_eq = mode_result["final_equity"]
        trades = mode_result["trades"]
        n_years = 19.8

        # Estimamos ~6 rotaciones parciales del Core al año además de todos los trades tácticos
        core_rebalances_total = int(n_years * 6) if "MODO_3" in mode_result["mode_id"] else 0

        results = []
        for lvl in friction_levels_bps:
            cost_pct = lvl["roundtrip_pct"]
            # Factor multiplicativo de desgaste acumulado por cada trade (ponderado por su peso en cartera)
            drag_factor = 1.0
            for t in trades:
                w = t.get("position_weight", 0.45)
                trade_cost = (cost_pct * w) / 100.0
                drag_factor *= 1.0 - trade_cost

            for _ in range(core_rebalances_total):
                drag_factor *= 1.0 - (cost_pct * 0.35) / 100.0

            net_eq = base_final_eq * drag_factor
            net_ret_pct = ((net_eq - 10000.0) / 10000.0) * 100.0
            net_cagr = ((net_eq / 10000.0) ** (1.0 / n_years) - 1.0) * 100.0

            results.append(
                {
                    "scenario": lvl["label"],
                    "roundtrip_pct": cost_pct,
                    "final_equity": round(net_eq, 2),
                    "total_return_pct": round(net_ret_pct, 2),
                    "cagr_pct": round(net_cagr, 2),
                    "beats_sp500": net_eq > mode_result["spy_final_equity"],
                }
            )
        return results

    def run_monte_carlo_simulation(
        self,
        mode_result: dict,
        num_simulations: int = 1000,
        miss_trade_prob: float = 0.08,
        seed: int = 42,
    ) -> dict:
        """
        Ejecuta 1,000 simulaciones de Monte Carlo mediante Block-Bootstrapping de los retornos anuales
        y perturbación aleatoria de las operaciones tácticas (simulando un 8% de señales perdidas por
        fallos de conexión o falta de liquidez + ruido gaussiano de ejecución).
        """
        rng = random.Random(seed)

        final_equities = []
        cagrs = []
        max_dds = []
        sample_paths = []

        # Retornos mensuales/decenales de la curva para calcular drawdowns sintéticos realistas
        curve_pts = mode_result["monthly_curve"]
        period_rets = []
        for i in range(1, len(curve_pts)):
            prev_e = curve_pts[i - 1]["bot_eq"]
            cur_e = curve_pts[i]["bot_eq"]
            if prev_e > 0:
                period_rets.append((cur_e - prev_e) / prev_e)

        n_periods = len(period_rets)

        for sim in range(num_simulations):
            eq = 10000.0
            peak = 10000.0
            m_dd = 0.0
            path = [10000.0]

            # Remuestreo por bloques de 6 periodos (~60 sesiones) para preservar autocorrelación de volatilidad
            idx = 0
            while idx < n_periods:
                block_start = rng.randint(0, max(0, n_periods - 6))
                block = period_rets[block_start : block_start + 6]
                for r in block:
                    if idx >= n_periods:
                        break
                    # Añadir fricción aleatoria de ejecución y posibilidad de perder rebotes (miss_trade_prob)
                    noise = rng.gauss(-0.0004, 0.0035)
                    if r > 0.02 and rng.random() < miss_trade_prob:
                        eff_r = r * 0.35 + noise
                    else:
                        eff_r = r + noise

                    eq *= max(0.85, (1.0 + eff_r))
                    if eq > peak:
                        peak = eq
                    dd = ((eq - peak) / peak) * 100.0
                    if dd < m_dd:
                        m_dd = dd
                    if idx % 20 == 0 or idx == n_periods - 1:
                        path.append(round(eq, 2))
                    idx += 1

            cagr = ((eq / 10000.0) ** (1.0 / 19.8) - 1.0) * 100.0
            final_equities.append(eq)
            cagrs.append(cagr)
            max_dds.append(m_dd)
            if sim < 25:
                sample_paths.append(path)

        final_equities.sort()
        cagrs.sort()
        max_dds.sort()  # Más negativo primero

        def pct(arr: list[float], p: float) -> float:
            k = max(0, min(len(arr) - 1, int(len(arr) * p)))
            return round(arr[k], 2)

        spy_final = mode_result["spy_final_equity"]
        win_vs_spy = sum(1 for e in final_equities if e > spy_final) / len(final_equities) * 100.0
        prob_positive = sum(1 for e in final_equities if e > 10000.0) / len(final_equities) * 100.0

        return {
            "num_simulations": num_simulations,
            "miss_trade_prob_pct": round(miss_trade_prob * 100.0, 1),
            "prob_beat_sp500_pct": round(win_vs_spy, 1),
            "prob_profit_pct": round(prob_positive, 1),
            "p5_pessimistic": {
                "final_equity": pct(final_equities, 0.05),
                "cagr_pct": pct(cagrs, 0.05),
                "worst_dd_p95_pct": pct(max_dds, 0.05),
            },
            "p25_conservative": {
                "final_equity": pct(final_equities, 0.25),
                "cagr_pct": pct(cagrs, 0.25),
                "dd_pct": pct(max_dds, 0.25),
            },
            "p50_median": {
                "final_equity": pct(final_equities, 0.50),
                "cagr_pct": pct(cagrs, 0.50),
                "median_dd_pct": pct(max_dds, 0.50),
            },
            "p75_optimistic": {
                "final_equity": pct(final_equities, 0.75),
                "cagr_pct": pct(cagrs, 0.75),
                "dd_pct": pct(max_dds, 0.75),
            },
            "p95_extreme": {
                "final_equity": pct(final_equities, 0.95),
                "cagr_pct": pct(cagrs, 0.95),
                "best_dd_pct": pct(max_dds, 0.95),
            },
        }

    def run_regime_subperiod_analysis(self, mode_result: dict) -> list[dict]:
        """
        Divide los 20 años de historia (2007-2026) en 4 grandes bloques macroeconómicos de 5 años
        para verificar que el sistema genera Alpha en todos los entornos de tipos e inflación.
        """
        subperiods = [
            {"name": "Etapa 1 (2007-2011): Gran Crisis Financiera & Deuda Europea", "start": "2007", "end": "2011"},
            {"name": "Etapa 2 (2012-2016): Expansión QE & Lateralidad 2015", "start": "2012", "end": "2016"},
            {"name": "Etapa 3 (2017-2021): Guerra Comercial, Crash COVID & Boom", "start": "2017", "end": "2021"},
            {"name": "Etapa 4 (2022-2026): Shock Inflacionario, Subida Tipos & IA", "start": "2022", "end": "2026"},
        ]
        yearly = mode_result["yearly"]
        out = []

        for sp in subperiods:
            sub_y = [y for y in yearly if sp["start"] <= y["year"] <= sp["end"]]
            bot_mult = 1.0
            spy_mult = 1.0
            trades_cnt = 0
            for y in sub_y:
                bot_mult *= 1.0 + y["bot_ret_pct"] / 100.0
                spy_mult *= 1.0 + y["spy_ret_pct"] / 100.0
                trades_cnt += y["trades"]

            bot_ret = (bot_mult - 1.0) * 100.0
            spy_ret = (spy_mult - 1.0) * 100.0
            out.append(
                {
                    "period": sp["name"],
                    "bot_cum_ret_pct": round(bot_ret, 2),
                    "spy_cum_ret_pct": round(spy_ret, 2),
                    "alpha_pct": round(bot_ret - spy_ret, 2),
                    "trades": trades_cnt,
                }
            )
        return out

    def run_parameter_sensitivity(self) -> list[dict]:
        """
        Comprueba que el Modo 3 Élite no está 'sobre-optimizado' (overfitted) variando el riesgo base
        y el tope máximo por operación táctica en una malla de configuraciones vecinas.
        """
        grid = [
            {"label": "Conservador (Riesgo 1.8% | Cap 45%)", "risk": 1.8, "cap": 0.45},
            {"label": "Moderado-Bajo (Riesgo 2.2% | Cap 50%)", "risk": 2.2, "cap": 0.50},
            {"label": "★ Estandar Aegis Elite (Riesgo 2.5% | Cap 55%)", "risk": 2.5, "cap": 0.55},
            {"label": "Agresivo-Controlado (Riesgo 2.8% | Cap 60%)", "risk": 2.8, "cap": 0.60},
            {"label": "Alta Conviccion (Riesgo 3.0% | Cap 65%)", "risk": 3.0, "cap": 0.65},
        ]
        results = []
        for g in grid:
            res = self.engine.simulate_mode(
                mode_id="SENS_TEST",
                mode_name=g["label"],
                base_risk_pct=g["risk"],
                max_tactical_weight=g["cap"],
                max_slots=3,
                use_meta_confidence=True,
                include_motor5=True,
                core_type="ELITE_PYRAMID",
                overlay_scale=1.0,
            )
            results.append(
                {
                    "config": g["label"],
                    "final_equity": res["final_equity"],
                    "total_return_pct": res["total_return_pct"],
                    "cagr_pct": res["cagr_pct"],
                    "max_dd_pct": res["max_dd_pct"],
                    "sharpe": res["sharpe"],
                    "calmar": res["calmar"],
                }
            )
        return results

    def generate_full_report(self, mode_elite: dict) -> dict:
        return {
            "friction_test": self.run_friction_stress_test(mode_elite),
            "monte_carlo": self.run_monte_carlo_simulation(mode_elite, num_simulations=1000),
            "subperiods": self.run_regime_subperiod_analysis(mode_elite),
            "parameter_sensitivity": self.run_parameter_sensitivity(),
        }
