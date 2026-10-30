"""
Controlador Central Orientado a Objetos del Bot de Trading (aegis_quant/live/bot_controller.py).

Funcionalidades Principales:
1. Programador Horario Inteligente (Timezone & DST Aware):
   - Anclado a las 15:55 America/New_York (5 minutos antes del cierre de Wall Street).
   - Ajusta dinámicamente la hora local de Madrid (21:55 CEST en verano / 20:55 CET en desfases DST).
2. Monitor de Pulso de Mercado en Vivo (Market Pulse):
   - Descarga cotizaciones y variaciones del día (% cambio) para SPY, QQQ, VIX, VIX3M, etc.
   - Actualiza precios reales en caliente para el cálculo de valoraciones y órdenes de bróker.
3. Notificaciones Enriquecidas para Signal y Telegram:
   - Resumen ejecutivo con variación diaria del mercado, estado de la cartera y posiciones.
   - Eliminación de artefactos de redondeo de punto flotante.
4. Orquestador de Operativa (AUTO_100 y COPILOTO):
   - Ejecución directa en bróker o creación de propuestas de confirmación.
"""

import json
import os
import threading
import time
import urllib.request
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from aegis_quant.data.market_repository import MarketDataRepository
from aegis_quant.indicators.quant_feature_engine import QuantFeatureEngine
from aegis_quant.live.broker_adapter import (
    AlpacaPaperBrokerAdapter,
    BaseBrokerAdapter,
    LocalPaperBrokerAdapter,
)
from aegis_quant.live.config_store import BotConfigStore
from aegis_quant.live.notifier_service import MultiChannelNotifier
from aegis_quant.models.market_models import MarketBar
from aegis_quant.portfolio.aegis_engine import AegisPortfolioEngine


