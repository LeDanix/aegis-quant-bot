"""
Servicio Orientado a Objetos de Notificaciones Móviles (aegis_quant/live/notifier_service.py).
Soporta:
  1. Telegram Bot API (HTTPS directo sin instalar demonios extra en el Ubuntu Server).
  2. Signal REST API (Compatible con contenedor local signal-cli-rest-api o CallMeBot Signal).
"""

import json
import urllib.request
import urllib.parse
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class BaseNotifier(ABC):
    """Interfaz base para todos los canales de notificación móvil."""

    @abstractmethod
    def send_message(self, text: str) -> Tuple[bool, str]:
        pass


class TelegramNotifier(BaseNotifier):
    """Cliente ligero para la API oficial de Telegram Bots."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = (bot_token or "").strip()
        self.chat_id = (chat_id or "").strip()

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str) -> Tuple[bool, str]:
        if not self.is_configured():
            return False, "Telegram no configurado (Falta Bot Token o Chat ID)."

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = json.dumps(
            {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return True, "Mensaje enviado correctamente a Telegram."
                return False, f"Telegram devolvió código HTTP {resp.status}"
        except Exception as exc:
            return False, f"Error al conectar con Telegram API: {exc}"


class SignalRestNotifier(BaseNotifier):
    """
    Cliente para Signal:
      - Soporta un endpoint local `signal-cli-rest-api` en el Ubuntu Server (ej. http://127.0.0.1:8085/v2/send)
      - O un webhook URL GET/POST compatible (como CallMeBot Signal).
    """

    def __init__(self, api_url: str, sender_phone: str, recipient_phone: str):
        self.api_url = (api_url or "").strip()
        self.sender_phone = (sender_phone or "").strip()
        self.recipient_phone = (recipient_phone or "").strip()

    def is_configured(self) -> bool:
        return bool(self.api_url and self.recipient_phone)

    def send_message(self, text: str) -> Tuple[bool, str]:
        if not self.is_configured():
            return False, "Signal no configurado (Falta URL de API o Teléfono destino)."

        try:
            # Soporte CallMeBot si el usuario pega una URL de api.callmebot.com
            if "callmebot.com" in self.api_url:
                clean_txt = urllib.parse.quote(text)
                full_url = f"{self.api_url}&text={clean_txt}" if "?" in self.api_url else f"{self.api_url}?phone={urllib.parse.quote(self.recipient_phone)}&apikey={urllib.parse.quote(self.sender_phone)}&text={clean_txt}"
                with urllib.request.urlopen(full_url, timeout=8) as resp:
                    return (resp.status == 200), f"CallMeBot Signal HTTP {resp.status}"

            # Estándar signal-cli-rest-api en Ubuntu Server
            payload = json.dumps(
                {
                    "message": text,
                    "number": self.sender_phone or self.recipient_phone,
                    "recipients": [self.recipient_phone],
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                self.api_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                return (resp.status in (200, 201)), f"Signal REST HTTP {resp.status}"
        except Exception as exc:
            return False, f"Error al enviar por Signal REST: {exc}"


class MultiChannelNotifier:
    """Orquestador que envía notificaciones al móvil según la preferencia del usuario."""

    def __init__(self, config: Dict[str, Any]):
        self.channel = config.get("notify_channel", "TELEGRAM")
        self.telegram = TelegramNotifier(
            config.get("telegram_bot_token", ""),
            config.get("telegram_chat_id", ""),
        )
        self.signal = SignalRestNotifier(
            config.get("signal_api_url", ""),
            config.get("signal_sender_phone", ""),
            config.get("signal_recipient_phone", ""),
        )

    def notify(self, text: str) -> Tuple[bool, str]:
        if self.channel == "NONE":
            return True, "Notificaciones desactivadas por configuración."

        results = []
        any_ok = False

        if self.channel in ("TELEGRAM", "BOTH"):
            ok, msg = self.telegram.send_message(text)
            any_ok = any_ok or ok
            results.append(f"Telegram: {msg}")

        if self.channel in ("SIGNAL", "BOTH"):
            # Limpiar etiquetas HTML básicas para Signal en texto plano
            plain = (
                text.replace("<b>", "")
                .replace("</b>", "")
                .replace("<code>", "")
                .replace("</code>", "")
            )
            ok, msg = self.signal.send_message(plain)
            any_ok = any_ok or ok
            results.append(f"Signal: {msg}")

        return any_ok, " | ".join(results)
