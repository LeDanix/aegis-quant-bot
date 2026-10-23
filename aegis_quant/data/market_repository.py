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
from typing import Dict, List
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
    }

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, "data")
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def fetch_symbol(self, symbol_key: str, start_year: int = 2006, force_refresh: bool = False) -> List[MarketBar]:
        cache_path = os.path.join(self.data_dir, f"{symbol_key}_daily.json")
        if os.path.exists(cache_path) and not force_refresh:
            with open(cache_path, "r", encoding="utf-8") as f:
                raw_list = json.load(f)
            return [MarketBar(**item) for item in raw_list]

        yahoo_sym = self.UNIVERSE_CONFIG[symbol_key]["yahoo"]
        period1 = int(datetime.datetime(start_year, 1, 1, tzinfo=datetime.UTC).timestamp())
        period2 = int(time.time()) + 86400

        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}"
            f"?period1={period1}&period2={period2}&interval=1d&events=history"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw_bytes = urllib.request.urlopen(req, timeout=20).read()
        payload = json.loads(raw_bytes)["chart"]["result"][0]

        timestamps = payload["timestamp"]
        quote = payload["indicators"]["quote"][0]
        opens = quote["open"]
        highs = quote["high"]
        lows = quote["low"]
        closes = quote["close"]
        volumes = quote.get("volume", [0] * len(timestamps))

        adj_closes = None
        if "adjclose" in payload["indicators"] and payload["indicators"]["adjclose"]:
            adj_closes = payload["indicators"]["adjclose"][0].get("adjclose")

        raw_list = []
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
            raw_list.append({
                "date": dt_str,
                "open": round(float(o), 4),
                "high": round(float(h), 4),
                "low": round(float(l), 4),
                "close": round(float(c), 4),
                "adj_close": round(float(adj_closes[i]), 4) if (adj_closes and adj_closes[i] is not None) else round(float(c), 4),
                "volume": int(vol),
            })

        raw_list.sort(key=lambda x: x["date"])
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(raw_list, f, indent=2)

        return [MarketBar(**item) for item in raw_list]

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
