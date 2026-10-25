"""
Aegis-Quant Strategy Engines Package (aegis_quant/strategies/__init__.py).

Exports the BaseStrategy and the 5 modular trading engines:
  - BaseStrategy (base.py)
  - SchermanPullbackStrategy (m1_pullback.py)
  - SchermanVixDivergenceStrategy (m2_vix_divergence.py)
  - BearMarketShortStrategy (m3_bear_short.py)
  - CommodityBreakoutCTAStrategy (m4_cta_trend.py)
  - VolTermStructureCrushStrategy (m5_vol_crush.py)
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
