"""
Unit Tests for Motor 3: Bear Market Short / Crisis Alpha Strategy (tests/test_m3_bear_short.py).
Tests:
  - Bear market regime filter (Close < SMA200 and SMA50 < SMA200).
  - Mode A: Rally Exhaustion (BOUNCE with RSI2 > 85 and VIX > 18).
  - Mode B: Panic Breakdown (BREAKDOWN under 20d low with VIX > 22).
  - Short stop loss above entry price (high >= stop_price).
  - Exit on bull regime restoration (Close > SMA200 * 1.01).
"""

import unittest
from aegis_quant.strategies.m3_bear_short import BearMarketShortStrategy
from tests.helpers import create_mock_bar


class TestBearMarketShortStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = BearMarketShortStrategy()

    def test_entry_blocked_in_bull_market(self):
        """When Close > SMA200, short engine must never trigger."""
        bar = create_mock_bar(close=500.0, sma200=450.0, rsi2=90.0)
        ok, _, _ = self.strategy._check_entry(bar)
        self.assertFalse(ok)

    def test_entry_triggered_on_bear_rally_exhaustion(self):
        """In bear market (Close < SMA200), an overbought bounce (RSI2 > 85) triggers BOUNCE short."""
        bar = create_mock_bar(
            close=390.0,
            sma50=395.0,
            sma200=420.0,
            sma200_rising=False,
            rsi2=88.0,
            vix_close=24.0,
            atr14=6.0,
        )
        ok, mode, reason = self.strategy._check_entry(bar)
        self.assertTrue(ok)
        self.assertEqual(mode, "BOUNCE")
        self.assertIn("Bear Rally Exhaustion", reason)

    def test_entry_triggered_on_bear_breakdown(self):
        """In bear market, breakdown under 20-day low with VIX > 22 triggers BREAKDOWN short."""
        bar = create_mock_bar(
            close=370.0,
            prev_low_20=375.0,
            sma50=390.0,
            sma200=420.0,
            sma200_rising=False,
            rsi2=25.0,
            vix_close=26.0,
            atr14=7.0,
        )
        ok, mode, reason = self.strategy._check_entry(bar)
        self.assertTrue(ok)
        self.assertEqual(mode, "BREAKDOWN")
        self.assertIn("Bear Breakdown", reason)

    def test_short_stop_loss_above_entry(self):
        """For short positions, stop price is above the entry: Close + 2.2 * ATR."""
        bar = create_mock_bar(close=400.0, atr14=10.0)
        stop_p, stop_d = self.strategy._calculate_stops(bar)
        self.assertEqual(stop_p, 422.0)
        self.assertEqual(stop_d, 5.5)

    def test_exit_on_short_stop_loss(self):
        """Short exit triggers when bar High rises to or above stop price."""
        bar = create_mock_bar(high=425.0, close=420.0, open_px=415.0)
        exit_flag, exit_price, reason = self.strategy._check_exit(
            bar, days=2, stop_price=422.0, mode="BOUNCE"
        )
        self.assertTrue(exit_flag)
        self.assertEqual(exit_price, 422.0)
        self.assertIn("Stop Loss Bajista", reason)

    def test_exit_on_bounce_target(self):
        """BOUNCE short exits when Close drops below SMA5 or RSI2 < 20."""
        bar = create_mock_bar(close=380.0, sma5=385.0, high=390.0, rsi2=18.0)
        exit_flag, exit_price, reason = self.strategy._check_exit(
            bar, days=2, stop_price=422.0, mode="BOUNCE"
        )
        self.assertTrue(exit_flag)
        self.assertEqual(exit_price, 380.0)
        self.assertIn("Target Corto", reason)


if __name__ == "__main__":
    unittest.main()
