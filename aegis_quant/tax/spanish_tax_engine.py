"""
Módulo Fiscal Automático AEAT / IRPF para Residentes en España (aegis_quant/tax/spanish_tax_engine.py).

Implementa la normativa tributaria vigente de la Agencia Tributaria (Ley 35/2006 del IRPF):
  1. Conversión independiente a Euros (EUR) en fecha de adquisición y en fecha de transmisión
     según el tipo de cambio oficial EUR/USD del Banco Central Europeo (Consulta DGT V1097-19).
  2. Emparejamiento estricto de lotes por antigüedad FIFO (First-In, First-Out, Art. 37.2 LIRPF)
     agrupado por valor homogéneo (ISIN UCITS).
  3. Detector automático de la Regla Antiaplicación de Pérdidas de los 2 Meses (Art. 33.5.f LIRPF):
     difiere temporalmente las minusvalías si existen recompras de valores homogéneos (mismo ISIN)
     en los +-60 días naturales alrededor de la venta con pérdida mientras subsistan títulos en cartera,
     liberándolas automáticamente cuando se transmite la totalidad sin recompra posterior en 60 días.
  4. Cálculo progresivo de la Base Imponible del Ahorro (19% - 28%) y compensación de saldos
     negativos durante los 4 ejercicios fiscales siguientes (Art. 49 LIRPF).
  5. Monitor patrimonial del Modelo 720 (umbral informativo de 50.000 EUR en bróker extranjero)
     y generación de resumen directo para Renta WEB (Apartado F2, Casillas 0326-0335) + exportación CSV.
"""

import csv
import io
import json
import os
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from aegis_quant.live.config_store import atomic_write_json

MODELO_720_THRESHOLD_EUR = 50000.0

# Escala progresiva vigente Base Imponible del Ahorro (IRPF España)
SPANISH_SAVINGS_BRACKETS: List[Tuple[float, float]] = [
    (6000.0, 0.19),
    (50000.0, 0.21),
    (200000.0, 0.23),
    (300000.0, 0.27),
    (float("inf"), 0.28),
]

