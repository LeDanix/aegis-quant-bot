"""
Unit Tests for Motor 4: Multi-Asset CTA Trend Breakout Strategy (tests/test_m4_cta_trend.py).
Tests:
  - 20-day Donchian breakout entry with SMA50 > SMA200 alignment.
  - Entry rejection if breakout lacks trend alignment.
  - Dynamic trailing stop calculation (max of initial stop, 10d low, peak - 3x ATR).
  - Trend termination exit on Close < SMA50.
"""

import unittest

from aegis_quant.strategies.m4_cta_trend import CommodityBreakoutCTAStrategy
from tests.helpers import create_mock_bar


class TestCommodityBreakoutCTAStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = CommodityBreakoutCTAStrategy()

    def test_donchian_breakout_entry_triggered(self):
        """When Close breaks above 20d high with SMA50 > SMA200, entry must trigger."""
        bar = create_mock_bar(
            close=195.0,
            prev_high_20=190.0,
            sma50=180.0,
            sma200=160.0,
            atr14=3.0,
        )
        ok, reason = self.strategy._check_entry(bar, "GLD")
        self.assertTrue(ok)
        self.assertIn("Ruptura Donchian 20d", reason)
        self.assertIn("SMA50>SMA200", reason)

    def test_breakout_rejected_if_trend_not_aligned(self):
        """If Close breaks 20d high but SMA50 < SMA200, entry must be rejected."""
        bar = create_mock_bar(
            close=195.0,
            prev_high_20=190.0,
            sma50=150.0,
            sma200=170.0,
            atr14=3.0,
        )
        ok, _ = self.strategy._check_entry(bar, "GLD")
        self.assertFalse(ok)

    def test_dynamic_trailing_stop_calculation(self):
        """Trailing stop must elevate to protect profits as market creates higher lows."""
        bar = create_mock_bar(prev_low_10=188.0, atr14=2.0)
        # initial stop = 175.0, highest close = 196.0 -> highest_close - 3*ATR = 190.0
        # prev_low_10 = 188.0
        # trailing stop = max(175.0, 188.0, 190.0) = 190.0
        trailing_stop = self.strategy._calculate_trailing_stop(bar, initial_stop=175.0, highest_close=196.0)
        self.assertEqual(trailing_stop, 190.0)

    def test_exit_on_loss_of_medium_term_trend(self):
        """When Close drops below SMA50, position must be liquidated."""
        bar = create_mock_bar(close=178.0, sma50=182.0, low=177.0)
        exit_flag, exit_price, reason = self.strategy._check_exit(bar, days=15, trailing_stop=170.0)
        self.assertTrue(exit_flag)
        self.assertEqual(exit_price, 178.0)
        self.assertIn("Close < SMA50", reason)


if __name__ == "__main__":
    unittest.main()
