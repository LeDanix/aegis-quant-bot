"""
Motor 4: Multi-Asset CTA Trend Breakout Strategy (aegis_quant/strategies/m4_cta_trend.py).

Quantitative & Academic Foundation:
-----------------------------------
- Origin & Literature: Richard Donchian (father of trend following), David Harding (Winton Capital),
  and AQR Capital Management ('A Century of Evidence on Trend-Following Investing').
- Core Hypothesis: Commodities and fixed income assets (GLD, USO, ZS/SOYB, TLT) exhibit structural
  autocorrelation driven by macroeconomic monetary cycles, supply-demand imbalances, and geopolitical
  shocks. When price breaks out to a new 20-day high above a rising 50-day and 200-day moving average,
  it enters a persistent multi-month trend. Trailing stops based on Donchian 10-day low and ATR
  lock in trend profits while cutting adverse rotations.

Execution Parameters:
- Direction: LONG
- Target Assets: GLD (Gold), USO (Oil), ZS / SOYB (Soybeans), TLT (20+ Yr Treasuries)
- Entry Trigger: 20-day Donchian High breakout with SMA(50) > SMA(200)
- Trailing Stop: max(initial stop, 10-day Donchian Low, Highest Close - 3x ATR)
- Max Holding Time: 45 trading sessions
"""

from aegis_quant.models.market_models import ClosedTrade, EnrichedBar, TradeSignal
from aegis_quant.strategies.base import BaseStrategy


class CommodityBreakoutCTAStrategy(BaseStrategy):
    """
    Motor 4: Multi-Asset CTA Trend Following (GLD, USO, ZS, TLT).
    Provides crisis and stagflation alpha that is structurally uncorrelated to equity indices.
    """

    def __init__(self):
        super().__init__(
            engine_id="M4_CTA_TREND",
            engine_name="Motor 4: Multi-Asset CTA Trend Breakout (LONG)",
            category="cta_trend",
        )

    def _check_entry(self, b: EnrichedBar, symbol: str) -> tuple[bool, str]:
        """
        Evaluates 20-day Donchian channel breakout with moving average confirmation.

        Rules:
        1. Golden trend alignment: Close > SMA50 and SMA50 > SMA200.
        2. Breakout: Close > 20-day prior high (prev_high_20).
        3. ATR check: atr14 > 0.
        """
        if b.close > b.sma50 and b.sma50 > b.sma200 and b.close > b.prev_high_20 and b.atr14 > 0:
            reason = f"Ruptura Donchian 20d ({b.prev_high_20:.2f}) en {symbol} con SMA50>SMA200"
            return True, reason
        return False, ""

    def _calculate_stops(self, b: EnrichedBar) -> tuple[float, float]:
        """Calculates initial stop loss based on 2.5x ATR below close."""
        stop_price = b.close - 2.5 * b.atr14
        stop_dist_pct = max(1.5, ((b.close - stop_price) / b.close) * 100.0)
        return stop_price, stop_dist_pct

    def _calculate_trailing_stop(self, b: EnrichedBar, initial_stop: float, highest_close: float) -> float:
        """Dynamic trailing stop: highest of initial stop, 10-day low, and 3x ATR below peak."""
        return max(initial_stop, b.prev_low_10, highest_close - 3.0 * b.atr14)

    def _check_exit(self, b: EnrichedBar, days: int, trailing_stop: float) -> tuple[bool, float, str]:
        """Checks trailing stop and trend exhaustion exits."""
        if b.low <= trailing_stop:
            exit_price = trailing_stop if b.open > trailing_stop else b.open
            return True, exit_price, "Trailing Stop Donchian 10d / 3xATR"

        if b.close < b.sma50:
            return True, b.close, "Perdida de Tendencia Media (Close < SMA50)"

        if days >= 45:
            return True, b.close, "Rotacion Temporal CTA (45 sesiones)"

        return False, b.close, ""

    def simulate(
        self,
        symbol: str,
        series: list[EnrichedBar],
        start_date: str = "2007-01-01",
        include_open: bool = False,
    ) -> list[ClosedTrade]:
        """Executes a chronological historical simulation of Motor 4."""
        trades: list[ClosedTrade] = []
        in_pos = False
        entry_idx = 0
        entry_bar: EnrichedBar | None = None
        stop_price = 0.0
        stop_dist_pct = 0.0
        min_low = 0.0
        highest_close = 0.0
        entry_reason = ""

        for i in range(205, len(series)):
            b = series[i]
            if b.date < start_date and not in_pos:
                continue

            if not in_pos:
                ok, reason = self._check_entry(b, symbol)
                if ok:
                    in_pos = True
                    entry_idx = i
                    entry_bar = b
                    stop_price, stop_dist_pct = self._calculate_stops(b)
                    min_low = b.close
                    highest_close = b.close
                    entry_reason = reason
            else:
                assert entry_bar is not None
                days = i - entry_idx
                if b.low < min_low:
                    min_low = b.low
                if b.close > highest_close:
                    highest_close = b.close

                trailing_stop = self._calculate_trailing_stop(b, stop_price, highest_close)
                exit_flag, exit_price, exit_reason = self._check_exit(b, days, trailing_stop)

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
                            meta_confidence=1.0,
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
                    meta_confidence=1.0,
                )
            )

        return trades

    def evaluate_live(self, symbol: str, series: list[EnrichedBar]) -> TradeSignal | None:
        """Evaluates today's bar for live CTA breakout signal generation."""
        if len(series) < 205:
            return None
        b = series[-1]
        ok, reason = self._check_entry(b, symbol)
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
            target_description=f"Trailing Stop Min 10d ({b.prev_low_10:.2f}) o SMA50 ({b.sma50:.2f})",
            reason=reason,
            meta_confidence=1.0,
        )
