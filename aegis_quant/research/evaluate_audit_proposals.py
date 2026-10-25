"""
Evaluación Empírica Institucional (2007–2026) de los Nuevos Motores Propuestos en la Auditoría
(`aegis_quant/research/evaluate_audit_proposals.py`).

Evalúa sin sesgo de anticipación (zero lookahead bias) sobre $10,000 iniciales (2007-01-01 a 2026-10-21):
  0. Baseline: Modo 3 Élite actual (M1–M5 + Core Dual-Momentum + VTS)
  1. + M6: Diferencial de Crédito Corporativo (HYG / LQD Z-Score 50d)
  2. + M7 (Filtro): Multiplicador Estacional Turn-of-the-Month (TOTM)
  3. + M7 (Motor Táctico + Overlay): Entrada Táctica Fin de Mes en Pullback Suave + Overlay TOTM
  4. + M8: Prima de Riesgo de Varianza (VRP = VIX^2 - RV20^2)
  5. + M9: Divergencia de Amplitud de Mercado (RSP / SPY Equal-Weight vs Cap-Weight)
  6. Combinación Completa (M6 + M7 + M8 + M9)
"""

import os
import sys
import copy
import math
import calendar
from datetime import date, timedelta
from typing import Dict, List, Set

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from aegis_quant.data.market_repository import MarketDataRepository
from aegis_quant.indicators.quant_feature_engine import QuantFeatureEngine
from aegis_quant.models.market_models import ClosedTrade, EnrichedBar
from aegis_quant.portfolio.aegis_engine import AegisPortfolioEngine
from aegis_quant.risk.meta_kelly_sizer import MetaLabelRiskManager


def business_days_remaining_in_month(iso_date: str) -> int:
    """Días hábiles (lun-vie) restantes en el mes natural (100% determinista y causal)."""
    d = date.fromisoformat(iso_date)
    last_day = calendar.monthrange(d.year, d.month)[1]
    rem = 0
    cur = d + timedelta(days=1)
    end = date(d.year, d.month, last_day)
    while cur <= end:
        if cur.weekday() < 5:
            rem += 1
        cur += timedelta(days=1)
    return rem


def business_day_index_in_month(iso_date: str) -> int:
    """Índice de día hábil (lun-vie) dentro del mes (1 = primer día hábil)."""
    d = date.fromisoformat(iso_date)
    idx = 0
    cur = date(d.year, d.month, 1)
    while cur <= d:
        if cur.weekday() < 5:
            idx += 1
        cur += timedelta(days=1)
    return idx


def is_totm_date(iso_date: str) -> bool:
    """Ventana Turn-of-the-Month (Lakonishok & Smidt 1988): último día hábil a 4º día hábil."""
    return business_days_remaining_in_month(iso_date) <= 1 or business_day_index_in_month(iso_date) <= 4


def compute_ratio_zscore(num_bars, den_bars, window: int = 50) -> Dict[str, float]:
    """Calcula Z-Score rodante de 50 sesiones del ratio HYG / LQD."""
    num_map = {b.date: b.close for b in num_bars}
    den_map = {b.date: b.close for b in den_bars}
    common_dates = sorted(set(num_map.keys()) & set(den_map.keys()))
    ratios = [num_map[d] / den_map[d] for d in common_dates]
    z_by_date: Dict[str, float] = {}
    for i, d in enumerate(common_dates):
        if i < window:
            z_by_date[d] = 0.0
            continue
        w = ratios[i - window + 1 : i + 1]
        mean = sum(w) / len(w)
        std = math.sqrt(sum((x - mean) ** 2 for x in w) / len(w))
        z_by_date[d] = (ratios[i] - mean) / std if std > 1e-9 else 0.0
    return z_by_date


def compute_breadth_exhaustion(rsp_bars, spy_bars) -> Set[str]:
    """Detecta divergencia bajista RSP/SPY cuando SPY marca máximos de 20 sesiones."""
    rsp_map = {b.date: b.close for b in rsp_bars}
    spy_map = {b.date: b.close for b in spy_bars}
    common = sorted(set(rsp_map.keys()) & set(spy_map.keys()))
    ratios = [rsp_map[d] / spy_map[d] for d in common]
    spy_closes = [spy_map[d] for d in common]
    exhaustion_dates: Set[str] = set()
    for i, d in enumerate(common):
        if i < 55:
            continue
        spy_high20 = max(spy_closes[i - 20 : i])
        sma20_now = sum(ratios[i - 19 : i + 1]) / 20.0
        sma20_prev5 = sum(ratios[i - 24 : i - 4]) / 20.0
        sma50_now = sum(ratios[i - 49 : i + 1]) / 50.0
        if spy_closes[i] >= spy_high20 and sma20_now < sma20_prev5 and ratios[i] < sma50_now:
            exhaustion_dates.add(d)
    return exhaustion_dates


