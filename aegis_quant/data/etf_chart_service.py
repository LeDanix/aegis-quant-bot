"""
Servicio de Series Históricas y Cotizaciones de ETFs Operativos (aegis_quant/data/etf_chart_service.py).

Proporciona series diarias OHLCV completas (2006/2007–2026), medias móviles institucionales
SMA(50) y SMA(200), indicador RSI(2) de Wilder, retornos por horizonte temporal y metadatos
de equivalencia europea UCITS en Tradegate (Opción A) para la sección interactiva de ETFs.
"""

import json
import os
import threading
from typing import Any, Dict, List, Optional, Tuple


ETF_UNIVERSE_META: Dict[str, Dict[str, str]] = {
    "SPY": {
        "symbol": "SPY",
        "display_name": "S&P 500 Index ETF",
        "asset_class": "Renta Variable EE. UU. (Gran Capitalización)",
        "ucits_ticker": "SPYL / SXR8",
        "isin": "IE000XZSV718 / IE00B5BMR087",
        "venue": "Tradegate (TGATE) · EUR",
        "ter": "0,03% (SPYL) / 0,07% (SXR8)",
        "engines": "Core Modo 3 · M1 · M2 · M3 (DXS3) · M5 · M6",
    },
    "QQQ": {
        "symbol": "QQQ",
        "display_name": "Nasdaq-100 Technology ETF",
        "asset_class": "Renta Variable EE. UU. (Crecimiento / Tecnología)",
        "ucits_ticker": "EQQQ",
        "isin": "IE0032077012",
        "venue": "Tradegate (TGATE) · EUR",
        "ter": "0,30% (EQQQ)",
        "engines": "Core Modo 3 · M1 · M2 · M3 · M5 · M6",
    },
    "GLD": {
        "symbol": "GLD",
        "display_name": "Physical Gold Bullion ETF",
        "asset_class": "Activo Refugio · Oro Físico",
        "ucits_ticker": "4GLD / SGLD",
        "isin": "DE000A0S9GB0 / IE00B579F325",
        "venue": "Tradegate (TGATE) · EUR",
        "ter": "0,00%–0,12%",
        "engines": "Motor 4 · Tendencia Multi-Activo CTA",
    },
    "TLT": {
        "symbol": "TLT",
        "display_name": "US Treasury Bond 20+ Year ETF",
        "asset_class": "Renta Fija Soberana EE. UU. Largo Plazo",
        "ucits_ticker": "DTLA",
        "isin": "IE00BFM6TC58",
        "venue": "Tradegate (TGATE) · EUR",
        "ter": "0,07% (DTLA)",
        "engines": "Motor 4 · Tendencia Multi-Activo CTA",
    },
    "USO": {
        "symbol": "USO",
        "display_name": "WTI Crude Oil Energy ETF",
        "asset_class": "Materias Primas Energéticas (Petróleo WTI)",
        "ucits_ticker": "CRUD",
        "isin": "GB00B15KXV33",
        "venue": "Tradegate (TGATE) · EUR",
        "ter": "0,49% (CRUD)",
        "engines": "Motor 4 · Tendencia Multi-Activo CTA",
    },
    "ZS": {
        "symbol": "ZS",
        "display_name": "Soybeans Agricultural ETF",
        "asset_class": "Materias Primas Agrícolas (Soja)",
        "ucits_ticker": "SOYB",
        "isin": "GB00B15KY211",
        "venue": "Tradegate (TGATE) · EUR",
        "ter": "0,49% (SOYB)",
        "engines": "Motor 4 · Tendencia Multi-Activo CTA",
    },
}

ORDERED_ETF_SYMBOLS: List[str] = ["SPY", "QQQ", "GLD", "TLT", "USO", "ZS"]


