"""
Object-Oriented Mobile Notification Service (aegis_quant/live/notifier_service.py).
Dedicated to Signal Messenger:
  - Direct HTTP via CallMeBot Signal Gateway (free personal API)
  - Local Docker signal-cli-rest-api daemon (e.g. http://127.0.0.1:8085/v2/send)
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
            return False, "Signal no configurado (falta número de teléfono o apikey/URL de pasarela)."

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
    """Dispatches notifications across configured active channels (Signal Messenger)."""

    def __init__(self, config: Dict[str, Any]):
        phone = config.get("mobile_phone") or config.get("signal_recipient_phone", "")
        self.signal = SignalRestNotifier(
            api_url=config.get("signal_api_url", "https://api.callmebot.com/signal/send.php"),
            phone=phone,
            apikey=config.get("signal_apikey", ""),
        )

    def notify(self, text: str) -> Tuple[bool, str]:
        if not self.signal.is_configured():
            return True, "Canal de notificaciones Signal no configurado."
        ok, msg = self.signal.send_message(text)
        return ok, f"Signal: {msg}"
