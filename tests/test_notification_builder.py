"""
Unit Tests for Enriched Mobile Notification Builder (tests/test_notification_builder.py).
Tests:
  - Formats market pulse with % daily changes for SPY, QQQ, VIX.
  - Formats portfolio equity and positions cleanly without float artifacts.
  - Verifies that executed orders or holding confirmations are clearly displayed.
"""

import unittest
from aegis_quant.live.bot_controller import LiveBotController


class TestNotificationBuilder(unittest.TestCase):
    def test_notification_message_formatting(self):
        """Verifies that the executive report contains all required quantitative sections."""
        # Create a mock controller without starting background thread
        class DummyController(LiveBotController):
            def __init__(self):
                pass

        ctrl = DummyController()
        ctrl.get_time_info = staticmethod(LiveBotController.get_time_info)

        pulse = {
            "SPY": {"price": 580.50, "change_pct": 0.45},
            "QQQ": {"price": 490.20, "change_pct": -0.32},
            "VIX": {"price": 16.50, "change_pct": -1.2},
            "VIX3M": {"price": 18.50, "change_pct": 0.0},
        }

        state_after = {
            "account": {
                "total_equity_usd": 10250.00,
                "initial_capital": 10000.00,
                "cash_usd": 50.00,
                "total_return_pct": 2.50,
                "current_dd_pct": -0.80,
            },
            "positions": [
                {
                    "broker_symbol": "SPY",
                    "weight_pct": 85.0,
                    "market_value_usd": 8700.00,
                    "unrealized_pnl_usd": 180.00,
                },
                {
                    "broker_symbol": "QQQ",
                    "weight_pct": 15.0,
                    "market_value_usd": 1500.00,
                    "unrealized_pnl_usd": 70.00,
                },
            ],
        }

        orders = [
            {
                "side": "BUY",
                "symbol": "SPY",
                "notional_usd": 1200.00,
                "motor": "CORE_BULL",
            }
        ]

        msg = ctrl._build_notification_message("Reloj Automático", orders, pulse, state_after)

        # 1. Market pulse check
        self.assertIn("PULSO DEL MERCADO HOY", msg)
        self.assertIn("<b>SPY</b>: $580.50 (+0.45%)", msg)
        self.assertIn("<b>QQQ</b>: $490.20 (-0.32%)", msg)
        self.assertIn("<b>VIX</b>: 16.50", msg)
        self.assertIn("Ratio: 0.892 (Contango (Alcista))", msg)

        # 2. Portfolio equity and positions
        self.assertIn("Capital Total: <b>$10,250.00</b>", msg)
        self.assertIn("SPY (85.0%): $8,700.00 (P&L: +$180.00)", msg)
        self.assertIn("QQQ (15.0%): $1,500.00 (P&L: +$70.00)", msg)

        # 3. Orders execution check
        self.assertIn("BUY SPY</b>: $1,200.00 (CORE_BULL)", msg)

        # 4. Check when no orders are executed
        msg_no_orders = ctrl._build_notification_message("Reloj Automático", [], pulse, state_after)
        self.assertIn("Sin rotación necesaria. Cartera alineada al régimen.", msg_no_orders)


if __name__ == "__main__":
    unittest.main()
