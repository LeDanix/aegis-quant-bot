"""
Motor Orientado a Objetos de Simulación de Cartera y Orquestación Multi-Estrategia (AegisPortfolioEngine).
Permite ejecutar y comparar en igualdad de condiciones (2007-2026):
  1. Benchmark S&P 500 Buy & Hold (SPY)
  2. Modo 1: Táctico Conservador (1.5% Riesgo, Base de la Pirámide)
  3. Modo 2: Táctico Puro Scherman (2.5% Riesgo + Meta-Labeling + 5 Motores, ~80% Liquidez)
  4. Modo 3 Base: Prioridad Táctica + Liquidez Ociosa en Core S&P 500 (Tendencia Limpia)
  5. Modo 3 Élite (Cúspide de la Pirámide): Prioridad Táctica (5 Motores con VIX/VIX3M Vol-Crush
     y Meta-Labeling Kelly) + Liquidez Ociosa en Core Dual-Momentum con Volatility Targeting.
"""

import copy
import math
from typing import Any, Dict, List, Optional
from aegis_quant.models.market_models import EnrichedBar, ClosedTrade, TradeSignal
from aegis_quant.strategies.base import OPEN_TRADE_EXIT_DATE
from aegis_quant.strategies.m6_totm_flow import is_totm_window
from aegis_quant.strategies.strategies import (
    BaseStrategy,
    SchermanPullbackStrategy,
    SchermanVixDivergenceStrategy,
    BearMarketShortStrategy,
    CommodityBreakoutCTAStrategy,
    VolTermStructureCrushStrategy,
    TurnOfTheMonthFlowStrategy,
)
from aegis_quant.risk.meta_kelly_sizer import MetaLabelRiskManager


