"""
Motor 2: Scherman VIX Divergence Strategy (aegis_quant/strategies/m2_vix_divergence.py).

Quantitative & Academic Foundation:
-----------------------------------
- Origin & Literature: Intermarket volatility divergence theory (David Scherman,
  Larry McMillan 'McMillan on Options', and CBOE market microstructure).
- Core Hypothesis: CBOE Volatility Index (VIX) tracks 30-day implied volatility priced
  into S&P 500 index options. When equities are making fresh short-term lows or languishing
  in oversold territory, but VIX fails to confirm with higher highs and instead rolls over
  from elevated levels (>= 20.0), institutional demand for put option protection is exhausted.
  This intermarket divergence signals an imminent volatility crush and equity rally.

Execution Parameters:
- Direction: LONG
- Target Assets: SPY, QQQ
- Stop Loss: 2.2x ATR(14)
- Profit Target: Close > SMA(5) with holding >= 2 days, or RSI(2) > 80
- Max Holding Time: 10 trading sessions
"""

from typing import List, Optional, Tuple
from aegis_quant.models.market_models import EnrichedBar, TradeSignal, ClosedTrade
from aegis_quant.strategies.base import BaseStrategy


class SchermanVixDivergenceStrategy(BaseStrategy):
    """
    Motor 2: Divergencia Intermercado S&P 500 vs VIX (LONG).
    Detects exhaustion of selling pressure when price is weak but implied volatility rolls over.
    """

    def __init__(self):
        super().__init__(
            engine_id="M2_VIX_DIV",
            engine_name="Motor 2: Divergencia Intermercado VIX (LONG)",
            category="intermarket_long",
        )

    def _check_entry(
        self, b: EnrichedBar, recent_bars: List[EnrichedBar]
    ) -> Tuple[bool, str, float]:
        """
        Evaluates intermarket divergence between price action and VIX.
        
        Requires:
        1. Macro context: Close > SMA200 * 0.96 and RSI(2) < 20.0 and positive ATR.
        2. Volatility peak: Recent 5-day VIX high >= 20.0.
        3. Volatility rollover: Today's VIX < 5-day VIX peak * 0.96.
        4. Price exhaustion: Today's low near 5-day low (<= low * 1.008) OR RSI(2) < 12.0.
        """
        if b.close <= b.sma200 * 0.96 or b.rsi2 >= 20.0 or b.atr14 <= 0:
            return False, "", 0.0

        if not recent_bars:
            return False, "", 0.0

        recent_vix_high = max(x.vix_close for x in recent_bars)
        recent_px_low = min(x.low for x in recent_bars)

        vix_turning_down = (
            recent_vix_high >= 20.0
            and b.vix_close < recent_vix_high * 0.96
            and (b.low <= recent_px_low * 1.008 or b.rsi2 < 12.0)
        )
        if not vix_turning_down:
            return False, "", 0.0

        reason = (
            f"Divergencia VIX (Pico 5d={recent_vix_high:.1f} -> Hoy={b.vix_close:.1f}) "
            f"+ RSI(2)={b.rsi2:.1f}"
        )
        return True, reason, recent_vix_high

    def _calculate_stops(self, b: EnrichedBar) -> Tuple[float, float]:
        """Calculates stop loss price and percentage distance based on 2.2x ATR."""
        stop_price = b.close - 2.2 * b.atr14
        stop_dist_pct = max(1.2, ((b.close - stop_price) / b.close) * 100.0)
        return stop_price, stop_dist_pct

    def _check_exit(
        self, b: EnrichedBar, days: int, stop_price: float
    ) -> Tuple[bool, float, str]:
        """Checks exit conditions for open divergence positions."""
        if b.low <= stop_price:
            exit_price = stop_price if b.open > stop_price else b.open
            return True, exit_price, "Stop Loss ATR (2.2x)"

        if b.close > b.sma5 and days >= 2:
            return True, b.close, "Target: Cierre > SMA(5)"

        if b.rsi2 > 80.0:
            return True, b.close, "Target: RSI(2) > 80"

        if days >= 10:
            return True, b.close, "Time Stop: 10 sesiones"

        return False, b.close, ""

    def simulate(
        self,
        symbol: str,
        series: List[EnrichedBar],
        start_date: str = "2007-01-01",
        include_open: bool = False,
    ) -> List[ClosedTrade]:
        """Executes a chronological historical simulation of Motor 2."""
        trades: List[ClosedTrade] = []
        in_pos = False
        entry_idx = 0
        entry_bar: Optional[EnrichedBar] = None
        stop_price = 0.0
        stop_dist_pct = 0.0
        min_low = 0.0
        entry_reason = ""
        meta_conf = 1.0

        for i in range(205, len(series)):
            b = series[i]
            if b.date < start_date and not in_pos:
                continue

            if not in_pos:
                recent_bars = series[i - 5 : i]
                ok, reason, _ = self._check_entry(b, recent_bars)
                if ok:
                    in_pos = True
                    entry_idx = i
                    entry_bar = b
                    stop_price, stop_dist_pct = self._calculate_stops(b)
                    min_low = b.close
                    entry_reason = reason
                    meta_conf = self.compute_meta_confidence(b, "LONG", 1.10)
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
        """Evaluates today's bar for live signal generation."""
        if len(series) < 205:
            return None
        b = series[-1]
        recent_bars = series[-6:-1]
        ok, reason, recent_vix_high = self._check_entry(b, recent_bars)
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
            target_description=f"Cierre > SMA(5) ({b.sma5:.2f}) o RSI(2)>80",
            reason=f"Divergencia VIX (Pico 5d={recent_vix_high:.1f} -> Hoy={b.vix_close:.1f})",
            meta_confidence=self.compute_meta_confidence(b, "LONG", 1.10),
        )
