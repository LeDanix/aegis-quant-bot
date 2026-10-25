"""
Object-Oriented Mobile Notification Service (aegis_quant/live/notifier_service.py).
Supports:
  1. Signal Messenger:
     - Direct HTTP via CallMeBot Signal Gateway (free personal API)
     - Local Docker signal-cli-rest-api daemon (e.g. http://127.0.0.1:8085/v2/send)
  2. Telegram Bot API:
     - Direct HTTPS via Telegram official Bot API
"""

import json
import urllib.request
import urllib.parse
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class BaseNotifier(ABC):
    """Base interface for mobile notification channels."""

    @abstractmethod
    def send_message(self, text: str) -> Tuple[bool, str]:
        pass


class TelegramNotifier(BaseNotifier):
    """Lightweight client for official Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = (bot_token or "").strip()
        self.chat_id = (chat_id or "").strip()

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str) -> Tuple[bool, str]:
        if not self.is_configured():
            return False, "Telegram not configured (Bot Token or Chat ID missing)."

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
                    return True, "Message delivered successfully to Telegram."
                return False, f"Telegram API returned HTTP status {resp.status}"
        except Exception as exc:
            return False, f"Telegram connection error: {exc}"


class SignalRestNotifier(BaseNotifier):
    """
    Client for Signal Messenger:
      - CallMeBot Gateway (free personal Signal API: api.callmebot.com/signal/send.php)
      - Or local signal-cli-rest-api container on Ubuntu Server.
    """

    def __init__(self, api_url: str, phone: str, apikey: str = ""):
        self.api_url = (api_url or "").strip()
        self.phone = (phone or "").strip()
        self.apikey = (apikey or "").strip()

    def is_configured(self) -> bool:
        return bool(self.phone and (self.api_url or self.apikey))

    def send_message(self, text: str) -> Tuple[bool, str]:
        if not self.is_configured():
            return False, "Signal not configured (Missing phone number or gateway URL/apikey)."

        # Strip basic HTML tags for plain Signal formatting
        clean_text = (
            text.replace("<b>", "")
            .replace("</b>", "")
            .replace("<code>", "")
            .replace("</code>", "")
        )

        try:
            target_url = self.api_url or "https://api.callmebot.com/signal/send.php"

            # 1. CallMeBot endpoint handling
            if "callmebot.com" in target_url:
                encoded_msg = urllib.parse.quote(clean_text)
                encoded_phone = urllib.parse.quote(self.phone)
                encoded_key = urllib.parse.quote(self.apikey)
                full_url = f"{target_url}?phone={encoded_phone}&apikey={encoded_key}&text={encoded_msg}"
                req = urllib.request.Request(full_url, headers={"User-Agent": "AegisQuant/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    raw_body = resp.read().decode("utf-8", errors="replace")
                    if "ERROR" in raw_body or "Error Num" in raw_body:
                        import re
                        m = re.search(r"Error Text:</u>\s*([^<]+)", raw_body)
                        err_txt = m.group(1).strip() if m else raw_body[:80].strip()
                        return False, f"CallMeBot error: {err_txt} (Verifica si debes usar tu UUID en vez del número)"
                    return (resp.status == 200), "CallMeBot Signal: Mensaje entregado con éxito."

            # 2. Local Docker signal-cli-rest-api
            payload = json.dumps(
                {
                    "message": clean_text,
                    "number": self.phone,
                    "recipients": [self.phone],
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                target_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return (resp.status in (200, 201)), f"Signal REST HTTP {resp.status}"
        except Exception as exc:
            return False, f"Signal gateway error: {exc}"


class MultiChannelNotifier:
    """Dispatches notifications across configured active channels (Signal and/or Telegram)."""

    def __init__(self, config: Dict[str, Any]):
        phone = config.get("mobile_phone") or config.get("signal_recipient_phone", "")
        self.signal = SignalRestNotifier(
            api_url=config.get("signal_api_url", "https://api.callmebot.com/signal/send.php"),
            phone=phone,
            apikey=config.get("signal_apikey", ""),
        )
        self.telegram = TelegramNotifier(
            bot_token=config.get("telegram_bot_token", ""),
            chat_id=config.get("telegram_chat_id", ""),
        )

    def notify(self, text: str) -> Tuple[bool, str]:
        results = []
        any_ok = False

        if self.signal.is_configured():
            ok, msg = self.signal.send_message(text)
            any_ok = any_ok or ok
            results.append(f"Signal: {msg}")

        if self.telegram.is_configured():
            ok, msg = self.telegram.send_message(text)
            any_ok = any_ok or ok
            results.append(f"Telegram: {msg}")

        if not results:
            return True, "No mobile notification channels configured."

        return any_ok, " | ".join(results)
