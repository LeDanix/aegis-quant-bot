"""
Motor 5: Volatility Term Structure Backwardation Vol-Crush Strategy (aegis_quant/strategies/m5_vol_crush.py).

Quantitative & Academic Foundation:
-----------------------------------
- Origin & Literature: CBOE Volatility Term Structure research, Brent Donnelly, and options
  dealer positioning dynamics (Market Maker Gamma & Vanna hedging flows).
- Core Hypothesis: Under normal market conditions, the volatility term structure is in
  Contango (VIX < VIX3M, ratio VTS < 1.00). In extreme panic sell-offs, options demand drives
  short-term implied volatility far above 3-month volatility (Backwardation, VTS >= 1.00).
  Market makers are forced to short index futures to hedge negative gamma.
  As soon as panic subsides and the VTS ratio compresses sharply (VTS < 5-day peak * 0.965),
  implied volatility collapses ('vol crush'). This mechanical shift flips dealer positioning:
  dealers must aggressively cover short delta hedges (positive Vanna flow) by buying index
  futures, creating explosive, high-probability 'V-shaped' equity market recoveries.

Execution Parameters:
- Direction: LONG
- Target Assets: SPY, QQQ
- Entry Trigger: Compression from 5-day peak VTS ratio >= 1.00 with price stabilizing
- Stop Loss: 2.3x ATR(14)
- Profit Target: Normalization to SMA(20) with holding >= 2 days, or RSI(2) > 82
- Max Holding Time: 12 trading sessions
"""

from typing import List, Optional, Tuple
from aegis_quant.models.market_models import EnrichedBar, TradeSignal, ClosedTrade
from aegis_quant.strategies.base import BaseStrategy


class VolTermStructureCrushStrategy(BaseStrategy):
    """
    Motor 5 (Cúspide de la Pirámide): VIX/VIX3M Term Structure Vol-Crush (LONG).
    Institutional volatility surface arbitrage capturing dealer gamma/vanna unwinding.
    """

    def __init__(self):
        super().__init__(
            engine_id="M5_VOL_CRUSH",
            engine_name="Motor 5: VIX/VIX3M Term Structure Vol-Crush (LONG)",
            category="vol_surface_arb",
        )

    def _check_entry(
        self, b: EnrichedBar, prev_bar: EnrichedBar, recent_bars: List[EnrichedBar]
    ) -> Tuple[bool, str, float]:
        """
        Evaluates compression of volatility term structure backwardation.
        
        Requires:
        1. Valid bar & non-zero ATR.
        2. Free-fall filter: Avoid catastrophic systemic waterfalls without floor
           (reject if Close < SMA200 * 0.86 and VTS > 1.12).
        3. Backwardation threshold: Max VTS ratio in past 5 days >= 1.00.
        4. Compression trigger: Today's VTS < 5-day peak * 0.965 and VTS < previous day VTS.
        5. Price stabilization: RSI(2) < 45.0 and Close > previous day's low.
        """
        if b.atr14 <= 0 or not recent_bars or prev_bar is None:
            return False, "", 0.0

        if b.close < b.sma200 * 0.86 and b.vts_ratio > 1.12:
            return False, "", 0.0

        peak_vts = max(x.vts_ratio for x in recent_bars)
        vts_crush = (
            peak_vts >= 1.00
            and b.vts_ratio < peak_vts * 0.965
            and b.vts_ratio < b.vts_prev
            and b.rsi2 < 45.0
            and b.close > prev_bar.low
        )
        if not vts_crush:
            return False, "", 0.0

        reason = (
            f"Compresion Backwardation VIX/VIX3M (Pico 5d={peak_vts:.2f} -> Hoy={b.vts_ratio:.2f}) "
            f"+ Flujo Vanna Positivo"
        )
        return True, reason, peak_vts

    def _calculate_stops(self, b: EnrichedBar) -> Tuple[float, float]:
        """Calculates stop loss based on 2.3x ATR below close."""
        stop_price = b.close - 2.3 * b.atr14
        stop_dist_pct = max(1.2, ((b.close - stop_price) / b.close) * 100.0)
        return stop_price, stop_dist_pct

    def _check_exit(
        self, b: EnrichedBar, entry_bar: EnrichedBar, days: int, stop_price: float
    ) -> Tuple[bool, float, str]:
        """Checks exit conditions for Vol-Crush trades."""
        if b.low <= stop_price:
            exit_price = stop_price if b.open > stop_price else b.open
            return True, exit_price, "Stop Loss Vol-Crush (2.3x ATR)"

        if b.vts_ratio > 1.06 and b.close < entry_bar.close:
            return True, b.close, f"Re-expansion Backwardation (VTS={b.vts_ratio:.2f})"

        if b.close > b.sma20 and days >= 2:
            return True, b.close, "Target Vol-Crush: Normalizacion a SMA(20)"

        if b.rsi2 > 82.0:
            return True, b.close, f"Target Vol-Crush: Impulso RSI(2)={b.rsi2:.1f}>82"

        if days >= 12:
            return True, b.close, "Time Stop Vol-Crush: 12 sesiones"

        return False, b.close, ""

    def simulate(
        self,
        symbol: str,
        series: List[EnrichedBar],
        start_date: str = "2007-01-01",
        include_open: bool = False,
    ) -> List[ClosedTrade]:
        """Executes a chronological historical simulation of Motor 5."""
        trades: List[ClosedTrade] = []
        in_pos = False
        entry_idx = 0
        entry_bar: Optional[EnrichedBar] = None
        stop_price = 0.0
        stop_dist_pct = 0.0
        min_low = 0.0
        entry_reason = ""
        meta_conf = 1.20

        for i in range(205, len(series)):
            b = series[i]
            if b.date < start_date and not in_pos:
                continue

            if not in_pos:
                prev_bar = series[i - 1]
                recent_window = series[i - 5 : i]
                ok, reason, _ = self._check_entry(b, prev_bar, recent_window)
                if ok:
                    in_pos = True
                    entry_idx = i
                    entry_bar = b
                    stop_price, stop_dist_pct = self._calculate_stops(b)
                    min_low = b.close
                    entry_reason = reason
                    meta_conf = self.compute_meta_confidence(b, "LONG", 1.20)
            else:
                assert entry_bar is not None
                days = i - entry_idx
                if b.low < min_low:
                    min_low = b.low

                exit_flag, exit_price, exit_reason = self._check_exit(
                    b, entry_bar, days, stop_price
                )
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
        """Evaluates today's bar for live Vol-Crush signal generation."""
        if len(series) < 205:
            return None
        b = series[-1]
        prev_bar = series[-2]
        recent_window = series[-6:-1]
        ok, reason, _ = self._check_entry(b, prev_bar, recent_window)
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
            target_description=f"Normalizacion a SMA(20) ({b.sma20:.2f}) o RSI(2)>82",
            reason=reason,
            meta_confidence=self.compute_meta_confidence(b, "LONG", 1.20),
        )
