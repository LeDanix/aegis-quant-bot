"""
Motor 1: Scherman Equity Pullback Strategy (aegis_quant/strategies/m1_pullback.py).

Quantitative & Academic Foundation:
-----------------------------------
- Origin & Literature: Larry Connors ('Short Term Trading Strategies That Work', 2008),
  David Scherman, and quantitative mean-reversion research in US Equity Indexes (SPY, QQQ).
- Core Hypothesis: Secular equity bull markets (Close > SMA 200) exhibit persistent upward
  drift. When extreme short-term panic occurs (RSI(2) < 10, multiple consecutive down days,
  or piercing below the lower Bollinger Band), market makers and algorithmic liquidity
  providers step in, creating a high-win-rate (>75%) mean-reverting bounce.

Execution Parameters:
- Direction: LONG
- Target Assets: SPY, QQQ
- Stop Loss: 2.5x ATR(14)
- Profit Target: Close > SMA(5) or RSI(2) > 75
- Max Holding Time: 10 trading sessions
"""

from typing import List, Optional, Tuple
from aegis_quant.models.market_models import EnrichedBar, TradeSignal, ClosedTrade
from aegis_quant.strategies.base import BaseStrategy


class SchermanPullbackStrategy(BaseStrategy):
    """
    Motor 1: Scherman Equity Pullback (LONG en SPY, QQQ).
    Buys short-term liquidity exhaustion dips within structural bull trends.
    """

    def __init__(self):
        super().__init__(
            engine_id="M1_PULLBACK",
            engine_name="Motor 1: Scherman Equity Pullback (LONG)",
            category="mean_reversion_long",
        )

    def _check_entry(self, b: EnrichedBar) -> Tuple[bool, str]:
        """
        Evaluates whether an EnrichedBar meets the quantitative entry conditions.
        
        Rules:
        1. Structural Trend: Close > SMA(200) and positive ATR.
        2. Mean Reversion Trigger (any of three):
           a) RSI(2) < 10.0
           b) Close < Lower Bollinger Band(30, 2σ) AND RSI(2) < 25.0
           c) 3+ consecutive down days AND RSI(2) < 18.0
        """
        if b.close <= b.sma200 or b.atr14 <= 0:
            return False, ""

        cond_rsi = b.rsi2 < 10.0
        cond_band = b.close < b.lower_band30 and b.rsi2 < 25.0
        cond_streak = b.down_streak >= 3 and b.rsi2 < 18.0

        if not (cond_rsi or cond_band or cond_streak):
            return False, ""

        reasons = []
        if cond_rsi:
            reasons.append(f"RSI(2)={b.rsi2:.1f}<10")
        if cond_band:
            reasons.append("Close<BollingerInf(30,2s)")
        if cond_streak:
            reasons.append(f"{b.down_streak} dias bajistas")

        return True, " + ".join(reasons) + " con Close>SMA200"

    def _calculate_stops(self, b: EnrichedBar) -> Tuple[float, float]:
        """Calculates stop loss price and percentage distance based on 2.5x ATR."""
        stop_price = b.close - 2.5 * b.atr14
        stop_dist_pct = max(1.2, ((b.close - stop_price) / b.close) * 100.0)
        return stop_price, stop_dist_pct

    def _check_exit(
        self, b: EnrichedBar, days: int, stop_price: float
    ) -> Tuple[bool, float, str]:
        """
        Checks whether the open position should be closed today.
        
        Returns:
            (exit_flag, exit_price, exit_reason)
        """
        if b.low <= stop_price:
            exit_price = stop_price if b.open > stop_price else b.open
            return True, exit_price, "Stop Loss ATR (2.5x)"

        if b.close > b.sma5:
            return True, b.close, "Target: Cierre > SMA(5)"

        if b.rsi2 > 75.0:
            return True, b.close, f"Target: RSI(2)={b.rsi2:.1f}>75"

        if days >= 10:
            return True, b.close, "Time Stop: 10 sesiones"

        if b.close < b.sma200 * 0.97:
            return True, b.close, "Cambio Regimen (<SMA200)"

        return False, b.close, ""

    def simulate(
        self, symbol: str, series: List[EnrichedBar], start_date: str = "2007-01-01"
    ) -> List[ClosedTrade]:
        """Executes a chronological historical simulation of Motor 1."""
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
                ok, reason = self._check_entry(b)
                if ok:
                    in_pos = True
                    entry_idx = i
                    entry_bar = b
                    stop_price, stop_dist_pct = self._calculate_stops(b)
                    min_low = b.close
                    entry_reason = reason
                    meta_conf = self.compute_meta_confidence(b, "LONG", 1.0)
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

        return trades

    def evaluate_live(self, symbol: str, series: List[EnrichedBar]) -> Optional[TradeSignal]:
        """Evaluates today's bar for live signal generation."""
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
            target_description=f"Cierre > SMA(5) ({b.sma5:.2f}) o RSI(2)>75 o max 10 sesiones",
            reason=reason,
            meta_confidence=self.compute_meta_confidence(b, "LONG", 1.0),
        )
