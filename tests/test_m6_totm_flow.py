"""
Unit Tests for Motor 6: Turn-of-the-Month Institutional Flow (tests/test_m6_totm_flow.py).
"""

import unittest
from datetime import date, timedelta

from aegis_quant.portfolio.aegis_engine import AegisPortfolioEngine
from aegis_quant.strategies.base import OPEN_TRADE_EXIT_DATE
from aegis_quant.strategies.m6_totm_flow import (
    TurnOfTheMonthFlowStrategy,
    business_day_index_in_month,
    business_days_remaining_in_month,
    is_totm_window,
)
from tests.helpers import create_mock_bar


class TestM6TotmFlowStrategy(unittest.TestCase):
    def setUp(self):
        self.strat = TurnOfTheMonthFlowStrategy()

    def test_calendar_business_day_helpers(self):
        # Octubre 2026: viernes 30 es el último día hábil del mes (sábado 31 fin de semana)
        self.assertEqual(business_days_remaining_in_month("2026-10-30"), 0)
        self.assertEqual(business_days_remaining_in_month("2026-10-29"), 1)
        self.assertGreater(business_days_remaining_in_month("2026-10-15"), 5)
        self.assertTrue(is_totm_window("2026-10-29"))
        self.assertTrue(is_totm_window("2026-10-30"))
        # Lunes 2 de noviembre de 2026 es el 1er día hábil del mes -> ventana TOTM
        self.assertEqual(business_day_index_in_month("2026-11-02"), 1)
        self.assertTrue(is_totm_window("2026-11-02"))
        self.assertFalse(is_totm_window("2026-10-15"))

    def test_triggers_on_month_end_pullback_in_contango(self):
        start = date(2026, 1, 1)
        series = [
            create_mock_bar(
                date=(start + timedelta(days=i)).isoformat(),
                close=450.0,
                sma5=448.0,
                sma200=400.0,
                rsi2=55.0,
                atr14=5.0,
                vts_ratio=0.90,
            )
            for i in range(215)
        ]
        # Añadir barra de fin de mes (viernes 2026-10-30) con debilidad RSI(2)=24 < 35 y Contango VTS=0.91
        series.append(
            create_mock_bar(
                date="2026-10-30",
                close=445.0,
                low=443.0,
                sma5=450.0,
                sma200=405.0,
                rsi2=24.0,
                atr14=5.0,
                vts_ratio=0.91,
            )
        )
        sig = self.strat.evaluate_live("QQQ", series)
        self.assertIsNotNone(sig)
        self.assertEqual(sig.engine_id, "M6_TOTM")
        self.assertEqual(sig.direction, "LONG")

        # En T+1 y T+2 rebota por encima de SMA(5) -> cierra con ganancia
        series.append(
            create_mock_bar(
                date="2026-11-02",
                close=448.0,
                low=444.0,
                sma5=449.0,
                sma200=405.0,
                rsi2=48.0,
                atr14=5.0,
                vts_ratio=0.90,
            )
        )
        series.append(
            create_mock_bar(
                date="2026-11-03",
                close=454.0,
                low=448.0,
                sma5=449.5,
                sma200=406.0,
                rsi2=76.0,
                atr14=5.0,
                vts_ratio=0.89,
            )
        )
        trades = self.strat.simulate("QQQ", series, start_date="2026-01-01")
        self.assertEqual(len(trades), 1)
        self.assertTrue(trades[0].win)
        self.assertEqual(trades[0].entry_date, "2026-10-30")
        self.assertEqual(trades[0].exit_date, "2026-11-03")

    def test_ignores_mid_month_or_backwardation(self):
        start = date(2026, 1, 1)
        series = [
            create_mock_bar(
                date=(start + timedelta(days=i)).isoformat(),
                close=450.0,
                sma200=400.0,
                rsi2=55.0,
                atr14=5.0,
                vts_ratio=0.90,
            )
            for i in range(215)
        ]
        # Mitad de mes (2026-10-15): no debe disparar aunque RSI(2) < 35
        series.append(
            create_mock_bar(
                date="2026-10-15",
                close=445.0,
                sma200=405.0,
                rsi2=20.0,
                atr14=5.0,
                vts_ratio=0.90,
            )
        )
        self.assertIsNone(self.strat.evaluate_live("QQQ", series))

        # Fin de mes pero en Backwardation (VTS=1.04 >= 0.98): no debe disparar
        series.append(
            create_mock_bar(
                date="2026-10-30",
                close=445.0,
                sma200=405.0,
                rsi2=20.0,
                atr14=5.0,
                vts_ratio=1.04,
            )
        )
        self.assertIsNone(self.strat.evaluate_live("QQQ", series))

    def test_include_open_and_live_engine_toggle(self):
        start = date(2026, 1, 1)
        qqq = [
            create_mock_bar(
                date=(start + timedelta(days=i)).isoformat(),
                close=450.0,
                sma5=448.0,
                sma50=430.0,
                sma200=400.0,
                rsi2=55.0,
                atr14=5.0,
                vts_ratio=0.90,
            )
            for i in range(215)
        ]
        qqq.append(
            create_mock_bar(
                date="2026-10-30",
                close=445.0,
                low=443.0,
                sma5=450.0,
                sma50=430.0,
                sma200=405.0,
                rsi2=30.0,
                atr14=5.0,
                vts_ratio=0.91,
            )
        )
        spy = [
            create_mock_bar(
                date=b.date,
                close=520.0,
                sma5=518.0,
                sma50=500.0,
                sma200=470.0,
                rsi2=52.0,
                atr14=5.0,
                vts_ratio=0.91,
            )
            for b in qqq
        ]

        open_trades = self.strat.simulate("QQQ", qqq, start_date="2026-01-01", include_open=True)
        self.assertEqual(len(open_trades), 1)
        self.assertEqual(open_trades[0].exit_date, OPEN_TRADE_EXIT_DATE)

        engine = AegisPortfolioEngine({"SPY": spy, "QQQ": qqq}, start_date="2026-01-01")
        live_on = engine.compute_live_portfolio(enabled_motors={"M6_TOTM": True})
        self.assertEqual(len(live_on["tactical"]["open_trades"]), 1)
        self.assertEqual(live_on["tactical"]["open_trades"][0]["engine_id"], "M6_TOTM")

        live_off = engine.compute_live_portfolio(enabled_motors={"M6_TOTM": False})
        self.assertEqual(live_off["tactical"]["open_trades"], [])


if __name__ == "__main__":
    unittest.main()
