"""
Unit Tests for Dynamic Live Tactical Scanner M1-M5 + Core Modo 3 Élite (tests/test_live_tactical_scanner.py).
Verifies Audit Fix #1:
  - Live evaluation triggers tactical signals on the latest bar (e.g. M1 Pullback, M3 Bear Short).
  - Multi-day tactical positions opened in prior sessions remain allocated until their exit rule triggers.
  - Idle capital (1.0 - tactical weight) is dynamically allocated to Core Modo 3 Élite without exceeding 100%.
  - Individual motor enable/disable toggles in config are respected.
"""

import unittest
from datetime import date, timedelta
from typing import List

from aegis_quant.models.market_models import EnrichedBar
from aegis_quant.portfolio.aegis_engine import AegisPortfolioEngine
from tests.helpers import create_mock_bar


def _build_series(n: int = 220, base_close: float = 500.0) -> List[EnrichedBar]:
    start = date(2026, 1, 1)
    bars: List[EnrichedBar] = []
    for i in range(n):
        d = (start + timedelta(days=i)).isoformat()
        bars.append(
            create_mock_bar(
                date=d,
                close=base_close,
                open_px=base_close,
                high=base_close + 3.0,
                low=base_close - 3.0,
                sma5=base_close - 2.0,
                sma20=base_close - 5.0,
                sma50=base_close - 10.0,
                sma200=base_close - 40.0,
                rsi2=50.0,
                atr14=5.0,
                vix_close=15.0,
                vix3m_close=17.5,
                vts_ratio=0.86,
            )
        )
    return bars


