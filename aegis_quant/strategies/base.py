"""
Base Strategy Architecture & Meta-Labeling Framework (aegis_quant/strategies/base.py).

Theoretical Foundation:
-----------------------
This module defines the abstract base interface for all quantitative trading engines
in the Aegis-Quant system, as well as the meta-labeling conviction mechanism inspired
by Dr. Marcos López de Prado (Advances in Financial Machine Learning).

Primary vs Secondary Models (Meta-Labeling):
- Primary Models: Generate directional signals (LONG / SHORT) based on regime, price
  action, and indicator extremes.
- Secondary Model (Meta-Labeler): Does not predict direction, but rather sizes conviction
  and probability of success by evaluating the intermarket volatility microstructure
  (VIX/VIX3M term structure ratio and realized volatility).
"""

from abc import ABC, abstractmethod

from aegis_quant.models.market_models import ClosedTrade, EnrichedBar, TradeSignal

# Fecha de salida "centinela" para operaciones que siguen abiertas al final de la serie.
# Al ser lexicográficamente mayor que cualquier fecha ISO real, el filtro de huecos
# (`exit_date > entry_date`) las trata como ocupando capital indefinidamente.
OPEN_TRADE_EXIT_DATE = "9999-12-31"


class BaseStrategy(ABC):
    """
    Abstract Base Class for all quantitative strategy engines in Aegis-Quant.

    Subclasses must implement:
      - simulate(symbol, series, start_date): Historical simulation producing ClosedTrade records.
      - evaluate_live(symbol, series): Evaluates the latest market bar to generate a live TradeSignal.
    """

    def __init__(self, engine_id: str, engine_name: str, category: str):
        """
        Initialize strategy metadata.

        :param engine_id: Short unique identifier (e.g., 'M1_PULLBACK', 'M5_VOL_CRUSH').
        :param engine_name: Descriptive name with direction and academic style.
        :param category: Engine category ('mean_reversion_long', 'cta_trend', etc.).
        """
        self.engine_id = engine_id
        self.engine_name = engine_name
        self.category = category

    @abstractmethod
    def simulate(
        self,
        symbol: str,
        series: list[EnrichedBar],
        start_date: str = "2007-01-01",
        include_open: bool = False,
    ) -> list[ClosedTrade]:
        """
        Executes a historical backtest of the strategy over an enriched daily bar series.

        :param symbol: Ticker symbol (e.g. 'SPY', 'QQQ', 'GLD').
        :param series: Chronologically ordered list of EnrichedBar objects.
        :param start_date: Starting ISO date filter (default '2007-01-01').
        :param include_open: If True, a position still open on the last bar is also returned
            (built with `build_open_trade`, exit_date = OPEN_TRADE_EXIT_DATE). Used by the live
            bot to know which tactical trades are active today by replaying history.
        :return: List of ClosedTrade instances containing executed trades.
        """
        pass

    def build_open_trade(
        self,
        symbol: str,
        direction: str,
        entry_bar: EnrichedBar,
        last_bar: EnrichedBar,
        days: int,
        stop_distance_pct: float,
        entry_reason: str,
        meta_confidence: float,
    ) -> ClosedTrade:
        """
        Represents a still-open position as a ClosedTrade marked with OPEN_TRADE_EXIT_DATE.

        The "exit" price is the latest close (mark-to-market), so raw_ret_pct is the current
        unrealised return. This lets the live scanner reuse exactly the same slot/sizing
        pipeline as the backtest (`AegisPortfolioEngine.filter_and_size_tactical_trades`).
        """
        sign = 1.0 if direction == "LONG" else -1.0
        raw_ret = sign * ((last_bar.close - entry_bar.close) / entry_bar.close) * 100.0
        return ClosedTrade(
            engine_id=self.engine_id,
            engine_name=self.engine_name,
            symbol=symbol,
            direction=direction,
            entry_date=entry_bar.date,
            entry_price=round(entry_bar.close, 2),
            exit_date=OPEN_TRADE_EXIT_DATE,
            exit_price=round(last_bar.close, 2),
            days=days,
            raw_ret_pct=round(raw_ret, 3),
            mae_pct=0.0,
            stop_distance_pct=round(stop_distance_pct, 3),
            win=raw_ret > 0,
            entry_reason=entry_reason,
            exit_reason="ABIERTA",
            meta_confidence=meta_confidence,
        )

    @abstractmethod
    def evaluate_live(self, symbol: str, series: list[EnrichedBar]) -> TradeSignal | None:
        """
        Evaluates the most recent market data bar for active signal triggers today.

        :param symbol: Ticker symbol.
        :param series: Chronologically ordered list of EnrichedBar objects up to today.
        :return: TradeSignal if triggered, otherwise None.
        """
        pass

    @staticmethod
    def compute_meta_confidence(bar: EnrichedBar, direction: str, base_score: float = 1.0) -> float:
        """
        Calculates meta-labeling conviction multiplier (0.55x to 1.35x).

        Quantitative Logic:
        -------------------
        - In LONG trades:
          * Healthy Contango (VIX/VIX3M < 0.92) provides tailwinds -> Boost confidence (+0.15).
          * Acute accelerating Backwardation (> 1.05 and rising) implies liquidity cascade -> Penalize (-0.25).
          * Extreme price exhaustion (RSI(2) < 5.0) -> Boost confidence (+0.10).
        - In SHORT trades:
          * Backwardation (VIX/VIX3M >= 1.00) confirms institutional panic -> Boost confidence (+0.20).
          * Calm Contango (VIX/VIX3M < 0.88) signals strong underlying bid -> Penalize (-0.20).
        """
        conf = base_score
        if direction == "LONG":
            if bar.vts_ratio < 0.92:
                conf += 0.15
            elif bar.vts_ratio > 1.05 and bar.vts_ratio >= bar.vts_prev:
                conf -= 0.25
            if bar.rsi2 < 5.0:
                conf += 0.10
        elif direction == "SHORT":
            if bar.vts_ratio >= 1.00:
                conf += 0.20
            elif bar.vts_ratio < 0.88:
                conf -= 0.20
        return round(max(0.55, min(1.35, conf)), 2)
