"""
Almacén Persistente de Configuración y Estado en Vivo del Bot (aegis_quant/live/config_store.py).
Guarda en disco (JSON con escritura atómica: fichero temporal + fsync + os.replace) todos los parámetros editables desde la web,
las posiciones abiertas en Paper Trading, el historial de órdenes y la consola de logs,
garantizando que si el Ubuntu Server se reinicia por un corte de luz, el bot recupere
exactamente su estado al arrancar.
"""

import os
import json
import tempfile
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional


def atomic_write_json(path: str, data: Any) -> None:
    """
    Escribe un JSON en disco de forma atómica (todo o nada).

    Por qué: escribir con ``open(path, "w")`` trunca primero el fichero a 0 bytes;
    si el proceso muere o se va la luz justo en ese instante, el estado del bot
    queda vacío/corrupto y el siguiente arranque falla con ``JSONDecodeError``.

    Cómo: se escribe en un fichero temporal del MISMO directorio, se fuerza a disco
    (``fsync``) y se sustituye el original con ``os.replace``, que en POSIX es una
    operación atómica: cualquier lector ve el fichero antiguo completo o el nuevo
    completo, nunca uno a medias.

    :param path: Ruta final del fichero JSON.
    :param data: Objeto serializable a JSON.
    """
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_path, path)
        _fsync_directory(directory)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _fsync_directory(directory: str) -> None:
    """Persiste la entrada de directorio tras el rename (best-effort, no disponible en Windows)."""
    try:
        dir_fd = os.open(directory, os.O_RDONLY)
    except (OSError, AttributeError):
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        pass
    finally:
        os.close(dir_fd)


class BotConfigStore:
    """Gestiona la configuración viva del bot y el estado persistente en disco."""

    # RLock: permite que un método protegido llame a otro protegido sin bloquearse a sí mismo.
    _lock = threading.RLock()

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.config_path = os.path.join(self.data_dir, "bot_live_config.json")
        self.state_path = os.path.join(self.data_dir, "bot_live_state.json")

        self._ensure_defaults()

    def get_state_path(self, env: Optional[str] = None) -> str:
        """Devuelve la ruta del fichero de estado según el entorno (PAPER vs LIVE_REAL)."""
        if env is None:
            try:
                if os.path.exists(self.config_path):
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        env = cfg.get("environment", "PAPER")
                else:
                    env = "PAPER"
            except Exception:
                env = "PAPER"

        if env == "LIVE_REAL":
            return os.path.join(self.data_dir, "bot_live_state_real.json")
        else:
            # Para Paper Trading mantenemos compatibilidad con bot_live_state.json existente
            return self.state_path

    def get_ledger_path(self, env: Optional[str] = None) -> str:
        """Devuelve el fichero de auditoría contable inmutable JSONL según el entorno."""
        if env is None:
            try:
                if os.path.exists(self.config_path):
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        env = cfg.get("environment", "PAPER")
                else:
                    env = "PAPER"
            except Exception:
                env = "PAPER"

        if env == "LIVE_REAL":
            return os.path.join(self.data_dir, "ledger_real_trades.jsonl")
        else:
            return os.path.join(self.data_dir, "ledger_paper_trades.jsonl")

    def append_trade_ledger(self, order_entry: Dict[str, Any]) -> None:
        """Escribe una entrada inmutable en el libro contable de operaciones (JSONL) para auditoría e IRPF."""
        with self._lock:
            ledger_path = self.get_ledger_path()
            with open(ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(order_entry, ensure_ascii=False) + "\n")

    def _default_config(self) -> Dict[str, Any]:
        return {
            # Entorno de operativa: "PAPER" (Simulado / Sandbox) | "LIVE_REAL" (Dinero Real en Mercado)
            "environment": "PAPER",
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
            # Interruptores individuales de los 6 motores
            "enabled_motors": {
                "M1_PULLBACK": True,
                "M2_VIX_DIV": True,
                "M3_BEAR_SHORT": True,
                "M4_CTA_TREND": True,
                "M5_VOL_CRUSH": True,
                "M6_TOTM": True,
            },
            # Credenciales Alpaca Paper Trading (https://app.alpaca.markets)
            "alpaca_api_key": "",
            "alpaca_secret_key": "",
            "alpaca_endpoint": "https://paper-api.alpaca.markets",
            # Mobile Alert Channel (Signal Messenger)
            "mobile_phone": "",
            "signal_api_url": "https://api.callmebot.com/signal/send.php",
            "signal_apikey": "",
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
                atomic_write_json(self.config_path, self._default_config())
            # Asegurar estado por defecto si no existe
            cur_state_path = self.get_state_path()
            if not os.path.exists(cur_state_path):
                atomic_write_json(cur_state_path, self._default_state())

    def get_config(self) -> Dict[str, Any]:
        with self._lock:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            defaults = self._default_config()
            for k, v in defaults.items():
                if k not in cfg:
                    cfg[k] = v
            if isinstance(cfg.get("enabled_motors"), dict):
                for mk, mv in defaults["enabled_motors"].items():
                    cfg["enabled_motors"].setdefault(mk, mv)
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
            atomic_write_json(self.config_path, cfg)

            # Si el entorno cambió, asegurar que existe el fichero de estado de ese entorno
            target_state_path = self.get_state_path(cfg.get("environment", "PAPER"))
            if not os.path.exists(target_state_path):
                atomic_write_json(target_state_path, self._default_state())

            return cfg

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            p = self.get_state_path()
            if not os.path.exists(p):
                atomic_write_json(p, self._default_state())
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)

    def save_state(self, state: Dict[str, Any]) -> None:
        with self._lock:
            p = self.get_state_path()
            atomic_write_json(p, state)

    def append_log(self, msg: str, level: str = "INFO") -> None:
        with self._lock:
            p = self.get_state_path()
            if not os.path.exists(p):
                atomic_write_json(p, self._default_state())
            with open(p, "r", encoding="utf-8") as f:
                state = json.load(f)
            entry = {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": level,
                "msg": msg,
            }
            logs: List[Dict[str, str]] = state.get("logs", [])
            logs.insert(0, entry)
            state["logs"] = logs[:120]  # Mantener los últimos 120 eventos
            atomic_write_json(p, state)