def _calc_easter(year: int) -> date:
    """Calcula el domingo de Pascua usando el algoritmo anónimo de Meeus/Jones/Butcher."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _format_currency_signal(amount: float, is_pnl: bool = False, currency: str = "$") -> str:
    """
    Formatea importes monetarios para notificaciones de Signal y pasarelas móviles:
      - Sin separador de miles (cifra continua sin espacios ni comas, ej: '8495.12').
      - Separador decimal: punto '.' estricto con 2 decimales.
      - Símbolo de moneda: ubicado al final con espacio ('8495.12 $').
        Evita que pasarelas como CallMeBot/signal-cli evalúen '$8' o '$1' como
        variables de entorno de shell y borren el dígito del millar antes de la coma.
    """
    formatted = f"{abs(amount):.2f}"
    if is_pnl:
        sign = "+" if amount > 0 else ("-" if amount < 0 else "")
        return f"{sign}{formatted} {currency}".strip()
    sign = "-" if amount < 0 else ""
    return f"{sign}{formatted} {currency}".strip()


def get_nyse_holidays(year: int) -> dict[date, str]:
    """Calcula los festivos oficiales de la Bolsa de Nueva York (NYSE/Nasdaq) para un año dado."""
    import datetime as _dt

    holidays: dict[date, str] = {}

    def add_observed(d: date, name: str) -> None:
        if d.weekday() == 5:
            holidays[d - _dt.timedelta(days=1)] = f"{name} (Observado)"
        elif d.weekday() == 6:
            holidays[d + _dt.timedelta(days=1)] = f"{name} (Observado)"
        else:
            holidays[d] = name

    # 1. Año Nuevo
    nyd = date(year, 1, 1)
    if nyd.weekday() == 6:
        holidays[date(year, 1, 2)] = "Año Nuevo (Observado)"
    elif nyd.weekday() < 5:
        holidays[nyd] = "Año Nuevo"

    # 2. Martin Luther King Jr. (3er lunes de enero)
    first_mon_jan = 1 + (7 - date(year, 1, 1).weekday()) % 7
    if date(year, 1, 1).weekday() == 0:
        first_mon_jan = 1
    holidays[date(year, 1, first_mon_jan + 14)] = "Martin Luther King Jr. Day"

    # 3. Presidents' Day / Washington (3er lunes de febrero)
    first_mon_feb = 1 + (7 - date(year, 2, 1).weekday()) % 7
    if date(year, 2, 1).weekday() == 0:
        first_mon_feb = 1
    holidays[date(year, 2, first_mon_feb + 14)] = "Presidents' Day (Washington)"

    # 4. Viernes Santo (Good Friday: 2 días antes de Pascua)
    easter = _calc_easter(year)
    holidays[easter - _dt.timedelta(days=2)] = "Viernes Santo (Good Friday)"

    # 5. Memorial Day (último lunes de mayo)
    last_day_may = date(year, 5, 31)
    last_mon_may = 31 - (last_day_may.weekday() % 7)
    holidays[date(year, 5, last_mon_may)] = "Memorial Day"

    # 6. Juneteenth (19 de junio)
    add_observed(date(year, 6, 19), "Juneteenth")

    # 7. Día de la Independencia (4 de julio)
    add_observed(date(year, 7, 4), "Día de la Independencia (4 de Julio)")

    # 8. Labor Day (primer lunes de septiembre)
    first_mon_sep = 1 + (7 - date(year, 9, 1).weekday()) % 7
    if date(year, 9, 1).weekday() == 0:
        first_mon_sep = 1
    holidays[date(year, 9, first_mon_sep)] = "Labor Day"

    # 9. Acción de Gracias (4º jueves de noviembre)
    first_thu_nov = 1 + (3 - date(year, 11, 1).weekday()) % 7
    holidays[date(year, 11, first_thu_nov + 21)] = "Acción de Gracias (Thanksgiving)"

    # 10. Navidad (25 de diciembre)
    add_observed(date(year, 12, 25), "Navidad")

    return holidays


class LiveBotController:
    """Controlador Central del Bot de Paper Trading 24/7 y Centro de Mando Web/Móvil."""

    def __init__(
        self,
        base_dir: str,
        summary_data: dict[str, Any],
        start_scheduler: bool = True,
        enable_network_init: bool = True,
    ):
        """
        Inicializa el controlador, almacén de configuración y programador en segundo plano.

        :param base_dir: Directorio raíz del proyecto aegis-quant-bot.
        :param summary_data: Diccionario con datos de auditoría histórica y escáner base.
        :param start_scheduler: Si True, inicia el hilo demonio horario 24/7.
        :param enable_network_init: Si True, refresca cotizaciones de mercado al arrancar.
        """
        self.base_dir = base_dir
        self.summary_data = summary_data
        self.store = BotConfigStore(base_dir)
        self.repo = MarketDataRepository(data_dir=os.path.join(base_dir, "data"))
        self._scan_lock = threading.RLock()
        self._last_auto_run_date = ""

        # Precios de mercado actuales y estado dinámico de motores tácticos M1-M5
        self.latest_prices: dict[str, float] = {}
        self.market_pulse_cache: dict[str, Any] = {}
        self.live_scan_cache: dict[str, Any] = dict(summary_data.get("live_scan", {}))
        self.tactical_status_cache: dict[str, Any] = {}
        self._last_pulse_time: float = time.time() if enable_network_init else 0.0
        self._pulse_lock = threading.Lock()

        for asset in self.live_scan_cache.get("assets", []):
            self.latest_prices[asset["symbol"]] = float(asset["close"])

        # Intentar refresco inicial de mercado y evaluación inicial desde caché local
        if enable_network_init:
            self.refresh_market_pulse()
        try:
            self._evaluate_live_engine(refresh_remote=False)
        except Exception as exc:
            self.store.append_log(f"Aviso en precarga táctica inicial: {exc}", "WARN")

        # Arrancar hilo vigilante del reloj horario en segundo plano (Daemon)
        if start_scheduler:
            self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self._scheduler_thread.start()

        # Si la cuenta Paper está recién creada y el bot viene en AUTO_100, sincronizar cartera inicial
        state = self.store.get_state()
        if enable_network_init and not state.get("positions") and state.get("last_scan_time", "").startswith("Nunca"):
            self.run_scan_and_sync(trigger_source="Arranque Inicial Automático")

    # -------------------------------------------------------------------------
    # GESTIÓN HORARIA Y DESFASE DST (ESPAÑA VS WALL STREET)
    # -------------------------------------------------------------------------

    @staticmethod
    def get_time_info(target_ny_time: str = "15:55") -> dict[str, Any]:
        """
        Calcula metadatos horarios sincronizados entre Wall Street (New York) y España (Madrid).
        Detecta y solventa automáticamente los desfases estacionales de cambio de hora (DST).
        """
        try:
            now_ny = datetime.now(ZoneInfo("America/New_York"))
            now_madrid = datetime.now(ZoneInfo("Europe/Madrid"))
        except Exception:
            now_ny = datetime.now()
            now_madrid = datetime.now()

        try:
            ny_h, ny_m = map(int, target_ny_time.split(":"))
            today_ny = now_ny.date()
            sched_dt_ny = datetime(
                today_ny.year,
                today_ny.month,
                today_ny.day,
                ny_h,
                ny_m,
                tzinfo=ZoneInfo("America/New_York"),
            )
            sched_dt_madrid = sched_dt_ny.astimezone(ZoneInfo("Europe/Madrid"))
            madrid_scheduled_hhmm = sched_dt_madrid.strftime("%H:%M")
            madrid_tz_abbr = sched_dt_madrid.strftime("%Z")
        except Exception:
            madrid_scheduled_hhmm = "21:55"
            madrid_tz_abbr = "CET"

        # Cálculo de diferencia de husos horarios
        offset_ny = now_ny.utcoffset().total_seconds() / 3600.0 if now_ny.utcoffset() else -5.0
        offset_madrid = now_madrid.utcoffset().total_seconds() / 3600.0 if now_madrid.utcoffset() else 1.0
        diff_hours = int(round(offset_madrid - offset_ny))
        is_dst_mismatch = diff_hours != 6

        is_open, market_status_desc = LiveBotController.is_market_open_now(now_ny)

        return {
            "ny_time": now_ny.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "madrid_time": now_madrid.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "schedule_time_ny": f"{target_ny_time} {now_ny.strftime('%Z')}",
            "schedule_time_madrid": f"{madrid_scheduled_hhmm} {madrid_tz_abbr}",
            "time_diff_hours": diff_hours,
            "is_dst_mismatch": is_dst_mismatch,
            "is_market_open": is_open,
            "market_status_desc": market_status_desc,
            "mismatch_notice": (
                f"Desfase estacional activo ({diff_hours}h de diferencia en vez de 6h). "
                f"Wall Street cierra hoy a las {madrid_scheduled_hhmm} {madrid_tz_abbr} en España."
                if is_dst_mismatch
                else ""
            ),
        }

    @staticmethod
    def is_market_open_now(now_ny: datetime | None = None) -> tuple[bool, str]:
        """
        Determina con precisión al minuto si la sesión regular de Wall Street (NYSE/Nasdaq)
        está actualmente abierta:
        - Lunes a viernes
        - No es festivo oficial NYSE
        - Entre las 09:30:00 y las 16:00:00 hora de Nueva York (America/New_York).
        """
        if now_ny is None:
            try:
                now_ny = datetime.now(ZoneInfo("America/New_York"))
            except Exception:
                now_ny = datetime.now()

        today_date = now_ny.date() if isinstance(now_ny, datetime) else now_ny
        weekday = today_date.weekday()

        if weekday == 5:
            return False, "Mercado cerrado: Fin de semana (Sábado). Wall Street inactivo."
        if weekday == 6:
            return False, "Mercado cerrado: Fin de semana (Domingo). Wall Street inactivo."

        holidays = get_nyse_holidays(today_date.year)
        if today_date in holidays:
            return False, f"Mercado cerrado: Festivo oficial en Wall Street ({holidays[today_date]})."

        if isinstance(now_ny, datetime):
            hhmm = now_ny.hour * 60 + now_ny.minute
            open_mm = 9 * 60 + 30  # 09:30 ET
            close_mm = 16 * 60  # 16:00 ET
            if hhmm < open_mm:
                return False, "Mercado cerrado: Pre-apertura (abre a las 09:30 NY)."
            if hhmm >= close_mm:
                return False, "Mercado cerrado: Fuera de sesión regular (cerró a las 16:00 NY)."

        return True, "Mercado abierto: Sesión regular activa en Wall Street."

    @staticmethod
    def get_market_session_status(now_ny: datetime | None = None) -> tuple[bool, str]:
        """
        Devuelve (is_closed: bool, reason: str).
        Determina si el mercado estadounidense (NYSE/Nasdaq) está cerrado hoy
        por fin de semana (sábado/domingo) o festivo oficial en Wall Street.
        """
        if now_ny is None:
            try:
                now_ny = datetime.now(ZoneInfo("America/New_York"))
            except Exception:
                now_ny = datetime.now()

        today_date = now_ny.date() if isinstance(now_ny, datetime) else now_ny
        weekday = today_date.weekday()

        if weekday == 5:
            return True, "Mercado cerrado: Fin de semana (Sábado). Wall Street inactivo."
        if weekday == 6:
            return True, "Mercado cerrado: Fin de semana (Domingo). Wall Street inactivo."

        holidays = get_nyse_holidays(today_date.year)
        if today_date in holidays:
            return True, f"Mercado cerrado: Festivo oficial en Wall Street ({holidays[today_date]})."

        return False, "Mercado abierto: Sesión de negociación activa."

    def _scheduler_loop(self) -> None:
        """
        Bucle vigilante 24/7.
        Verifica cada 25 segundos si es la hora de cierre en Wall Street (15:55 America/New_York)
        de lunes a domingo para ejecutar el rebalanceo de fin de sesión o emitir el reporte diario.
        """
        while True:
            try:
                cfg = self.store.get_config()
                if cfg.get("bot_running", True):
                    try:
                        now_ny = datetime.now(ZoneInfo("America/New_York"))
                    except Exception:
                        now_ny = datetime.now()

                    hhmm_ny = now_ny.strftime("%H:%M")
                    today_ny_str = now_ny.strftime("%Y-%m-%d")
                    target_ny = cfg.get("schedule_time_ny", "15:55")

                    # Disparo diario los 7 días de la semana a la hora fijada de Wall Street (15:55 NY)
                    if hhmm_ny == target_ny and self._last_auto_run_date != today_ny_str:
                        self._last_auto_run_date = today_ny_str
                        t_info = self.get_time_info(target_ny)
                        trigger_desc = f"Reloj Automático ({target_ny} NY / {t_info['schedule_time_madrid']})"
                        self.store.append_log(f"Disparando ciclo diario programado: {trigger_desc}", "INFO")
                        self.run_scan_and_sync(trigger_source=trigger_desc)
            except Exception as exc:
                self.store.append_log(f"Error en bucle horario: {exc}", "ERROR")
            time.sleep(25)

    # -------------------------------------------------------------------------
    # MONITOR DE PULSO DE MERCADO EN VIVO (MARKET PULSE)
    # -------------------------------------------------------------------------

    def refresh_market_pulse(self) -> dict[str, Any]:
        """
        Consulta concurrentemente cotizaciones reales en vivo y variaciones del día (% de cambio)
        para el universo de activos (SPY, QQQ, VIX, VIX3M, GLD, TLT, USO, ZS).
        Actualiza `self.latest_prices` con precios reales de mercado.
        """
        from concurrent.futures import ThreadPoolExecutor

        symbols_map = {
            "SPY": "SPY",
            "QQQ": "QQQ",
            "VIX": "%5EVIX",
            "VIX3M": "%5EVIX3M",
            "GLD": "GLD",
            "TLT": "TLT",
            "USO": "USO",
            "ZS": "ZS%3DF",
            "BTC": "BTC-USD",
        }

        def _fetch_one(item: tuple[str, str]) -> tuple[str, dict[str, Any], float | None]:
            sym, y_sym = item
            try:
                # Usar range=1d para que chartPreviousClose corresponda a la sesión anterior exacta (ayer)
                # y no a hace 5 días (lo que falseaba el cambio diario con range=5d).
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{y_sym}?interval=1d&range=1d"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))["chart"]["result"][0]["meta"]
                    px = data.get("regularMarketPrice")
                    prev = data.get("chartPreviousClose") or data.get("previousClose")
                    pct_direct = data.get("regularMarketChangePercent")
                    if px is not None:
                        px_val = round(float(px), 2)
                        prev_val = round(float(prev), 2) if prev is not None else px_val
                        if pct_direct is not None:
                            pct = round(float(pct_direct), 2)
                        elif prev_val and px_val:
                            pct = round(((px_val - prev_val) / prev_val) * 100.0, 2)
                        else:
                            pct = 0.0
                        return (
                            sym,
                            {
                                "price": px_val,
                                "prev_close": prev_val,
                                "change_pct": pct,
                            },
                            px_val,
                        )
            except Exception:
                pass
            fallback_px = self.latest_prices.get(sym, 100.0)
            return (
                sym,
                {"price": fallback_px, "prev_close": fallback_px, "change_pct": 0.0},
                None,
            )

        pulse: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            for sym, entry, px_val in pool.map(_fetch_one, list(symbols_map.items())):
                if px_val is not None:
                    self.latest_prices[sym] = px_val
                pulse[sym] = entry

        self.market_pulse_cache = pulse
        return pulse

    def _get_broker(self) -> BaseBrokerAdapter:
        """Instancia el adaptador de bróker configurado (Local Paper o Alpaca Paper)."""
        cfg = self.store.get_config()
        provider = cfg.get("broker_provider", "LOCAL_PAPER")
        if provider == "ALPACA_PAPER":
            return AlpacaPaperBrokerAdapter(self.store, self.latest_prices)
        return LocalPaperBrokerAdapter(self.store, self.latest_prices)

    # -------------------------------------------------------------------------
    # CÁLCULO DE ASIGNACIÓN OBJETIVO (CARTERA TARGET DINÁMICA M1-M5 + CORE)
    # -------------------------------------------------------------------------

    def _evaluate_live_engine(self, refresh_remote: bool = True) -> dict[str, dict[str, Any]]:
        """
        Evalúa en vivo sobre barras diarias reales (caché + actualización Yahoo Finance)
        tanto los 5 motores tácticos (M1..M5, incluyendo trades multisesión aún abiertos
        y nuevas señales de hoy) como la asignación del Core Modo 3 Élite sobre la liquidez ociosa.
        """
        cfg = self.store.get_config()
        enabled = cfg.get("enabled_motors", {})
        base_risk_pct = float(cfg.get("risk_per_trade_pct", 2.5))
        max_fast = float(cfg.get("max_fast_slot_pct", 55.0)) / 100.0
        max_cta = float(cfg.get("max_cta_slot_pct", 40.0)) / 100.0

        try:
            today_ny_str = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        except Exception:
            today_ny_str = datetime.now().strftime("%Y-%m-%d")

        if refresh_remote:
            raw_universe = self.repo.refresh_universe_live(
                completed_before=today_ny_str,
                fallback_prices=self.latest_prices,
            )
        else:
            raw_universe = {sym: self.repo._read_cache(sym) for sym in MarketDataRepository.UNIVERSE_CONFIG.keys()}
            raw_universe = {sym: [MarketBar(**item) for item in rows] for sym, rows in raw_universe.items() if rows}

        # Fallback seguro si aún no existen series históricas en disco (p.ej. tests aislados)
        if "SPY" not in raw_universe or len(raw_universe.get("SPY", [])) < 210:
            live_scan = self.live_scan_cache or self.summary_data.get("live_scan", {})
            core_alloc = live_scan.get("core_allocation", {"SPY": 85.0, "QQQ": 15.0})
            targets: dict[str, dict[str, Any]] = {}
            for sym, pct in core_alloc.items():
                if pct > 0:
                    targets[sym] = {
                        "weight": round(float(pct) / 100.0, 4),
                        "direction": "LONG",
                        "motor": "CORE_BULL",
                        "reason": f"Nucleo Inteligente Modo 3 Elite ({live_scan.get('vts_state', 'Contango')})",
                    }
            return targets

        # Sincronizar latest_prices con el último cierre disponible si no hubo pulso más reciente
        for sym, bars in raw_universe.items():
            if bars and sym not in self.market_pulse_cache:
                self.latest_prices[sym] = round(float(bars[-1].close), 2)

        # Ventana deslizante de 450 sesiones (~1.8 años): suficiente para convergencia exacta
        # de SMA(200), ATR(14), RSI(2) y operaciones CTA de hasta 45 sesiones, reduciendo latencia 12x.
        vix_slice = raw_universe.get("VIX", [])[-450:]
        vix3m_slice = raw_universe.get("VIX3M", [])[-450:]
        feature_engine = QuantFeatureEngine(
            vix_bars=vix_slice,
            vix3m_bars=vix3m_slice,
        )
        enriched_universe: dict[str, Any] = {}
        live_start_date = "2007-01-01"
        for sym, bars in raw_universe.items():
            if sym in ("VIX", "VIX3M"):
                continue
            sliced = bars[-450:] if len(bars) > 450 else bars
            enriched_universe[sym] = feature_engine.enrich_series(sliced)
            if sym == "SPY" and len(sliced) > 210:
                live_start_date = sliced[205].date

        portfolio_engine = AegisPortfolioEngine(
            enriched_universe=enriched_universe,
            start_date=live_start_date,
        )
        live_res = portfolio_engine.compute_live_portfolio(
            enabled_motors=enabled,
            base_risk_pct=base_risk_pct,
            max_fast_weight=max_fast,
            max_cta_weight=max_cta,
            max_slots=3,
        )
        self.live_scan_cache = live_res["live_scan"]
        self.tactical_status_cache = live_res["tactical"]
        return live_res["targets"]

    def compute_target_portfolio(
        self, simulate_motor: str | None = None, refresh_remote: bool = True
    ) -> dict[str, dict[str, Any]]:
        """
        Calcula las ponderaciones objetivo de la cartera:
          - Modo simulación de motor táctico (para comprobación rápida).
          - Evaluación dinámica en vivo de Motores M1–M5 + Core Adaptativo Modo 3 Élite.
        """
        cfg = self.store.get_config()
        enabled = cfg.get("enabled_motors", {})
        max_fast = float(cfg.get("max_fast_slot_pct", 55.0)) / 100.0
        max_cta = float(cfg.get("max_cta_slot_pct", 40.0)) / 100.0

        targets: dict[str, dict[str, Any]] = {}

        # Simulación táctica de motores a petición del usuario
        if simulate_motor == "M1_PULLBACK" and enabled.get("M1_PULLBACK", True):
            targets["QQQ"] = {
                "weight": max_fast,
                "direction": "LONG",
                "motor": "M1_PULLBACK",
                "reason": "Motor 1 (Pullback): RSI(2)<10 + 3 dias de caida en tendencia alcista",
            }
            targets["SPY"] = {
                "weight": round(1.0 - max_fast, 2),
                "direction": "LONG",
                "motor": "CORE_BULL",
                "reason": "Core Inteligente S&P 500 (Tendencia alcista en contango)",
            }
            return targets

        if simulate_motor == "M2_VIX_DIV" and enabled.get("M2_VIX_DIV", True):
            targets["SPY"] = {
                "weight": max_fast,
                "direction": "LONG",
                "motor": "M2_VIX_DIV",
                "reason": "Motor 2 (Divergencia VIX): Compresion de VIX desde pico 5d con RSI(2)<20",
            }
            targets["QQQ"] = {
                "weight": round(1.0 - max_fast, 2),
                "direction": "LONG",
                "motor": "CORE_BULL",
                "reason": "Core Inteligente Nasdaq 100",
            }
            return targets

        if simulate_motor == "M4_CTA_TREND" and enabled.get("M4_CTA_TREND", True):
            targets["ZS"] = {
                "weight": max_cta,
                "direction": "LONG",
                "motor": "M4_CTA_TREND",
                "reason": "Motor 4 (CTA Materias Primas): Ruptura Donchian 20d en Soja (ETF SOYB)",
            }
            targets["USO"] = {
                "weight": 0.25,
                "direction": "LONG",
                "motor": "M4_CTA_TREND",
                "reason": "Motor 4 (CTA Materias Primas): Tendencia alcista en Petroleo (USO)",
            }
            targets["SPY"] = {
                "weight": round(1.0 - max_cta - 0.25, 2),
                "direction": "LONG",
                "motor": "CORE_BULL",
                "reason": "Core Inteligente S&P 500",
            }
            return targets

        if simulate_motor == "M5_VOL_CRUSH" and enabled.get("M5_VOL_CRUSH", True):
            targets["SPY"] = {
                "weight": max_fast,
                "direction": "LONG",
                "motor": "M5_VOL_CRUSH",
                "reason": "Motor 5 (Vol-Crush Institucional): Colapso VIX/VIX3M > 5%",
            }
            targets["QQQ"] = {
                "weight": round(1.0 - max_fast, 2),
                "direction": "LONG",
                "motor": "CORE_BULL",
                "reason": "Core Nasdaq 100",
            }
            return targets

        if simulate_motor == "M3_BEAR_SHORT" and enabled.get("M3_BEAR_SHORT", True):
            targets["QQQ"] = {
                "weight": 0.35,
                "direction": "SHORT",
                "motor": "M3_BEAR_SHORT",
                "reason": "Motor 3 (Corto en Crisis): Agotamiento de rebote en mercado bajista",
            }
            targets["GLD"] = {
                "weight": max_cta,
                "direction": "LONG",
                "motor": "M4_CTA_TREND",
                "reason": "Motor 4 (Refugio en Oro GLD durante crisis)",
            }
            return targets

        if simulate_motor == "M6_TOTM" and enabled.get("M6_TOTM", True):
            targets["QQQ"] = {
                "weight": max_fast,
                "direction": "LONG",
                "motor": "M6_TOTM",
                "reason": "Motor 6 (Flujo Fin de Mes TOTM): Debilidad RSI(2)<35 previa a flujos institucionales T+1..T+4",
            }
            targets["SPY"] = {
                "weight": round(1.0 - max_fast, 2),
                "direction": "LONG",
                "motor": "CORE_BULL",
                "reason": "Core Inteligente S&P 500 (Ventana TOTM en Contango)",
            }
            return targets

        # Evaluación dinámica en vivo de Motores M1–M6 + Core Modo 3 Élite
        return self._evaluate_live_engine(refresh_remote=refresh_remote)

    # -------------------------------------------------------------------------
    # CONSTRUCCIÓN DE NOTIFICACIONES MÓVILES ENRIQUECIDAS
    # -------------------------------------------------------------------------

    def _build_notification_message(
        self,
        trigger_source: str,
        orders: list[dict[str, Any]],
        pulse: dict[str, Any],
        state_after: dict[str, Any],
        direct_reason: str | None = None,
    ) -> str:
        """
        Construye un mensaje informativo e institucional para Signal y Telegram.
        Incluye variación diaria de mercado, estado de cartera, posiciones y órdenes.
        """
        t_info = self.get_time_info()
        lines = [
            "🦅 <b>AEGIS-QUANT | REPORTE DE CIERRE</b>",
            f"🕒 {t_info['schedule_time_ny']} | {t_info['schedule_time_madrid']}",
            f"📌 Origen: {trigger_source}",
        ]

        if t_info.get("is_dst_mismatch"):
            lines.append(f"⚠️ {t_info['mismatch_notice']}")

        lines.extend(["", "📊 <b>PULSO DEL MERCADO HOY:</b>"])

        # Variaciones de los índices clave
        for sym in ["SPY", "QQQ"]:
            if sym in pulse:
                p = pulse[sym]
                chg = p.get("change_pct", 0.0)
                sign = "+" if chg >= 0 else ""
                lines.append(f"• <b>{sym}</b>: {_format_currency_signal(float(p['price']))} ({sign}{chg:.2f}%)")

        # Estructura Temporal de Volatilidad
        vix = pulse.get("VIX", {}).get("price")
        vix3m = pulse.get("VIX3M", {}).get("price")
        if vix and vix3m:
            vts_ratio = round(vix / vix3m, 3)
            vts_state = "Contango (Alcista)" if vts_ratio < 1.0 else "Backwardation (Pánico/Cobertura)"
            lines.append(f"• <b>VIX</b>: {vix:.2f} | <b>VIX3M</b>: {vix3m:.2f} | Ratio: {vts_ratio:.3f} ({vts_state})")

        # Rendimiento de la cartera
        acct = state_after.get("account", {})
        eq = float(acct.get("total_equity_usd", 10000.0))
        tot_ret = float(acct.get("total_return_pct", 0.0))
        dd = float(acct.get("current_dd_pct", 0.0))
        cash = float(acct.get("cash_usd", 0.0))

        lines.extend(
            [
                "",
                "💼 <b>ESTADO DE CARTERA:</b>",
                f"• Capital Total: <b>{_format_currency_signal(eq)}</b> (Retorno: {tot_ret:+.2f}%)",
                f"• Efectivo (Cash): {_format_currency_signal(cash)} | Max Drawdown: {dd:.2f}%",
                "",
                "🎯 <b>POSICIONES ACTIVAS:</b>",
            ]
        )

        positions = state_after.get("positions", [])
        if positions:
            for pos in positions:
                sym = pos.get("broker_symbol", pos.get("internal_symbol"))
                w = float(pos.get("weight_pct", 0.0))
                mkt_val = float(pos.get("market_value_usd", 0.0))
                pnl = float(pos.get("unrealized_pnl_usd", 0.0))
                lines.append(
                    f"• {sym} ({w:.1f}%): {_format_currency_signal(mkt_val)} (P&L: {_format_currency_signal(pnl, is_pnl=True)})"
                )
        else:
            lines.append("• 100% en Efectivo / Sin posiciones abiertas.")

        lines.append("")
        tactical_info = getattr(self, "tactical_status_cache", None) or {}
        open_tactical = tactical_info.get("open_trades") or []
        if open_tactical:
            lines.append(f"🧠 <b>MOTORES TÁCTICOS ACTIVOS ({len(open_tactical)}):</b>")
            for ot in open_tactical:
                lines.append(
                    f"• <b>{ot['engine_id']}</b> en {ot['symbol']} ({ot['direction']}, {ot['weight_pct']:.1f}%): {ot['reason']}"
                )
            lines.append("")

        if orders:
            lines.append(f"⚡ <b>ÓRDENES EJECUTADAS HOY ({len(orders)}):</b>")
            for o in orders:
                notional = float(o.get("notional_usd", 0.0))
                lines.append(
                    f"- <b>{o['side']} {o['symbol']}</b>: {_format_currency_signal(notional)} ({o.get('motor', 'CORE')})"
                )
        else:
            reason_txt = direct_reason or "Sin rotación necesaria. Cartera alineada al régimen."
            lines.append(f"⚡ <b>OPERATIVA HOY:</b> {reason_txt}")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # EJECUCIÓN Y ESCANEO EN VIVO (RUN SCAN & SYNC)
    # -------------------------------------------------------------------------

    def run_scan_and_sync(
        self, trigger_source: str = "Manual desde Web", simulate_motor: str | None = None
    ) -> dict[str, Any]:
        """
        Ejecuta el ciclo de escaneo de mercado (protegido por lock reentrante):
          1. Verifica si el mercado está abierto o cerrado (fin de semana o festivo en Wall Street).
          2. Si está cerrado, genera y emite el reporte de estado con frase explicativa directa a Signal.
          3. Si está abierto, refresca cotizaciones, evalúa motores tácticos y ejecuta órdenes.
          4. Emite reporte diario puntual a Signal especificando la razón exacta si no hay operaciones.
        """
        with self._scan_lock:
            cfg = self.store.get_config()
            try:
                now_ny = datetime.now(ZoneInfo("America/New_York"))
            except Exception:
                now_ny = datetime.now()

            is_closed, closed_reason = self.get_market_session_status(now_ny)

            # Si el mercado está cerrado (fin de semana o festivo en Wall Street) y no es simulación Sandbox
            if is_closed and simulate_motor is None:
                pulse = self.market_pulse_cache or self.refresh_market_pulse()
                state = self.store.get_state()
                pos = state.get("positions", [])
                if pos:
                    pos_desc = ", ".join(
                        [
                            f"{p.get('broker_symbol', p.get('internal_symbol'))} ({float(p.get('weight_pct', 0.0)):.1f}%)"
                            for p in pos
                        ]
                    )
                    direct_reason = f"{closed_reason} Posiciones activas mantenidas sin cambios: {pos_desc}."
                else:
                    direct_reason = f"{closed_reason} Cartera al 100% en liquidez/efectivo protegido."

                full_msg = self._build_notification_message(
                    trigger_source, [], pulse, state, direct_reason=direct_reason
                )
                self._send_mobile_alert(full_msg)
                self.store.append_log(f"Reporte diario emitido: {closed_reason}", "INFO")
                return {
                    "ok": True,
                    "mode": cfg.get("execution_mode", "AUTO_100"),
                    "orders_count": 0,
                    "message": direct_reason,
                }

            pulse = self.refresh_market_pulse()
            targets = self.compute_target_portfolio(simulate_motor=simulate_motor)
            exec_mode = cfg.get("execution_mode", "AUTO_100")

            # MODO COPILOTO (Requiere confirmación previa en la interfaz)
            if exec_mode == "COPILOT_CONFIRM":
                state = self.store.get_state()
                proposal = {
                    "id": f"PROP-{int(time.time())}",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "trigger_source": trigger_source,
                    "targets": targets,
                }
                state["pending_confirmations"] = [proposal]
                self.store.save_state(state)
                msg = f"Modo Copiloto: Propuesta lista ({trigger_source}). Esperando confirmacion web."
                self.store.append_log(msg, "INFO")
                self._send_mobile_alert(
                    f"<b>AEGIS-QUANT (COPILOTO)</b>\nPropuesta generada ({trigger_source}).\n"
                    f"Revisa el Centro de Mando Web para confirmar la operativa."
                )
                return {"ok": True, "mode": "COPILOT_CONFIRM", "message": msg}

            # MODO 100% AUTOMÁTICO (Por defecto)
            broker = self._get_broker()
            ok, orders, msg = broker.execute_target_weights(targets, reason_summary=trigger_source)
            state_after = self.store.get_state()

            # Construir y despachar notificación enriquecida
            # Se envía siempre en ejecuciones programadas o cuando hay órdenes activas
            is_scheduled = "Reloj Automático" in trigger_source
            if orders or is_scheduled:
                direct_reason = None
                if not orders:
                    live_scan = getattr(self, "live_scan_cache", None) or {}
                    regime = live_scan.get("regime", "")
                    pos = state_after.get("positions", [])
                    acct = state_after.get("account", {})
                    cash_pct = round(
                        (float(acct.get("cash_usd", 0.0)) / max(1.0, float(acct.get("total_equity_usd", 1.0)))) * 100.0,
                        1,
                    )
                    tactical_info = getattr(self, "tactical_status_cache", None) or {}
                    open_tactical = tactical_info.get("open_trades") or []

                    if pos:
                        pos_desc = ", ".join(
                            [
                                f"{p.get('broker_symbol', p.get('internal_symbol'))} ({float(p.get('weight_pct', 0.0)):.1f}%)"
                                for p in pos
                            ]
                        )
                        if open_tactical:
                            direct_reason = (
                                f"Sin cambios. Posiciones activas mantenidas: {pos_desc} (Efectivo: {cash_pct:.1f}%). "
                                f"Razón: Operaciones tácticas en curso siguiendo su plan de salida (stops y targets vigentes; sin nuevas señales hoy)."
                            )
                        elif regime in ("BULL_QUIET_CONTANGO", "BULL_MODERATE_VOL"):
                            direct_reason = (
                                f"Sin rotación necesaria. Posiciones activas mantenidas: {pos_desc} (Efectivo: {cash_pct:.1f}%). "
                                f"Razón: Cartera ya alineada al 100% con los pesos óptimos del régimen alcista."
                            )
                        else:
                            direct_reason = (
                                f"Sin cambios. Posiciones activas mantenidas: {pos_desc} (Efectivo: {cash_pct:.1f}%). "
                                f"Razón: Asignación alineada al régimen actual ({regime}); sin rotación hoy."
                            )
                    else:
                        if regime == "BEAR_DEFENSIVE":
                            direct_reason = (
                                "Sin operaciones. Cartera al 100% en liquidez/efectivo. "
                                "Razón: Mercado en régimen defensivo (SPY por debajo de SMA-50) y ningún motor táctico (M1–M6) activó señal de entrada."
                            )
                        elif regime == "BEAR_CRISIS_BACKWARDATION":
                            direct_reason = (
                                "Sin operaciones. Cartera al 100% en liquidez/efectivo. "
                                "Razón: Alerta institucional por pánico/backwardation (VIX/VIX3M >= 1.0); capital completamente preservado."
                            )
                        elif regime in ("BULL_QUIET_CONTANGO", "BULL_MODERATE_VOL"):
                            direct_reason = (
                                "Sin operaciones. Cartera temporalmente al 100% en liquidez/efectivo "
                                "en espera de la siguiente señal táctica o rebalanceo Core."
                            )
                        else:
                            direct_reason = (
                                "Sin operaciones. Cartera al 100% en liquidez/efectivo protegida; "
                                "sin señales activas hoy."
                            )

                full_msg = self._build_notification_message(
                    trigger_source, orders, pulse, state_after, direct_reason=direct_reason
                )
                self._send_mobile_alert(full_msg)

            return {"ok": ok, "mode": "AUTO_100", "orders_count": len(orders), "message": msg}

    def approve_pending(self) -> dict[str, Any]:
        """Aprueba y ejecuta una propuesta pendiente en modo Copiloto."""
        state = self.store.get_state()
        pending = state.get("pending_confirmations", [])
        if not pending:
            return {"ok": False, "message": "No hay ordenes pendientes de confirmacion."}
        prop = pending[0]
        state["pending_confirmations"] = []
        self.store.save_state(state)

        broker = self._get_broker()
        ok, orders, msg = broker.execute_target_weights(
            prop["targets"], reason_summary=f"Aprobado en Copiloto ({prop['trigger_source']})"
        )
        pulse = self.refresh_market_pulse()
        state_after = self.store.get_state()
        if orders:
            full_msg = self._build_notification_message(
                f"Aprobado en Copiloto ({prop['trigger_source']})", orders, pulse, state_after
            )
            self._send_mobile_alert(full_msg)

        return {"ok": ok, "orders_count": len(orders), "message": msg}

    def reject_pending(self) -> dict[str, Any]:
        """Descarta la propuesta de órdenes en modo Copiloto."""
        state = self.store.get_state()
        state["pending_confirmations"] = []
        self.store.save_state(state)
        msg = "Propuesta de ordenes descartada por el usuario."
        self.store.append_log(msg, "WARN")
        return {"ok": True, "message": msg}

    def get_full_status(self, force_pulse: bool = False) -> dict[str, Any]:
        """Devuelve el estado consolidado para pintar el Centro de Mando Web y Móvil."""
        now_ts = time.time()
        # Refrescar cotizaciones reales de Yahoo Finance si expiró el TTL de 60s o se fuerza explícitamente
        if force_pulse or (now_ts - self._last_pulse_time > 60.0):
            if self._pulse_lock.acquire(blocking=False):
                try:
                    self.refresh_market_pulse()
                    self._last_pulse_time = time.time()
                except Exception:
                    pass
                finally:
                    self._pulse_lock.release()

        cfg = self.store.get_config()
        broker = self._get_broker()
        conn_ok, conn_msg = broker.test_connection()
        state = broker.get_portfolio_snapshot()
        t_info = self.get_time_info(cfg.get("schedule_time_ny", "15:55"))

        return {
            "server_time": t_info["madrid_time"],
            "ny_time": t_info["ny_time"],
            "schedule_time_ny": t_info["schedule_time_ny"],
            "schedule_time_madrid": t_info["schedule_time_madrid"],
            "is_market_open": t_info.get("is_market_open", False),
            "market_status_desc": t_info.get("market_status_desc", ""),
            "time_info": t_info,
            "market_pulse": self.market_pulse_cache,
            "config": cfg,
            "broker_connection": {"ok": conn_ok, "message": conn_msg},
            "state": state,
            "live_scan": self.live_scan_cache or self.summary_data.get("live_scan", {}),
            "tactical": self.tactical_status_cache,
        }

    def handle_action(self, action_payload: dict[str, Any]) -> dict[str, Any]:
        """Procesa cualquier acción interactiva enviada desde la Web o Móvil."""
        action = action_payload.get("action", "")

        if action == "TOGGLE_BOT":
            cfg = self.store.get_config()
            new_running = not cfg.get("bot_running", True)
            self.store.update_config({"bot_running": new_running})
            status_txt = "BOT INICIADO (Vigilancia horaria activa)" if new_running else "BOT PAUSADO por el usuario"
            self.store.append_log(status_txt, "INFO" if new_running else "WARN")
            self._send_mobile_alert(f"<b>Aegis-Quant:</b> {status_txt}")
            return {"ok": True, "message": status_txt}

        if action == "SCAN_NOW":
            sim_motor = action_payload.get("simulate_motor")
            return self.run_scan_and_sync(
                trigger_source=("Escaneo Manual desde Web" if not sim_motor else f"Simulacion Motor {sim_motor}"),
                simulate_motor=sim_motor,
            )

        if action == "APPROVE_PENDING":
            return self.approve_pending()

        if action == "REJECT_PENDING":
            return self.reject_pending()

        if action == "PANIC_CLOSE_ALL":
            broker = self._get_broker()
            ok, msg = broker.close_all_positions("Boton de Panico pulsado desde el Centro de Mando Web")
            # Cancelar e invalidar cualquier propuesta de Copiloto pendiente para evitar ejecuciones obsoletas
            state = self.store.get_state()
            if state.get("pending_confirmations"):
                state["pending_confirmations"] = []
                self.store.save_state(state)
            self._send_mobile_alert(f"<b>ALERTA DE CIERRE TOTAL AEGIS-QUANT</b>\n{msg}")
            return {"ok": ok, "message": msg}

        if action == "RESET_ACCOUNT":
            cfg = self.store.get_config()
            if cfg.get("environment") == "LIVE_REAL":
                msg = "Acción bloqueada: No se puede reiniciar saldo en entorno Real (LIVE_REAL)."
                self.store.append_log(msg, "WARN")
                return {"ok": False, "message": msg}

            cap = float(cfg.get("allocated_capital_usd", 10000.0))
            fresh = self.store._default_state()
            fresh["account"]["initial_capital"] = cap
            fresh["account"]["cash_usd"] = cap
            fresh["account"]["total_equity_usd"] = cap
            fresh["account"]["peak_equity_usd"] = cap
            fresh["logs"].insert(
                0,
                {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "level": "INFO",
                    "msg": f"Cuenta Paper Trading reiniciada a ${cap:,.2f} en efectivo.",
                },
            )
            self.store.save_state(fresh)
            return {"ok": True, "message": f"Cuenta Paper Trading reiniciada a ${cap:,.2f}."}

        if action == "TEST_SIGNAL":
            cfg = self.store.get_config()
            notifier = MultiChannelNotifier(cfg)
            ok, msg = notifier.signal.send_message(
                "Aegis-Quant Signal Alert: Connection verified successfully. Real-time trading updates active."
            )
            self.store.append_log(f"Signal notification test: {msg}", "INFO" if ok else "WARN")
            return {"ok": ok, "message": msg}

        if action == "TEST_NOTIFICATION":
            cfg = self.store.get_config()
            notifier = MultiChannelNotifier(cfg)
            pulse = self.refresh_market_pulse()
            state = self.store.get_state()
            sample_msg = self._build_notification_message("Prueba de Notificación Móvil", [], pulse, state)
            ok, msg = notifier.notify(sample_msg)
            self.store.append_log(f"Mobile notification test: {msg}", "INFO" if ok else "WARN")
            return {"ok": ok, "message": msg}

        return {"ok": False, "message": f"Unknown action: {action}"}

    def _send_mobile_alert(self, text: str) -> None:
        """Envía el mensaje formateado a través de los canales móviles activos."""
        cfg = self.store.get_config()
        notifier = MultiChannelNotifier(cfg)
        ok, msg = notifier.notify(text)
        self.store.append_log(f"Alerta móvil: {msg}", "INFO" if ok else "WARN")
