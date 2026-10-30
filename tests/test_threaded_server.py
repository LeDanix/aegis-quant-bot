"""
Unit Tests for Multi-Threaded HTTP Server & Gzip Compression (tests/test_threaded_server.py).
Verifies Audit Fix #2:
  - Slow requests (e.g. Yahoo Finance latency) do NOT block concurrent fast requests (e.g. Kill-Switch / status).
  - Responses > 1 KB are gzip-compressed when client sends Accept-Encoding: gzip.
  - Directory traversal outside web_app/ is blocked.
"""

import gzip
import json
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from web_app.server import AegisRequestHandler


class _TestHandler(AegisRequestHandler):
    def do_GET(self):
        if self.path == "/test/slow":
            time.sleep(0.45)
            self._send_json({"slow": True})
            return
        if self.path == "/test/fast":
            self._send_json({"fast": True, "big": "x" * 2048})
            return
        return super().do_GET()

    def log_message(self, format, *args):
        pass


class TestThreadedServer(unittest.TestCase):
    def setUp(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _TestHandler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def test_fast_request_not_blocked_by_slow_request(self):
        slow_done = threading.Event()

        def call_slow():
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/test/slow", timeout=3).read()
            slow_done.set()

        t_slow = threading.Thread(target=call_slow)
        t_slow.start()
        time.sleep(0.05)  # Ensure slow request is already inside handler

        t0 = time.monotonic()
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/test/fast",
            headers={"Accept-Encoding": "gzip"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            encoding = resp.headers.get("Content-Encoding")
            raw = resp.read()
        elapsed = time.monotonic() - t0
        t_slow.join()

        # On a single-threaded server elapsed would be >= 0.40s; with ThreadingHTTPServer it completes immediately
        self.assertLess(elapsed, 0.25)
        self.assertEqual(encoding, "gzip")
        decoded = json.loads(gzip.decompress(raw).decode("utf-8"))
        self.assertTrue(decoded["fast"])

    def test_path_traversal_blocked(self):
        translated = _TestHandler.translate_path(_TestHandler, "/../../etc/passwd")
        self.assertTrue(translated.endswith("__forbidden__"))

    def test_init_lock_is_reentrant(self):
        # Prevents regression where get_controller() holding _init_lock calls get_summary()
        with AegisRequestHandler._init_lock:
            acquired_inner = AegisRequestHandler._init_lock.acquire(blocking=False)
            self.assertTrue(acquired_inner)
            AegisRequestHandler._init_lock.release()


if __name__ == "__main__":
    unittest.main()
