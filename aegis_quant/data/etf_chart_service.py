"""
Servicio de Series Históricas y Cotizaciones de ETFs Operativos (aegis_quant/data/etf_chart_service.py).

Proporciona series diarias OHLCV completas (2006/2007–2026), actualización horaria de la sesión en curso
y visualización en resolución 1D (Diario) o 1H (Horario), medias móviles institucionales
SMA(50) y SMA(200), indicador RSI(2) de Wilder, retornos por horizonte temporal y metadatos
de equivalencia europea UCITS en Tradegate (Opción A) para la sección interactiva de ETFs.

NOTA CRÍTICA DE AISLAMIENTO CUANTITATIVO:
Este servicio solo gestiona la capa de visualización e interfaz web.
NUNCA modifica ni sobreescribe los ficheros históricos diarios base (data/<SYMBOL>_daily.json)
empleados por los motores algorítmicos del bot (M1 a M6) ni altera la toma de decisiones.
El histórico horario intradía se almacena de forma aislada en data/cache_etf_hourly/.
"""

import os
import json
import time
import threading
import urllib.request
import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from aegis_quant.live.config_store import atomic_write_json


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
    "BTC": {
        "symbol": "BTC",
        "display_name": "Bitcoin Spot / Physical ETP",
        "asset_class": "Activo Digital Asimétrico (Cripto)",
        "ucits_ticker": "BTCE / 21BC",
        "isin": "DE000A27Z304 / CH1199067054",
        "venue": "Tradegate (TGATE) / Xetra · EUR",
        "ter": "0,21% (21BC) / 0,60% (BTCE)",
        "engines": "Motor 4 · Tendencia Multi-Activo CTA (Cap 15%)",
    },
}

ORDERED_ETF_SYMBOLS: List[str] = ["SPY", "QQQ", "GLD", "TLT", "USO", "ZS", "BTC"]

ETF_HOURLY_YAHOO_TICKERS: Dict[str, str] = {
    "SPY": "SPY",
    "QQQ": "QQQ",
    "GLD": "GLD",
    "TLT": "TLT",
    "USO": "USO",
    "ZS": "ZS=F",
    "BTC": "BTC-USD",
}


