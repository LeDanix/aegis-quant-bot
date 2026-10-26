"""
Motor 6: Turn-of-the-Month Institutional Cashflow Strategy (aegis_quant/strategies/m6_totm_flow.py).

Quantitative & Academic Foundation:
-----------------------------------
- Origin & Literature: Lakonishok & Smidt (1988, Review of Financial Studies, "Are Seasonal
  Anomalies Real? A Ninety-Year Perspective") and McConnell & Xu (2008, Financial Analysts Journal,
  "Equity Returns at the Turn of the Month").
- Core Structural Mechanism: Unlike technical patterns that decay when crowded, the Turn-of-the-Month
  (TOTM) premium is driven by structural, non-discretionary institutional cashflows: bi-weekly/monthly
  payroll deductions, automatic 401(k)/pension contributions, dividend reinvestments, and institutional
  month-end mandate allocations concentrated between the final trading session of month M (T-1..T0)
  and the first 4 trading sessions of month M+1 (T+1..T+4).
- Selective Alpha Filter: Entering blindly every month dilutes edge. Motor 6 demands a confluence of:
  1. Primary secular uptrend (Close > SMA 200).
  2. Healthy Contango volatility term structure (VIX/VIX3M < 0.98 — no systemic credit stress).
  3. Mild end-of-month pullback/consolidation (RSI(2) < 35.0) during the final 1–2 business days
     of the month, buying discounted inventory right before programmatic T+1..T+4 inflows arrive.

Execution Parameters:
- Direction: LONG
- Target Assets: QQQ, SPY
- Entry Trigger: Business days remaining in month <= 1, Close > SMA(200), VTS < 0.98, RSI(2) < 35.0
- Stop Loss: 2.5x ATR(14) (min 1.35%)
- Profit Target: Mean reversion above SMA(5) after >= 2 sessions, or completion of T+4 TOTM window
"""

import calendar
from datetime import date, timedelta
from typing import List, Optional, Tuple

from aegis_quant.models.market_models import ClosedTrade, EnrichedBar, TradeSignal
from aegis_quant.strategies.base import BaseStrategy


def business_days_remaining_in_month(iso_date: str) -> int:
    """Returns weekday sessions (Mon-Fri) strictly remaining after `iso_date` in the same month."""
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
    """Returns the 1-based weekday index (Mon-Fri) within `iso_date`'s calendar month."""
    d = date.fromisoformat(iso_date)
    idx = 0
    cur = date(d.year, d.month, 1)
    while cur <= d:
        if cur.weekday() < 5:
            idx += 1
        cur += timedelta(days=1)
    return idx


def is_totm_window(iso_date: str) -> bool:
    """True during the institutional Turn-of-the-Month window (last 2 weekdays to 4th weekday)."""
    return business_days_remaining_in_month(iso_date) <= 1 or business_day_index_in_month(iso_date) <= 4