def generate_m7_totm_trades(enriched: Dict[str, List[EnrichedBar]], start_date: str = "2007-01-01") -> List[ClosedTrade]:
    """
    Motor 7 Táctico (Turn-of-the-Month Institutional Flow):
    Compra debilidad moderada (RSI(2) < 35) al cierre de fin de mes en tendencia alcista estructural
    (Close > SMA200 y VTS < 0.98) para capturar los flujos automáticos de pensiones/nóminas de T+1..T+4.
    """
    trades: List[ClosedTrade] = []
    for sym in ("QQQ", "SPY"):
        series = enriched[sym]
        in_pos = False
        entry_idx = 0
        entry_bar = None
        stop_price = 0.0
        stop_dist_pct = 0.0
        for i in range(205, len(series)):
            b = series[i]
            if b.date < start_date and not in_pos:
                continue
            if not in_pos:
                if (
                    b.close > b.sma200
                    and b.vts_ratio < 0.98
                    and b.rsi2 < 35.0
                    and business_days_remaining_in_month(b.date) <= 1
                ):
                    in_pos = True
                    entry_idx = i
                    entry_bar = b
                    stop_price = b.close - 2.5 * b.atr14
                    stop_dist_pct = max(1.35, ((b.close - stop_price) / b.close) * 100.0)
            else:
                days = i - entry_idx
                if b.low <= stop_price or days >= 4 or (days >= 2 and b.close > b.sma5):
                    if b.low <= stop_price:
                        exit_px = stop_price if b.open > stop_price else b.open
                        exit_reason = "Stop Loss ATR (2.5x)"
                    else:
                        exit_px = b.close
                        exit_reason = "Target TOTM Fin Ventana / >SMA(5)"
                    raw_ret = ((exit_px - entry_bar.close) / entry_bar.close) * 100.0
                    trades.append(
                        ClosedTrade(
                            engine_id="M7_TOTM",
                            engine_name="Motor 7: Turn-of-the-Month Flow (LONG)",
                            symbol=sym,
                            direction="LONG",
                            entry_date=entry_bar.date,
                            entry_price=round(entry_bar.close, 2),
                            exit_date=b.date,
                            exit_price=round(exit_px, 2),
                            days=days,
                            raw_ret_pct=round(raw_ret, 3),
                            mae_pct=0.0,
                            stop_distance_pct=round(stop_dist_pct, 3),
                            win=raw_ret > 0,
                            entry_reason=f"Fin de mes con RSI(2)={entry_bar.rsi2:.1f}<35 en Contango",
                            exit_reason=exit_reason,
                            meta_confidence=1.15,
                        )
                    )
                    in_pos = False
    return trades


