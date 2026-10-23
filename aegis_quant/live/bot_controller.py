"""
Controlador Central en Vivo del Bot (aegis_quant/live/bot_controller.py).
Orquesta el programador horario (21:55 CET), la lectura del radar cuantitativo,
la ejecución automática o con confirmación (Copiloto), el envío de alertas a Telegram/Signal
y la exposición de acciones en caliente para el Centro de Mando Web.
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from aegis_quant.live.config_store import BotConfigStore
from aegis_quant.live.broker_adapter import (
    BaseBrokerAdapter,
    LocalPaperBrokerAdapter,
    AlpacaPaperBrokerAdapter,
)
from aegis_quant.live.notifier_service import MultiChannelNotifier


class LiveBotController:
    """Controlador Orientado a Objetos del Bot de Paper Trading 24/7."""

    def __init__(self, base_dir: str, summary_data: Dict[str, Any]):
        self.base_dir = base_dir
        self.summary_data = summary_data
        self.store = BotConfigStore(base_dir)
        self._last_auto_run_date = ""

        # Extraer precios actuales del escáner en vivo
        self.latest_prices: Dict[str, float] = {}
        live_scan = summary_data.get("live_scan", {})
        for asset in live_scan.get("assets", []):
            self.latest_prices[asset["symbol"]] = float(asset["close"])

        # Arrancar hilo programador en segundo plano (Daemon)
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

        # Si la cuenta Paper está recién creada y el bot viene en AUTO_100, sincronizar cartera inicial
        state = self.store.get_state()
        if not state.get("positions") and state.get("last_scan_time", "").startswith("Nunca"):
            self.run_scan_and_sync(trigger_source="Arranque Inicial Automático")

    def _get_broker(self) -> BaseBrokerAdapter:
        cfg = self.store.get_config()
        provider = cfg.get("broker_provider", "LOCAL_PAPER")
        if provider == "ALPACA_PAPER":
            return AlpacaPaperBrokerAdapter(self.store, self.latest_prices)
        return LocalPaperBrokerAdapter(self.store, self.latest_prices)

    def _scheduler_loop(self) -> None:
        """Vigila cada 30 segundos si es la hora programada (por defecto 21:55 CET) para ejecutar el ciclo diario."""
        while True:
            try:
                cfg = self.store.get_config()
                if cfg.get("bot_running", True):
                    now = datetime.now()
                    hhmm = now.strftime("%H:%M")
                    today_str = now.strftime("%Y-%m-%d")
                    # Lunes (0) a Viernes (4) a la hora de cierre de Wall Street (21:55 CET)
                    if (
                        now.weekday() < 5
                        and hhmm == cfg.get("schedule_time_cet", "21:55")
                        and self._last_auto_run_date != today_str
                    ):
                        self._last_auto_run_date = today_str
                        self.run_scan_and_sync(trigger_source=f"Reloj Automático ({hhmm} CET)")
            except Exception as exc:
                self.store.append_log(f"Error en bucle horario: {exc}", "ERROR")
            time.sleep(25)

    def get_full_status(self) -> Dict[str, Any]:
        """Devuelve el estado completo para pintar el Centro de Mando en la Web y en el Móvil."""
        cfg = self.store.get_config()
        broker = self._get_broker()
        conn_ok, conn_msg = broker.test_connection()
        state = broker.get_portfolio_snapshot()
        return {
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "config": cfg,
            "broker_connection": {"ok": conn_ok, "message": conn_msg},
            "state": state,
            "live_scan": self.summary_data.get("live_scan", {}),
        }

    def compute_target_portfolio(
        self, simulate_motor: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calcula los pesos objetivo de la cartera combinando:
          - El estado actual del régimen VIX/VIX3M (Core Inteligente SPY + QQQ)
          - Los motores tácticos habilitados en la configuración web
          - Opcionalmente una señal táctica simulada para pruebas en vivo del usuario.
        """
        cfg = self.store.get_config()
        enabled = cfg.get("enabled_motors", {})
        max_fast = float(cfg.get("max_fast_slot_pct", 55.0)) / 100.0
        max_cta = float(cfg.get("max_cta_slot_pct", 40.0)) / 100.0

        targets: Dict[str, Dict[str, Any]] = {}

        # Si el usuario pulsa "Simular Disparo de Motor" para probar cómo opera en vivo:
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
                "motor": "M2_VIX_DIV",
                "reason": "Motor 2 (Divergencia VIX): Giro de volatilidad en Nasdaq 100",
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

        # Escaneo Real del Dia (Hoy: Regimen BULL_QUIET_CONTANGO VIX/VIX3M = 0.891)
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

    def run_scan_and_sync(
        self, trigger_source: str = "Manual desde Web", simulate_motor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ejecuta el escaneo de mercado y aplica las órdenes (o pide confirmación si está en Copiloto)."""
        cfg = self.store.get_config()
        targets = self.compute_target_portfolio(simulate_motor=simulate_motor)
        exec_mode = cfg.get("execution_mode", "AUTO_100")

        # Si está en modo COPILOTO (Confirmación previa), guardar propuesta pendiente y avisar al móvil
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
            msg = f"Modo Copiloto: Propuesta lista ({trigger_source}). Esperando confirmacion en la interfaz web."
            self.store.append_log(msg, "INFO")
            self._send_mobile_alert(
                f"<b>AEGIS-QUANT (COPILOTO)</b>\nPropuesta generada ({trigger_source}).\nRevisa la interfaz web para confirmar las ordenes."
            )
            return {"ok": True, "mode": "COPILOT_CONFIRM", "message": msg}

        # Modo 100% Automatico (Por defecto): Ejecutar directamente en el broker Paper
        broker = self._get_broker()
        ok, orders, msg = broker.execute_target_weights(targets, reason_summary=trigger_source)
        if orders:
            lines = [f"<b>AEGIS-QUANT PAPER TRADING ({cfg.get('broker_provider')})</b>"]
            lines.append(f"Motivo: {trigger_source}")
            for o in orders:
                lines.append(
                    f"- <b>{o['side']} {o['symbol']}</b>: ${o['notional_usd']:,.2f} ({o['motor']})"
                )
            state_after = self.store.get_state()
            eq = state_after["account"]["total_equity_usd"]
            lines.append(f"Capital total: <b>${eq:,.2f}</b>")
            self._send_mobile_alert("\n".join(lines))

        return {"ok": ok, "mode": "AUTO_100", "orders_count": len(orders), "message": msg}

    def approve_pending(self) -> Dict[str, Any]:
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
        return {"ok": ok, "orders_count": len(orders), "message": msg}

    def reject_pending(self) -> Dict[str, Any]:
        state = self.store.get_state()
        state["pending_confirmations"] = []
        self.store.save_state(state)
        msg = "Propuesta de ordenes descartada por el usuario."
        self.store.append_log(msg, "WARN")
        return {"ok": True, "message": msg}

    def handle_action(self, action_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa cualquier boton pulsado por el usuario en la Web o Movil."""
        action = action_payload.get("action", "")

        if action == "TOGGLE_BOT":
            cfg = self.store.get_config()
            new_running = not cfg.get("bot_running", True)
            self.store.update_config({"bot_running": new_running})
            status_txt = "BOT INICIADO (Vigilancia 24/7 activa)" if new_running else "BOT PAUSADO por el usuario"
            self.store.append_log(status_txt, "INFO" if new_running else "WARN")
            self._send_mobile_alert(f"<b>Aegis-Quant:</b> {status_txt}")
            return {"ok": True, "message": status_txt}

        if action == "SCAN_NOW":
            sim_motor = action_payload.get("simulate_motor")
            return self.run_scan_and_sync(
                trigger_source="Escaneo Manual desde Web" if not sim_motor else f"Simulacion Motor {sim_motor}",
                simulate_motor=sim_motor,
            )

        if action == "APPROVE_PENDING":
            return self.approve_pending()

        if action == "REJECT_PENDING":
            return self.reject_pending()

        if action == "PANIC_CLOSE_ALL":
            broker = self._get_broker()
            ok, msg = broker.close_all_positions("Boton de Panico pulsado desde el Centro de Mando Web")
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

        if action == "TEST_NOTIFICATION":
            cfg = self.store.get_config()
            notifier = MultiChannelNotifier(cfg)
            ok, msg = notifier.notify(
                "<b>Prueba de Conexion Movil Aegis-Quant</b>\n"
                "Servidor conectado correctamente. Recibiras aqui cada operacion del bot."
            )
            self.store.append_log(f"Prueba de notificacion movil: {msg}", "INFO" if ok else "WARN")
            return {"ok": ok, "message": msg}

        return {"ok": False, "message": f"Acción desconocida: {action}"}

    def _send_mobile_alert(self, text: str) -> None:
        cfg = self.store.get_config()
        if cfg.get("notify_channel", "NONE") == "NONE":
            return
        notifier = MultiChannelNotifier(cfg)
        notifier.notify(text)