class EtfChartService:
    """
    Servicio de datos y métricas para las gráficas interactivas de ETFs.
    Mantiene caché en memoria e invalidación automática, con actualización horaria
    aislada de la sesión en curso para no alterar nunca los datos del bot de trading.
    """

    _lock = threading.RLock()
    _series_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _hourly_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data")
        self.hourly_cache_dir = os.path.join(self.data_dir, "cache_etf_hourly")
        os.makedirs(self.hourly_cache_dir, exist_ok=True)

    @staticmethod
    def normalize_symbol(symbol: Optional[str]) -> str:
        clean = str(symbol or "SPY").strip().upper()
        if clean == "SOYB":
            return "ZS"
        if clean not in ETF_UNIVERSE_META:
            return "SPY"
        return clean

    # -------------------------------------------------------------------------
    # DESCARGA Y CACHÉ HORARIA AISLADA (1H INTRADÍA)
    # -------------------------------------------------------------------------

    def _meta_file_path(self) -> str:
        return os.path.join(self.hourly_cache_dir, "cache_meta.json")

    def _hourly_file_path(self, symbol: str) -> str:
        return os.path.join(self.hourly_cache_dir, f"{symbol}_1h.json")

    def get_hourly_cache_meta(self) -> Dict[str, Any]:
        path = self._meta_file_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_refresh_ts": 0.0,
            "last_refresh_iso": "--",
            "last_refresh_human": "--",
            "status": "pending",
        }

    def _fetch_one_hourly(self, symbol: str, timeout: float = 6.0) -> Tuple[str, List[Dict[str, Any]]]:
        ticker = ETF_HOURLY_YAHOO_TICKERS.get(symbol, symbol)
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            f"?range=1mo&interval=1h&events=history"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw_bytes = urllib.request.urlopen(req, timeout=timeout).read()
        res = json.loads(raw_bytes)["chart"]["result"][0]
        timestamps = res.get("timestamp") or []
        quote = res["indicators"]["quote"][0]
        opens, highs, lows, closes = quote["open"], quote["high"], quote["low"], quote["close"]
        vols = quote.get("volume") or [0] * len(timestamps)

        bars: List[Dict[str, Any]] = []
        for i, ts in enumerate(timestamps):
            c = closes[i]
            if c is None or c <= 0:
                continue
            o = opens[i] if opens[i] is not None else c
            h = highs[i] if highs[i] is not None else max(o, c)
            l = lows[i] if lows[i] is not None else min(o, c)
            v = vols[i] if vols and vols[i] is not None else 0

            # Formatear en horario local de Wall Street (New York)
            dt_ny = datetime.datetime.fromtimestamp(ts, ZoneInfo("America/New_York"))
            bars.append({
                "datetime": dt_ny.strftime("%Y-%m-%d %H:%M"),
                "date": dt_ny.strftime("%Y-%m-%d"),
                "open": round(float(o), 2),
                "high": round(float(h), 2),
                "low": round(float(l), 2),
                "close": round(float(c), 2),
                "volume": int(v),
            })
        return symbol, bars

    def refresh_all_hourly(self, force: bool = False, timeout: float = 6.0) -> Dict[str, Any]:
        """
        Descarga concurrentemente las barras horarias (1H) del último mes para los 6 ETFs.
        Las persiste de forma atómica en data/cache_etf_hourly/<SYMBOL>_1h.json.
        Frecuencia por defecto: máximo 1 vez cada 3600 segundos (1 hora), salvo force=True.
        """
        with self._lock:
            meta = self.get_hourly_cache_meta()
            elapsed = time.time() - float(meta.get("last_refresh_ts", 0.0))
            if not force and elapsed < 3600 and meta.get("status") == "ok":
                return meta

            # Actualizar en paralelo con timeout controlado
            successful_symbols: List[str] = []
            try:
                symbols_to_fetch = list(ORDERED_ETF_SYMBOLS)
                with ThreadPoolExecutor(max_workers=4) as pool:
                    futures = [pool.submit(self._fetch_one_hourly, s, timeout) for s in symbols_to_fetch]
                    for fut in futures:
                        try:
                            sym, bars = fut.result()
                            if bars:
                                atomic_write_json(self._hourly_file_path(sym), bars)
                                self._hourly_cache[sym] = (time.time(), bars)
                                successful_symbols.append(sym)
                        except Exception:
                            continue

                now_madrid = datetime.datetime.now(ZoneInfo("Europe/Madrid"))
                new_meta = {
                    "last_refresh_ts": round(time.time(), 2),
                    "last_refresh_iso": now_madrid.strftime("%Y-%m-%d %H:%M:%S"),
                    "last_refresh_human": now_madrid.strftime("%H:%M"),
                    "status": "ok" if successful_symbols else "partial",
                    "updated_symbols": successful_symbols,
                }
                atomic_write_json(self._meta_file_path(), new_meta)
                return new_meta
            except Exception as exc:
                return {
                    "last_refresh_ts": meta.get("last_refresh_ts", 0.0),
                    "last_refresh_iso": meta.get("last_refresh_iso", "--"),
                    "last_refresh_human": meta.get("last_refresh_human", "--"),
                    "status": f"error: {exc}",
                }

    def _load_hourly_bars(self, symbol: str) -> List[Dict[str, Any]]:
        file_path = self._hourly_file_path(symbol)
        if not os.path.exists(file_path):
            return []
        try:
            mtime = os.path.getmtime(file_path)
            cached = self._hourly_cache.get(symbol)
            if cached is not None and cached[0] == mtime:
                return cached[1]
            with open(file_path, "r", encoding="utf-8") as f:
                bars = json.load(f)
            self._hourly_cache[symbol] = (mtime, bars)
            return bars
        except Exception:
            return []

    # -------------------------------------------------------------------------
    # CÁLCULO DE MÉTRICAS Y SERIES (OHLCV, SMA50, SMA200, RSI2)
    # -------------------------------------------------------------------------

    @staticmethod
    def _compute_series_payload(
        symbol: str, raw_bars: List[Dict[str, Any]], date_key: str = "date"
    ) -> Dict[str, Any]:
        """Calcula de forma determinista SMA(50), SMA(200), RSI(2) y retornos sobre la lista de barras."""
        bars = [
            b for b in raw_bars
            if b.get(date_key) and float(b.get("close") or 0.0) > 0.0
        ]
        bars.sort(key=lambda x: str(x[date_key]))

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

            dates.append(str(b[date_key]))
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

        # Retorno YTD
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

        return {
            "meta": dict(ETF_UNIVERSE_META.get(symbol, {})),
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
                "ret_total_pct": ret_total_pct,
                "high_52w": round(max(w52_highs), 2) if w52_highs else 0.0,
                "low_52w": round(min(w52_lows), 2) if w52_lows else 0.0,
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

    # -------------------------------------------------------------------------
    # GENERACIÓN DE SERIES: RESOLUCIÓN 1D (DIARIA) vs 1H (HORARIA)
    # -------------------------------------------------------------------------

    def _load_computed_series(
        self, symbol: str, live_prices: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Carga la serie histórica diaria base desde data/<SYMBOL>_daily.json.
        Si la sesión de hoy tiene datos en la caché horaria o en live_prices,
        integra la vela del día EN MEMORIA para la visualización, sin modificar el archivo en disco.
        """
        file_path = os.path.join(self.data_dir, f"{symbol}_daily.json")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Serie histórica no encontrada para {symbol}: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw_bars = json.load(f)

        # Clonar barras base
        bars: List[Dict[str, Any]] = [
            dict(b) for b in raw_bars
            if b.get("date") and float(b.get("close") or 0.0) > 0.0
        ]
        bars.sort(key=lambda x: str(x["date"]))

        # Comprobar si hay actividad intradía hoy
        try:
            today_ny = datetime.datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        except Exception:
            today_ny = datetime.date.today().isoformat()

        hourly_bars = self._load_hourly_bars(symbol)
        today_hourly = [b for b in hourly_bars if b.get("date") == today_ny]

        live_map = live_prices or {}
        live_px = live_map.get(symbol)

        if today_hourly:
            t_open = today_hourly[0]["open"]
            t_high = max(b["high"] for b in today_hourly)
            t_low = min(b["low"] for b in today_hourly)
            t_close = today_hourly[-1]["close"]
            t_vol = sum(int(b.get("volume") or 0) for b in today_hourly)

            if live_px is not None and float(live_px) > 0:
                t_close = round(float(live_px), 2)
                t_high = max(t_high, t_close)
                t_low = min(t_low, t_close)

            synthetic_today = {
                "date": today_ny,
                "open": t_open,
                "high": t_high,
                "low": t_low,
                "close": t_close,
                "volume": t_vol,
            }

            if bars and bars[-1]["date"] == today_ny:
                bars[-1] = synthetic_today
            elif bars and bars[-1]["date"] < today_ny:
                bars.append(synthetic_today)
        elif live_px is not None and float(live_px) > 0:
            px = round(float(live_px), 2)
            if bars and bars[-1]["date"] == today_ny:
                bars[-1]["close"] = px
                bars[-1]["high"] = max(bars[-1].get("high", px), px)
                bars[-1]["low"] = min(bars[-1].get("low", px), px)
            elif bars and bars[-1]["date"] < today_ny:
                prev_c = bars[-1]["close"]
                bars.append({
                    "date": today_ny,
                    "open": prev_c,
                    "high": max(prev_c, px),
                    "low": min(prev_c, px),
                    "close": px,
                    "volume": 0,
                })

        return self._compute_series_payload(symbol, bars, date_key="date")

    def _load_computed_hourly_series(self, symbol: str) -> Dict[str, Any]:
        """Carga la serie horaria (1H) desde la caché aislada data/cache_etf_hourly/<SYMBOL>_1h.json."""
        hourly_bars = self._load_hourly_bars(symbol)
        if len(hourly_bars) < 5:
            # Fallback seguro a la serie diaria si aún no hay suficientes barras horarias
            return self._load_computed_series(symbol)
        return self._compute_series_payload(symbol, hourly_bars, date_key="datetime")

    # -------------------------------------------------------------------------
    # MÉTODO PRINCIPAL DE CONSULTA (PAYLOAD REST PARA LA WEB)
    # -------------------------------------------------------------------------

    def get_etf_payload(
        self,
        symbol: Optional[str] = "SPY",
        live_prices: Optional[Dict[str, float]] = None,
        timeframe: str = "1d",
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Devuelve el catálogo de los 6 ETFs y la serie detallada del ETF seleccionado.

        :param symbol: Ticker del activo ('SPY', 'QQQ', 'GLD', 'TLT', 'USO', 'ZS').
        :param live_prices: Precios en vivo más recientes del controlador.
        :param timeframe: '1d' para velas diarias institucionales (con vela de hoy actualizada)
                          o '1h' para serie horaria detallada del último mes.
        :param force_refresh: Si True, fuerza la actualización horaria inmediata contra Yahoo.
        """
        norm_sym = self.normalize_symbol(symbol)
        tf = "1h" if str(timeframe).lower() == "1h" else "1d"
        live_map = live_prices or {}

        # Actualización horaria segura (no bloqueante en caso de corte de red)
        try:
            self.refresh_all_hourly(force=force_refresh)
        except Exception:
            pass

        meta_info = self.get_hourly_cache_meta()

        catalog: List[Dict[str, Any]] = []
        selected_data: Optional[Dict[str, Any]] = None

        for sym in ORDERED_ETF_SYMBOLS:
            # Para el catálogo de tarjetas rápidas siempre usamos métricas de 1D con precio en vivo
            data_1d = self._load_computed_series(sym, live_prices=live_map)
            m = dict(data_1d["metrics"])
            meta = data_1d["meta"]

            live_px = live_map.get(sym)
            if live_px is not None and float(live_px) > 0:
                px = round(float(live_px), 2)
                prev = float(m.get("prev_close") or px)
                m["last_close"] = px
                if abs(px - data_1d["metrics"]["last_close"]) > 1e-4 and prev > 0:
                    m["day_change_pct"] = round(((px - prev) / prev) * 100.0, 2)
                m["trend"] = "ALCISTA" if px >= float(m.get("sma200") or 0) else "BAJISTA"

            catalog.append({
                "symbol": sym,
                "display_name": meta.get("display_name", sym),
                "ucits_ticker": meta.get("ucits_ticker", ""),
                "isin": meta.get("isin", ""),
                "last_close": m["last_close"],
                "day_change_pct": m["day_change_pct"],
                "ret_1y_pct": m["ret_1y_pct"],
                "trend": m["trend"],
            })

            if sym == norm_sym:
                hourly_res = self._load_computed_hourly_series(norm_sym)
                if tf == "1h":
                    selected_data = {
                        "meta": meta,
                        "metrics": m,  # Mantener KPIs de referencia
                        "series": hourly_res["series"],
                        "hourly_series": hourly_res["series"],
                    }
                else:
                    selected_data = {
                        "meta": meta,
                        "metrics": m,
                        "series": data_1d["series"],
                        "hourly_series": hourly_res["series"],
                    }

        elapsed = time.time() - float(meta_info.get("last_refresh_ts", 0.0))
        next_secs = max(0, int(3600 - elapsed))

        return {
            "ok": True,
            "selected_symbol": norm_sym,
            "timeframe": tf,
            "hourly_meta": {
                "last_refresh_human": meta_info.get("last_refresh_human", "--"),
                "last_refresh_iso": meta_info.get("last_refresh_iso", "--"),
                "next_refresh_in_seconds": next_secs,
                "is_hourly_updated": True,
            },
            "catalog": catalog,
            "etf": selected_data,
        }
