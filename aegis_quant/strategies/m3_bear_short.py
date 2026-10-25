"""
Motor 3: Bear Market Short-Selling / Crisis Alpha Strategy (aegis_quant/strategies/m3_bear_short.py).

Quantitative & Academic Foundation:
-----------------------------------
- Origin & Literature: Victor Sperandeo ('Trader Vic: Methods of a Wall Street Master'),
  Stan Weinstein ('Secrets For Profiting in Bull and Bear Markets'), and Mark Minervini.
- Core Hypothesis: During structural bear markets (Close < SMA200 and SMA50 < SMA200),
  counter-trend bounces are driven by short-covering rather than institutional accumulation.
  Once overbought (RSI(2) > 85 or 3 consecutive up days), upside momentum stalls at
  overhead supply, initiating violent downward rollovers. Alternatively, breakdown below
  the 20-day low under high VIX (>22) signals acute liquidity liquidation.

Execution Parameters:
- Direction: SHORT
- Target Assets: SPY, QQQ
- Stop Loss: 2.2x ATR(14) above entry price
- Regime Filter: Confirmed Bear Market (Close < SMA200 and SMA50 < SMA200)
- Profit Target: Close < SMA(5) or RSI(2) < 20
- Max Holding Time: 12 trading sessions
"""

from typing import List, Optional, Tuple
from aegis_quant.models.market_models import EnrichedBar, TradeSignal, ClosedTrade
from aegis_quant.strategies.base import BaseStrategy


class BearMarketShortStrategy(BaseStrategy):
    """
    Motor 3: Bear Market Short-Selling / Crisis Alpha (SHORT en SPY, QQQ).
    Generates non-correlated positive alpha during severe bear markets (e.g. 2008, 2022).
    """

    def __init__(self):
        super().__init__(
            engine_id="M3_BEAR_SHORT",
            engine_name="Motor 3: Bear Market Short / Crisis Alpha (SHORT)",
            category="crisis_short",
        )

    def _check_entry(self, b: EnrichedBar) -> Tuple[bool, str, str]:
        """
        Evaluates bear market conditions and determines entry mode.
        
        Returns:
            (is_entry, mode_type ['BOUNCE'|'BREAKDOWN'], entry_reason)
        """
        is_bear = (b.close < b.sma200) and (b.sma50 < b.sma200 or not b.sma200_rising)
        if not is_bear or b.atr14 <= 0:
            return False, "", ""

        cond_bounce = (
            (b.rsi2 > 85.0 or b.up_streak >= 3)
            and b.close < b.sma200 * 0.99
            and b.vix_close > 18.0
        )
        cond_panic = b.close < b.prev_low_20 and b.vix_close > 22.0 and b.rsi2 > 15.0

        if cond_bounce:
            return (
                True,
                "BOUNCE",
                f"Bear Rally Exhaustion: Close<SMA200 + RSI(2)={b.rsi2:.1f}>85 + VIX={b.vix_close:.1f}",
            )
        if cond_panic:
            return (
                True,
                "BREAKDOWN",
                f"Bear Breakdown: Ruptura Min 20d ({b.prev_low_20:.2f}) + VIX={b.vix_close:.1f}",
            )
        return False, "", ""

    def _calculate_stops(self, b: EnrichedBar) -> Tuple[float, float]:
        """Calculates short stop loss price and percentage distance based on 2.2x ATR above close."""
        stop_price = b.close + 2.2 * b.atr14
        stop_dist_pct = max(1.2, ((stop_price - b.close) / b.close) * 100.0)
        return stop_price, stop_dist_pct

    def _check_exit(
        self, b: EnrichedBar, days: int, stop_price: float, mode: str
    ) -> Tuple[bool, float, str]:
        """
        Checks exit conditions for short positions.
        
        Returns:
            (exit_flag, exit_price, exit_reason)
        """
        if b.high >= stop_price:
            exit_price = stop_price if b.open < stop_price else b.open
            return True, exit_price, "Stop Loss Bajista ATR (2.2x)"

        if b.close > b.sma200 * 1.01:
            return True, b.close, "Fin Regimen Bajista (Close > SMA200)"

        if mode == "BOUNCE" and (b.close < b.sma5 or b.rsi2 < 20.0):
            return True, b.close, f"Target Corto: Cierre < SMA(5) / RSI(2)={b.rsi2:.1f}"

        if mode == "BREAKDOWN" and (b.close > b.sma20 or days >= 15):
            return True, b.close, "Trailing Stop Bajista (Cierre > SMA20 / 15d)"

        if days >= 12:
            return True, b.close, "Time Stop Corto: 12 sesiones"

        return False, b.close, ""

    def simulate(
        self, symbol: str, series: List[EnrichedBar], start_date: str = "2007-01-01"
    ) -> List[ClosedTrade]:
        """Executes a chronological historical simulation of Motor 3."""
        trades: List[ClosedTrade] = []
        in_pos = False
        entry_idx = 0
        entry_bar: Optional[EnrichedBar] = None
        stop_price = 0.0
        stop_dist_pct = 0.0
        max_high = 0.0
        entry_reason = ""
        mode = ""
        meta_conf = 1.0

        for i in range(205, len(series)):
            b = series[i]
            if b.date < start_date and not in_pos:
                continue

            if not in_pos:
                ok, m_type, reason = self._check_entry(b)
                if ok:
                    in_pos = True
                    entry_idx = i
                    entry_bar = b
                    mode = m_type
                    stop_price, stop_dist_pct = self._calculate_stops(b)
                    max_high = b.close
                    entry_reason = reason
                    meta_conf = self.compute_meta_confidence(b, "SHORT", 1.05)
            else:
                assert entry_bar is not None
                days = i - entry_idx
                if b.high > max_high:
                    max_high = b.high

                exit_flag, exit_price, exit_reason = self._check_exit(b, days, stop_price, mode)
                if exit_flag:
                    raw_ret = ((entry_bar.close - exit_price) / entry_bar.close) * 100.0
                    mae = ((entry_bar.close - max_high) / entry_bar.close) * 100.0
                    trades.append(
                        ClosedTrade(
                            engine_id=self.engine_id,
                            engine_name=self.engine_name,
                            symbol=symbol,
                            direction="SHORT",
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

        return trades

    def evaluate_live(self, symbol: str, series: List[EnrichedBar]) -> Optional[TradeSignal]:
        """Evaluates today's bar for live short signal generation."""
        if len(series) < 205:
            return None
        b = series[-1]
        ok, _, reason = self._check_entry(b)
        if not ok:
            return None

        stop_p, stop_d = self._calculate_stops(b)
        return TradeSignal(
            engine_id=self.engine_id,
            engine_name=self.engine_name,
            symbol=symbol,
            direction="SHORT",
            date=b.date,
            entry_price=round(b.close, 2),
            stop_price=round(stop_p, 2),
            stop_distance_pct=round(stop_d, 2),
            target_description=f"Caida hacia SMA(5) ({b.sma5:.2f}) o RSI(2)<20",
            reason=reason,
            meta_confidence=self.compute_meta_confidence(b, "SHORT", 1.05),
        )
