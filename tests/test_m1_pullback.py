"""
Unit Tests for Motor 1: Scherman Pullback Strategy (tests/test_m1_pullback.py).
Tests:
  - Entry conditions (RSI(2)<10, Bollinger Band penetration, 3-day down streak).
  - Stop loss calculations and exits.
  - Profit target exits (Close > SMA5, RSI2 > 75).
  - Trend filters (Close <= SMA200 blocks entry).
"""

import unittest

from aegis_quant.strategies.m1_pullback import SchermanPullbackStrategy
from tests.helpers import create_mock_bar


class TestSchermanPullbackStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = SchermanPullbackStrategy()

    def test_entry_triggered_by_rsi2_extreme_in_bull_trend(self):
        """When in bull trend (Close > SMA200) and RSI(2) < 10, entry must trigger."""
        bar = create_mock_bar(close=500.0, sma200=450.0, rsi2=6.5, atr14=4.0)
        ok, reason = self.strategy._check_entry(bar)
        self.assertTrue(ok)
        self.assertIn("RSI(2)=6.5<10", reason)
        self.assertIn("Close>SMA200", reason)

    def test_entry_triggered_by_lower_bollinger_penetration(self):
        """When Close < lower Bollinger band and RSI2 < 25, entry must trigger."""
        bar = create_mock_bar(
            close=480.0,
            lower_band30=485.0,
            sma200=450.0,
            rsi2=22.0,
            atr14=4.0,
        )
        ok, reason = self.strategy._check_entry(bar)
        self.assertTrue(ok)
        self.assertIn("Close<BollingerInf", reason)

    def test_entry_triggered_by_3_day_down_streak(self):
        """When 3 consecutive down days occur and RSI2 < 18, entry must trigger."""
        bar = create_mock_bar(
            close=490.0,
            sma200=450.0,
            rsi2=15.0,
            down_streak=3,
            atr14=4.0,
        )
        ok, reason = self.strategy._check_entry(bar)
        self.assertTrue(ok)
        self.assertIn("3 dias bajistas", reason)

    def test_entry_blocked_in_bear_regime(self):
        """Even with extreme oversold RSI(2) = 3.0, if Close <= SMA200 entry must be rejected."""
        bar = create_mock_bar(close=400.0, sma200=450.0, rsi2=3.0, atr14=4.0)
        ok, _ = self.strategy._check_entry(bar)
        self.assertFalse(ok)

    def test_calculate_stops(self):
        """Stop price must be Close - 2.5 * ATR14."""
        bar = create_mock_bar(close=500.0, atr14=10.0)
        stop_p, stop_d = self.strategy._calculate_stops(bar)
        self.assertEqual(stop_p, 475.0)
        self.assertEqual(stop_d, 5.0)

    def test_exit_on_target_sma5(self):
        """Exit must trigger when Close > SMA5."""
        bar = create_mock_bar(close=502.0, sma5=498.0, low=495.0, rsi2=55.0)
        exit_flag, exit_price, reason = self.strategy._check_exit(bar, days=2, stop_price=475.0)
        self.assertTrue(exit_flag)
        self.assertEqual(exit_price, 502.0)
        self.assertIn("Target: Cierre > SMA(5)", reason)

    def test_exit_on_stop_loss(self):
        """Exit must trigger at stop price when bar Low <= stop price."""
        bar = create_mock_bar(open_px=480.0, low=470.0, close=472.0, sma5=498.0)
        exit_flag, exit_price, reason = self.strategy._check_exit(bar, days=1, stop_price=475.0)
        self.assertTrue(exit_flag)
        self.assertEqual(exit_price, 475.0)
        self.assertIn("Stop Loss ATR", reason)

    def test_exit_on_time_stop(self):
        """Exit must trigger when position reaches 10 days."""
        bar = create_mock_bar(close=490.0, sma5=495.0, low=485.0, rsi2=50.0)
        exit_flag, exit_price, reason = self.strategy._check_exit(bar, days=10, stop_price=470.0)
        self.assertTrue(exit_flag)
        self.assertIn("Time Stop: 10 sesiones", reason)


if __name__ == "__main__":
    unittest.main()
