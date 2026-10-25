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

import time
import json
import urllib.request
import threading
from datetime import datetime, date
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional, Tuple

from aegis_quant.live.config_store import BotConfigStore
from aegis_quant.live.broker_adapter import (
    BaseBrokerAdapter,
    LocalPaperBrokerAdapter,
    AlpacaPaperBrokerAdapter,
)
from aegis_quant.live.notifier_service import MultiChannelNotifier


class LiveBotController:
    """Controlador Central del Bot de Paper Trading 24/7 y Centro de Mando Web/Móvil."""

    def __init__(self, base_dir: str, summary_data: Dict[str, Any]):
        """
        Inicializa el controlador, almacén de configuración y programador en segundo plano.

        :param base_dir: Directorio raíz del proyecto aegis-quant-bot.
        :param summary_data: Diccionario con datos de auditoría histórica y escáner base.
        """
        self.base_dir = base_dir
        self.summary_data = summary_data
        self.store = BotConfigStore(base_dir)
        self._last_auto_run_date = ""

        # Precios de mercado actuales (inicializados con fallback del escáner)
        self.latest_prices: Dict[str, float] = {}
        self.market_pulse_cache: Dict[str, Any] = {}
        live_scan = summary_data.get("live_scan", {})
        for asset in live_scan.get("assets", []):
            self.latest_prices[asset["symbol"]] = float(asset["close"])

        # Intentar refresco inicial de mercado en vivo
        self.refresh_market_pulse()

        # Arrancar hilo vigilante del reloj horario en segundo plano (Daemon)
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

        # Si la cuenta Paper está recién creada y el bot viene en AUTO_100, sincronizar cartera inicial
        state = self.store.get_state()
        if not state.get("positions") and state.get("last_scan_time", "").startswith("Nunca"):
            self.run_scan_and_sync(trigger_source="Arranque Inicial Automático")

    # -------------------------------------------------------------------------
    # GESTIÓN HORARIA Y DESFASE DST (ESPAÑA VS WALL STREET)
    # -------------------------------------------------------------------------

    @staticmethod
    def get_time_info(target_ny_time: str = "15:55") -> Dict[str, Any]:
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
        offset_madrid = (
            now_madrid.utcoffset().total_seconds() / 3600.0 if now_madrid.utcoffset() else 1.0
        )
        diff_hours = int(round(offset_madrid - offset_ny))
        is_dst_mismatch = diff_hours != 6

        return {
            "ny_time": now_ny.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "madrid_time": now_madrid.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "schedule_time_ny": f"{target_ny_time} {now_ny.strftime('%Z')}",
            "schedule_time_madrid": f"{madrid_scheduled_hhmm} {madrid_tz_abbr}",
            "time_diff_hours": diff_hours,
            "is_dst_mismatch": is_dst_mismatch,
            "mismatch_notice": (
                f"Desfase estacional activo ({diff_hours}h de diferencia en vez de 6h). "
                f"Wall Street cierra hoy a las {madrid_scheduled_hhmm} {madrid_tz_abbr} en España."
                if is_dst_mismatch
                else ""
            ),
        }

    def _scheduler_loop(self) -> None:
        """
        Bucle vigilante 24/7.
        Verifica cada 25 segundos si es la hora de cierre en Wall Street (15:55 America/New_York)
        de lunes a viernes para ejecutar el rebalanceo de fin de sesión.
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

                    # Lunes (0) a Viernes (4) a la hora fijada de Wall Street (15:55 NY)
                    if (
                        now_ny.weekday() < 5
                        and hhmm_ny == target_ny
                        and self._last_auto_run_date != today_ny_str
                    ):
                        self._last_auto_run_date = today_ny_str
                        t_info = self.get_time_info(target_ny)
                        trigger_desc = (
                            f"Reloj Automático ({target_ny} NY / {t_info['schedule_time_madrid']})"
                        )
                        self.store.append_log(
                            f"Disparando ciclo diario programado: {trigger_desc}", "INFO"
                        )
                        self.run_scan_and_sync(trigger_source=trigger_desc)
            except Exception as exc:
                self.store.append_log(f"Error en bucle horario: {exc}", "ERROR")
            time.sleep(25)

    # -------------------------------------------------------------------------
    # MONITOR DE PULSO DE MERCADO EN VIVO (MARKET PULSE)
    # -------------------------------------------------------------------------

    def refresh_market_pulse(self) -> Dict[str, Any]:
        """
        Consulta cotizaciones reales en vivo y variaciones del día (% de cambio)
        para el universo de activos (SPY, QQQ, VIX, VIX3M, GLD, TLT, USO, ZS).
        Actualiza `self.latest_prices` con precios reales de mercado.
        """
        symbols_map = {
            "SPY": "SPY",
            "QQQ": "QQQ",
            "VIX": "%5EVIX",
            "VIX3M": "%5EVIX3M",
            "GLD": "GLD",
            "TLT": "TLT",
            "USO": "USO",
            "ZS": "ZS%3DF",
        }
        pulse: Dict[str, Any] = {}

        for sym, y_sym in symbols_map.items():
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{y_sym}?interval=1d&range=5d"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))["chart"]["result"][0]["meta"]
                    px = data.get("regularMarketPrice")
                    prev = data.get("chartPreviousClose")
                    if px is not None:
                        px = round(float(px), 2)
                        self.latest_prices[sym] = px
                        pct = round(((px - prev) / prev) * 100.0, 2) if prev and px else 0.0
                        pulse[sym] = {
                            "price": px,
                            "prev_close": round(float(prev), 2) if prev else px,
                            "change_pct": pct,
                        }
            except Exception:
                # Si falla temporalmente Yahoo Finance, conservar precio conocido
                fallback_px = self.latest_prices.get(sym, 100.0)
                pulse[sym] = {
                    "price": fallback_px,
                    "prev_close": fallback_px,
                    "change_pct": 0.0,
                }

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
    # CÁLCULO DE ASIGNACIÓN OBJETIVO (CARTERA TARGET)
    # -------------------------------------------------------------------------

    def compute_target_portfolio(
        self, simulate_motor: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calcula las ponderaciones objetivo de la cartera:
          - Modo simulación de motor táctico (para comprobación rápida).
          - Escaneo del Core Adaptativo Modo 3 Élite según régimen de volatilidad.
        """
        cfg = self.store.get_config()
        enabled = cfg.get("enabled_motors", {})
        max_fast = float(cfg.get("max_fast_slot_pct", 55.0)) / 100.0
        max_cta = float(cfg.get("max_cta_slot_pct", 40.0)) / 100.0

        targets: Dict[str, Dict[str, Any]] = {}

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

        # Escaneo real del régimen del día (Modo 3 Élite Core)
        live_scan = self.summary_data.get("live_scan", {})
        core_alloc = live_scan.get("core_allocation", {"SPY": 85.0, "QQQ": 15.0})
        for sym, pct in core_alloc.items():
            if pct > 0:
                targets[sym] = {
                    "weight": round(float(pct) / 100.0, 4),
                    "direction": "LONG",
                    "motor": "CORE_BULL",
                    "reason": f"Nucleo Inteligente Modo 3 Elite ({live_scan.get('vts_state', 'Contango')})",
                }
        return targets

    # -------------------------------------------------------------------------
    # CONSTRUCCIÓN DE NOTIFICACIONES MÓVILES ENRIQUECIDAS
    # -------------------------------------------------------------------------

    def _build_notification_message(
        self,
        trigger_source: str,
        orders: List[Dict[str, Any]],
        pulse: Dict[str, Any],
        state_after: Dict[str, Any],
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
                lines.append(f"• <b>{sym}</b>: ${p['price']:,.2f} ({sign}{chg:.2f}%)")

        # Estructura Temporal de Volatilidad
        vix = pulse.get("VIX", {}).get("price")
        vix3m = pulse.get("VIX3M", {}).get("price")
        if vix and vix3m:
            vts_ratio = round(vix / vix3m, 3)
            vts_state = (
                "Contango (Alcista)" if vts_ratio < 1.0 else "Backwardation (Pánico/Cobertura)"
            )
            lines.append(f"• <b>VIX</b>: {vix:.2f} | <b>VIX3M</b>: {vix3m:.2f} | Ratio: {vts_ratio:.3f} ({vts_state})")

        # Rendimiento de la cartera
        acct = state_after.get("account", {})
        eq = float(acct.get("total_equity_usd", 10000.0))
        tot_ret = float(acct.get("total_return_pct", 0.0))
        dd = float(acct.get("current_dd_pct", 0.0))
        cash = float(acct.get("cash_usd", 0.0))

        lines.extend([
            "",
            "💼 <b>ESTADO DE CARTERA:</b>",
            f"• Capital Total: <b>${eq:,.2f}</b> (Retorno: {tot_ret:+.2f}%)",
            f"• Efectivo (Cash): ${cash:,.2f} | Max Drawdown: {dd:.2f}%",
            "",
            "🎯 <b>POSICIONES ACTIVAS:</b>",
        ])

        positions = state_after.get("positions", [])
        if positions:
            for pos in positions:
                sym = pos.get("broker_symbol", pos.get("internal_symbol"))
                w = float(pos.get("weight_pct", 0.0))
                mkt_val = float(pos.get("market_value_usd", 0.0))
                pnl = float(pos.get("unrealized_pnl_usd", 0.0))
                sign = "+" if pnl >= 0 else ""
                lines.append(f"• {sym} ({w:.1f}%): ${mkt_val:,.2f} (P&L: {sign}${pnl:,.2f})")
        else:
            lines.append("• 100% en Efectivo / Sin posiciones abiertas.")

        lines.append("")
        if orders:
            lines.append(f"⚡ <b>ÓRDENES EJECUTADAS HOY ({len(orders)}):</b>")
            for o in orders:
                notional = float(o.get("notional_usd", 0.0))
                lines.append(f"- <b>{o['side']} {o['symbol']}</b>: ${notional:,.2f} ({o.get('motor', 'CORE')})")
        else:
            lines.append("⚡ <b>OPERATIVA HOY:</b> Sin rotación necesaria. Cartera alineada al régimen.")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # EJECUCIÓN Y ESCANEO EN VIVO (RUN SCAN & SYNC)
    # -------------------------------------------------------------------------

    def run_scan_and_sync(
        self, trigger_source: str = "Manual desde Web", simulate_motor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo de escaneo de mercado:
          1. Refresca precios de mercado y pulso del día en vivo.
          2. Calcula pesos objetivo de la cartera.
          3. Ejecuta órdenes en el bróker o genera propuesta en modo Copiloto.
          4. Emite notificación enriquecida a los canales móviles activos.
        """
        cfg = self.store.get_config()
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
            full_msg = self._build_notification_message(trigger_source, orders, pulse, state_after)
            self._send_mobile_alert(full_msg)

        return {"ok": ok, "mode": "AUTO_100", "orders_count": len(orders), "message": msg}

    def approve_pending(self) -> Dict[str, Any]:
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

    def reject_pending(self) -> Dict[str, Any]:
        """Descarta la propuesta de órdenes en modo Copiloto."""
        state = self.store.get_state()
        state["pending_confirmations"] = []
        self.store.save_state(state)
        msg = "Propuesta de ordenes descartada por el usuario."
        self.store.append_log(msg, "WARN")
        return {"ok": True, "message": msg}

    def get_full_status(self) -> Dict[str, Any]:
        """Devuelve el estado consolidado para pintar el Centro de Mando Web y Móvil."""
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
            "time_info": t_info,
            "market_pulse": self.market_pulse_cache,
            "config": cfg,
            "broker_connection": {"ok": conn_ok, "message": conn_msg},
            "state": state,
            "live_scan": self.summary_data.get("live_scan", {}),
        }

    def handle_action(self, action_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa cualquier acción interactiva enviada desde la Web o Móvil."""
        action = action_payload.get("action", "")

        if action == "TOGGLE_BOT":
            cfg = self.store.get_config()
            new_running = not cfg.get("bot_running", True)
            self.store.update_config({"bot_running": new_running})
            status_txt = (
                "BOT INICIADO (Vigilancia horaria activa)"
                if new_running
                else "BOT PAUSADO por el usuario"
            )
            self.store.append_log(status_txt, "INFO" if new_running else "WARN")
            self._send_mobile_alert(f"<b>Aegis-Quant:</b> {status_txt}")
            return {"ok": True, "message": status_txt}

        if action == "SCAN_NOW":
            sim_motor = action_payload.get("simulate_motor")
            return self.run_scan_and_sync(
                trigger_source=(
                    "Escaneo Manual desde Web" if not sim_motor else f"Simulacion Motor {sim_motor}"
                ),
                simulate_motor=sim_motor,
            )

        if action == "APPROVE_PENDING":
            return self.approve_pending()

        if action == "REJECT_PENDING":
            return self.reject_pending()

        if action == "PANIC_CLOSE_ALL":
            broker = self._get_broker()
            ok, msg = broker.close_all_positions(
                "Boton de Panico pulsado desde el Centro de Mando Web"
            )
            self._send_mobile_alert(f"<b>ALERTA DE CIERRE TOTAL AEGIS-QUANT</b>\n{msg}")
            return {"ok": ok, "message": msg}

        if action == "RESET_ACCOUNT":
            cfg = self.store.get_config()
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

        if action == "TEST_TELEGRAM":
            cfg = self.store.get_config()
            notifier = MultiChannelNotifier(cfg)
            ok, msg = notifier.telegram.send_message(
                "<b>Aegis-Quant Telegram Alert</b>\nConnection verified successfully. Real-time trading updates active."
            )
            self.store.append_log(f"Telegram notification test: {msg}", "INFO" if ok else "WARN")
            return {"ok": ok, "message": msg}

        if action == "TEST_NOTIFICATION":
            cfg = self.store.get_config()
            notifier = MultiChannelNotifier(cfg)
            pulse = self.refresh_market_pulse()
            state = self.store.get_state()
            sample_msg = self._build_notification_message(
                "Prueba de Notificación Móvil", [], pulse, state
            )
            ok, msg = notifier.notify(sample_msg)
            self.store.append_log(f"Mobile notification test: {msg}", "INFO" if ok else "WARN")
            return {"ok": ok, "message": msg}

        return {"ok": False, "message": f"Unknown action: {action}"}

    def _send_mobile_alert(self, text: str) -> None:
        """Envía el mensaje formateado a través de los canales móviles activos."""
        cfg = self.store.get_config()
        notifier = MultiChannelNotifier(cfg)
        notifier.notify(text)
