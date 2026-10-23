"""
Gestor Orientado a Objetos de Riesgo Cuantitativo, Meta-Labeling, Kelly Fraccional
y Volatility Targeting (MetaLabelRiskManager).
"""

from typing import Dict
from aegis_quant.models.market_models import EnrichedBar


class MetaLabelRiskManager:
    """
    Implementa la Cúspide de la Pirámide en Gestión de Capital (Sin Apalancamiento Oculto):
      1. Position Sizing por Riesgo Fijo + Multiplicador de Convicción (Meta-Labeling / Kelly Fraccional)
      2. Filtro de Régimen Institucional Multicapa (Precio SMA50/SMA200 + Nivel VIX + Estructura VIX/VIX3M)
      3. Volatility Targeting Dinámico + Dual Momentum sobre la Liquidez Ociosa (Anti-Cash-Drag)
    """

    def __init__(
        self,
        base_risk_pct: float = 2.5,
        max_tactical_weight: float = 0.85,
        target_vol_pct: float = 16.0,
        use_meta_confidence: bool = True,
    ):
        self.base_risk_pct = base_risk_pct
        self.max_tactical_weight = max_tactical_weight
        self.target_vol_pct = target_vol_pct
        self.use_meta_confidence = use_meta_confidence

    def compute_tactical_weight(
        self,
        stop_distance_pct: float,
        meta_confidence: float = 1.0,
        engine_id: str = "",
    ) -> float:
        eff_stop = max(1.35, stop_distance_pct)
        conf_mult = meta_confidence if self.use_meta_confidence else 1.0
        raw_w = (self.base_risk_pct * conf_mult) / eff_stop
        # Presupuesto de riesgo equilibrado por familia de motor para que un trade CTA largo
        # de 30 días nunca bloquee la liquidez de los motores rápidos de 4 días (M1/M2/M3/M5).
        engine_cap = 0.40 if engine_id == "M4_CTA_TREND" else self.max_tactical_weight
        return round(min(engine_cap, max(0.15, raw_w)), 4)

    def classify_regime(self, spy_bar: EnrichedBar) -> str:
        """
        Clasifica el régimen macroeconómico combinando alineación estructural de medias
        (Close > SMA50 > SMA200), volatilidad implícita (VIX) y Estructura Temporal (VIX / VIX3M).
        """
        clean_bull_trend = (
            spy_bar.close > spy_bar.sma200
            and spy_bar.sma50 > spy_bar.sma200
            and spy_bar.close > spy_bar.sma50
        )
        low_stress_vol = spy_bar.vix_close < 21.0 and spy_bar.vts_ratio < 0.96

        if clean_bull_trend and low_stress_vol:
            return "BULL_QUIET_CONTANGO"
        elif clean_bull_trend and spy_bar.vts_ratio < 1.00 and spy_bar.vix_close < 24.0:
            return "BULL_MODERATE_VOL"
        elif spy_bar.close > spy_bar.sma200 and spy_bar.vts_ratio >= 1.00:
            return "BULL_STRESS_BACKWARDATION"
        else:
            if spy_bar.vts_ratio >= 1.00:
                return "BEAR_CRISIS_BACKWARDATION"
            return "BEAR_DEFENSIVE"

    def compute_elite_core_allocation(
        self,
        bars_by_sym: Dict[str, EnrichedBar],
        idle_capital_fraction: float = 1.0,
    ) -> Dict[str, float]:
        """
        Asigna únicamente el Capital Ocioso (1.0 - Exposición Táctica Activa), garantizando
        que la suma total (Táctico + Core) jamás supere el 100% del capital (0% deuda/margen):
          - En Régimen BULL_QUIET_CONTANGO: invierte el capital ocioso combinando Dual-Momentum
            (SPY + QQQ) escalado por Volatility Targeting.
          - En Régimen BULL_MODERATE_VOL: invierte el 50% del capital ocioso en SPY/GLD.
          - En Régimen Bajista o Backwardation (VIX/VIX3M >= 1.0): 0% bolsa pasiva (cero whipsaws)
            y rotación defensiva de hasta un 30% del capital ocioso hacia Oro (GLD) o Bonos (TLT)
            únicamente si están en tendencia alcista confirmada.
        """
        if idle_capital_fraction <= 0.02:
            return {}

        spy = bars_by_sym.get("SPY")
        if spy is None:
            return {}

        alloc: Dict[str, float] = {}
        regime = self.classify_regime(spy)

        if regime == "BULL_QUIET_CONTANGO":
            vol_scalar = min(1.0, max(0.65, self.target_vol_pct / max(10.0, spy.realized_vol20)))
            eff_idle = idle_capital_fraction * vol_scalar
            qqq = bars_by_sym.get("QQQ")

            if qqq and qqq.close > qqq.sma50 > qqq.sma200 and qqq.mom60_vol_adj > spy.mom60_vol_adj:
                alloc["SPY"] = round(eff_idle * 0.55, 4)
                alloc["QQQ"] = round(eff_idle * 0.45, 4)
            else:
                alloc["SPY"] = round(eff_idle * 0.85, 4)
                if qqq and qqq.close > qqq.sma200:
                    alloc["QQQ"] = round(eff_idle * 0.15, 4)

        elif regime == "BULL_MODERATE_VOL":
            eff_idle = idle_capital_fraction * 0.50
            alloc["SPY"] = round(eff_idle, 4)

        else:
            # En estrés de volatilidad o mercado bajista: 0% exposición pasiva a SPY/QQQ.
            # Rotación Crisis-Alpha prudente hacia Oro (GLD) si presenta tendencia y momentum fuerte.
            gld = bars_by_sym.get("GLD")
            if gld and gld.close > gld.sma50 > gld.sma200 and gld.mom60_vol_adj > 0.55:
                alloc["GLD"] = round(idle_capital_fraction * 0.30, 4)

        return alloc
