"""
Backwards-compatible Strategy Module (aegis_quant/strategies/strategies.py).

All strategy engines have been modularized into dedicated files:
  - BaseStrategy                    -> aegis_quant.strategies.base
  - SchermanPullbackStrategy        -> aegis_quant.strategies.m1_pullback
  - SchermanVixDivergenceStrategy   -> aegis_quant.strategies.m2_vix_divergence
  - BearMarketShortStrategy         -> aegis_quant.strategies.m3_bear_short
  - CommodityBreakoutCTAStrategy    -> aegis_quant.strategies.m4_cta_trend
  - VolTermStructureCrushStrategy   -> aegis_quant.strategies.m5_vol_crush

This file re-exports all strategy classes to preserve 100% backwards compatibility.
"""

from aegis_quant.strategies.base import BaseStrategy
from aegis_quant.strategies.m1_pullback import SchermanPullbackStrategy
from aegis_quant.strategies.m2_vix_divergence import SchermanVixDivergenceStrategy
from aegis_quant.strategies.m3_bear_short import BearMarketShortStrategy
from aegis_quant.strategies.m4_cta_trend import CommodityBreakoutCTAStrategy
from aegis_quant.strategies.m5_vol_crush import VolTermStructureCrushStrategy

__all__ = [
    "BaseStrategy",
    "SchermanPullbackStrategy",
    "SchermanVixDivergenceStrategy",
    "BearMarketShortStrategy",
    "CommodityBreakoutCTAStrategy",
    "VolTermStructureCrushStrategy",
]
