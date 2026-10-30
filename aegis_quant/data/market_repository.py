"""
Repositorio Orientado a Objetos de Datos de Mercado (MarketDataRepository).
Gestiona la descarga, actualización y caché local de los 8 activos del universo
(incluyendo ^VIX y ^VIX3M para calcular la Estructura Temporal de Volatilidad).
"""

import os
import json
import time
import urllib.request
import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from aegis_quant.models.market_models import MarketBar


class MarketDataRepository:
    UNIVERSE_CONFIG = {
        "SPY":   {"yahoo": "SPY",      "name": "S&P 500 ETF",                "asset_class": "equity"},
        "QQQ":   {"yahoo": "QQQ",      "name": "Nasdaq 100 ETF",             "asset_class": "equity"},
        "VIX":   {"yahoo": "%5EVIX",   "name": "CBOE 30-Day Volatility",     "asset_class": "volatility"},
        "VIX3M": {"yahoo": "%5EVIX3M", "name": "CBOE 3-Month Volatility",    "asset_class": "volatility"},
        "GLD":   {"yahoo": "GLD",      "name": "SPDR Gold Trust (Oro)",      "asset_class": "commodity_safe"},
        "TLT":   {"yahoo": "TLT",      "name": "US Treasury 20+ Yr Bond",    "asset_class": "bond_safe"},
        "USO":   {"yahoo": "USO",      "name": "WTI Crude Oil ETF",          "asset_class": "commodity_cyc"},
        "ZS":    {"yahoo": "ZS%3DF",   "name": "CME Soybean Futures (Soja)", "asset_class": "commodity_agri"},
        "BTC":   {"yahoo": "BTC-USD",  "name": "Bitcoin (BTC-USD / BTCE)",   "asset_class": "crypto_cta"},
    }

    # Símbolos auxiliares usados en investigación (no forman parte del universo operativo).
    EXTRA_SYMBOLS = {
        "HYG": {"yahoo": "HYG", "name": "iShares High Yield Corporate Bond"},
        "LQD": {"yahoo": "LQD", "name": "iShares Investment Grade Corporate Bond"},
        "RSP": {"yahoo": "RSP", "name": "Invesco S&P 500 Equal Weight"},
    }

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, "data")
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def _cache_path(self, symbol_key: str) -> str:
        """Ruta del fichero de caché local de un símbolo (data/<SYMBOL>_daily.json)."""
        return os.path.join(self.data_dir, f"{symbol_key}_daily.json")

    def _yahoo_symbol(self, symbol_key: str) -> str:
        """Ticker Yahoo para una clave interna (admite símbolos fuera del universo base, p.ej. 'HYG')."""
        meta = self.UNIVERSE_CONFIG.get(symbol_key) or self.EXTRA_SYMBOLS.get(symbol_key)
        return meta["yahoo"] if meta else symbol_key

    def _download_chart(self, symbol_key: str, query: str, timeout: float) -> List[Dict]:
        """
        Descarga velas diarias de Yahoo Finance (endpoint v8/chart) y las normaliza.

        :param symbol_key: Clave interna del activo.
        :param query: Parámetros de rango, p.ej. 'range=1mo' o 'period1=..&period2=..'.
        :param timeout: Timeout de red en segundos.
        :return: Lista de dicts {date, open, high, low, close, adj_close, volume} ordenada por fecha.
        """
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{self._yahoo_symbol(symbol_key)}"
            f"?{query}&interval=1d&events=history"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw_bytes = urllib.request.urlopen(req, timeout=timeout).read()
        payload = json.loads(raw_bytes)["chart"]["result"][0]
        return self._parse_chart_payload(payload)

    @staticmethod
    def _parse_chart_payload(payload: Dict) -> List[Dict]:
        """Convierte la respuesta JSON de Yahoo en filas limpias (descarta velas incompletas/duplicadas)."""
        timestamps = payload.get("timestamp") or []
        quote = payload["indicators"]["quote"][0]
        opens, highs, lows, closes = quote["open"], quote["high"], quote["low"], quote["close"]
        volumes = quote.get("volume") or [0] * len(timestamps)

        adj_closes = None
        if payload["indicators"].get("adjclose"):
            adj_closes = payload["indicators"]["adjclose"][0].get("adjclose")

        rows: List[Dict] = []
        seen = set()
        for i, ts in enumerate(timestamps):
            o, h, l, c = opens[i], highs[i], lows[i], closes[i]
            if c is None or o is None or h is None or l is None or c <= 0:
                continue
            dt_str = datetime.datetime.fromtimestamp(ts, datetime.UTC).strftime("%Y-%m-%d")
            if dt_str in seen:
                continue
            seen.add(dt_str)
            vol = volumes[i] if volumes and volumes[i] is not None else 0
            adj = adj_closes[i] if (adj_closes and adj_closes[i] is not None) else c
            rows.append({
                "date": dt_str,
                "open": round(float(o), 4),
                "high": round(float(h), 4),
                "low": round(float(l), 4),
                "close": round(float(c), 4),
                "adj_close": round(float(adj), 4),
                "volume": int(vol),
            })
        rows.sort(key=lambda x: x["date"])
        return rows

    def _read_cache(self, symbol_key: str) -> List[Dict]:
        """Lee la caché local; devuelve lista vacía si no existe."""
        cache_path = self._cache_path(symbol_key)
        if not os.path.exists(cache_path):
            return []
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_cache(self, symbol_key: str, rows: List[Dict]) -> None:
        """Guarda la caché con escritura atómica (nunca deja un fichero a medias)."""
        from aegis_quant.live.config_store import atomic_write_json

        atomic_write_json(self._cache_path(symbol_key), rows)

    def fetch_symbol(self, symbol_key: str, start_year: int = 2006, force_refresh: bool = False) -> List[MarketBar]:
        """
        Devuelve el histórico diario completo de un símbolo, usando la caché local si existe.

        :param symbol_key: Clave interna ('SPY', 'VIX', 'HYG'...).
        :param start_year: Año de inicio de la descarga completa.
        :param force_refresh: Si True, ignora la caché y vuelve a descargar todo.
        """
        if not force_refresh:
            cached = self._read_cache(symbol_key)
            if cached:
                return [MarketBar(**item) for item in cached]

        period1 = int(datetime.datetime(start_year, 1, 1, tzinfo=datetime.UTC).timestamp())
        period2 = int(time.time()) + 86400
        rows = self._download_chart(symbol_key, f"period1={period1}&period2={period2}", timeout=20)
        self._write_cache(symbol_key, rows)
        return [MarketBar(**item) for item in rows]

    def refresh_recent(
        self, symbol_key: str, completed_before: str, range_str: str = "1mo", timeout: float = 8.0
    ) -> List[MarketBar]:
        """
        Actualiza el histórico con las últimas sesiones y devuelve la serie completa EN MEMORIA,
        incluida la vela de hoy aún en formación (a las 15:55 NY su 'close' es el precio actual).

        Sólo se persisten en caché las sesiones ya cerradas (fecha < ``completed_before``),
        para no guardar nunca una vela intradía incompleta como si fuera definitiva.

        :param symbol_key: Clave interna del activo.
        :param completed_before: Fecha ISO (hoy en Nueva York); velas anteriores = sesiones cerradas.
        :param range_str: Ventana descargada de Yahoo ('5d', '1mo', '3mo'...).
        :param timeout: Timeout de red en segundos.
        """
        cached = {row["date"]: row for row in self._read_cache(symbol_key)}
        recent = self._download_chart(symbol_key, f"range={range_str}", timeout=timeout)

        merged = dict(cached)
        for row in recent:
            merged[row["date"]] = row
        all_rows = [merged[d] for d in sorted(merged)]

        completed = [r for r in all_rows if r["date"] < completed_before]
        if len(completed) > len(cached):
            self._write_cache(symbol_key, completed)
        return [MarketBar(**item) for item in all_rows]

    def load_universe(self, force_refresh: bool = False, verbose: bool = True) -> Dict[str, List[MarketBar]]:
        universe_bars: Dict[str, List[MarketBar]] = {}
        for key, meta in self.UNIVERSE_CONFIG.items():
            bars = self.fetch_symbol(key, start_year=2006, force_refresh=force_refresh)
            universe_bars[key] = bars
            if verbose:
                print(
                    f"[AegisData] {key:5s} ({meta['name']:28s}): "
                    f"{len(bars):4d} sesiones | {bars[0].date} -> {bars[-1].date}"
                )
        return universe_bars

    def refresh_universe_live(
        self,
        completed_before: str,
        fallback_prices: Optional[Dict[str, float]] = None,
        timeout: float = 5.0,
    ) -> Dict[str, List[MarketBar]]:
        """
        Refresca concurrentemente las últimas velas de los 8 activos del universo
        para evaluación táctica M1–M5 en vivo. Si algún activo falla en red, recurre
        a su caché histórica local sin abortar el escaneo.
        """
        fallback_prices = fallback_prices or {}

        def _load_one(key: str) -> List[MarketBar]:
            try:
                return self.refresh_recent(
                    key, completed_before=completed_before, range_str="1mo", timeout=timeout
                )
            except Exception:
                bars = self.fetch_symbol(key, start_year=2006, force_refresh=False)
                px = fallback_prices.get(key)
                if px and bars and bars[-1].date < completed_before:
                    bars = list(bars) + [
                        MarketBar(
                            date=completed_before,
                            open=round(float(px), 4),
                            high=round(float(px), 4),
                            low=round(float(px), 4),
                            close=round(float(px), 4),
                            adj_close=round(float(px), 4),
                            volume=0,
                        )
                    ]
                return bars

        keys = list(self.UNIVERSE_CONFIG.keys())
        universe_bars: Dict[str, List[MarketBar]] = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            for key, bars in zip(keys, pool.map(_load_one, keys)):
                universe_bars[key] = bars
        return universe_bars
