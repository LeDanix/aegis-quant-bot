"""
Servidor Web y Centro de Mando REST Orientado a Objetos para Aegis-Quant Studio (web_app/server.py).
Escucha en 0.0.0.0:8085 (accesible en local http://localhost:8085 y por VPN Tailscale desde el móvil).
Endpoints:
  - GET  /api/summary        : Dataset completo de los 4 modos, 6 motores (780 operaciones), robustez y cascada fiscal.
  - GET  /api/live/status    : Estado en tiempo real del Bot, cartera, 6 motores tácticos, órdenes y logs.
  - GET  /api/tax/live-audit : Auditoría fiscal automática AEAT (FIFO, regla 2 meses, BCE EUR/USD, Modelo 720, Renta WEB F2).
  - GET  /api/tax/export.csv : Exportación CSV UTF-8 BOM para Excel y Renta WEB.
  - POST /api/live/action    : Ejecuta acciones de mando (Iniciar/Parar, Escanear, Simular Motor M1-M6, Pánico, Test Móvil).
  - POST /api/live/config    : Actualiza parámetros del bot en caliente desde la web o móvil.
"""

import os
import sys
import gzip
import json
import threading
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# Asegurar que el paquete raíz `aegis_quant` esté en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from aegis_quant.live.bot_controller import LiveBotController
from aegis_quant.tax.spanish_tax_engine import SpanishTaxAuditor


class AegisRequestHandler(SimpleHTTPRequestHandler):
    base_dir = BASE_DIR
    web_dir = os.path.dirname(os.path.abspath(__file__))
    summary_cache = None
    summary_raw_bytes = None
    summary_gzip_bytes = None
    bot_controller: LiveBotController = None
    _init_lock = threading.RLock()

    @classmethod
    def get_summary(cls):
        if cls.summary_cache is None:
            with cls._init_lock:
                if cls.summary_cache is None:
                    summary_path = os.path.join(cls.base_dir, "data", "aegis_backtest_summary.json")
                    with open(summary_path, "r", encoding="utf-8") as f:
                        cls.summary_cache = json.load(f)
                    cls.summary_raw_bytes = json.dumps(cls.summary_cache, ensure_ascii=False).encode("utf-8")
                    cls.summary_gzip_bytes = gzip.compress(cls.summary_raw_bytes, compresslevel=6)
        return cls.summary_cache

    @classmethod
    def get_controller(cls) -> LiveBotController:
        if cls.bot_controller is None:
            with cls._init_lock:
                if cls.bot_controller is None:
                    cls.bot_controller = LiveBotController(cls.base_dir, cls.get_summary())
        return cls.bot_controller

    def translate_path(self, path):
        parsed = urllib.parse.urlparse(path).path
        if parsed == "/" or parsed == "/index.html":
            return os.path.join(self.web_dir, "index.html")
        rel = os.path.normpath(parsed.lstrip("/").replace("/", os.sep))
        candidate = os.path.abspath(os.path.join(self.web_dir, rel))
        if os.path.commonpath([os.path.abspath(self.web_dir), candidate]) != os.path.abspath(self.web_dir):
            return os.path.join(self.web_dir, "__forbidden__")
        return candidate

    def _client_accepts_gzip(self) -> bool:
        """True si el navegador anuncia soporte gzip (todos los móviles modernos lo hacen)."""
        return "gzip" in self.headers.get("Accept-Encoding", "")

    def _send_bytes(self, payload: bytes, use_gzip: bool, status_code: int = 200):
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            if use_gzip:
                self.send_header("Content-Encoding", "gzip")
                self.send_header("Vary", "Accept-Encoding")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_json(self, data: dict, status_code: int = 200):
        """
        Envía una respuesta JSON. Si es grande (>1 KB) y el cliente lo admite, la comprime
        con gzip: el resumen de backtest pasa de ~4 MB a unos cientos de KB, clave en datos móviles.
        """
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        use_gzip = len(payload) > 1024 and self._client_accepts_gzip()
        if use_gzip:
            payload = gzip.compress(payload, compresslevel=6)
        self._send_bytes(payload, use_gzip=use_gzip, status_code=status_code)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/summary":
            self.get_summary()
            if self._client_accepts_gzip() and self.summary_gzip_bytes is not None:
                self._send_bytes(self.summary_gzip_bytes, use_gzip=True, status_code=200)
            else:
                self._send_bytes(self.summary_raw_bytes, use_gzip=False, status_code=200)
            return

        if parsed.path == "/api/live/status":
            ctrl = self.get_controller()
            self._send_json(ctrl.get_full_status())
            return

        if parsed.path == "/api/tax/live-audit":
            qs = urllib.parse.parse_qs(parsed.query)
            env = (qs.get("env", ["PAPER"])[0] or "PAPER").upper()
            year = qs.get("year", ["ALL"])[0] or "ALL"
            prior_loss = 0.0
            try:
                prior_loss = max(0.0, float(qs.get("prior_loss", ["0"])[0]))
            except (TypeError, ValueError):
                prior_loss = 0.0
            auditor = SpanishTaxAuditor(self.base_dir, allow_network_fx=False)
            report = auditor.audit_environment(
                env=env,
                tax_year=year,
                prior_loss_carryforward_eur=prior_loss,
            )
            self._send_json(report)
            return

        if parsed.path == "/api/tax/export.csv":
            qs = urllib.parse.parse_qs(parsed.query)
            env = (qs.get("env", ["PAPER"])[0] or "PAPER").upper()
            year = qs.get("year", ["ALL"])[0] or "ALL"
            auditor = SpanishTaxAuditor(self.base_dir, allow_network_fx=False)
            csv_text = auditor.export_audit_csv(env=env, tax_year=year)
            csv_bytes = csv_text.encode("utf-8")
            filename = f"aegis_quant_aeat_irpf_{env.lower()}_{year.lower()}.csv"
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(csv_bytes)))
                self.end_headers()
                self.wfile.write(csv_bytes)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        # Servir activos estáticos locales (HTML, CSS compilado, JS, SVG) con gzip y MIME explícito
        local_file = self.translate_path(self.path)
        if os.path.isfile(local_file):
            ext = os.path.splitext(local_file)[1].lower()
            mime_map = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".svg": "image/svg+xml",
            }
            if ext in mime_map:
                try:
                    with open(local_file, "rb") as f:
                        payload = f.read()
                    use_gzip = len(payload) > 1024 and self._client_accepts_gzip()
                    if use_gzip:
                        payload = gzip.compress(payload, compresslevel=6)
                    self.send_response(200)
                    self.send_header("Content-Type", mime_map[ext])
                    if "echarts.min.js" in local_file:
                        self.send_header("Cache-Control", "public, max-age=86400")
                    else:
                        self.send_header("Cache-Control", "no-cache, must-revalidate")
                    if use_gzip:
                        self.send_header("Content-Encoding", "gzip")
                        self.send_header("Vary", "Accept-Encoding")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError):
                    pass
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
        sys.stderr.write("[%s] %s - %s\n" % (self.log_date_time_string(), self.client_address[0], format % args))
        sys.stderr.flush()


