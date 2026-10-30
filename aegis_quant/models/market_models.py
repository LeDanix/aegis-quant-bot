"""
Modelos de Dominio Orientados a Objetos para Aegis-Quant.
Representan de forma inmutable y tipada las barras de mercado, estados de régimen,
señales operativas, operaciones cerradas y métricas de cartera.
"""

from dataclasses import dataclass


@dataclass
class MarketBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int


@dataclass
class EnrichedBar(MarketBar):
    sma5: float = 0.0
    sma20: float = 0.0
    sma30: float = 0.0
    sma50: float = 0.0
    sma200: float = 0.0
    sma200_rising: bool = False
    std30: float = 0.0
    lower_band30: float = 0.0
    upper_band30: float = 0.0
    rsi2: float = 50.0
    atr14: float = 0.0
    realized_vol20: float = 15.0  # Volatilidad anualizada de 20 días (%)
    mom60_vol_adj: float = 0.0  # Momentum de 60 días ajustado por volatilidad (Sharpe 3m)
    down_streak: int = 0
    up_streak: int = 0
    prev_high_20: float = 0.0
    prev_low_10: float = 0.0
    prev_high_50: float = 0.0
    prev_low_20: float = 0.0
    # Datos intermercado de volatilidad implícita (Cúspide de la pirámide)
    vix_close: float = 18.0
    vix3m_close: float = 20.0
    vts_ratio: float = 0.90  # Ratio Estructura Temporal = VIX / VIX3M (<1 Contango, >1 Backwardation)
    vts_prev: float = 0.90


@dataclass
class TradeSignal:
    engine_id: str
    engine_name: str
    symbol: str
    direction: str  # 'LONG' | 'SHORT'
    date: str
    entry_price: float
    stop_price: float
    stop_distance_pct: float
    target_description: str
    reason: str
    meta_confidence: float = 1.0  # Factor de convicción del Meta-Labeler (0.5 a 1.35)


@dataclass
class ClosedTrade:
    engine_id: str
    engine_name: str
    symbol: str
    direction: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    days: int
    raw_ret_pct: float
    mae_pct: float
    stop_distance_pct: float
    win: bool
    entry_reason: str
    exit_reason: str
    meta_confidence: float = 1.0
    position_weight: float = 0.0
    portfolio_ret_pct: float = 0.0
    portfolio_mae_pct: float = 0.0

    def to_dict(self) -> dict:
        return {
            "engine_id": self.engine_id,
            "engine_name": self.engine_name,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_date": self.entry_date,
            "entry_price": self.entry_price,
            "exit_date": self.exit_date,
            "exit_price": self.exit_price,
            "days": self.days,
            "raw_ret_pct": self.raw_ret_pct,
            "mae_pct": self.mae_pct,
            "stop_distance_pct": self.stop_distance_pct,
            "win": self.win,
            "entry_reason": self.entry_reason,
            "exit_reason": self.exit_reason,
            "meta_confidence": self.meta_confidence,
            "position_weight": self.position_weight,
            "portfolio_ret_pct": self.portfolio_ret_pct,
            "portfolio_mae_pct": self.portfolio_mae_pct,
        }
