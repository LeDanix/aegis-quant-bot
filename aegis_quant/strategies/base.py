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
from typing import Dict, List, Optional, Tuple
from aegis_quant.models.market_models import EnrichedBar, TradeSignal, ClosedTrade


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
        self, symbol: str, series: List[EnrichedBar], start_date: str = "2007-01-01"
    ) -> List[ClosedTrade]:
        """
        Executes a historical backtest of the strategy over an enriched daily bar series.
        
        :param symbol: Ticker symbol (e.g. 'SPY', 'QQQ', 'GLD').
        :param series: Chronologically ordered list of EnrichedBar objects.
        :param start_date: Starting ISO date filter (default '2007-01-01').
        :return: List of ClosedTrade instances containing executed trades.
        """
        pass

    @abstractmethod
    def evaluate_live(self, symbol: str, series: List[EnrichedBar]) -> Optional[TradeSignal]:
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
