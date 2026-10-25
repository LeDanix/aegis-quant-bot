"""
Unit Tests for Motor 2: Scherman VIX Divergence Strategy (tests/test_m2_vix_divergence.py).
Tests:
  - Divergence detection (VIX turning down from peak >= 20 while price is oversold).
  - Normal conditions blocking entry (VIX not high enough or still expanding).
  - Exits on SMA(5) after holding >= 2 days or RSI(2) > 80.
"""

import unittest
from aegis_quant.strategies.m2_vix_divergence import SchermanVixDivergenceStrategy
from tests.helpers import create_mock_bar


class TestSchermanVixDivergenceStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = SchermanVixDivergenceStrategy()

    def test_divergence_entry_triggered(self):
        """When VIX rolls over from 5d peak >= 20 while price tests low, entry must trigger."""
        recent_bars = [
            create_mock_bar(vix_close=22.0, low=490.0),
            create_mock_bar(vix_close=25.0, low=488.0),  # Peak VIX = 25.0
            create_mock_bar(vix_close=24.5, low=486.0),
            create_mock_bar(vix_close=24.0, low=485.0),
            create_mock_bar(vix_close=23.5, low=484.0),
        ]
        # Today: VIX compressed to 23.0 (< 25 * 0.96 = 24.0), RSI2 = 10 (< 12)
        today_bar = create_mock_bar(
            close=484.0,
            low=483.0,
            sma200=450.0,
            rsi2=10.0,
            vix_close=23.0,
            atr14=5.0,
        )
        ok, reason, peak_vix = self.strategy._check_entry(today_bar, recent_bars)
        self.assertTrue(ok)
        self.assertEqual(peak_vix, 25.0)
        self.assertIn("Divergencia VIX", reason)

    def test_divergence_blocked_if_vix_peak_under_20(self):
        """If peak VIX was only 18 (< 20), divergence does not trigger."""
        recent_bars = [create_mock_bar(vix_close=17.0, low=490.0) for _ in range(5)]
        today_bar = create_mock_bar(close=484.0, rsi2=10.0, vix_close=15.0, atr14=5.0)
        ok, _, _ = self.strategy._check_entry(today_bar, recent_bars)
        self.assertFalse(ok)

    def test_exit_on_target_sma5_with_holding_period(self):
        """Exit triggers when Close > SMA5 and holding days >= 2."""
        bar = create_mock_bar(close=500.0, sma5=495.0, low=490.0, rsi2=60.0)
        exit_flag, exit_price, reason = self.strategy._check_exit(bar, days=2, stop_price=470.0)
        self.assertTrue(exit_flag)
        self.assertEqual(exit_price, 500.0)
        self.assertIn("Target: Cierre > SMA(5)", reason)

    def test_no_exit_on_day_1_even_if_close_above_sma5(self):
        """Strategy requires at least 2 days to let the divergence mean-reversion mature."""
        bar = create_mock_bar(close=500.0, sma5=495.0, low=490.0, rsi2=60.0)
        exit_flag, _, _ = self.strategy._check_exit(bar, days=1, stop_price=470.0)
        self.assertFalse(exit_flag)


if __name__ == "__main__":
    unittest.main()