class TurnOfTheMonthFlowStrategy(BaseStrategy):
    """
    Motor 6: Turn-of-the-Month Institutional Cashflow (LONG).
    Captures programmatic pension/payroll inflows at month-end pullbacks in Contango regimes.
    """

    def __init__(self):
        super().__init__(
            engine_id="M6_TOTM",
            engine_name="Motor 6: Turn-of-the-Month Institutional Flow (LONG)",
            category="calendar_institutional_flow",
        )

    def _check_entry(self, b: EnrichedBar) -> Tuple[bool, str]:
        """Evaluates deterministic end-of-month institutional flow setup."""
        if b.atr14 <= 0:
            return False, ""

        rem_bdays = business_days_remaining_in_month(b.date)
        if (
            rem_bdays <= 1
            and b.close > b.sma200
            and b.vts_ratio < 0.98
            and b.rsi2 < 35.0
        ):
            reason = (
                f"Flujo Institucional Fin de Mes (T-{rem_bdays}d) con RSI(2)={b.rsi2:.1f}<35 "
                f"en Contango (VTS={b.vts_ratio:.2f})"
            )
            return True, reason

        return False, ""

    def _calculate_stops(self, b: EnrichedBar) -> Tuple[float, float]:
        """Calculates 2.5x ATR(14) stop loss with 1.35% floor."""
        stop_price = b.close - 2.5 * b.atr14
        stop_dist_pct = max(1.35, ((b.close - stop_price) / b.close) * 100.0)
        return stop_price, stop_dist_pct

    def _check_exit(
        self, b: EnrichedBar, days: int, stop_price: float
    ) -> Tuple[bool, float, str]:
        """Checks stop loss, SMA(5) impulse target after T+2, or T+4 window completion."""
        if b.low <= stop_price:
            exit_px = stop_price if b.open > stop_price else b.open
            return True, exit_px, "Stop Loss TOTM (2.5x ATR)"

        if days >= 2 and b.close > b.sma5:
            return True, b.close, "Target TOTM: Impulso sobre SMA(5)"

        if days >= 4:
            return True, b.close, "Cierre Ventana Flujo Fin de Mes (T+4)"

        return False, b.close, ""

    def simulate(
        self,
        symbol: str,
        series: List[EnrichedBar],
        start_date: str = "2007-01-01",
        include_open: bool = False,
    ) -> List[ClosedTrade]:
        """Executes a chronological historical simulation of Motor 6 (TOTM)."""
        trades: List[ClosedTrade] = []
        in_pos = False
        entry_idx = 0
        entry_bar: Optional[EnrichedBar] = None
        stop_price = 0.0
        stop_dist_pct = 0.0
        min_low = 0.0
        entry_reason = ""
        meta_conf = 1.15

        for i in range(205, len(series)):
            b = series[i]
            if b.date < start_date and not in_pos:
                continue

            if not in_pos:
                ok, reason = self._check_entry(b)
                if ok:
                    in_pos = True
                    entry_idx = i
                    entry_bar = b
                    stop_price, stop_dist_pct = self._calculate_stops(b)
                    min_low = b.close
                    entry_reason = reason
                    meta_conf = 1.15
            else:
                assert entry_bar is not None
                days = i - entry_idx
                if b.low < min_low:
                    min_low = b.low

                exit_flag, exit_price, exit_reason = self._check_exit(b, days, stop_price)
                if exit_flag:
                    raw_ret = ((exit_price - entry_bar.close) / entry_bar.close) * 100.0
                    mae = ((min_low - entry_bar.close) / entry_bar.close) * 100.0
                    trades.append(
                        ClosedTrade(
                            engine_id=self.engine_id,
                            engine_name=self.engine_name,
                            symbol=symbol,
                            direction="LONG",
                            entry_date=entry_bar.date,
                            entry_price=round(entry_bar.close, 2),
                            exit_date=b.date,
                            exit_price=round(exit_price, 2),
                            days=days,
                            raw_ret_pct=round(raw_ret, 3),
                            mae_pct=round(min(0.0, mae), 3),
                            stop_distance_pct=round(stop_dist_pct, 3),
                            win=raw_ret > 0,
                            entry_reason=entry_reason,
                            exit_reason=exit_reason,
                            meta_confidence=meta_conf,
                        )
                    )
                    in_pos = False

        if include_open and in_pos and entry_bar is not None:
            trades.append(
                self.build_open_trade(
                    symbol=symbol,
                    direction="LONG",
                    entry_bar=entry_bar,
                    last_bar=series[-1],
                    days=len(series) - 1 - entry_idx,
                    stop_distance_pct=stop_dist_pct,
                    entry_reason=entry_reason,
                    meta_confidence=meta_conf,
                )
            )

        return trades

    def evaluate_live(self, symbol: str, series: List[EnrichedBar]) -> Optional[TradeSignal]:
        """Evaluates today's bar for live Turn-of-the-Month signal generation."""
        if len(series) < 205:
            return None
        b = series[-1]
        ok, reason = self._check_entry(b)
        if not ok:
            return None

        stop_p, stop_d = self._calculate_stops(b)
        return TradeSignal(
            engine_id=self.engine_id,
            engine_name=self.engine_name,
            symbol=symbol,
            direction="LONG",
            date=b.date,
            entry_price=round(b.close, 2),
            stop_price=round(stop_p, 2),
            stop_distance_pct=round(stop_d, 2),
            target_description=f"Impulso sobre SMA(5) ({b.sma5:.2f}) o Ventana T+4",
            reason=reason,
            meta_confidence=1.15,
        )
