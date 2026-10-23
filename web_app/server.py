"""
Servidor Web y Centro de Mando REST Orientado a Objetos para Aegis-Quant Studio (web_app/server.py).
Escucha en 0.0.0.0:8080 (accesible en local http://localhost:8080 y por VPN Tailscale desde el móvil).
Endpoints:
  - GET  /api/summary     : Dataset completo de los 4 modos, 725 operaciones, robustez y escáner.
  - GET  /api/live/status : Estado en tiempo real del Bot Paper Trading, cartera, órdenes y logs.
  - POST /api/live/action : Ejecuta acciones de mando (Iniciar/Parar, Escanear, Simular Motor, Pánico, Test Móvil).
  - POST /api/live/config : Actualiza parámetros del bot en caliente desde la web o móvil.
"""

import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Asegurar que el paquete raíz `aegis_quant` esté en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from aegis_quant.live.bot_controller import LiveBotController


class AegisRequestHandler(SimpleHTTPRequestHandler):
    base_dir = BASE_DIR
    web_dir = os.path.dirname(os.path.abspath(__file__))
    summary_cache = None
    bot_controller: LiveBotController = None

    @classmethod
    def get_summary(cls):
        if cls.summary_cache is None:
            summary_path = os.path.join(cls.base_dir, "data", "aegis_backtest_summary.json")
            with open(summary_path, "r", encoding="utf-8") as f:
                cls.summary_cache = json.load(f)
        return cls.summary_cache

    @classmethod
    def get_controller(cls) -> LiveBotController:
        if cls.bot_controller is None:
            cls.bot_controller = LiveBotController(cls.base_dir, cls.get_summary())
        return cls.bot_controller

    def translate_path(self, path):
        parsed = urllib.parse.urlparse(path).path
        if parsed == "/" or parsed == "/index.html":
            return os.path.join(self.web_dir, "index.html")
        rel = parsed.lstrip("/").replace("/", os.sep)
        return os.path.join(self.web_dir, rel)

    def _send_json(self, data: dict, status_code: int = 200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/summary":
            self._send_json(self.get_summary())
            return

        if parsed.path == "/api/live/status":
            ctrl = self.get_controller()
            self._send_json(ctrl.get_full_status())
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            body = json.loads(raw_body)
        except Exception:
            body = {}

        ctrl = self.get_controller()

        if parsed.path == "/api/live/action":
            res = ctrl.handle_action(body)
            self._send_json({"result": res, "status": ctrl.get_full_status()})
            return

        if parsed.path == "/api/live/config":
            updated = ctrl.store.update_config(body)
            ctrl.store.append_log(
                f"Parámetros actualizados en caliente desde la Web (Modo={updated.get('execution_mode')}, Bróker={updated.get('broker_provider')}, Capital=${updated.get('allocated_capital_usd'):,.0f}).",
                "INFO",
            )
            self._send_json({"ok": True, "config": updated, "status": ctrl.get_full_status()})
            return

        self._send_json({"ok": False, "error": "Ruta POST no encontrada"}, 404)

    def log_message(self, format, *args):
        pass


def run_server(port: int = 8080):
    # Inicializar el controlador en vivo al arrancar el servidor
    AegisRequestHandler.get_controller()
    # Escuchar en 0.0.0.0 para permitir acceso desde localhost y desde Tailscale VPN en el móvil
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, AegisRequestHandler)
    print("=" * 78)
    print(f"AEGIS-QUANT WEB STUDIO & PAPER TRADING CONTROL CENTER ACTIVO")
    print(f"  -> Acceso Local PC      : http://localhost:{port}")
    print(f"  -> Acceso Móvil Tailscale: http://<IP-TAILSCALE-SERVIDOR>:{port}")
    print("=" * 78)
    httpd.serve_forever()


if __name__ == "__main__":
    run_server(8080)
