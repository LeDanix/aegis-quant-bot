"""
Test Helpers and Synthetic Fixtures for Aegis-Quant (tests/helpers.py).
Provides a lightweight factory to create EnrichedBar objects for unit testing strategies.
"""

from aegis_quant.models.market_models import EnrichedBar


def create_mock_bar(
    date: str = "2026-10-25",
    close: float = 500.0,
    open_px: float = 500.0,
    high: float = 505.0,
    low: float = 495.0,
    sma5: float = 498.0,
    sma20: float = 490.0,
    sma50: float = 480.0,
    sma200: float = 450.0,
    sma200_rising: bool = True,
    rsi2: float = 50.0,
    atr14: float = 5.0,
    lower_band30: float = 485.0,
    upper_band30: float = 515.0,
    down_streak: int = 0,
    up_streak: int = 0,
    prev_high_20: float = 510.0,
    prev_low_20: float = 475.0,
    prev_low_10: float = 480.0,
    vix_close: float = 16.0,
    vix3m_close: float = 18.0,
    vts_ratio: float = 0.888,
    vts_prev: float = 0.890,
    realized_vol20: float = 12.0,
) -> EnrichedBar:
    """Creates a fully populated EnrichedBar instance with custom override attributes."""
    return EnrichedBar(
        date=date,
        open=open_px,
        high=high,
        low=low,
        close=close,
        adj_close=close,
        volume=1000000,
        sma5=sma5,
        sma20=sma20,
        sma50=sma50,
        sma200=sma200,
        sma200_rising=sma200_rising,
        rsi2=rsi2,
        atr14=atr14,
        upper_band30=upper_band30,
        lower_band30=lower_band30,
        down_streak=down_streak,
        up_streak=up_streak,
        prev_high_20=prev_high_20,
        prev_low_20=prev_low_20,
        prev_low_10=prev_low_10,
        mom60_vol_adj=0.45,
        realized_vol20=realized_vol20,
        vix_close=vix_close,
        vix3m_close=vix3m_close,
        vts_ratio=vts_ratio,
        vts_prev=vts_prev,
    )