# Catálogo oficial de equivalencias UCITS (Opción A: Tradegate Exchange en EUR)
UCITS_CATALOG: Dict[str, Dict[str, str]] = {
    "SPY": {
        "ucits_ticker": "SXR8 / SPYL",
        "primary_ucits": "SXR8",
        "isin": "IE00B5BMR087",
        "issuer": "iShares Core S&P 500 UCITS ETF (Acc)",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "SXR8": {
        "ucits_ticker": "SXR8",
        "primary_ucits": "SXR8",
        "isin": "IE00B5BMR087",
        "issuer": "iShares Core S&P 500 UCITS ETF (Acc)",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "CSPX": {
        "ucits_ticker": "CSPX",
        "primary_ucits": "SXR8",
        "isin": "IE00B5BMR087",
        "issuer": "iShares Core S&P 500 UCITS ETF (Acc)",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "SPYL": {
        "ucits_ticker": "SPYL",
        "primary_ucits": "SPYL",
        "isin": "IE000XZSV718",
        "issuer": "SPDR S&P 500 UCITS ETF (Acc)",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "QQQ": {
        "ucits_ticker": "EQQQ",
        "primary_ucits": "EQQQ",
        "isin": "IE0032077012",
        "issuer": "Invesco EQQQ Nasdaq-100 UCITS ETF",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "EQQQ": {
        "ucits_ticker": "EQQQ",
        "primary_ucits": "EQQQ",
        "isin": "IE0032077012",
        "issuer": "Invesco EQQQ Nasdaq-100 UCITS ETF",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "GLD": {
        "ucits_ticker": "4GLD / SGLD",
        "primary_ucits": "SGLD",
        "isin": "IE00B579F325",
        "issuer": "Invesco Physical Gold ETC",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "SGLD": {
        "ucits_ticker": "SGLD",
        "primary_ucits": "SGLD",
        "isin": "IE00B579F325",
        "issuer": "Invesco Physical Gold ETC",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "4GLD": {
        "ucits_ticker": "4GLD",
        "primary_ucits": "4GLD",
        "isin": "DE000A0S9GB0",
        "issuer": "Xetra-Gold ETC",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "TLT": {
        "ucits_ticker": "DTLA",
        "primary_ucits": "DTLA",
        "isin": "IE00BFM6TC58",
        "issuer": "iShares USD Treasury Bond 20+yr UCITS ETF (Acc)",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "DTLA": {
        "ucits_ticker": "DTLA",
        "primary_ucits": "DTLA",
        "isin": "IE00BFM6TC58",
        "issuer": "iShares USD Treasury Bond 20+yr UCITS ETF (Acc)",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "USO": {
        "ucits_ticker": "CRUD",
        "primary_ucits": "CRUD",
        "isin": "GB00B15KXV33",
        "issuer": "WisdomTree WTI Crude Oil ETC",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "CRUD": {
        "ucits_ticker": "CRUD",
        "primary_ucits": "CRUD",
        "isin": "GB00B15KXV33",
        "issuer": "WisdomTree WTI Crude Oil ETC",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "ZS": {
        "ucits_ticker": "SOYB",
        "primary_ucits": "SOYB",
        "isin": "GB00B15KY211",
        "issuer": "WisdomTree Soybeans ETC",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "SOYB": {
        "ucits_ticker": "SOYB",
        "primary_ucits": "SOYB",
        "isin": "GB00B15KY211",
        "issuer": "WisdomTree Soybeans ETC",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
    "DXS3": {
        "ucits_ticker": "DXS3",
        "primary_ucits": "DXS3",
        "isin": "LU0322251520",
        "issuer": "Xtrackers S&P 500 Inverse Daily Swap UCITS ETF (-1x)",
        "venue": "Tradegate (TGATE)",
        "currency": "EUR",
    },
}

# Tabla base determinista de referencias históricas EUR/USD del BCE para funcionamiento offline
_HISTORICAL_ECB_ANCHORS: Dict[str, float] = {
    "2020": 1.1420,
    "2021": 1.1827,
    "2022": 1.0530,
    "2023": 1.0813,
    "2024": 1.0824,
    "2025": 1.0850,
    "2026": 1.0860,
}


def map_to_ucits_metadata(symbol: str) -> Dict[str, str]:
    """Devuelve metadatos UCITS e ISIN homogéneo para cualquier ticker interno o europeo."""
    clean = str(symbol or "SPY").strip().upper()
    if clean in UCITS_CATALOG:
        return dict(UCITS_CATALOG[clean])
    return {
        "ucits_ticker": clean,
        "primary_ucits": clean,
        "isin": f"SIM-{clean}",
        "issuer": f"Instrumento Cotizado ({clean})",
        "venue": "Tradegate / IBKR",
        "currency": "USD",
    }


def calculate_spanish_savings_irpf(taxable_gain: float) -> float:
    """
    Calcula la cuota íntegra estatal+autonómica de la Base Imponible del Ahorro en España
    aplicando los tramos progresivos marginales (19%, 21%, 23%, 27%, 28%).
    """
    if taxable_gain <= 0.0:
        return 0.0

    remaining = float(taxable_gain)
    prev_limit = 0.0
    total_tax = 0.0

    for upper_limit, rate in SPANISH_SAVINGS_BRACKETS:
        if remaining <= 0.0:
            break
        band_width = upper_limit - prev_limit
        taxable_in_band = min(remaining, band_width)
        total_tax += taxable_in_band * rate
        remaining -= taxable_in_band
        prev_limit = upper_limit

    return round(total_tax, 2)


class ECBExchangeRateProvider:
    """
    Proveedor de tipos de cambio diarios oficiales EUR/USD del Banco Central Europeo (BCE).
    Cachea los cambios en disco de forma atómica (`data/fx_eurusd_ecb.json`) y soporta modo
    offline determinista para no bloquear jamás la ejecución de órdenes ni tests unitarios.
    """

    def __init__(self, data_dir: str, allow_network: bool = False):
        self.data_dir = data_dir
        self.allow_network = allow_network
        os.makedirs(self.data_dir, exist_ok=True)
        self.cache_path = os.path.join(self.data_dir, "fx_eurusd_ecb.json")
        self._rates: Dict[str, float] = self._load_cache()

    def _load_cache(self) -> Dict[str, float]:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return {str(k): float(v) for k, v in data.items()}
            except Exception:
                pass
        return {}

    def _save_cache(self) -> None:
        try:
            atomic_write_json(self.cache_path, self._rates)
        except Exception:
            pass

    def get_eur_usd_rate(self, iso_date: str) -> float:
        """
        Devuelve cuántos USD equivalen a 1 EUR (`1 EUR = X USD`, ej. `1.0860`) en `iso_date`.
        Importe en EUR = Importe en USD / get_eur_usd_rate(fecha).
        """
        day_str = str(iso_date or "")[:10]
        if len(day_str) != 10:
            day_str = datetime.now().strftime("%Y-%m-%d")

        if day_str in self._rates:
            return self._rates[day_str]

        if self.allow_network:
            fetched = self._fetch_frankfurter_ecb(day_str)
            if fetched is not None and fetched > 0.2:
                self._rates[day_str] = round(fetched, 5)
                self._save_cache()
                return self._rates[day_str]

        # Buscar día previo más cercano en caché (fines de semana / festivos TARGET2)
        prior_keys = [k for k in self._rates.keys() if k <= day_str]
        if prior_keys:
            return self._rates[max(prior_keys)]

        yr = day_str[:4]
        return _HISTORICAL_ECB_ANCHORS.get(yr, 1.0860)

    @staticmethod
    def _fetch_frankfurter_ecb(day_str: str) -> Optional[float]:
        """Consulta el fixing oficial del BCE vía Frankfurter API pública (sin API key)."""
        try:
            today_iso = date.today().isoformat()
            q_date = min(day_str, today_iso)
            url = f"https://api.frankfurter.app/{q_date}?from=EUR&to=USD"
            req = urllib.request.Request(url, headers={"User-Agent": "AegisQuant/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                usd_rate = payload.get("rates", {}).get("USD")
                if usd_rate:
                    return float(usd_rate)
        except Exception:
            return None
        return None


def compute_backtest_tax_waterfall(mode_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcula la cascada histórica auditada (2007–2026) para un residente fiscal en España:
      - Curva Bruta del algoritmo (`gross_eq`).
      - Curva Neta Operativa (`op_net_eq`): descontando comisiones IBKR Tiered (0.05%),
        slippage/horquilla (0.02%) y TER anual ponderado de los ETFs UCITS (0.10%).
      - Curva Neta en Bolsillo tras IRPF (`net_eq`): liquidando anualmente la escala progresiva
        de la Base del Ahorro (19%-28%) y aplicando compensación de pérdidas durante 4 ejercicios.
      - Comparativa frente a S&P 500 Buy & Hold neto tras TER (0.07%) e IRPF único al final.
    """
    initial_capital = float(mode_result.get("initial_capital", 10000.0))
    yearly = mode_result.get("yearly", [])
    monthly_curve = mode_result.get("monthly_curve", [])

    # Costes unitarios realistas en Interactive Brokers (Europa / Tradegate):
    # - 0.10% TER anual medio ponderado en ETFs UCITS de acumulación
    # - 0.015% impacto neto sobre el total de cartera por cada operación táctica ejecutada
    #   (comisión IBKR Tiered 0.05% + spread 0.02% ponderado por rotación neta sobre el Core)
    annual_etf_ter_pct = 0.0010
    per_trade_portfolio_fee_pct = 0.00015

    net_cap = initial_capital
    op_net_cap = initial_capital
    total_tax_paid = 0.0
    total_op_fees = 0.0

    # Cola FIFO de pérdidas pendientes de compensar (máximo 4 ejercicios siguientes, Art. 49 LIRPF)
    loss_carry_queue: List[List[float]] = []  # elementos [year_int, remaining_loss_usd]

    yearly_breakdown: List[Dict[str, Any]] = []
    year_scale_map: Dict[str, Tuple[float, float, float, float, float, float]] = {}

    gross_track = initial_capital
    for y_row in yearly:
        yr_str = str(y_row["year"])
        yr_int = int(yr_str)
        gross_ret_pct = float(y_row["bot_ret_pct"])
        trades_cnt = int(y_row.get("trades", 0))

        gross_start = gross_track
        gross_end = gross_start * (1.0 + gross_ret_pct / 100.0)
        gross_track = gross_end

        # 1. Evolución de la curva Neta Operativa (pre-impuestos)
        annual_fee_rate = annual_etf_ter_pct + trades_cnt * per_trade_portfolio_fee_pct
        op_start = op_net_cap
        op_end = max(0.0, op_start * (1.0 + (gross_ret_pct / 100.0) - annual_fee_rate))
        op_net_cap = op_end

        # 2. Evolución de la curva Neta tras IRPF anual (con reinversión compuesta)
        yr_start_net = net_cap
        gross_gain_on_net_base = yr_start_net * (gross_ret_pct / 100.0)
        op_fees_usd = round(yr_start_net * annual_fee_rate, 2)
        total_op_fees += op_fees_usd

        realized_gain = round(gross_gain_on_net_base - op_fees_usd, 2)

        # Caducar pérdidas con antigüedad > 4 años
        loss_carry_queue = [item for item in loss_carry_queue if (yr_int - int(item[0])) <= 4 and item[1] > 0.0]

        loss_offset_used = 0.0
        taxable_base = 0.0
        tax_paid = 0.0

        if realized_gain < 0.0:
            loss_carry_queue.append([yr_int, abs(realized_gain)])
        elif realized_gain > 0.0:
            rem_gain = realized_gain
            for bucket in loss_carry_queue:
                if rem_gain <= 0.0:
                    break
                used = min(rem_gain, bucket[1])
                bucket[1] = round(bucket[1] - used, 2)
                rem_gain = round(rem_gain - used, 2)
                loss_offset_used = round(loss_offset_used + used, 2)
            loss_carry_queue = [b for b in loss_carry_queue if b[1] > 0.005]
            taxable_base = round(max(0.0, rem_gain), 2)
            tax_paid = calculate_spanish_savings_irpf(taxable_base)

        total_tax_paid += tax_paid
        net_end = round(yr_start_net + realized_gain - tax_paid, 2)
        net_ret_pct = ((net_end - yr_start_net) / yr_start_net) * 100.0 if yr_start_net > 0 else 0.0
        eff_rate_pct = (tax_paid / taxable_base * 100.0) if taxable_base > 0 else 0.0
        pending_loss = round(sum(b[1] for b in loss_carry_queue), 2)

        yearly_breakdown.append({
            "year": yr_str,
            "start_capital": round(yr_start_net, 2),
            "gross_ret_pct": round(gross_ret_pct, 2),
            "operational_fees": op_fees_usd,
            "realized_gain_usd": realized_gain,
            "loss_offset_used": round(loss_offset_used, 2),
            "taxable_base": taxable_base,
            "tax_paid": round(tax_paid, 2),
            "effective_rate_pct": round(eff_rate_pct, 1),
            "loss_carried_forward": pending_loss,
            "net_end_equity": net_end,
            "net_ret_pct": round(net_ret_pct, 2),
        })

        year_scale_map[yr_str] = (
            gross_start,
            gross_end,
            op_start,
            op_end,
            yr_start_net,
            net_end,
        )
        net_cap = net_end

    # Construir curva temporal continua alineada con monthly_curve
    net_curve: List[Dict[str, Any]] = []
    for pt in monthly_curve:
        d = pt["date"]
        yr = d[:4]
        g_eq = float(pt["bot_eq"])
        s_eq = float(pt["spy_eq"])
        if yr in year_scale_map:
            g_s, g_e, op_s, op_e, n_s, n_e = year_scale_map[yr]
            if abs(g_e - g_s) > 1e-6:
                frac = (g_eq - g_s) / (g_e - g_s)
                op_pt = op_s + frac * (op_e - op_s)
                net_pt = n_s + frac * (n_e - n_s)
            else:
                ratio = g_eq / max(1.0, g_s)
                op_pt = op_s * ratio
                net_pt = n_s * ratio
        else:
            op_pt = g_eq
            net_pt = g_eq

        net_curve.append({
            "date": d,
            "gross_eq": round(g_eq, 2),
            "op_net_eq": round(max(100.0, op_pt), 2),
            "net_eq": round(max(100.0, net_pt), 2),
            "spy_eq": round(s_eq, 2),
        })

    # Métricas consolidadas 2007-2026
    gross_final = float(mode_result["final_equity"])
    gross_cagr = float(mode_result["cagr_pct"])
    n_years = (
        math.log(gross_final / initial_capital) / math.log(1.0 + gross_cagr / 100.0)
        if gross_cagr > 0 and gross_final > initial_capital
        else max(1.0, len(yearly))
    )

    op_net_cagr = ((op_net_cap / initial_capital) ** (1.0 / n_years) - 1.0) * 100.0
    net_cagr = ((net_cap / initial_capital) ** (1.0 / n_years) - 1.0) * 100.0
    net_total_ret = ((net_cap - initial_capital) / initial_capital) * 100.0

    # S&P 500 Buy & Hold con TER UCITS (0.07% anual) y tributación única al reembolsar al final
    spy_gross_final = float(mode_result["spy_final_equity"])
    spy_after_ter = spy_gross_final * ((1.0 - 0.0007) ** n_years)
    spy_gain = max(0.0, spy_after_ter - initial_capital)
    spy_tax = calculate_spanish_savings_irpf(spy_gain)
    spy_net_final = round(spy_after_ter - spy_tax, 2)

    op_drag = round(gross_cagr - op_net_cagr, 2)
    tax_drag = round(op_net_cagr - net_cagr, 2)
    total_drag = round(gross_cagr - net_cagr, 2)
    wealth_ratio = round(net_cap / max(1.0, spy_net_final), 2)

    return {
        "profile": {
            "taxpayer_type": "Persona física residente en España (IRPF)",
            "tax_base": "Base Imponible del Ahorro (Ganancias Patrimoniales FIFO)",
            "loss_carryforward_years": 4,
            "operational_fees_included": True,
            "broker_pricing": "Interactive Brokers Tiered + Tradegate (0.05% orden)",
            "etf_ter_included": "0.10% medio ponderado anual (ETFs UCITS Acumulación)",
            "slippage_included": "0.02% por operación (órdenes limitadas)",
        },
        "metrics": {
            "initial_capital": round(initial_capital, 2),
            "gross_final_equity": round(gross_final, 2),
            "gross_cagr_pct": round(gross_cagr, 2),
            "gross_total_return_pct": round(float(mode_result["total_return_pct"]), 2),
            "op_net_final_equity": round(op_net_cap, 2),
            "op_net_cagr_pct": round(op_net_cagr, 2),
            "net_final_equity": round(net_cap, 2),
            "net_cagr_pct": round(net_cagr, 2),
            "net_total_return_pct": round(net_total_ret, 2),
            "total_operational_fees_usd": round(total_op_fees, 2),
            "total_tax_paid_usd": round(total_tax_paid, 2),
            "total_friction_cagr_pct": total_drag,
            "op_drag_pct": op_drag,
            "tax_drag_pct": tax_drag,
            "spy_final_equity": round(spy_gross_final, 2),
            "spy_cagr_pct": round(float(mode_result["spy_cagr_pct"]), 2),
            "spy_net_final_equity": spy_net_final,
            "net_wealth_ratio_vs_spy_net": wealth_ratio,
        },
        "yearly_breakdown": yearly_breakdown,
        "net_curve": net_curve,
    }


import math


@dataclass
class _OpenFifoLot:
    lot_id: int
    isin: str
    symbol: str
    ucits_ticker: str
    direction: str  # "LONG" | "SHORT"
    open_date: str
    qty_initial: float
    qty_remaining: float
    unit_price_ccy: float
    currency: str
    fx_eur_usd: float
    unit_fee_eur: float


@dataclass
class ClosedFifoTransmission:
    tx_id: int
    lot_id: int
    isin: str
    symbol: str
    ucits_ticker: str
    issuer: str
    direction: str
    acquisition_date: str
    transmission_date: str
    tax_year: str
    qty: float
    fx_acquisition: float
    fx_transmission: float
    acquisition_value_eur: float
    transmission_value_eur: float
    fees_eur: float
    gross_gain_eur: float
    remaining_homogeneous_qty: float
    blocked_2m: bool = False
    unblocked_date: Optional[str] = None
    effective_tax_year: str = ""
    rule_2m_note: str = "Computable"
    motor: str = ""

    @property
    def computable_gain_eur(self) -> float:
        return 0.0 if self.blocked_2m else self.gross_gain_eur

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "isin": self.isin,
            "symbol": self.symbol,
            "ucits_ticker": self.ucits_ticker,
            "issuer": self.issuer,
            "direction": self.direction,
            "acquisition_date": self.acquisition_date,
            "transmission_date": self.transmission_date,
            "tax_year": self.tax_year,
            "effective_tax_year": self.effective_tax_year or self.tax_year,
            "qty": round(self.qty, 4),
            "fx_acquisition": round(self.fx_acquisition, 4),
            "fx_transmission": round(self.fx_transmission, 4),
            "acquisition_value_eur": round(self.acquisition_value_eur, 2),
            "transmission_value_eur": round(self.transmission_value_eur, 2),
            "fees_eur": round(self.fees_eur, 2),
            "gross_gain_eur": round(self.gross_gain_eur, 2),
            "blocked_2m": self.blocked_2m,
            "computable_gain_eur": round(self.computable_gain_eur, 2),
            "rule_2m_note": self.rule_2m_note,
            "motor": self.motor,
        }


class SpanishTaxAuditor:
    """
    Motor de Auditoría Fiscal Automática sobre el Libro Contable Inmutable (`ledger_*.jsonl`).
    Aplica conversión diaria EUR/USD del BCE, método FIFO por ISIN, Regla Antiaplicación de los
    2 Meses (Art. 33.5.f LIRPF), casillas Renta WEB y vigilancia del Modelo 720.
    """

    def __init__(self, base_dir: str, allow_network_fx: bool = False):
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data")
        self.fx_provider = ECBExchangeRateProvider(self.data_dir, allow_network=allow_network_fx)

    def load_ledger_entries(self, env: str = "PAPER") -> List[Dict[str, Any]]:
        filename = "ledger_real_trades.jsonl" if env == "LIVE_REAL" else "ledger_paper_trades.jsonl"
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            return []
        rows: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows

    def audit_environment(
        self,
        env: str = "PAPER",
        tax_year: str = "ALL",
        current_equity_usd: Optional[float] = None,
        prior_loss_carryforward_eur: float = 0.0,
        reference_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        entries = self.load_ledger_entries(env=env)
        if current_equity_usd is None:
            state_file = "bot_live_state_real.json" if env == "LIVE_REAL" else "bot_live_state.json"
            state_path = os.path.join(self.data_dir, state_file)
            current_equity_usd = 10000.0
            if os.path.exists(state_path):
                try:
                    with open(state_path, "r", encoding="utf-8") as sf:
                        st = json.load(sf)
                        current_equity_usd = float(st.get("account", {}).get("total_equity_usd", 10000.0))
                except Exception:
                    pass

        return self.audit_entries(
            entries=entries,
            env=env,
            tax_year=tax_year,
            current_equity_usd=current_equity_usd,
            prior_loss_carryforward_eur=prior_loss_carryforward_eur,
            reference_date=reference_date,
        )

    def audit_entries(
        self,
        entries: List[Dict[str, Any]],
        env: str = "PAPER",
        tax_year: str = "ALL",
        current_equity_usd: float = 10000.0,
        prior_loss_carryforward_eur: float = 0.0,
        reference_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        ref_iso = (reference_date or date.today().isoformat())[:10]
        open_long_lots: Dict[str, List[_OpenFifoLot]] = {}
        open_short_lots: Dict[str, List[_OpenFifoLot]] = {}
        closed_txs: List[ClosedFifoTransmission] = []

        # Registro cronológico de compras y liquidaciones totales por ISIN para evaluar la regla de 2 meses
        acquisition_events: Dict[str, List[Tuple[str, int, float]]] = {}  # isin -> [(date, lot_id, qty)]
        zero_holding_events: Dict[str, List[str]] = {}  # isin -> [dates where remaining_qty reached 0]

        lot_seq = 0
        tx_seq = 0

        for raw in entries:
            status = str(raw.get("status", "FILLED")).upper()
            if status not in ("FILLED", "ACCEPTED", "COMPLETED"):
                continue

            ts = str(raw.get("timestamp") or raw.get("time") or ref_iso)
            op_date = ts[:10]
            sym = str(raw.get("symbol") or "SPY").upper()
            side = str(raw.get("side") or "BUY").upper()
            motor = str(raw.get("motor") or "")

            try:
                qty = float(raw.get("qty", 0.0))
            except (TypeError, ValueError):
                qty = 0.0
            price = float(raw.get("price_usd") or raw.get("price") or 0.0)
            notional = float(raw.get("notional_usd") or (qty * price) or 0.0)
            if qty <= 0.0 and price > 0.0 and notional > 0.0:
                qty = round(notional / price, 6)
            if qty <= 1e-7 or price <= 0.0:
                continue

            meta = map_to_ucits_metadata(sym)
            isin = str(raw.get("isin") or meta["isin"])
            ucits_ticker = str(raw.get("ucits_ticker") or meta["primary_ucits"])
            issuer = meta["issuer"]
            ccy = str(raw.get("currency") or "USD").upper()

            if ccy == "EUR":
                fx = 1.0
            else:
                fx = float(raw.get("fx_eur_usd") or self.fx_provider.get_eur_usd_rate(op_date))
                if fx <= 0.0:
                    fx = 1.0860

            fee_ccy = float(raw.get("commission_usd") or raw.get("commission") or 0.0)
            fee_eur_total = fee_ccy / fx
            unit_fee_eur = fee_eur_total / qty

            if side == "BUY":
                lot_seq += 1
                lot = _OpenFifoLot(
                    lot_id=lot_seq,
                    isin=isin,
                    symbol=sym,
                    ucits_ticker=ucits_ticker,
                    direction="LONG",
                    open_date=op_date,
                    qty_initial=qty,
                    qty_remaining=qty,
                    unit_price_ccy=price,
                    currency=ccy,
                    fx_eur_usd=fx,
                    unit_fee_eur=unit_fee_eur,
                )
                open_long_lots.setdefault(isin, []).append(lot)
                acquisition_events.setdefault(isin, []).append((op_date, lot_seq, qty))

            elif side in ("SELL", "SELL_PARTIAL") or (
                side == "LIQUIDATE_ALL" and open_long_lots.get(isin)
            ):
                lots = open_long_lots.get(isin, [])
                rem_to_sell = qty if side != "LIQUIDATE_ALL" else max(qty, sum(l.qty_remaining for l in lots))
                while rem_to_sell > 1e-7 and lots:
                    head = lots[0]
                    matched = min(rem_to_sell, head.qty_remaining)
                    head.qty_remaining = round(head.qty_remaining - matched, 8)
                    rem_to_sell = round(rem_to_sell - matched, 8)
                    if head.qty_remaining <= 1e-7:
                        lots.pop(0)

                    acq_eur = matched * (head.unit_price_ccy / head.fx_eur_usd) + matched * head.unit_fee_eur
                    trans_eur = matched * (price / fx) - matched * unit_fee_eur
                    gain_eur = trans_eur - acq_eur
                    rem_homog = round(sum(l.qty_remaining for l in lots), 6)

                    tx_seq += 1
                    closed_txs.append(
                        ClosedFifoTransmission(
                            tx_id=tx_seq,
                            lot_id=head.lot_id,
                            isin=isin,
                            symbol=sym,
                            ucits_ticker=ucits_ticker,
                            issuer=issuer,
                            direction="LONG",
                            acquisition_date=head.open_date,
                            transmission_date=op_date,
                            tax_year=op_date[:4],
                            effective_tax_year=op_date[:4],
                            qty=matched,
                            fx_acquisition=head.fx_eur_usd,
                            fx_transmission=fx,
                            acquisition_value_eur=acq_eur,
                            transmission_value_eur=trans_eur,
                            fees_eur=matched * (head.unit_fee_eur + unit_fee_eur),
                            gross_gain_eur=gain_eur,
                            remaining_homogeneous_qty=rem_homog,
                            motor=motor,
                        )
                    )
                    if rem_homog <= 1e-7:
                        zero_holding_events.setdefault(isin, []).append(op_date)

            elif side == "SELL_SHORT":
                lot_seq += 1
                lot = _OpenFifoLot(
                    lot_id=lot_seq,
                    isin=isin,
                    symbol=sym,
                    ucits_ticker=ucits_ticker,
                    direction="SHORT",
                    open_date=op_date,
                    qty_initial=qty,
                    qty_remaining=qty,
                    unit_price_ccy=price,
                    currency=ccy,
                    fx_eur_usd=fx,
                    unit_fee_eur=unit_fee_eur,
                )
                open_short_lots.setdefault(isin, []).append(lot)

            elif side in ("BUY_TO_COVER", "LIQUIDATE_ALL") and open_short_lots.get(isin):
                s_lots = open_short_lots.get(isin, [])
                rem_cover = qty if side != "LIQUIDATE_ALL" else max(qty, sum(l.qty_remaining for l in s_lots))
                while rem_cover > 1e-7 and s_lots:
                    head = s_lots[0]
                    matched = min(rem_cover, head.qty_remaining)
                    head.qty_remaining = round(head.qty_remaining - matched, 8)
                    rem_cover = round(rem_cover - matched, 8)
                    if head.qty_remaining <= 1e-7:
                        s_lots.pop(0)

                    # En cortos: transmisión = venta inicial; adquisición = recompra de cierre
                    trans_eur = matched * (head.unit_price_ccy / head.fx_eur_usd) - matched * head.unit_fee_eur
                    acq_eur = matched * (price / fx) + matched * unit_fee_eur
                    gain_eur = trans_eur - acq_eur
                    rem_homog = round(sum(l.qty_remaining for l in s_lots), 6)

                    tx_seq += 1
                    closed_txs.append(
                        ClosedFifoTransmission(
                            tx_id=tx_seq,
                            lot_id=head.lot_id,
                            isin=isin,
                            symbol=sym,
                            ucits_ticker=ucits_ticker,
                            issuer=issuer,
                            direction="SHORT",
                            acquisition_date=op_date,
                            transmission_date=op_date,
                            tax_year=op_date[:4],
                            effective_tax_year=op_date[:4],
                            qty=matched,
                            fx_acquisition=fx,
                            fx_transmission=head.fx_eur_usd,
                            acquisition_value_eur=acq_eur,
                            transmission_value_eur=trans_eur,
                            fees_eur=matched * (head.unit_fee_eur + unit_fee_eur),
                            gross_gain_eur=gain_eur,
                            remaining_homogeneous_qty=rem_homog,
                            motor=motor,
                        )
                    )

        # Evaluar Regla Antiaplicación de los 2 Meses (Art. 33.5.f LIRPF, +-60 días naturales)
        self._apply_two_month_wash_sale_rule(
            closed_txs=closed_txs,
            acquisition_events=acquisition_events,
            zero_holding_events=zero_holding_events,
            open_long_lots=open_long_lots,
        )

        # Ventanas activas de bloqueo de 60 días desde pérdidas recientes
        active_lockouts = self._compute_active_60d_lockouts(closed_txs, ref_iso)

        # Años fiscales disponibles en el libro contable
        years_available = sorted({tx.effective_tax_year for tx in closed_txs}, reverse=True)
        current_yr = ref_iso[:4]
        if current_yr not in years_available:
            years_available.insert(0, current_yr)

        # Filtrar por año fiscal solicitado
        if tax_year and tax_year.upper() != "ALL":
            filtered_txs = [tx for tx in closed_txs if tx.effective_tax_year == str(tax_year)]
        else:
            filtered_txs = list(closed_txs)

        gross_gains_eur = round(sum(tx.gross_gain_eur for tx in filtered_txs if tx.gross_gain_eur > 0), 2)
        deductible_losses_eur = round(
            sum(tx.gross_gain_eur for tx in filtered_txs if tx.gross_gain_eur < 0 and not tx.blocked_2m), 2
        )
        deferred_losses_2m_eur = round(
            sum(abs(tx.gross_gain_eur) for tx in filtered_txs if tx.gross_gain_eur < 0 and tx.blocked_2m), 2
        )

        net_before_prior = round(gross_gains_eur + deductible_losses_eur, 2)
        prior_used = round(min(max(0.0, net_before_prior), max(0.0, prior_loss_carryforward_eur)), 2)
        taxable_savings_base_eur = round(max(0.0, net_before_prior - prior_used), 2)
        loss_to_carry_forward_eur = round(abs(min(0.0, net_before_prior)), 2)

        estimated_irpf_eur = calculate_spanish_savings_irpf(taxable_savings_base_eur)
        eff_rate_pct = (
            round((estimated_irpf_eur / taxable_savings_base_eur) * 100.0, 2)
            if taxable_savings_base_eur > 0
            else 0.0
        )

        # Agrupación por Emisor / ISIN para Renta WEB (Apartado F2, Casillas 0326-0335)
        isin_groups: Dict[str, Dict[str, Any]] = {}
        for tx in filtered_txs:
            grp = isin_groups.setdefault(
                tx.isin,
                {
                    "isin": tx.isin,
                    "ucits_ticker": tx.ucits_ticker,
                    "issuer": tx.issuer,
                    "operations_count": 0,
                    "total_acquisition_eur": 0.0,
                    "total_transmission_eur": 0.0,
                    "gross_pnl_eur": 0.0,
                    "deferred_loss_2m_eur": 0.0,
                    "computable_pnl_eur": 0.0,
                },
            )
            grp["operations_count"] += 1
            grp["total_acquisition_eur"] = round(grp["total_acquisition_eur"] + tx.acquisition_value_eur, 2)
            grp["total_transmission_eur"] = round(grp["total_transmission_eur"] + tx.transmission_value_eur, 2)
            grp["gross_pnl_eur"] = round(grp["gross_pnl_eur"] + tx.gross_gain_eur, 2)
            if tx.blocked_2m and tx.gross_gain_eur < 0:
                grp["deferred_loss_2m_eur"] = round(grp["deferred_loss_2m_eur"] + abs(tx.gross_gain_eur), 2)
            grp["computable_pnl_eur"] = round(grp["computable_pnl_eur"] + tx.computable_gain_eur, 2)

        # Monitor Modelo 720 (50.000 EUR en cuentas/valores en el extranjero)
        fx_today = self.fx_provider.get_eur_usd_rate(ref_iso)
        equity_eur = round(float(current_equity_usd) / max(0.2, fx_today), 2)
        m720_pct = round(min(999.0, (equity_eur / MODELO_720_THRESHOLD_EUR) * 100.0), 1)
        m720_required = equity_eur >= MODELO_720_THRESHOLD_EUR

        # Lotes FIFO actualmente abiertos en cartera
        open_lots_summary = []
        for isin_key, l_list in open_long_lots.items():
            for l in l_list:
                if l.qty_remaining > 1e-6:
                    cost_eur = round(
                        l.qty_remaining * (l.unit_price_ccy / l.fx_eur_usd) + l.qty_remaining * l.unit_fee_eur,
                        2,
                    )
                    open_lots_summary.append({
                        "isin": isin_key,
                        "symbol": l.symbol,
                        "ucits_ticker": l.ucits_ticker,
                        "open_date": l.open_date,
                        "qty_remaining": round(l.qty_remaining, 4),
                        "fx_acquisition": round(l.fx_eur_usd, 4),
                        "cost_basis_eur": cost_eur,
                    })

        return {
            "ok": True,
            "environment": env,
            "tax_year": tax_year,
            "reference_date": ref_iso,
            "fx_eur_usd_today": round(fx_today, 4),
            "years_available": years_available,
            "summary": {
                "closed_lots_count": len(filtered_txs),
                "open_lots_count": len(open_lots_summary),
                "gross_gains_eur": gross_gains_eur,
                "deductible_losses_eur": deductible_losses_eur,
                "deferred_losses_2m_eur": deferred_losses_2m_eur,
                "prior_loss_offset_eur": prior_used,
                "taxable_savings_base_eur": taxable_savings_base_eur,
                "loss_carryforward_4y_eur": loss_to_carry_forward_eur,
                "estimated_irpf_eur": estimated_irpf_eur,
                "effective_rate_pct": eff_rate_pct,
            },
            "modelo_720": {
                "threshold_eur": MODELO_720_THRESHOLD_EUR,
                "current_equity_usd": round(float(current_equity_usd), 2),
                "current_equity_eur": equity_eur,
                "threshold_usage_pct": m720_pct,
                "margin_remaining_eur": round(max(0.0, MODELO_720_THRESHOLD_EUR - equity_eur), 2),
                "required": m720_required,
                "status_label": (
                    "Obligatorio (Supera 50.000 € - Presentar Ene-Mar)"
                    if m720_required
                    else "Exento (Inferior a 50.000 €)"
                ),
            },
            "renta_web_f2": {
                "section": "Apartado F2 · Ganancias y pérdidas patrimoniales (Acciones / ETFs negociados)",
                "casillas": "0326 – 0335",
                "total_transmission_eur": round(sum(tx.transmission_value_eur for tx in filtered_txs), 2),
                "total_acquisition_eur": round(sum(tx.acquisition_value_eur for tx in filtered_txs), 2),
                "by_isin": list(isin_groups.values()),
            },
            "active_60d_lockouts": active_lockouts,
            "transmissions": [tx.to_dict() for tx in reversed(filtered_txs)],
            "open_fifo_lots": open_lots_summary,
        }

    @staticmethod
    def _apply_two_month_wash_sale_rule(
        closed_txs: List[ClosedFifoTransmission],
        acquisition_events: Dict[str, List[Tuple[str, int, float]]],
        zero_holding_events: Dict[str, List[str]],
        open_long_lots: Dict[str, List[_OpenFifoLot]],
    ) -> None:
        """
        Aplica el Art. 33.5.f LIRPF (Regla de los 2 meses = +-60 días naturales en valores cotizados):
        Si una transmisión genera pérdida patrimonial y existen compras de valores homogéneos (mismo ISIN)
        distintas del propio lote transmitido dentro de [-60d, +60d]:
          - Si hubo recompra posterior en (0, +60d] o quedaron participaciones de compra previa [-60d, 0),
            la pérdida queda bloqueada salvo que posteriormente el inversor liquide a 0 todo el ISIN y
            permanezca >60 días sin recomprar.
        """
        for tx in closed_txs:
            if tx.direction != "LONG" or tx.gross_gain_eur >= 0.0:
                continue

            try:
                sale_dt = date.fromisoformat(tx.transmission_date)
            except ValueError:
                continue

            win_start = (sale_dt - timedelta(days=60)).isoformat()
            win_end = (sale_dt + timedelta(days=60)).isoformat()

            acqs = acquisition_events.get(tx.isin, [])
            # Compras posteriores dentro de los 60 días siguientes
            subsequent_buys = [
                ev for ev in acqs if tx.transmission_date < ev[0] <= win_end and ev[1] != tx.lot_id
            ]
            # Compras previas dentro de los 60 días anteriores que NO se liquidaron en esta venta
            prior_recent_buys_held = (
                tx.remaining_homogeneous_qty > 1e-7
                and any(
                    win_start <= ev[0] <= tx.transmission_date and ev[1] != tx.lot_id
                    for ev in acqs
                )
            )

            if not subsequent_buys and not prior_recent_buys_held:
                tx.blocked_2m = False
                tx.rule_2m_note = "Pérdida computable (sin recompra en +-60 días)"
                continue

            # Verificar si en una fecha posterior se vendió el 100% del ISIN sin recompra en +60 días
            unblock_dt_str: Optional[str] = None
            last_recompra_date = subsequent_buys[-1][0] if subsequent_buys else tx.transmission_date
            for z_date in zero_holding_events.get(tx.isin, []):
                if z_date <= last_recompra_date:
                    continue
                z_end = (date.fromisoformat(z_date) + timedelta(days=60)).isoformat()
                has_rebuy_after_zero = any(z_date < ev[0] <= z_end for ev in acqs)
                still_open_now = any(l.qty_remaining > 1e-7 for l in open_long_lots.get(tx.isin, []))
                if not has_rebuy_after_zero and not still_open_now:
                    unblock_dt_str = z_date
                    break

            if unblock_dt_str is not None:
                tx.blocked_2m = False
                tx.unblocked_date = unblock_dt_str
                tx.effective_tax_year = unblock_dt_str[:4]
                tx.rule_2m_note = f"Liberada al liquidar posición el {unblock_dt_str}"
            else:
                tx.blocked_2m = True
                tx.rule_2m_note = "Diferida Art. 33.5.f (Recompra homogénea < 2 meses)"

    @staticmethod
    def _compute_active_60d_lockouts(
        closed_txs: List[ClosedFifoTransmission], ref_iso: str
    ) -> List[Dict[str, Any]]:
        """Detecta ventas con pérdida en los últimos 60 días para alertar sobre ventana de recompra."""
        try:
            ref_dt = date.fromisoformat(ref_iso)
        except ValueError:
            return []

        by_isin: Dict[str, Dict[str, Any]] = {}
        for tx in closed_txs:
            if tx.gross_gain_eur >= 0.0:
                continue
            try:
                s_dt = date.fromisoformat(tx.transmission_date)
            except ValueError:
                continue
            days_elapsed = (ref_dt - s_dt).days
            if 0 <= days_elapsed <= 60:
                unlock_dt = (s_dt + timedelta(days=61)).isoformat()
                item = by_isin.setdefault(
                    tx.isin,
                    {
                        "isin": tx.isin,
                        "ucits_ticker": tx.ucits_ticker,
                        "last_loss_sale_date": tx.transmission_date,
                        "unlock_date": unlock_dt,
                        "days_remaining": max(0, 61 - days_elapsed),
                        "loss_at_risk_eur": 0.0,
                    },
                )
                item["loss_at_risk_eur"] = round(item["loss_at_risk_eur"] + abs(tx.gross_gain_eur), 2)
                if tx.transmission_date >= item["last_loss_sale_date"]:
                    item["last_loss_sale_date"] = tx.transmission_date
                    item["unlock_date"] = unlock_dt
                    item["days_remaining"] = max(0, 61 - days_elapsed)
        return list(by_isin.values())

    def export_audit_csv(self, env: str = "PAPER", tax_year: str = "ALL") -> str:
        """
        Genera un fichero CSV (con BOM UTF-8 para apertura directa en Excel en España)
        con el desglose completo de lotes FIFO cerrados y casillas resumen para Renta WEB.
        """
        report = self.audit_environment(env=env, tax_year=tax_year)
        buf = io.StringIO()
        buf.write("\ufeff")  # UTF-8 BOM para compatibilidad directa con Microsoft Excel
        writer = csv.writer(buf, delimiter=";")

        writer.writerow([
            "ID_Transmision",
            "Ejercicio_Fiscal_Imputable",
            "ISIN_Homogeneo",
            "Ticker_Orden",
            "Equivalente_UCITS",
            "Denominacion_Emisor",
            "Direccion",
            "Fecha_Adquisicion",
            "Fecha_Transmision",
            "Participaciones",
            "Cambio_BCE_Compra_EURUSD",
            "Cambio_BCE_Venta_EURUSD",
            "Valor_Adquisicion_EUR",
            "Valor_Transmision_EUR",
            "Comisiones_Incluidas_EUR",
            "Plusvalia_Bruta_EUR",
            "Bloqueada_Regla_2_Meses",
            "Plusvalia_Computable_IRPF_EUR",
            "Observacion_AEAT",
        ])

        for tx in report["transmissions"]:
            writer.writerow([
                tx["tx_id"],
                tx["effective_tax_year"],
                tx["isin"],
                tx["symbol"],
                tx["ucits_ticker"],
                tx["issuer"],
                tx["direction"],
                tx["acquisition_date"],
                tx["transmission_date"],
                f"{tx['qty']:.4f}".replace(".", ","),
                f"{tx['fx_acquisition']:.4f}".replace(".", ","),
                f"{tx['fx_transmission']:.4f}".replace(".", ","),
                f"{tx['acquisition_value_eur']:.2f}".replace(".", ","),
                f"{tx['transmission_value_eur']:.2f}".replace(".", ","),
                f"{tx['fees_eur']:.2f}".replace(".", ","),
                f"{tx['gross_gain_eur']:.2f}".replace(".", ","),
                "SI" if tx["blocked_2m"] else "NO",
                f"{tx['computable_gain_eur']:.2f}".replace(".", ","),
                tx["rule_2m_note"],
            ])

        s = report["summary"]
        writer.writerow([])
        writer.writerow(["RESUMEN ANUAL RENTA WEB (APARTADO F2 - CASILLAS 0326-0335)", "", ""])
        writer.writerow(["Entorno Auditado", report["environment"], ""])
        writer.writerow(["Ejercicio Fiscal", report["tax_year"], ""])
        writer.writerow(["Ganancias Patrimoniales Brutas (EUR)", f"{s['gross_gains_eur']:.2f}".replace(".", ","), ""])
        writer.writerow(["Perdidas Deducibles FIFO (EUR)", f"{s['deductible_losses_eur']:.2f}".replace(".", ","), ""])
        writer.writerow(["Perdidas Diferidas Regla 2 Meses (EUR)", f"{s['deferred_losses_2m_eur']:.2f}".replace(".", ","), ""])
        writer.writerow(["Base Imponible del Ahorro Neta (EUR)", f"{s['taxable_savings_base_eur']:.2f}".replace(".", ","), ""])
        writer.writerow(["Cuota IRPF Estimada (19%-28%) (EUR)", f"{s['estimated_irpf_eur']:.2f}".replace(".", ","), ""])
        writer.writerow(["Estado Modelo 720 (Umbral 50.000 EUR)", report["modelo_720"]["status_label"], ""])

        return buf.getvalue()
