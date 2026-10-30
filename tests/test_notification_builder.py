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
        self.assertIn("<b>SPY</b>: 580.50 $ (+0.45%)", msg)
        self.assertIn("<b>QQQ</b>: 490.20 $ (-0.32%)", msg)
        self.assertIn("<b>VIX</b>: 16.50", msg)
        self.assertIn("Ratio: 0.892 (Contango (Alcista))", msg)

        # 2. Portfolio equity and positions (Sin separador de miles, decimales con punto, sin prefijo $)
        self.assertIn("Capital Total: <b>10250.00 $</b>", msg)
        self.assertIn("SPY (85.0%): 8700.00 $ (P&L: +180.00 $)", msg)
        self.assertIn("QQQ (15.0%): 1500.00 $ (P&L: +70.00 $)", msg)

        # 3. Orders execution check
        self.assertIn("BUY SPY</b>: 1200.00 $ (CORE_BULL)", msg)

        # 4. Anti-shell-expansion check (nunca debe haber $ prefijando números para evitar borrado en CallMeBot)
        self.assertNotIn("$10", msg)
        self.assertNotIn("$8", msg)
        self.assertNotIn("$1", msg)

        # 4. Check when no orders are executed (default fallback)
        msg_no_orders = ctrl._build_notification_message("Reloj Automático", [], pulse, state_after)
        self.assertIn("Sin rotación necesaria. Cartera alineada al régimen.", msg_no_orders)

        # 5. Check direct reason for closed market or defensive regime
        msg_closed = ctrl._build_notification_message(
            "Reloj Automático",
            [],
            pulse,
            state_after,
            direct_reason="Mercado cerrado: Fin de semana (Sábado). Wall Street inactivo. Cartera protegida.",
        )
        self.assertIn("Mercado cerrado: Fin de semana (Sábado)", msg_closed)
        self.assertIn("Cartera protegida.", msg_closed)

        # 6. Check differentiation between 100% cash and active positions maintained
        state_cash = {"account": {"total_equity_usd": 10000.0, "cash_usd": 10000.0, "total_return_pct": 0.0, "current_dd_pct": 0.0}, "positions": []}
        msg_100_cash = ctrl._build_notification_message(
            "Reloj Automático",
            [],
            pulse,
            state_cash,
            direct_reason="Sin operaciones. Cartera al 100% en liquidez/efectivo. Razón: Mercado en régimen defensivo (SPY por debajo de SMA-50) y ningún motor táctico (M1–M6) activó señal de entrada.",
        )
        self.assertIn("Cartera al 100% en liquidez/efectivo", msg_100_cash)
        self.assertIn("100% en Efectivo / Sin posiciones abiertas.", msg_100_cash)

        msg_active_pos = ctrl._build_notification_message(
            "Reloj Automático",
            [],
            pulse,
            state_after,
            direct_reason="Sin rotación necesaria. Posiciones activas mantenidas: SPY (85.0%), QQQ (15.0%) (Efectivo: 0.5%). Razón: Cartera ya alineada al 100% con los pesos óptimos del régimen alcista.",
        )
        self.assertIn("Posiciones activas mantenidas: SPY (85.0%), QQQ (15.0%)", msg_active_pos)
        self.assertIn("SPY (85.0%): 8700.00 $", msg_active_pos)

    def test_market_session_status(self):
        """Verifies weekend and holiday detection for Wall Street calendar."""
        import datetime
        from zoneinfo import ZoneInfo

        # Saturday
        sat = datetime.datetime(2026, 10, 24, 15, 55, tzinfo=ZoneInfo("America/New_York"))
        closed, reason = LiveBotController.get_market_session_status(sat)
        self.assertTrue(closed)
        self.assertIn("Sábado", reason)

        # Sunday
        sun = datetime.datetime(2026, 10, 25, 15, 55, tzinfo=ZoneInfo("America/New_York"))
        closed, reason = LiveBotController.get_market_session_status(sun)
        self.assertTrue(closed)
        self.assertIn("Domingo", reason)

        # Christmas Day 2026 (Friday Dec 25)
        xmas = datetime.datetime(2026, 12, 25, 15, 55, tzinfo=ZoneInfo("America/New_York"))
        closed, reason = LiveBotController.get_market_session_status(xmas)
        self.assertTrue(closed)
        self.assertIn("Navidad", reason)

        # Regular trading day (e.g. Wednesday Oct 21, 2026)
        wed = datetime.datetime(2026, 10, 21, 15, 55, tzinfo=ZoneInfo("America/New_York"))
        closed, reason = LiveBotController.get_market_session_status(wed)
        self.assertFalse(closed)
        self.assertIn("Sesión de negociación activa", reason)

    def test_is_market_open_now_and_time_info(self):
        import datetime
        from zoneinfo import ZoneInfo

        # Pre-apertura (09:15 ET)
        pre = datetime.datetime(2026, 10, 30, 9, 15, tzinfo=ZoneInfo("America/New_York"))
        is_open, desc = LiveBotController.is_market_open_now(pre)
        self.assertFalse(is_open)
        self.assertIn("Pre-apertura", desc)

        # Mercado abierto en sesión regular (10:30 ET)
        open_time = datetime.datetime(2026, 10, 30, 10, 30, tzinfo=ZoneInfo("America/New_York"))
        is_open, desc = LiveBotController.is_market_open_now(open_time)
        self.assertTrue(is_open)
        self.assertIn("activa", desc)

        # Mercado abierto justo antes del cierre (15:55 ET)
        near_close = datetime.datetime(2026, 10, 30, 15, 55, tzinfo=ZoneInfo("America/New_York"))
        is_open, desc = LiveBotController.is_market_open_now(near_close)
        self.assertTrue(is_open)

        # Fuera de sesión regular (16:05 ET)
        after_close = datetime.datetime(2026, 10, 30, 16, 5, tzinfo=ZoneInfo("America/New_York"))
        is_open, desc = LiveBotController.is_market_open_now(after_close)
        self.assertFalse(is_open)
        self.assertIn("Fuera de sesión", desc)

        # Fin de semana (Sábado a las 11:00 ET)
        sat = datetime.datetime(2026, 10, 31, 11, 0, tzinfo=ZoneInfo("America/New_York"))
        is_open, desc = LiveBotController.is_market_open_now(sat)
        self.assertFalse(is_open)
        self.assertIn("Sábado", desc)

        # Festivo oficial NYSE
        xmas = datetime.datetime(2026, 12, 25, 11, 0, tzinfo=ZoneInfo("America/New_York"))
        is_open, desc = LiveBotController.is_market_open_now(xmas)
        self.assertFalse(is_open)
        self.assertIn("Festivo oficial", desc)

        # get_time_info() contiene los metadatos de sesión
        t_info = LiveBotController.get_time_info()
        self.assertIn("is_market_open", t_info)
        self.assertIn("market_status_desc", t_info)
        self.assertIsInstance(t_info["is_market_open"], bool)


if __name__ == "__main__":
    unittest.main()
