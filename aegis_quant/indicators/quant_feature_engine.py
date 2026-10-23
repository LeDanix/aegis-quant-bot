"""
Motor Orientado a Objetos de Ingeniería de Características Cuantitativas (QuantFeatureEngine).
Integra tanto los indicadores de precio clásicos (Base de la Pirámide) como factores institucionales
avanzados (Cúspide de la Pirámide):
  1. Estructura Temporal de Volatilidad Implícita (VTS Ratio = VIX / VIX3M: Contango vs Backwardation)
  2. Volatilidad Realizada Anualizada de 20 sesiones (para Volatility Targeting dinámico)
  3. Momentum Ajustado por Volatilidad a 60 días (para Rotación Cross-Asset Dual Momentum)
"""

import math
from typing import Dict, List
from aegis_quant.models.market_models import MarketBar, EnrichedBar


class QuantFeatureEngine:
    def __init__(self, vix_bars: List[MarketBar] = None, vix3m_bars: List[MarketBar] = None):
        self.vix_map: Dict[str, MarketBar] = {b.date: b for b in (vix_bars or [])}
        self.vix3m_map: Dict[str, MarketBar] = {b.date: b for b in (vix3m_bars or [])}

    def enrich_series(self, bars: List[MarketBar]) -> List[EnrichedBar]:
        enriched: List[EnrichedBar] = []
        closes = [b.close for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]

        avg_gain_2 = 0.0
        avg_loss_2 = 0.0
        atr14 = 0.0
        down_streak = 0
        up_streak = 0
        daily_rets: List[float] = [0.0]

        for i, b in enumerate(bars):
            c = closes[i]
            h = highs[i]
            l = lows[i]
            d = b.date

            if i > 0:
                ret_d = (c - closes[i - 1]) / closes[i - 1]
                daily_rets.append(ret_d)
                if c < closes[i - 1]:
                    down_streak += 1
                    up_streak = 0
                elif c > closes[i - 1]:
                    up_streak += 1
                    down_streak = 0
                else:
                    down_streak = 0
                    up_streak = 0

            # Medias móviles
            w5 = closes[max(0, i - 4): i + 1]
            w20 = closes[max(0, i - 19): i + 1]
            w30 = closes[max(0, i - 29): i + 1]
            w50 = closes[max(0, i - 49): i + 1]
            w200 = closes[max(0, i - 199): i + 1]

            sma5 = sum(w5) / len(w5)
            sma20 = sum(w20) / len(w20)
            sma30 = sum(w30) / len(w30)
            sma50 = sum(w50) / len(w50)
            sma200 = sum(w200) / len(w200)

            var30 = sum((x - sma30) ** 2 for x in w30) / len(w30)
            std30 = math.sqrt(var30)
            lower_band30 = sma30 - 2.0 * std30
            upper_band30 = sma30 + 2.0 * std30

            # Volatilidad realizada anualizada (20 sesiones) para Volatility Targeting
            if i >= 20:
                ret_w20 = daily_rets[i - 19: i + 1]
                mean_r = sum(ret_w20) / len(ret_w20)
                var_r = sum((r - mean_r) ** 2 for r in ret_w20) / len(ret_w20)
                realized_vol20 = max(6.0, math.sqrt(var_r) * math.sqrt(252.0) * 100.0)
            else:
                realized_vol20 = 15.0

            # Momentum de 60 días ajustado por volatilidad (Cross-Asset Ranking Score)
            if i >= 60:
                ret60_pct = ((c - closes[i - 60]) / closes[i - 60]) * 100.0
                mom60_vol_adj = ret60_pct / max(8.0, realized_vol20)
            else:
                mom60_vol_adj = 0.0

            # RSI(2) de Wilder
            if i == 0:
                rsi2 = 50.0
            else:
                change = c - closes[i - 1]
                gain = max(0.0, change)
                loss = max(0.0, -change)
                if i == 1:
                    avg_gain_2 = gain
                    avg_loss_2 = loss
                else:
                    avg_gain_2 = (avg_gain_2 + gain) / 2.0
                    avg_loss_2 = (avg_loss_2 + loss) / 2.0
                if avg_loss_2 == 0:
                    rsi2 = 100.0 if avg_gain_2 > 0 else 50.0
                else:
                    rs = avg_gain_2 / avg_loss_2
                    rsi2 = 100.0 - (100.0 / (1.0 + rs))

            # ATR(14)
            if i == 0:
                tr = h - l
                atr14 = tr
            else:
                prev_c = closes[i - 1]
                tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
                if i < 14:
                    atr14 = ((atr14 * i) + tr) / (i + 1)
                else:
                    atr14 = (atr14 * 13.0 + tr) / 14.0

            # Canales de Donchian previos
            if i >= 20:
                prev_high_20 = max(highs[i - 20: i])
                prev_low_10 = min(lows[i - 10: i])
                prev_low_20 = min(lows[i - 20: i])
            else:
                prev_high_20 = h
                prev_low_10 = l
                prev_low_20 = l

            prev_high_50 = max(highs[i - 50: i]) if i >= 50 else prev_high_20
            prev_sma200 = enriched[i - 1].sma200 if i > 0 else sma200
            sma200_rising = sma200 > prev_sma200

            # Estructura Temporal de Volatilidad (VIX / VIX3M)
            vix_c = self.vix_map[d].close if d in self.vix_map else (enriched[i - 1].vix_close if i > 0 else 18.0)
            vix3m_c = self.vix3m_map[d].close if d in self.vix3m_map else (enriched[i - 1].vix3m_close if i > 0 else max(19.0, vix_c * 1.08))
            vts_ratio = vix_c / max(8.0, vix3m_c)
            vts_prev = enriched[i - 1].vts_ratio if i > 0 else vts_ratio

            enriched.append(
                EnrichedBar(
                    date=d,
                    open=b.open,
                    high=h,
                    low=l,
                    close=c,
                    adj_close=b.adj_close,
                    volume=b.volume,
                    sma5=round(sma5, 4),
                    sma20=round(sma20, 4),
                    sma30=round(sma30, 4),
                    sma50=round(sma50, 4),
                    sma200=round(sma200, 4),
                    sma200_rising=sma200_rising,
                    std30=round(std30, 4),
                    lower_band30=round(lower_band30, 4),
                    upper_band30=round(upper_band30, 4),
                    rsi2=round(rsi2, 2),
                    atr14=round(atr14, 4),
                    realized_vol20=round(realized_vol20, 2),
                    mom60_vol_adj=round(mom60_vol_adj, 3),
                    down_streak=down_streak,
                    up_streak=up_streak,
                    prev_high_20=round(prev_high_20, 4),
                    prev_low_10=round(prev_low_10, 4),
                    prev_high_50=round(prev_high_50, 4),
                    prev_low_20=round(prev_low_20, 4),
                    vix_close=round(vix_c, 2),
                    vix3m_close=round(vix3m_c, 2),
                    vts_ratio=round(vts_ratio, 4),
                    vts_prev=round(vts_prev, 4),
                )
            )

        return enriched
