"""
Almacén Persistente de Configuración y Estado en Vivo del Bot (aegis_quant/live/config_store.py).
Guarda en disco (JSON transaccional) todos los parámetros editables desde la web,
las posiciones abiertas en Paper Trading, el historial de órdenes y la consola de logs,
garantizando que si el Ubuntu Server se reinicia por un corte de luz, el bot recupere
exactamente su estado al arrancar.
"""

import os
import json
import threading
from datetime import datetime
from typing import Dict, Any, List


class BotConfigStore:
    """Gestiona la configuración viva del bot y el estado persistente en disco."""

    _lock = threading.Lock()

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.config_path = os.path.join(self.data_dir, "bot_live_config.json")
        self.state_path = os.path.join(self.data_dir, "bot_live_state.json")

        self._ensure_defaults()

    def _default_config(self) -> Dict[str, Any]:
        return {
            # Modo de operación: "AUTO_100" (Por defecto 100% automático) | "COPILOT_CONFIRM"
            "execution_mode": "AUTO_100",
            # Estado del demonio: True = Bot encendido vigilando horario | False = Bot parado
            "bot_running": True,
            # Proveedor de Paper Trading: "LOCAL_PAPER" | "ALPACA_PAPER" | "IBKR_PAPER"
            "broker_provider": "LOCAL_PAPER",
            # Parámetros de capital y riesgo editables en caliente desde la web
            "allocated_capital_usd": 10000.0,
            "risk_per_trade_pct": 2.5,
            "max_fast_slot_pct": 55.0,
            "max_cta_slot_pct": 40.0,
            "daily_kill_switch_dd_pct": -8.0,
            "schedule_time_cet": "21:55",
            "use_soyb_etf_for_zs": True,
            # Interruptores individuales de los 5 motores
            "enabled_motors": {
                "M1_PULLBACK": True,
                "M2_VIX_DIV": True,
                "M3_BEAR_SHORT": True,
                "M4_CTA_TREND": True,
                "M5_VOL_CRUSH": True,
            },
            # Credenciales Alpaca Paper Trading (https://app.alpaca.markets)
            "alpaca_api_key": "",
            "alpaca_secret_key": "",
            "alpaca_endpoint": "https://paper-api.alpaca.markets",
            # Configuración de Notificaciones Móviles (Telegram / Signal)
            "notify_channel": "TELEGRAM",  # "TELEGRAM" | "SIGNAL" | "BOTH" | "NONE"
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "signal_api_url": "http://127.0.0.1:8085/v2/send",
            "signal_sender_phone": "",
            "signal_recipient_phone": "",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _default_state(self) -> Dict[str, Any]:
        return {
            "account": {
                "initial_capital": 10000.0,
                "cash_usd": 10000.0,
                "positions_value_usd": 0.0,
                "total_equity_usd": 10000.0,
                "peak_equity_usd": 10000.0,
                "current_dd_pct": 0.0,
                "unrealized_pnl_usd": 0.0,
                "realized_pnl_usd": 0.0,
                "total_return_pct": 0.0,
                "kill_switch_triggered": False,
            },
            "positions": [],
            "pending_confirmations": [],
            "orders_history": [],
            "logs": [
                {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "level": "INFO",
                    "msg": "Sistema Aegis-Quant Paper Trading inicializado en modo 100% Automático (Capital inicial: $10,000).",
                }
            ],
            "last_scan_time": "Nunca (Pulsa 'Escanear y Sincronizar Ahora')",
        }

    def _ensure_defaults(self) -> None:
        with self._lock:
            if not os.path.exists(self.config_path):
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self._default_config(), f, indent=2, ensure_ascii=False)
            if not os.path.exists(self.state_path):
                with open(self.state_path, "w", encoding="utf-8") as f:
                    json.dump(self._default_state(), f, indent=2, ensure_ascii=False)

    def get_config(self) -> Dict[str, Any]:
        with self._lock:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            defaults = self._default_config()
            for k, v in defaults.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for k, v in updates.items():
                if k == "enabled_motors" and isinstance(v, dict):
                    cfg.setdefault("enabled_motors", {}).update(v)
                else:
                    cfg[k] = v
            cfg["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            return cfg

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)

    def save_state(self, state: Dict[str, Any]) -> None:
        with self._lock:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

    def append_log(self, msg: str, level: str = "INFO") -> None:
        with self._lock:
            with open(self.state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            entry = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": level,
                "msg": msg,
            }
            logs: List[Dict[str, str]] = state.get("logs", [])
            logs.insert(0, entry)
            state["logs"] = logs[:120]  # Mantener los últimos 120 eventos
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