class TestLiveTacticalScanner(unittest.TestCase):
    def test_calm_bull_allocates_100pct_to_elite_core(self):
        universe = {
            "SPY": _build_series(220, 500.0),
            "QQQ": _build_series(220, 420.0),
            "GLD": _build_series(220, 200.0),
        }
        engine = AegisPortfolioEngine(universe, start_date="2026-01-01")
        res = engine.compute_live_portfolio()

        self.assertEqual(res["tactical"]["open_trades"], [])
        self.assertEqual(res["tactical"]["signals_today"], [])
        self.assertAlmostEqual(res["tactical"]["idle_cash_pct"], 100.0)
        total_w = sum(v["weight"] for v in res["targets"].values())
        self.assertAlmostEqual(total_w, 1.0, places=3)
        self.assertEqual(res["targets"]["SPY"]["motor"], "CORE_BULL")

    def test_m1_pullback_live_signal_takes_priority_slot(self):
        qqq_series = _build_series(220, 420.0)
        # Trigger M1 Pullback today on QQQ: Close (410) > SMA200 (380), RSI(2)=6.0 < 10, Close < SMA(5)
        qqq_series[-1] = create_mock_bar(
            date=qqq_series[-1].date,
            close=410.0,
            open_px=414.0,
            high=415.0,
            low=409.0,
            sma5=418.0,
            sma20=419.0,
            sma50=405.0,
            sma200=380.0,
            rsi2=6.0,
            atr14=6.0,
            vix_close=17.0,
            vix3m_close=19.0,
            vts_ratio=0.89,
        )
        universe = {"SPY": _build_series(220, 500.0), "QQQ": qqq_series}
        engine = AegisPortfolioEngine(universe, start_date="2026-01-01")
        res = engine.compute_live_portfolio(max_fast_weight=0.55)

        self.assertEqual(len(res["tactical"]["open_trades"]), 1)
        ot = res["tactical"]["open_trades"][0]
        self.assertEqual(ot["engine_id"], "M1_PULLBACK")
        self.assertEqual(ot["symbol"], "QQQ")
        self.assertEqual(ot["days_held"], 0)
        self.assertGreater(len(res["tactical"]["signals_today"]), 0)
        self.assertIn("M1_PULLBACK", res["targets"]["QQQ"]["motor"])
        total_w = sum(v["weight"] for v in res["targets"].values())
        self.assertLessEqual(total_w, 1.0001)

    def test_multiday_open_trade_persists_until_exit_rule(self):
        qqq_series = _build_series(222, 420.0)
        # Entry 2 days ago (T-2): RSI(2)=5.0, Close=410 < SMA(5)=418
        qqq_series[-3] = create_mock_bar(
            date=qqq_series[-3].date,
            close=410.0,
            low=408.0,
            sma5=418.0,
            sma50=405.0,
            sma200=380.0,
            rsi2=5.0,
            atr14=5.0,
        )
        # Yesterday (T-1) and Today (T): RSI(2)=35 (no new entry signal!), Close=412 < SMA(5)=416 (still open!)
        for offset in (-2, -1):
            qqq_series[offset] = create_mock_bar(
                date=qqq_series[offset].date,
                close=412.0,
                low=410.0,
                sma5=416.0,
                sma50=405.0,
                sma200=380.0,
                rsi2=35.0,
                atr14=5.0,
            )

        universe = {"SPY": _build_series(222, 500.0), "QQQ": qqq_series}
        engine = AegisPortfolioEngine(universe, start_date="2026-01-01")
        res = engine.compute_live_portfolio(max_fast_weight=0.55)

        # Even though today has NO new entry signal, the position opened 2 days ago stays active!
        self.assertEqual(res["tactical"]["signals_today"], [])
        self.assertEqual(len(res["tactical"]["open_trades"]), 1)
        self.assertEqual(res["tactical"]["open_trades"][0]["days_held"], 2)
        self.assertIn("M1_PULLBACK", res["targets"]["QQQ"]["motor"])

        # Next day (T+1): Close=422 > SMA(5)=416 -> Target reached, position exits!
        next_day = (date.fromisoformat(qqq_series[-1].date) + timedelta(days=1)).isoformat()
        qqq_series.append(
            create_mock_bar(
                date=next_day,
                close=422.0,
                low=418.0,
                sma5=416.0,
                sma50=405.0,
                sma200=380.0,
                rsi2=68.0,
                atr14=5.0,
            )
        )
        spy_series = _build_series(223, 500.0)
        engine_after = AegisPortfolioEngine({"SPY": spy_series, "QQQ": qqq_series}, start_date="2026-01-01")
        res_after = engine_after.compute_live_portfolio(max_fast_weight=0.55)
        self.assertEqual(res_after["tactical"]["open_trades"], [])

    def test_disabled_motor_is_ignored(self):
        qqq_series = _build_series(220, 420.0)
        qqq_series[-1] = create_mock_bar(
            date=qqq_series[-1].date,
            close=410.0,
            low=409.0,
            sma5=418.0,
            sma50=405.0,
            sma200=380.0,
            rsi2=6.0,
            atr14=6.0,
        )
        universe = {"SPY": _build_series(220, 500.0), "QQQ": qqq_series}
        engine = AegisPortfolioEngine(universe, start_date="2026-01-01")
        res = engine.compute_live_portfolio(enabled_motors={"M1_PULLBACK": False})
        self.assertEqual(res["tactical"]["open_trades"], [])
        self.assertEqual(res["tactical"]["signals_today"], [])

    def test_m3_bear_short_preserved_without_core_overwrite(self):
        spy_series = _build_series(220, 400.0)
        # Bear market bounce exhaustion: Close (400) < SMA200 (450), RSI(2)=92 > 85, VIX=28 >= 22, up_streak=2
        spy_series[-1] = create_mock_bar(
            date=spy_series[-1].date,
            close=400.0,
            high=404.0,
            low=397.0,
            sma5=392.0,
            sma20=395.0,
            sma50=420.0,
            sma200=450.0,
            sma200_rising=False,
            rsi2=92.0,
            up_streak=2,
            atr14=8.0,
            vix_close=28.0,
            vix3m_close=26.0,
            vts_ratio=1.077,
        )
        engine = AegisPortfolioEngine({"SPY": spy_series}, start_date="2026-01-01")
        res = engine.compute_live_portfolio()
        self.assertEqual(res["targets"]["SPY"]["direction"], "SHORT")
        self.assertEqual(res["targets"]["SPY"]["motor"], "M3_BEAR_SHORT")


if __name__ == "__main__":
    unittest.main()
