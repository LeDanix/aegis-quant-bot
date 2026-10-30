"""
Unit Tests for Motor 5: Volatility Term Structure Vol-Crush Strategy (tests/test_m5_vol_crush.py).
Tests:
  - VTS ratio backwardation compression detection (peak >= 1.00 compressing > 3.5%).
  - Falling knife filter (avoiding entries during unmitigated Lehman-style waterfalls).
  - Target exit on normalization to SMA(20) after >= 2 days or RSI2 > 82.
  - Re-expansion abort exit if backwardation re-accelerates (> 1.06).
"""

import unittest

from aegis_quant.strategies.m5_vol_crush import VolTermStructureCrushStrategy
from tests.helpers import create_mock_bar


class TestVolTermStructureCrushStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = VolTermStructureCrushStrategy()

    def test_vol_crush_entry_triggered(self):
        """When 5-day peak VTS >= 1.00 compresses by >3.5% and price stabilizes, entry triggers."""
        recent_bars = [
            create_mock_bar(vts_ratio=1.02),
            create_mock_bar(vts_ratio=1.08),  # Peak VTS = 1.08
            create_mock_bar(vts_ratio=1.07),
            create_mock_bar(vts_ratio=1.05),
            create_mock_bar(vts_ratio=1.04),
        ]
        prev_bar = create_mock_bar(low=480.0, close=482.0)
        # Today: VTS compresses to 1.01 (< 1.08 * 0.965 = 1.042), Close = 485 > prev low 480, RSI2 = 28 (< 45)
        today_bar = create_mock_bar(
            close=485.0,
            vts_ratio=1.01,
            vts_prev=1.04,
            rsi2=28.0,
            atr14=6.0,
        )
        ok, reason, peak_vts = self.strategy._check_entry(today_bar, prev_bar, recent_bars)
        self.assertTrue(ok)
        self.assertEqual(peak_vts, 1.08)
        self.assertIn("Compresion Backwardation", reason)
        self.assertIn("Flujo Vanna Positivo", reason)

    def test_falling_knife_filter_blocks_entry(self):
        """During catastrophic waterfalls (>14% below SMA200 with severe VTS > 1.12), filter blocks entry."""
        recent_bars = [create_mock_bar(vts_ratio=1.18) for _ in range(5)]
        prev_bar = create_mock_bar(low=380.0)
        today_bar = create_mock_bar(
            close=380.0,
            sma200=450.0,  # 380 < 450 * 0.86 = 387
            vts_ratio=1.14,  # > 1.12
            vts_prev=1.16,
            atr14=12.0,
        )
        ok, _, _ = self.strategy._check_entry(today_bar, prev_bar, recent_bars)
        self.assertFalse(ok)

    def test_exit_on_target_sma20_after_day_2(self):
        """Exit triggers when price normalizes back above SMA20 after >= 2 days."""
        entry_bar = create_mock_bar(close=480.0)
        bar = create_mock_bar(close=495.0, sma20=490.0, low=485.0)
        exit_flag, exit_price, reason = self.strategy._check_exit(bar, entry_bar, days=3, stop_price=465.0)
        self.assertTrue(exit_flag)
        self.assertEqual(exit_price, 495.0)
        self.assertIn("Target Vol-Crush: Normalizacion a SMA(20)", reason)

    def test_exit_on_backwardation_reexpansion(self):
        """Exit aborts early if panic reignites with VTS > 1.06 and price below entry."""
        entry_bar = create_mock_bar(close=485.0)
        bar = create_mock_bar(close=480.0, vts_ratio=1.09, low=478.0)
        exit_flag, _, reason = self.strategy._check_exit(bar, entry_bar, days=1, stop_price=465.0)
        self.assertTrue(exit_flag)
        self.assertIn("Re-expansion Backwardation", reason)


if __name__ == "__main__":
    unittest.main()
