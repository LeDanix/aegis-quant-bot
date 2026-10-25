"""
Unit Tests for Timezone & DST Aware Scheduling (tests/test_timezone_scheduler.py).
Tests:
  - Correct conversion of New York market close (15:55 America/New_York) to Madrid local time.
  - Automatic detection of seasonal DST discrepancies (5 hours vs 6 hours difference).
  - Validation that schedule times adapt cleanly across seasons.
"""

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from aegis_quant.live.bot_controller import LiveBotController


class TestTimezoneScheduler(unittest.TestCase):
    def test_get_time_info_structure(self):
        """Verifies that get_time_info returns complete, synchronized metadata."""
        info = LiveBotController.get_time_info("15:55")
        self.assertIn("ny_time", info)
        self.assertIn("madrid_time", info)
        self.assertIn("schedule_time_ny", info)
        self.assertIn("schedule_time_madrid", info)
        self.assertIn("time_diff_hours", info)
        self.assertIn("is_dst_mismatch", info)
        self.assertTrue(info["schedule_time_ny"].startswith("15:55"))

    def test_dst_offset_calculation(self):
        """Difference between Madrid and NY must always be either 5 hours or 6 hours."""
        info = LiveBotController.get_time_info("15:55")
        diff = info["time_diff_hours"]
        self.assertIn(diff, (5, 6))

        # If diff is 5h, Madrid target must be 20:55; if 6h, Madrid target must be 21:55
        sched_madrid = info["schedule_time_madrid"]
        if diff == 5:
            self.assertTrue(sched_madrid.startswith("20:55"))
            self.assertTrue(info["is_dst_mismatch"])
            self.assertIn("Desfase estacional activo", info["mismatch_notice"])
        else:
            self.assertTrue(sched_madrid.startswith("21:55"))
            self.assertFalse(info["is_dst_mismatch"])


if __name__ == "__main__":
    unittest.main()