def evaluate_variant(
    engine: AegisPortfolioEngine,
    raw_trades_base: List[ClosedTrade],
    name: str,
    credit_z: Dict[str, float],
    breadth_exh: Set[str],
    use_m6: bool = False,
    use_m7: bool = False,
    use_m8: bool = False,
    use_m9: bool = False,
) -> Dict:
    risk_mgr = MetaLabelRiskManager(
        base_risk_pct=2.5,
        max_tactical_weight=0.55,
        target_vol_pct=16.0,
        use_meta_confidence=True,
    )

    spy_all = engine.universe["SPY"]
    vrp_by_date: Dict[str, float] = {}
    vrp_rebound_dates: Set[str] = set()
    vrp_list = []
    for i, b in enumerate(spy_all):
        vrp = (b.vix_close ** 2) - (b.realized_vol20 ** 2)
        vrp_by_date[b.date] = vrp
        vrp_list.append((b.date, vrp))
        if i >= 5:
            recent_min = min(x[1] for x in vrp_list[i - 5 : i])
            if vrp > 0 and recent_min < 0:
                vrp_rebound_dates.add(b.date)

    mod_trades: List[ClosedTrade] = []
    for orig in raw_trades_base:
        t = copy.deepcopy(orig)
        d = t.entry_date
        if use_m6 and t.engine_id in ("M1_PULLBACK", "M2_VIX_DIV") and credit_z.get(d, 0.0) < -1.5:
            continue
        if use_m7 and t.engine_id in ("M1_PULLBACK", "M5_VOL_CRUSH") and is_totm_date(d):
            t.meta_confidence = round(min(1.35, t.meta_confidence + 0.20), 2)
        if use_m8 and t.engine_id in ("M1_PULLBACK", "M5_VOL_CRUSH") and d in vrp_rebound_dates:
            t.meta_confidence = round(min(1.35, t.meta_confidence + 0.15), 2)
        mod_trades.append(t)

    tactical_trades = engine.filter_and_size_tactical_trades(mod_trades, risk_mgr, max_slots=3)
    trades_by_exit: Dict[str, List[ClosedTrade]] = {}
    for t in tactical_trades:
        trades_by_exit.setdefault(t.exit_date, []).append(t)

    spy_series = [b for b in engine.universe["SPY"] if b.date >= engine.start_date]
    equity = 10000.0
    peak_eq = 10000.0
    max_dd = 0.0
    daily_returns: List[float] = []

    trade_ptr = 0
    open_tactical: List[ClosedTrade] = []

    for idx, spy_bar in enumerate(spy_series):
        d = spy_bar.date
        while trade_ptr < len(tactical_trades) and tactical_trades[trade_ptr].entry_date <= d:
            open_tactical.append(tactical_trades[trade_ptr])
            trade_ptr += 1
        open_tactical = [t for t in open_tactical if t.exit_date >= d]

        active_tactical_weight = min(1.0, sum(t.position_weight for t in open_tactical))
        idle_cash_fraction = max(0.0, 1.0 - active_tactical_weight)
        prev_eq = equity

        core_ret_d = 0.0
        if idx > 0 and idle_cash_fraction > 0.01:
            prev_d = spy_series[idx - 1].date
            prev_bars = {
                sym: engine.date_map[sym][prev_d]
                for sym in engine.universe
                if prev_d in engine.date_map[sym]
            }
            alloc_weights = risk_mgr.compute_elite_core_allocation(
                prev_bars, idle_capital_fraction=idle_cash_fraction
            )
            if use_m7 and is_totm_date(d):
                reg = risk_mgr.classify_regime(prev_bars["SPY"])
                if reg in ("BULL_QUIET_CONTANGO", "BULL_MODERATE_VOL"):
                    cur_sum = sum(alloc_weights.get(s, 0.0) for s in ("SPY", "QQQ"))
                    if 0 < cur_sum < idle_cash_fraction:
                        scale_up = idle_cash_fraction / cur_sum
                        for s in ("SPY", "QQQ"):
                            if s in alloc_weights:
                                alloc_weights[s] = round(alloc_weights[s] * scale_up, 4)
            if use_m6 and credit_z.get(prev_d, 0.0) < -1.5:
                for s in ("SPY", "QQQ"):
                    if s in alloc_weights:
                        alloc_weights[s] = round(alloc_weights[s] * 0.70, 4)
            if use_m8 and vrp_by_date.get(prev_d, 50.0) < 0.0:
                for s in ("SPY", "QQQ"):
                    if s in alloc_weights:
                        alloc_weights[s] = round(alloc_weights[s] * 0.35, 4)
            if use_m9 and prev_d in breadth_exh:
                for s in ("SPY", "QQQ"):
                    if s in alloc_weights:
                        alloc_weights[s] = round(alloc_weights[s] * 0.50, 4)
            for sym, weight in alloc_weights.items():
                core_ret_d += weight * engine.ret_map[sym].get(d, 0.0)

        equity *= (1.0 + core_ret_d)
        if d in trades_by_exit:
            for t in trades_by_exit[d]:
                equity *= (1.0 + t.portfolio_ret_pct / 100.0)

        daily_ret = (equity - prev_eq) / prev_eq if prev_eq > 0 else 0.0
        daily_returns.append(daily_ret)
        if equity > peak_eq:
            peak_eq = equity
        dd = ((equity - peak_eq) / peak_eq) * 100.0
        if dd < max_dd:
            max_dd = dd

    n_years = max(1.0, len(spy_series) / 252.0)
    cagr = ((equity / 10000.0) ** (1.0 / n_years) - 1.0) * 100.0
    mean_d = sum(daily_returns) / len(daily_returns)
    std_d = math.sqrt(sum((r - mean_d) ** 2 for r in daily_returns) / len(daily_returns))
    down_std = math.sqrt(sum(r ** 2 for r in daily_returns if r < 0) / len(daily_returns))
    sharpe = (mean_d / std_d) * math.sqrt(252.0) if std_d > 0 else 0.0
    sortino = (mean_d / down_std) * math.sqrt(252.0) if down_std > 0 else 0.0
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0

    return {
        "name": name,
        "trades": len(tactical_trades),
        "final_equity": round(equity, 2),
        "cagr_pct": round(cagr, 2),
        "max_dd_pct": round(max_dd, 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "calmar": round(calmar, 2),
    }


def run_evaluation(extra_cache_dir: str = None) -> List[Dict]:
    main_repo = MarketDataRepository(data_dir=os.path.join(BASE_DIR, "data"))
    raw_universe = main_repo.load_universe(force_refresh=False, verbose=False)

    extra_dir = extra_cache_dir or os.path.join(BASE_DIR, "data", "research_cache")
    extra_repo = MarketDataRepository(data_dir=extra_dir)
    hyg = extra_repo.fetch_symbol("HYG", start_year=2006)
    lqd = extra_repo.fetch_symbol("LQD", start_year=2006)
    rsp = extra_repo.fetch_symbol("RSP", start_year=2006)

    feat = QuantFeatureEngine(vix_bars=raw_universe["VIX"], vix3m_bars=raw_universe["VIX3M"])
    enriched = {
        sym: feat.enrich_series(bars)
        for sym, bars in raw_universe.items()
        if sym not in ("VIX", "VIX3M")
    }
    engine = AegisPortfolioEngine(enriched_universe=enriched, start_date="2007-01-01")
    base_trades = engine.generate_raw_trades(include_motor5=True)
    m7_trades = sorted(
        base_trades + generate_m7_totm_trades(enriched, "2007-01-01"),
        key=lambda t: (t.entry_date, t.engine_id, t.symbol),
    )

    credit_z = compute_ratio_zscore(hyg, lqd, window=50)
    breadth_exh = compute_breadth_exhaustion(rsp, raw_universe["SPY"])

    results = [
        evaluate_variant(engine, base_trades, "0. Baseline: Modo 3 Elite Actual (M1-M5)", credit_z, breadth_exh),
        evaluate_variant(engine, base_trades, "1. + M6 Credit Spread (HYG/LQD)", credit_z, breadth_exh, use_m6=True),
        evaluate_variant(engine, base_trades, "2. + M7 TOTM (Solo Filtro/Conviccion)", credit_z, breadth_exh, use_m7=True),
        evaluate_variant(engine, m7_trades, "3. + M7 TOTM (Motor Tactico + Overlay)", credit_z, breadth_exh, use_m7=True),
        evaluate_variant(engine, base_trades, "4. + M8 Variance Risk Premium (VRP)", credit_z, breadth_exh, use_m8=True),
        evaluate_variant(engine, base_trades, "5. + M9 Market Breadth (RSP/SPY)", credit_z, breadth_exh, use_m9=True),
        evaluate_variant(engine, base_trades, "6. Combo Completo Filtros (M6+M7+M8+M9)", credit_z, breadth_exh, use_m6=True, use_m7=True, use_m8=True, use_m9=True),
    ]

    print("=" * 116)
    print(f"{'ARQUITECTURA EVALUADA (2007-2026 | $10k)':44s} | {'FINAL ($)':>11s} | {'CAGR':>6s} | {'MAX DD':>7s} | {'SHARPE':>6s} | {'SORTINO':>7s} | {'CALMAR':>6s} | {'TRADES':>6s}")
    print("=" * 116)
    for r in results:
        print(
            f"{r['name']:44s} | ${r['final_equity']:10,.2f} | {r['cagr_pct']:5.2f}% | {r['max_dd_pct']:6.2f}% | "
            f"{r['sharpe']:6.2f} | {r['sortino']:7.2f} | {r['calmar']:6.2f} | {r['trades']:6d}"
        )
    print("=" * 116)
    return results


if __name__ == "__main__":
    run_evaluation()
