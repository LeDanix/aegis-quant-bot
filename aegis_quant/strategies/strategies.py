"""
Jerarquía Orientada a Objetos de Estrategias Cuantitativas (BaseStrategy y 5 Motores Especializados).
Incluye los 4 motores clásicos + el Motor 5 de la Cúspide de la Pirámide:
VolTermStructureCrushStrategy (Compresión de Backwardation VIX/VIX3M y Desarme de Coberturas Gamma/Vanna).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from aegis_quant.models.market_models import EnrichedBar, TradeSignal, ClosedTrade


class BaseStrategy(ABC):
    def __init__(self, engine_id: str, engine_name: str, category: str):
        self.engine_id = engine_id
        self.engine_name = engine_name
        self.category = category

    @abstractmethod
    def simulate(self, symbol: str, series: List[EnrichedBar], start_date: str = "2007-01-01") -> List[ClosedTrade]:
        pass

    @abstractmethod
    def evaluate_live(self, symbol: str, series: List[EnrichedBar]) -> Optional[TradeSignal]:
        pass

    @staticmethod
    def compute_meta_confidence(bar: EnrichedBar, direction: str, base_score: float = 1.0) -> float:
        """
        Meta-Labeler (Inspirado en Marcos López de Prado):
        Pondera la convicción de una señal primaria según la microestructura intermercado
        (Estructura Temporal de Volatilidad VIX/VIX3M y régimen de volatilidad realizada).
        Devuelve un multiplicador de convicción entre 0.55 y 1.35.
        """
        conf = base_score
        if direction == "LONG":
            # Si la curva de volatilidad está en Contango sano (<0.95) o girando a la baja desde Backwardation
            if bar.vts_ratio < 0.92:
                conf += 0.15
            elif bar.vts_ratio > 1.05 and bar.vts_ratio >= bar.vts_prev:
                # Backwardation acelerando al alza: riesgo de cascada de liquidez
                conf -= 0.25
            if bar.rsi2 < 5.0:
                conf += 0.10
        elif direction == "SHORT":
            # En cortos, que el VIX/VIX3M esté en Backwardation (>1.0) confirma miedo institucional real
            if bar.vts_ratio >= 1.00:
                conf += 0.20
            elif bar.vts_ratio < 0.88:
                conf -= 0.20
        return round(max(0.55, min(1.35, conf)), 2)


class SchermanPullbackStrategy(BaseStrategy):
    """
    Motor 1: Scherman Equity Pullback (LONG en SPY, QQQ).
    Compra agotamiento extremo a corto plazo dentro de una tendencia alcista estructural (Close > SMA200).
    """

    def __init__(self):
        super().__init__(
            engine_id="M1_PULLBACK",
            engine_name="Motor 1: Scherman Equity Pullback (LONG)",
            category="mean_reversion_long",
        )

    def _check_entry(self, b: EnrichedBar) -> Tuple[bool, str]:
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

    def simulate(self, symbol: str, series: List[EnrichedBar], start_date: str = "2007-01-01") -> List[ClosedTrade]:
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
                    stop_price = b.close - 2.5 * b.atr14
                    stop_dist_pct = max(1.2, ((b.close - stop_price) / b.close) * 100.0)
                    min_low = b.close
                    entry_reason = reason
                    meta_conf = self.compute_meta_confidence(b, "LONG", 1.0)
            else:
                assert entry_bar is not None
                days = i - entry_idx
                if b.low < min_low:
                    min_low = b.low

                exit_flag = False
                exit_price = b.close
                exit_reason = ""

                if b.low <= stop_price:
                    exit_flag = True
                    exit_price = stop_price if b.open > stop_price else b.open
                    exit_reason = "Stop Loss ATR (2.5x)"
                elif b.close > b.sma5:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Target: Cierre > SMA(5)"
                elif b.rsi2 > 75.0:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = f"Target: RSI(2)={b.rsi2:.1f}>75"
                elif days >= 10:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Time Stop: 10 sesiones"
                elif b.close < b.sma200 * 0.97:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Cambio Regimen (<SMA200)"

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
        if len(series) < 205:
            return None
        b = series[-1]
        ok, reason = self._check_entry(b)
        if not ok:
            return None
        stop_p = b.close - 2.5 * b.atr14
        stop_d = max(1.2, ((b.close - stop_p) / b.close) * 100.0)
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


class SchermanVixDivergenceStrategy(BaseStrategy):
    """
    Motor 2: Divergencia Intermercado S&P 500 vs VIX (LONG).
    Detecta agotamiento de la presión vendedora en opciones cuando el índice marca mínimo o sobreventa
    pero el VIX se gira a la baja tras un pico de volatilidad.
    """

    def __init__(self):
        super().__init__(
            engine_id="M2_VIX_DIV",
            engine_name="Motor 2: Divergencia Intermercado VIX (LONG)",
            category="intermarket_long",
        )

    def simulate(self, symbol: str, series: List[EnrichedBar], start_date: str = "2007-01-01") -> List[ClosedTrade]:
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
                if b.close > b.sma200 * 0.96 and b.rsi2 < 20.0:
                    recent_bars = series[i - 5: i]
                    recent_vix_high = max(x.vix_close for x in recent_bars)
                    recent_px_low = min(x.low for x in recent_bars)

                    vix_turning_down = (
                        recent_vix_high >= 20.0
                        and b.vix_close < recent_vix_high * 0.96
                        and (b.low <= recent_px_low * 1.008 or b.rsi2 < 12.0)
                    )
                    if vix_turning_down and b.atr14 > 0:
                        in_pos = True
                        entry_idx = i
                        entry_bar = b
                        stop_price = b.close - 2.2 * b.atr14
                        stop_dist_pct = max(1.2, ((b.close - stop_price) / b.close) * 100.0)
                        min_low = b.close
                        entry_reason = (
                            f"Divergencia VIX (Pico 5d={recent_vix_high:.1f} -> Hoy={b.vix_close:.1f}) "
                            f"+ RSI(2)={b.rsi2:.1f}"
                        )
                        meta_conf = self.compute_meta_confidence(b, "LONG", 1.1)
            else:
                assert entry_bar is not None
                days = i - entry_idx
                if b.low < min_low:
                    min_low = b.low

                exit_flag = False
                exit_price = b.close
                exit_reason = ""

                if b.low <= stop_price:
                    exit_flag = True
                    exit_price = stop_price if b.open > stop_price else b.open
                    exit_reason = "Stop Loss ATR (2.2x)"
                elif b.close > b.sma5 and days >= 2:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Target: Cierre > SMA(5)"
                elif b.rsi2 > 80.0:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Target: RSI(2) > 80"
                elif days >= 10:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Time Stop: 10 sesiones"

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
        if len(series) < 205:
            return None
        b = series[-1]
        recent_bars = series[-6:-1]
        recent_vix_high = max(x.vix_close for x in recent_bars)
        recent_px_low = min(x.low for x in recent_bars)
        if (
            b.close > b.sma200 * 0.96
            and b.rsi2 < 20.0
            and recent_vix_high >= 20.0
            and b.vix_close < recent_vix_high * 0.96
            and (b.low <= recent_px_low * 1.008 or b.rsi2 < 12.0)
        ):
            stop_p = b.close - 2.2 * b.atr14
            stop_d = max(1.2, ((b.close - stop_p) / b.close) * 100.0)
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
                meta_confidence=self.compute_meta_confidence(b, "LONG", 1.1),
            )
        return None


class BearMarketShortStrategy(BaseStrategy):
    """
    Motor 3: Bear Market Short-Selling / Crisis Alpha (SHORT en SPY, QQQ).
    Opera exclusivamente cuando el mercado entra en Régimen Bajista (Close < SMA200 y SMA50 < SMA200).
    Combina:
      A) Venta de rebotes sobrecomprados (Bear Market Rally Exhaustion: RSI2 > 85)
      B) Ruptura de pánico (Momentum Breakdown bajo mínimo de 20 días con VIX > 22)
    """

    def __init__(self):
        super().__init__(
            engine_id="M3_BEAR_SHORT",
            engine_name="Motor 3: Bear Market Short / Crisis Alpha (SHORT)",
            category="crisis_short",
        )

    def _check_entry(self, b: EnrichedBar) -> Tuple[bool, str, str]:
        is_bear = (b.close < b.sma200) and (b.sma50 < b.sma200 or not b.sma200_rising)
        if not is_bear or b.atr14 <= 0:
            return False, "", ""

        cond_bounce = (b.rsi2 > 85.0 or b.up_streak >= 3) and b.close < b.sma200 * 0.99 and b.vix_close > 18.0
        cond_panic = b.close < b.prev_low_20 and b.vix_close > 22.0 and b.rsi2 > 15.0

        if cond_bounce:
            return (
                True,
                "BOUNCE",
                f"Bear Rally Exhaustion: Close<SMA200 + RSI(2)={b.rsi2:.1f}>85 + VIX={b.vix_close:.1f}",
            )
        if cond_panic:
            return (
                True,
                "BREAKDOWN",
                f"Bear Breakdown: Ruptura Min 20d ({b.prev_low_20:.2f}) + VIX={b.vix_close:.1f}",
            )
        return False, "", ""

    def simulate(self, symbol: str, series: List[EnrichedBar], start_date: str = "2007-01-01") -> List[ClosedTrade]:
        trades: List[ClosedTrade] = []
        in_pos = False
        entry_idx = 0
        entry_bar: Optional[EnrichedBar] = None
        stop_price = 0.0
        stop_dist_pct = 0.0
        max_high = 0.0
        entry_reason = ""
        mode = ""
        meta_conf = 1.0

        for i in range(205, len(series)):
            b = series[i]
            if b.date < start_date and not in_pos:
                continue

            if not in_pos:
                ok, m_type, reason = self._check_entry(b)
                if ok:
                    in_pos = True
                    entry_idx = i
                    entry_bar = b
                    mode = m_type
                    stop_price = b.close + 2.2 * b.atr14
                    stop_dist_pct = max(1.2, ((stop_price - b.close) / b.close) * 100.0)
                    max_high = b.close
                    entry_reason = reason
                    meta_conf = self.compute_meta_confidence(b, "SHORT", 1.05)
            else:
                assert entry_bar is not None
                days = i - entry_idx
                if b.high > max_high:
                    max_high = b.high

                exit_flag = False
                exit_price = b.close
                exit_reason = ""

                if b.high >= stop_price:
                    exit_flag = True
                    exit_price = stop_price if b.open < stop_price else b.open
                    exit_reason = "Stop Loss Bajista ATR (2.2x)"
                elif b.close > b.sma200 * 1.01:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Fin Regimen Bajista (Close > SMA200)"
                elif mode == "BOUNCE" and (b.close < b.sma5 or b.rsi2 < 20.0):
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = f"Target Corto: Cierre < SMA(5) / RSI(2)={b.rsi2:.1f}"
                elif mode == "BREAKDOWN" and (b.close > b.sma20 or days >= 15):
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Trailing Stop Bajista (Cierre > SMA20 / 15d)"
                elif days >= 12:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Time Stop Corto: 12 sesiones"

                if exit_flag:
                    raw_ret = ((entry_bar.close - exit_price) / entry_bar.close) * 100.0
                    mae = ((entry_bar.close - max_high) / entry_bar.close) * 100.0
                    trades.append(
                        ClosedTrade(
                            engine_id=self.engine_id,
                            engine_name=self.engine_name,
                            symbol=symbol,
                            direction="SHORT",
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
        if len(series) < 205:
            return None
        b = series[-1]
        ok, _, reason = self._check_entry(b)
        if not ok:
            return None
        stop_p = b.close + 2.2 * b.atr14
        stop_d = max(1.2, ((stop_p - b.close) / b.close) * 100.0)
        return TradeSignal(
            engine_id=self.engine_id,
            engine_name=self.engine_name,
            symbol=symbol,
            direction="SHORT",
            date=b.date,
            entry_price=round(b.close, 2),
            stop_price=round(stop_p, 2),
            stop_distance_pct=round(stop_d, 2),
            target_description=f"Caida hacia SMA(5) ({b.sma5:.2f}) o RSI(2)<20",
            reason=reason,
            meta_confidence=self.compute_meta_confidence(b, "SHORT", 1.05),
        )


class CommodityBreakoutCTAStrategy(BaseStrategy):
    """
    Motor 4: Multi-Asset CTA Trend Following (Materias Primas y Bonos: GLD, USO, ZS, TLT).
    Captura grandes tendencias inflacionarias o de refugio descorrelacionadas de la bolsa.
    """

    def __init__(self):
        super().__init__(
            engine_id="M4_CTA_TREND",
            engine_name="Motor 4: Multi-Asset CTA Trend Breakout (LONG)",
            category="cta_trend",
        )

    def simulate(self, symbol: str, series: List[EnrichedBar], start_date: str = "2007-01-01") -> List[ClosedTrade]:
        trades: List[ClosedTrade] = []
        in_pos = False
        entry_idx = 0
        entry_bar: Optional[EnrichedBar] = None
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
                if b.close > b.sma50 and b.sma50 > b.sma200 and b.close > b.prev_high_20 and b.atr14 > 0:
                    in_pos = True
                    entry_idx = i
                    entry_bar = b
                    stop_price = b.close - 2.5 * b.atr14
                    stop_dist_pct = max(1.5, ((b.close - stop_price) / b.close) * 100.0)
                    min_low = b.close
                    highest_close = b.close
                    entry_reason = f"Ruptura Donchian 20d ({b.prev_high_20:.2f}) en {symbol} con SMA50>SMA200"
            else:
                assert entry_bar is not None
                days = i - entry_idx
                if b.low < min_low:
                    min_low = b.low
                if b.close > highest_close:
                    highest_close = b.close

                trailing_stop = max(stop_price, b.prev_low_10, highest_close - 3.0 * b.atr14)

                exit_flag = False
                exit_price = b.close
                exit_reason = ""

                if b.low <= trailing_stop:
                    exit_flag = True
                    exit_price = trailing_stop if b.open > trailing_stop else b.open
                    exit_reason = "Trailing Stop Donchian 10d / 3xATR"
                elif b.close < b.sma50:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Perdida de Tendencia Media (Close < SMA50)"
                elif days >= 45:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Rotacion Temporal CTA (45 sesiones)"

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
        return trades

    def evaluate_live(self, symbol: str, series: List[EnrichedBar]) -> Optional[TradeSignal]:
        if len(series) < 205:
            return None
        b = series[-1]
        if b.close > b.sma50 and b.sma50 > b.sma200 and b.close > b.prev_high_20 and b.atr14 > 0:
            stop_p = b.close - 2.5 * b.atr14
            stop_d = max(1.5, ((b.close - stop_p) / b.close) * 100.0)
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
                reason=f"Ruptura Donchian 20d ({b.prev_high_20:.2f}) en {symbol}",
                meta_confidence=1.0,
            )
        return None


class VolTermStructureCrushStrategy(BaseStrategy):
    """
    Motor 5 (CÚSPIDE DE LA PIRÁMIDE): Volatility Term Structure Backwardation Exhaustion (VTS Vol-Crush).
    Técnica institucional de arbitraje de estructura temporal de volatilidad (VIX vs VIX3M) y flujos Vanna/Charm.
    - Cuando el ratio VTS = VIX / VIX3M supera 1.01 (Backwardation: el mercado paga más por seguro a 30 días
      que a 90 días por pánico agudo) y al día siguiente el ratio se comprime con fuerza (vts_ratio < pico_5d * 0.965),
      los Market Makers de opciones se ven obligados a recomprar futuros de S&P 500 y Nasdaq masivamente (Flujo Vanna)
      a medida que cae la volatilidad implícita, provocando los rebotes en 'V' más explosivos del mercado.
    """

    def __init__(self):
        super().__init__(
            engine_id="M5_VOL_CRUSH",
            engine_name="Motor 5: VIX/VIX3M Term Structure Vol-Crush (LONG)",
            category="vol_surface_arb",
        )

    def _check_entry(self, series: List[EnrichedBar], idx: int) -> Tuple[bool, str]:
        b = series[idx]
        if b.atr14 <= 0 or idx < 10:
            return False, ""
        # Evitar colapsos sistémicos en caída libre sin suelo (ej. Lehman en pleno octubre si Close está >18% bajo SMA200 y VTS sigue >1.15)
        if b.close < b.sma200 * 0.86 and b.vts_ratio > 1.12:
            return False, ""

        recent_window = series[idx - 5: idx]
        peak_vts = max(x.vts_ratio for x in recent_window)
        # Condición: En los últimos 5 días hubo Backwardation (VIX >= VIX3M, ratio >= 1.00)
        # y hoy la estructura temporal se comprime con fuerza mientras el precio aguanta o rebota
        vts_crush = (
            peak_vts >= 1.00
            and b.vts_ratio < peak_vts * 0.965
            and b.vts_ratio < b.vts_prev
            and b.rsi2 < 45.0
            and b.close > series[idx - 1].low
        )
        if not vts_crush:
            return False, ""

        reason = (
            f"Compresion Backwardation VIX/VIX3M (Pico 5d={peak_vts:.2f} -> Hoy={b.vts_ratio:.2f}) "
            f"+ Flujo Vanna Positivo"
        )
        return True, reason

    def simulate(self, symbol: str, series: List[EnrichedBar], start_date: str = "2007-01-01") -> List[ClosedTrade]:
        trades: List[ClosedTrade] = []
        in_pos = False
        entry_idx = 0
        entry_bar: Optional[EnrichedBar] = None
        stop_price = 0.0
        stop_dist_pct = 0.0
        min_low = 0.0
        entry_reason = ""
        meta_conf = 1.2

        for i in range(205, len(series)):
            b = series[i]
            if b.date < start_date and not in_pos:
                continue

            if not in_pos:
                ok, reason = self._check_entry(series, i)
                if ok:
                    in_pos = True
                    entry_idx = i
                    entry_bar = b
                    stop_price = b.close - 2.3 * b.atr14
                    stop_dist_pct = max(1.2, ((b.close - stop_price) / b.close) * 100.0)
                    min_low = b.close
                    entry_reason = reason
                    meta_conf = self.compute_meta_confidence(b, "LONG", 1.20)
            else:
                assert entry_bar is not None
                days = i - entry_idx
                if b.low < min_low:
                    min_low = b.low

                exit_flag = False
                exit_price = b.close
                exit_reason = ""

                if b.low <= stop_price:
                    exit_flag = True
                    exit_price = stop_price if b.open > stop_price else b.open
                    exit_reason = "Stop Loss Vol-Crush (2.3x ATR)"
                elif b.vts_ratio > 1.06 and b.close < entry_bar.close:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = f"Re-expansion Backwardation (VTS={b.vts_ratio:.2f})"
                elif b.close > b.sma20 and days >= 2:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Target Vol-Crush: Normalizacion a SMA(20)"
                elif b.rsi2 > 82.0:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = f"Target Vol-Crush: Impulso RSI(2)={b.rsi2:.1f}>82"
                elif days >= 12:
                    exit_flag = True
                    exit_price = b.close
                    exit_reason = "Time Stop Vol-Crush: 12 sesiones"

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
        if len(series) < 205:
            return None
        ok, reason = self._check_entry(series, len(series) - 1)
        if not ok:
            return None
        b = series[-1]
        stop_p = b.close - 2.3 * b.atr14
        stop_d = max(1.2, ((b.close - stop_p) / b.close) * 100.0)
        return TradeSignal(
            engine_id=self.engine_id,
            engine_name=self.engine_name,
            symbol=symbol,
            direction="LONG",
            date=b.date,
            entry_price=round(b.close, 2),
            stop_price=round(stop_p, 2),
            stop_distance_pct=round(stop_d, 2),
            target_description=f"Normalizacion a SMA(20) ({b.sma20:.2f}) o RSI(2)>82",
            reason=reason,
            meta_confidence=self.compute_meta_confidence(b, "LONG", 1.20),
        )