class EtfChartService:
    """Servicio cacheado en memoria con invalidación automática por mtime de fichero."""

    _lock = threading.RLock()
    _series_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data")

    @staticmethod
    def normalize_symbol(symbol: Optional[str]) -> str:
        clean = str(symbol or "SPY").strip().upper()
        if clean == "SOYB":
            return "ZS"
        if clean not in ETF_UNIVERSE_META:
            return "SPY"
        return clean

    def _load_computed_series(self, symbol: str) -> Dict[str, Any]:
        file_path = os.path.join(self.data_dir, f"{symbol}_daily.json")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Serie histórica no encontrada para {symbol}: {file_path}")

        mtime = os.path.getmtime(file_path)
        with self._lock:
            cached = self._series_cache.get(symbol)
            if cached is not None and cached[0] == mtime:
                return cached[1]

        with open(file_path, "r", encoding="utf-8") as f:
            raw_bars = json.load(f)

        # Filtrar barras válidas y ordenar cronológicamente
        bars = [
            b
            for b in raw_bars
            if b.get("date") and float(b.get("close") or 0.0) > 0.0
        ]
        bars.sort(key=lambda x: x["date"])

        dates: List[str] = []
        opens: List[float] = []
        highs: List[float] = []
        lows: List[float] = []
        closes: List[float] = []
        volumes: List[int] = []
        sma50_list: List[float] = []
        sma200_list: List[float] = []

        running_sum50 = 0.0
        running_sum200 = 0.0
        avg_gain_2 = 0.0
        avg_loss_2 = 0.0
        last_rsi2 = 50.0

        for idx, b in enumerate(bars):
            c = float(b["close"])
            o = float(b.get("open") or c)
            h = float(b.get("high") or max(o, c))
            l = float(b.get("low") or min(o, c))
            v = int(float(b.get("volume") or 0))

            dates.append(str(b["date"])[:10])
            opens.append(round(o, 2))
            highs.append(round(h, 2))
            lows.append(round(l, 2))
            closes.append(round(c, 2))
            volumes.append(v)

            running_sum50 += c
            if idx >= 50:
                running_sum50 -= closes[idx - 50]
                sma50_val = running_sum50 / 50.0
            else:
                sma50_val = running_sum50 / (idx + 1)

            running_sum200 += c
            if idx >= 200:
                running_sum200 -= closes[idx - 200]
                sma200_val = running_sum200 / 200.0
            else:
                sma200_val = running_sum200 / (idx + 1)

            sma50_list.append(round(sma50_val, 2))
            sma200_list.append(round(sma200_val, 2))

            if idx > 0:
                diff = c - closes[idx - 1]
                gain = max(0.0, diff)
                loss = max(0.0, -diff)
                if idx == 1:
                    avg_gain_2 = gain
                    avg_loss_2 = loss
                else:
                    avg_gain_2 = (avg_gain_2 + gain) / 2.0
                    avg_loss_2 = (avg_loss_2 + loss) / 2.0
                if avg_loss_2 == 0.0:
                    last_rsi2 = 100.0 if avg_gain_2 > 0 else 50.0
                else:
                    rs = avg_gain_2 / avg_loss_2
                    last_rsi2 = 100.0 - (100.0 / (1.0 + rs))

        n = len(closes)
        last_close = closes[-1] if n else 0.0
        prev_close = closes[-2] if n >= 2 else last_close
        day_change_pct = ((last_close - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0

        def _pct_since(offset: int) -> float:
            if n == 0:
                return 0.0
            ref_idx = max(0, n - 1 - offset)
            ref = closes[ref_idx]
            return round(((last_close - ref) / ref) * 100.0, 2) if ref > 0 else 0.0

        # Retorno YTD (desde último cierre del año anterior)
        last_year_str = dates[-1][:4] if n else "2026"
        ytd_ref = closes[0] if n else 1.0
        for i in range(n - 1, -1, -1):
            if dates[i][:4] < last_year_str:
                ytd_ref = closes[i]
                break
        ret_ytd_pct = round(((last_close - ytd_ref) / ytd_ref) * 100.0, 2) if ytd_ref > 0 else 0.0
        ret_total_pct = round(((last_close - closes[0]) / closes[0]) * 100.0, 2) if n and closes[0] > 0 else 0.0

        w52_highs = highs[max(0, n - 252):] if n else [0.0]
        w52_lows = lows[max(0, n - 252):] if n else [0.0]
        last_sma50 = sma50_list[-1] if n else 0.0
        last_sma200 = sma200_list[-1] if n else 0.0
        dist_sma200_pct = (
            round(((last_close - last_sma200) / last_sma200) * 100.0, 2)
            if last_sma200 > 0
            else 0.0
        )
        is_bull = last_close >= last_sma200

        payload = {
            "meta": dict(ETF_UNIVERSE_META[symbol]),
            "metrics": {
                "as_of_date": dates[-1] if n else "--",
                "bars_count": n,
                "start_date": dates[0] if n else "--",
                "last_close": round(last_close, 2),
                "prev_close": round(prev_close, 2),
                "day_change_pct": round(day_change_pct, 2),
                "ret_1m_pct": _pct_since(21),
                "ret_3m_pct": _pct_since(63),
                "ret_6m_pct": _pct_since(126),
                "ret_ytd_pct": ret_ytd_pct,
                "ret_1y_pct": _pct_since(252),
                "ret_5y_pct": _pct_since(1260),
                "ret_total_pct": ret_total_pct,
                "high_52w": round(max(w52_highs), 2),
                "low_52w": round(min(w52_lows), 2),
                "sma50": last_sma50,
                "sma200": last_sma200,
                "dist_sma200_pct": dist_sma200_pct,
                "rsi2": round(last_rsi2, 1),
                "trend": "ALCISTA" if is_bull else "BAJISTA",
            },
            "series": {
                "dates": dates,
                "opens": opens,
                "highs": highs,
                "lows": lows,
                "closes": closes,
                "volumes": volumes,
                "sma50": sma50_list,
                "sma200": sma200_list,
            },
        }

        with self._lock:
            self._series_cache[symbol] = (mtime, payload)
        return payload

    def get_etf_payload(
        self,
        symbol: Optional[str] = "SPY",
        live_prices: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Devuelve el catálogo completo de los 6 ETFs y la serie detallada del ETF seleccionado."""
        norm_sym = self.normalize_symbol(symbol)
        live_map = live_prices or {}

        catalog: List[Dict[str, Any]] = []
        selected_data: Optional[Dict[str, Any]] = None

        for sym in ORDERED_ETF_SYMBOLS:
            data = self._load_computed_series(sym)
            m = dict(data["metrics"])
            meta = data["meta"]

            # Si hay cotización intradía fresca del controlador en vivo, reflejarla en cabecera
            live_px = live_map.get(sym)
            if live_px is not None and float(live_px) > 0:
                px = round(float(live_px), 2)
                prev = float(m["prev_close"] or px)
                m["last_close"] = px
                if abs(px - data["metrics"]["last_close"]) > 1e-4 and prev > 0:
                    m["day_change_pct"] = round(((px - prev) / prev) * 100.0, 2)
                m["trend"] = "ALCISTA" if px >= float(m["sma200"] or 0) else "BAJISTA"

            catalog.append({
                "symbol": sym,
                "display_name": meta["display_name"],
                "ucits_ticker": meta["ucits_ticker"],
                "isin": meta["isin"],
                "last_close": m["last_close"],
                "day_change_pct": m["day_change_pct"],
                "ret_1y_pct": m["ret_1y_pct"],
                "trend": m["trend"],
            })

            if sym == norm_sym:
                selected_data = {
                    "meta": meta,
                    "metrics": m,
                    "series": data["series"],
                }

        return {
            "ok": True,
            "selected_symbol": norm_sym,
            "catalog": catalog,
            "etf": selected_data,
        }