class AegisPortfolioEngine:
    def __init__(self, enriched_universe: Dict[str, List[EnrichedBar]], start_date: str = "2007-01-01"):
        self.universe = enriched_universe
        self.start_date = start_date

        self.date_map: Dict[str, Dict[str, EnrichedBar]] = {}
        self.ret_map: Dict[str, Dict[str, float]] = {}

        for sym, series in self.universe.items():
            self.date_map[sym] = {}
            self.ret_map[sym] = {}
            for i, b in enumerate(series):
                self.date_map[sym][b.date] = b
                if i > 0:
                    self.ret_map[sym][b.date] = (b.close - series[i - 1].close) / series[i - 1].close
                else:
                    self.ret_map[sym][b.date] = 0.0

        # Instanciar los 6 motores cuantitativos OOP
        self.m1_pullback = SchermanPullbackStrategy()
        self.m2_vix_div = SchermanVixDivergenceStrategy()
        self.m3_bear_short = BearMarketShortStrategy()
        self.m4_cta_trend = CommodityBreakoutCTAStrategy()
        self.m5_vol_crush = VolTermStructureCrushStrategy()
        self.m6_totm = TurnOfTheMonthFlowStrategy()

        self.all_strategies: List[BaseStrategy] = [
            self.m1_pullback,
            self.m2_vix_div,
            self.m3_bear_short,
            self.m4_cta_trend,
            self.m5_vol_crush,
            self.m6_totm,
        ]

    def generate_raw_trades(
        self,
        include_motor5: bool = True,
        include_open: bool = False,
        enabled_motors: Optional[Dict[str, bool]] = None,
        include_motor6: Optional[bool] = None,
    ) -> List[ClosedTrade]:
        raw: List[ClosedTrade] = []
        en = enabled_motors or {}
        if include_motor6 is None:
            include_motor6 = include_motor5

        def _is_on(engine_id: str) -> bool:
            return bool(en.get(engine_id, True))

        totm_enabled = bool(include_motor6 and _is_on("M6_TOTM"))

        for eq_sym in ("SPY", "QQQ"):
            if eq_sym in self.universe:
                if _is_on("M1_PULLBACK"):
                    raw.extend(
                        self.m1_pullback.simulate(
                            eq_sym, self.universe[eq_sym], self.start_date, include_open=include_open
                        )
                    )
                if _is_on("M2_VIX_DIV"):
                    raw.extend(
                        self.m2_vix_div.simulate(
                            eq_sym, self.universe[eq_sym], self.start_date, include_open=include_open
                        )
                    )
                if _is_on("M3_BEAR_SHORT"):
                    raw.extend(
                        self.m3_bear_short.simulate(
                            eq_sym, self.universe[eq_sym], self.start_date, include_open=include_open
                        )
                    )
                if include_motor5 and _is_on("M5_VOL_CRUSH"):
                    raw.extend(
                        self.m5_vol_crush.simulate(
                            eq_sym, self.universe[eq_sym], self.start_date, include_open=include_open
                        )
                    )

        if totm_enabled:
            for eq_sym in ("QQQ", "SPY"):
                if eq_sym in self.universe:
                    raw.extend(
                        self.m6_totm.simulate(
                            eq_sym, self.universe[eq_sym], self.start_date, include_open=include_open
                        )
                    )
            for t in raw:
                if t.engine_id in ("M1_PULLBACK", "M5_VOL_CRUSH") and is_totm_window(t.entry_date):
                    t.meta_confidence = round(min(1.35, t.meta_confidence + 0.20), 2)

        if _is_on("M4_CTA_TREND"):
            for cta_sym in ("GLD", "USO", "ZS", "TLT", "BTC"):
                if cta_sym in self.universe:
                    raw.extend(
                        self.m4_cta_trend.simulate(
                            cta_sym, self.universe[cta_sym], self.start_date, include_open=include_open
                        )
                    )

        raw.sort(key=lambda t: (t.entry_date, t.engine_id, t.symbol))
        return raw

    def filter_and_size_tactical_trades(
        self,
        raw_trades: List[ClosedTrade],
        risk_manager: MetaLabelRiskManager,
        max_slots: int = 3,
    ) -> List[ClosedTrade]:
        accepted: List[ClosedTrade] = []
        active: List[ClosedTrade] = []

        for orig in raw_trades:
            t = copy.deepcopy(orig)
            active = [a for a in active if a.exit_date > t.entry_date]
            if any(a.symbol == t.symbol for a in active):
                continue
            if len(active) >= max_slots:
                continue

            used_weight = sum(a.position_weight for a in active)
            avail_weight = round(max(0.0, 1.0 - used_weight), 4)
            if avail_weight < 0.15:
                continue

            desired_w = risk_manager.compute_tactical_weight(
                t.stop_distance_pct, t.meta_confidence, engine_id=t.engine_id, symbol=t.symbol
            )
            w = round(min(desired_w, avail_weight), 4)
            t.position_weight = w
            t.portfolio_ret_pct = round(t.raw_ret_pct * w, 3)
            t.portfolio_mae_pct = round(t.mae_pct * w, 3)

            active.append(t)
            accepted.append(t)

        return accepted

    def simulate_mode(
        self,
        mode_id: str,
        mode_name: str,
        base_risk_pct: float,
        max_tactical_weight: float,
        max_slots: int,
        use_meta_confidence: bool,
        include_motor5: bool,
        core_type: str,  # 'NONE' | 'SPY_SMA200' | 'ELITE_PYRAMID'
        overlay_scale: float = 1.0,
        include_motor6: Optional[bool] = None,
    ) -> Dict:
        if include_motor6 is None:
            include_motor6 = include_motor5 and core_type == "ELITE_PYRAMID"

        risk_mgr = MetaLabelRiskManager(
            base_risk_pct=base_risk_pct,
            max_tactical_weight=max_tactical_weight,
            target_vol_pct=16.0,
            use_meta_confidence=use_meta_confidence,
        )
        raw_trades = self.generate_raw_trades(
            include_motor5=include_motor5,
            include_motor6=include_motor6,
        )
        tactical_trades = self.filter_and_size_tactical_trades(raw_trades, risk_mgr, max_slots=max_slots)

        trades_by_exit: Dict[str, List[ClosedTrade]] = {}
        for t in tactical_trades:
            trades_by_exit.setdefault(t.exit_date, []).append(t)

        spy_series = [b for b in self.universe["SPY"] if b.date >= self.start_date]

        equity = 10000.0
        peak_eq = 10000.0
        max_dd = 0.0

        spy_bh_eq = 10000.0
        spy_bh_peak = 10000.0
        spy_bh_max_dd = 0.0
        first_spy_close = spy_series[0].close

        yearly_stats: Dict[str, Dict] = {}
        monthly_curve: List[Dict] = []
        daily_returns: List[float] = []
        equity_by_date: Dict[str, float] = {}
        spy_eq_by_date: Dict[str, float] = {}
        pnl_by_engine: Dict[str, float] = {}
        trade_pnl_usd: Dict[int, float] = {}

        # Puntero eficiente para saber qué operaciones tácticas están abiertas cada día
        trade_ptr = 0
        open_tactical: List[ClosedTrade] = []

        for idx, spy_bar in enumerate(spy_series):
            d = spy_bar.date
            yr = d[:4]
            if yr not in yearly_stats:
                yearly_stats[yr] = {
                    "start_eq": equity,
                    "end_eq": equity,
                    "spy_start": spy_bar.close,
                    "spy_end": spy_bar.close,
                    "trades": 0,
                    "wins": 0,
                }

            # Actualizar lista de operaciones tácticas activas hoy (incluyendo el día de salida, pues el capital estuvo ocupado esa sesión)
            while trade_ptr < len(tactical_trades) and tactical_trades[trade_ptr].entry_date <= d:
                open_tactical.append(tactical_trades[trade_ptr])
                trade_ptr += 1
            open_tactical = [t for t in open_tactical if t.exit_date >= d]

            active_tactical_weight = min(1.0, sum(t.position_weight for t in open_tactical))
            idle_cash_fraction = max(0.0, 1.0 - active_tactical_weight)

            prev_eq = equity

            # 1. Rendimiento del Capital Ocioso en el Core (Anti-Cash-Drag en Mercados Alcistas)
            core_ret_d = 0.0
            if idx > 0 and idle_cash_fraction > 0.01:
                prev_d = spy_series[idx - 1].date
                if core_type == "SPY_SMA200":
                    prev_spy = self.date_map["SPY"][prev_d]
                    # Filtro de tendencia alcista limpia para evitar whipsaws en mercados bajistas
                    if (
                        prev_spy.close > prev_spy.sma200
                        and prev_spy.sma50 > prev_spy.sma200
                        and prev_spy.close > prev_spy.sma50
                        and prev_spy.vix_close < 21.0
                    ):
                        core_ret_d = (idle_cash_fraction * 0.70) * self.ret_map["SPY"].get(d, 0.0)
                elif core_type == "ELITE_PYRAMID":
                    prev_bars = {
                        sym: self.date_map[sym][prev_d]
                        for sym in self.universe
                        if prev_d in self.date_map[sym]
                    }
                    alloc_weights = risk_mgr.compute_elite_core_allocation(
                        prev_bars,
                        idle_capital_fraction=idle_cash_fraction,
                        totm_boost=bool(include_motor6 and is_totm_window(d)),
                    )
                    for sym, weight in alloc_weights.items():
                        core_ret_d += weight * self.ret_map[sym].get(d, 0.0)

            equity *= (1.0 + core_ret_d)

            # 2. Rendimiento de los Motores Tácticos (Prioridad #1) cerrados hoy
            if d in trades_by_exit:
                for t in trades_by_exit[d]:
                    eff_ret = t.portfolio_ret_pct * overlay_scale
                    pnl_usd = equity * (eff_ret / 100.0)
                    equity += pnl_usd
                    pnl_by_engine[t.engine_id] = pnl_by_engine.get(t.engine_id, 0.0) + pnl_usd
                    trade_pnl_usd[id(t)] = round(pnl_usd, 2)
                    yearly_stats[yr]["trades"] += 1
                    if t.win:
                        yearly_stats[yr]["wins"] += 1

            daily_ret = (equity - prev_eq) / prev_eq if prev_eq > 0 else 0.0
            daily_returns.append(daily_ret)

            if equity > peak_eq:
                peak_eq = equity
            dd = ((equity - peak_eq) / peak_eq) * 100.0
            if dd < max_dd:
                max_dd = dd

            # S&P 500 Buy & Hold
            spy_bh_eq = 10000.0 * (spy_bar.close / first_spy_close)
            if spy_bh_eq > spy_bh_peak:
                spy_bh_peak = spy_bh_eq
            s_dd = ((spy_bh_eq - spy_bh_peak) / spy_bh_peak) * 100.0
            if s_dd < spy_bh_max_dd:
                spy_bh_max_dd = s_dd

            yearly_stats[yr]["end_eq"] = equity
            yearly_stats[yr]["spy_end"] = spy_bar.close
            equity_by_date[d] = round(equity, 2)
            spy_eq_by_date[d] = round(spy_bh_eq, 2)

            if idx % 3 == 0 or idx == len(spy_series) - 1:
                monthly_curve.append({
                    "date": d,
                    "bot_eq": round(equity, 2),
                    "bot_dd": round(dd, 2),
                    "spy_eq": round(spy_bh_eq, 2),
                    "spy_dd": round(s_dd, 2),
                    "vix": spy_bar.vix_close,
                    "vts": spy_bar.vts_ratio,
                })

        # Métricas institucionales globales
        total_ret_pct = ((equity - 10000.0) / 10000.0) * 100.0
        spy_total_ret_pct = ((spy_bh_eq - 10000.0) / 10000.0) * 100.0
        n_years = max(1.0, len(spy_series) / 252.0)
        cagr_pct = ((equity / 10000.0) ** (1.0 / n_years) - 1.0) * 100.0
        spy_cagr_pct = ((spy_bh_eq / 10000.0) ** (1.0 / n_years) - 1.0) * 100.0

        mean_d = sum(daily_returns) / len(daily_returns)
        std_d = math.sqrt(sum((r - mean_d) ** 2 for r in daily_returns) / len(daily_returns))
        downside_rets = [r for r in daily_returns if r < 0]
        down_std_d = math.sqrt(sum(r ** 2 for r in downside_rets) / max(1, len(daily_returns)))

        sharpe = (mean_d / std_d) * math.sqrt(252.0) if std_d > 0 else 0.0
        sortino = (mean_d / down_std_d) * math.sqrt(252.0) if down_std_d > 0 else 0.0
        calmar = cagr_pct / abs(max_dd) if max_dd < 0 else 0.0

        yearly_list = []
        positive_years = 0
        bear_years_beaten = 0
        total_bear_years = 0
        for yr in sorted(yearly_stats.keys()):
            st = yearly_stats[yr]
            b_ret = ((st["end_eq"] - st["start_eq"]) / st["start_eq"]) * 100.0
            s_ret = ((st["spy_end"] - st["spy_start"]) / st["spy_start"]) * 100.0
            if b_ret > 0:
                positive_years += 1
            if s_ret < 0:
                total_bear_years += 1
                if b_ret > s_ret:
                    bear_years_beaten += 1
            yearly_list.append({
                "year": yr,
                "bot_ret_pct": round(b_ret, 2),
                "spy_ret_pct": round(s_ret, 2),
                "alpha_pct": round(b_ret - s_ret, 2),
                "trades": st["trades"],
                "win_rate": round((st["wins"] / st["trades"] * 100.0), 1) if st["trades"] > 0 else 0.0,
                "end_eq": round(st["end_eq"], 2),
            })

        engine_breakdown = {}
        for strat in self.all_strategies:
            sub = [t for t in tactical_trades if t.engine_id == strat.engine_id]
            if not sub:
                continue
            wins = [t for t in sub if t.win]
            losses = [t for t in sub if not t.win]
            gp = sum(t.portfolio_ret_pct for t in wins)
            gl = abs(sum(t.portfolio_ret_pct for t in losses))
            engine_breakdown[strat.engine_id] = {
                "name": strat.engine_name,
                "trades": len(sub),
                "win_rate": round(len(wins) / len(sub) * 100.0, 2),
                "profit_factor": round(gp / gl, 2) if gl > 0 else 99.0,
                "avg_ret_pct": round(sum(t.portfolio_ret_pct for t in sub) / len(sub), 2),
                "sum_ret_pct": round(sum(t.portfolio_ret_pct for t in sub), 2),
                "total_pnl_usd": round(pnl_by_engine.get(strat.engine_id, 0.0), 2),
            }

        total_wins = sum(1 for t in tactical_trades if t.win)
        gp_all = sum(t.portfolio_ret_pct for t in tactical_trades if t.win)
        gl_all = abs(sum(t.portfolio_ret_pct for t in tactical_trades if not t.win))

        trades_serialized = []
        for t in tactical_trades:
            td = t.to_dict()
            td["pnl_usd"] = trade_pnl_usd.get(id(t), 0.0)
            td["eq_at_exit"] = equity_by_date.get(t.exit_date, round(equity, 2))
            td["spy_eq_at_exit"] = spy_eq_by_date.get(t.exit_date, round(spy_bh_eq, 2))
            trades_serialized.append(td)

        return {
            "mode_id": mode_id,
            "mode_name": mode_name,
            "total_trades": len(tactical_trades),
            "win_rate": round((total_wins / len(tactical_trades) * 100.0), 2) if tactical_trades else 0.0,
            "profit_factor": round(gp_all / gl_all, 2) if gl_all > 0 else 99.0,
            "initial_capital": 10000.0,
            "final_equity": round(equity, 2),
            "total_return_pct": round(total_ret_pct, 2),
            "cagr_pct": round(cagr_pct, 2),
            "max_dd_pct": round(max_dd, 2),
            "sharpe": round(sharpe, 2),
            "sortino": round(sortino, 2),
            "calmar": round(calmar, 2),
            "positive_years": positive_years,
            "total_years": len(yearly_list),
            "bear_years_beaten": bear_years_beaten,
            "total_bear_years": total_bear_years,
            "spy_final_equity": round(spy_bh_eq, 2),
            "spy_total_return_pct": round(spy_total_ret_pct, 2),
            "spy_cagr_pct": round(spy_cagr_pct, 2),
            "spy_max_dd_pct": round(spy_bh_max_dd, 2),
            "yearly": yearly_list,
            "monthly_curve": monthly_curve,
            "engine_breakdown": engine_breakdown,
            "trades": trades_serialized,
        }

    def scan_live_market(self, enabled_motors: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        latest_bars = {sym: series[-1] for sym, series in self.universe.items() if series}
        spy = latest_bars["SPY"]
        risk_mgr = MetaLabelRiskManager()
        regime = risk_mgr.classify_regime(spy)
        en = enabled_motors or {}
        totm_on = bool(en.get("M6_TOTM", True) and is_totm_window(spy.date))
        core_alloc = risk_mgr.compute_elite_core_allocation(
            latest_bars, idle_capital_fraction=1.0, totm_boost=totm_on
        )

        signals: List[TradeSignal] = []
        for eq_sym in ("SPY", "QQQ"):
            if eq_sym not in self.universe:
                continue
            for strat in (
                self.m1_pullback,
                self.m2_vix_div,
                self.m3_bear_short,
                self.m5_vol_crush,
                self.m6_totm,
            ):
                if not en.get(strat.engine_id, True):
                    continue
                sig = strat.evaluate_live(eq_sym, self.universe[eq_sym])
                if sig:
                    signals.append(sig)

        if en.get("M4_CTA_TREND", True):
            for cta_sym in ("GLD", "USO", "ZS", "TLT", "BTC"):
                if cta_sym not in self.universe:
                    continue
                sig = self.m4_cta_trend.evaluate_live(cta_sym, self.universe[cta_sym])
                if sig:
                    signals.append(sig)

        asset_snapshots = []
        for sym, b in latest_bars.items():
            if sym in ("VIX", "VIX3M"):
                continue
            asset_snapshots.append({
                "symbol": sym,
                "date": b.date,
                "close": round(b.close, 2),
                "last_close": round(b.close, 2),
                "sma50": round(b.sma50, 2),
                "sma200": round(b.sma200, 2),
                "rsi2": round(b.rsi2, 1),
                "realized_vol20": round(b.realized_vol20, 1),
                "mom60_vol_adj": round(b.mom60_vol_adj, 2),
                "core_weight_pct": round(core_alloc.get(sym, 0.0) * 100.0, 1),
                "trend": "ALCISTA" if b.close > b.sma200 else "BAJISTA",
                "sma200_trend": "BULL" if b.close > b.sma200 else "BEAR",
            })

        return {
            "as_of_date": spy.date,
            "regime": regime,
            "vix_close": spy.vix_close,
            "vix3m_close": spy.vix3m_close,
            "vts_ratio": spy.vts_ratio,
            "vts_state": "CONTANGO (Normal / Alcista)" if spy.vts_ratio < 1.0 else "BACKWARDATION (Alerta Institucional)",
            "core_allocation": {k: round(v * 100.0, 1) for k, v in core_alloc.items()},
            "assets": asset_snapshots,
            "active_signals": [sig.__dict__ for sig in signals],
        }

    def compute_live_portfolio(
        self,
        enabled_motors: Optional[Dict[str, bool]] = None,
        base_risk_pct: float = 2.5,
        max_fast_weight: float = 0.55,
        max_cta_weight: float = 0.40,
        max_slots: int = 3,
    ) -> Dict[str, Any]:
        """
        Evalúa en vivo los 6 motores tácticos (incluyendo tanto señales disparadas hoy
        como operaciones multisesión abiertas en días previos que aún no han alcanzado
        su objetivo/stop) y asigna el capital ocioso restante al Core Modo 3 Élite.
        """
        en = enabled_motors if enabled_motors is not None else {}
        risk_mgr = MetaLabelRiskManager(
            base_risk_pct=base_risk_pct,
            max_tactical_weight=max_fast_weight,
            target_vol_pct=16.0,
            use_meta_confidence=True,
            max_cta_weight=max_cta_weight,
        )

        raw_trades = self.generate_raw_trades(
            include_motor5=bool(en.get("M5_VOL_CRUSH", True)),
            include_open=True,
            enabled_motors=en,
            include_motor6=bool(en.get("M6_TOTM", True)),
        )
        sized_trades = self.filter_and_size_tactical_trades(
            raw_trades, risk_mgr, max_slots=max_slots
        )
        open_tactical = [t for t in sized_trades if t.exit_date == OPEN_TRADE_EXIT_DATE]

        active_tactical_weight = min(1.0, sum(t.position_weight for t in open_tactical))
        idle_cash_fraction = round(max(0.0, 1.0 - active_tactical_weight), 4)

        latest_bars = {sym: series[-1] for sym, series in self.universe.items() if series}
        spy_date = latest_bars["SPY"].date if "SPY" in latest_bars else "2026-01-15"
        totm_on = bool(en.get("M6_TOTM", True) and is_totm_window(spy_date))
        core_alloc = risk_mgr.compute_elite_core_allocation(
            latest_bars, idle_capital_fraction=idle_cash_fraction, totm_boost=totm_on
        )
        live_scan = self.scan_live_market(enabled_motors=en)
        # Actualizar core_allocation efectivo tras descontar capital ocupado por tácticos
        live_scan["core_allocation"] = {k: round(v * 100.0, 1) for k, v in core_alloc.items()}

        targets: Dict[str, Dict[str, Any]] = {}
        for t in open_tactical:
            targets[t.symbol] = {
                "weight": round(t.position_weight, 4),
                "direction": t.direction,
                "motor": t.engine_id,
                "reason": f"{t.engine_name}: {t.entry_reason} (entrada {t.entry_date})",
            }

        for sym, w in core_alloc.items():
            if w <= 0.001:
                continue
            if sym not in targets:
                targets[sym] = {
                    "weight": round(w, 4),
                    "direction": "LONG",
                    "motor": "CORE_BULL",
                    "reason": f"Nucleo Inteligente Modo 3 Elite ({live_scan['vts_state']})",
                }
            elif targets[sym]["direction"] == "LONG":
                targets[sym]["weight"] = round(min(1.0, targets[sym]["weight"] + w), 4)
                targets[sym]["motor"] = f"{targets[sym]['motor']}+CORE"
                targets[sym]["reason"] = (
                    f"{targets[sym]['reason']} + Core Modo 3 ({round(w * 100.0, 1)}%)"
                )

        # Garantizar que la suma total de pesos jamás supere el 100% (0% margen/deuda)
        total_w = sum(item["weight"] for item in targets.values())
        if total_w > 1.0001:
            for item in targets.values():
                item["weight"] = round(item["weight"] / total_w, 4)

        open_trades_payload = [
            {
                "engine_id": t.engine_id,
                "engine_name": t.engine_name,
                "symbol": t.symbol,
                "direction": t.direction,
                "entry_date": t.entry_date,
                "entry_price": t.entry_price,
                "current_price": t.exit_price,
                "unrealized_ret_pct": round(t.raw_ret_pct, 2),
                "stop_distance_pct": round(t.stop_distance_pct, 2),
                "weight_pct": round(t.position_weight * 100.0, 1),
                "days_held": t.days,
                "reason": t.entry_reason,
            }
            for t in open_tactical
        ]

        tactical_summary = {
            "data_as_of": live_scan["as_of_date"],
            "regime": live_scan["regime"],
            "vts_ratio": live_scan["vts_ratio"],
            "vts_state": live_scan["vts_state"],
            "idle_cash_pct": round(idle_cash_fraction * 100.0, 1),
            "open_trades": open_trades_payload,
            "signals_today": live_scan["active_signals"],
            "core_allocation": live_scan["core_allocation"],
            "target_weights": {k: round(v["weight"] * 100.0, 1) for k, v in targets.items()},
        }

        return {
            "targets": targets,
            "live_scan": live_scan,
            "tactical": tactical_summary,
        }
