"""
Unit Tests for Atomic JSON Persistence & Thread-Safe Config Store (tests/test_atomic_config_store.py).
Verifies Audit Fix #3:
  - atomic_write_json writes cleanly without leaving .tmp_ files behind.
  - Interrupted / failed writes never truncate or corrupt the existing JSON file.
  - Concurrent multi-threaded save_state, append_log, and get_state never raise JSONDecodeError.
"""

import os
import json
import tempfile
import threading
import unittest

from aegis_quant.live.config_store import BotConfigStore, atomic_write_json


class TestAtomicConfigStore(unittest.TestCase):
    def test_atomic_write_leaves_no_temp_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "state.json")
            atomic_write_json(target, {"equity": 10250.5, "positions": ["SPY"]})
            with open(target, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded["equity"], 10250.5)
            leftovers = [n for n in os.listdir(tmpdir) if n.startswith(".tmp_")]
            self.assertEqual(leftovers, [])

    def test_failed_serialization_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "state.json")
            original = {"account": {"cash_usd": 10000.0}, "safe": True}
            atomic_write_json(target, original)

            # Attempt to write non-JSON-serializable object (simulating mid-write crash)
            with self.assertRaises(TypeError):
                atomic_write_json(target, {"bad": object()})

            # Original file must remain intact (not 0 bytes!) and no .tmp_ files left behind
            with open(target, "r", encoding="utf-8") as f:
                recovered = json.load(f)
            self.assertEqual(recovered, original)
            leftovers = [n for n in os.listdir(tmpdir) if n.startswith(".tmp_")]
            self.assertEqual(leftovers, [])

    def test_concurrent_reads_and_writes_thread_safe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = BotConfigStore(tmpdir)
            errors = []

            def writer(worker_id: int):
                try:
                    for i in range(15):
                        store.append_log(f"Worker {worker_id} event {i}", "INFO")
                except Exception as exc:
                    errors.append(exc)

            def reader():
                try:
                    for _ in range(25):
                        st = store.get_state()
                        self.assertIn("account", st)
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=writer, args=(w,)) for w in range(4)] + [
                threading.Thread(target=reader) for _ in range(4)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [])
            final_state = store.get_state()
            self.assertGreaterEqual(len(final_state["logs"]), 60)


if __name__ == "__main__":
    unittest.main()