def _get_tailscale_ip() -> str:
    try:
        import subprocess
        res = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return ""


def run_server(port: int = 8085):
    # Inicializar el controlador en vivo al arrancar el servidor
    AegisRequestHandler.get_controller()
    # Escuchar en 0.0.0.0 para permitir acceso desde localhost y desde Tailscale VPN en el móvil.
    # ThreadingHTTPServer atiende cada petición en su propio hilo: una consulta lenta a Yahoo
    # Finance (escaneo) ya no congela la web ni deja en cola el botón de pánico.
    server_address = ("0.0.0.0", port)
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(server_address, AegisRequestHandler)
    ts_ip = _get_tailscale_ip()
    print("=" * 78)
    print(f"AEGIS-QUANT WEB STUDIO & PAPER TRADING CONTROL CENTER ACTIVO")
    print(f"  -> Acceso Local PC      : http://localhost:{port}")
    if ts_ip:
        print(f"  -> Acceso Móvil Tailscale: http://{ts_ip}:{port}")
    else:
        print(f"  -> Acceso Móvil Tailscale: http://<IP-TAILSCALE-SERVIDOR>:{port}")
    print("=" * 78)
    sys.stdout.flush()
    httpd.serve_forever()


def main():
    port = 8085
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    elif "PORT" in os.environ:
        try:
            port = int(os.environ["PORT"])
        except ValueError:
            pass
    elif "AEGIS_PORT" in os.environ:
        try:
            port = int(os.environ["AEGIS_PORT"])
        except ValueError:
            pass
    run_server(port)


if __name__ == "__main__":
    main()
