import os
import unittest

from aegis_quant.data.etf_chart_service import ORDERED_ETF_SYMBOLS, EtfChartService

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestEtfChartService(unittest.TestCase):
    def setUp(self) -> None:
        self.service = EtfChartService(base_dir=BASE_DIR)

    def test_all_six_managed_etfs_load_cleanly(self) -> None:
        self.assertEqual(ORDERED_ETF_SYMBOLS, ["SPY", "QQQ", "GLD", "TLT", "USO", "ZS", "BTC"])
        for sym in ORDERED_ETF_SYMBOLS:
            res = self.service.get_etf_payload(sym)
            self.assertTrue(res["ok"])
            self.assertEqual(res["selected_symbol"], sym)
            self.assertEqual(len(res["catalog"]), 7)

            etf = res["etf"]
            self.assertEqual(etf["meta"]["symbol"], sym)
            self.assertTrue(etf["meta"]["ucits_ticker"])

            s = etf["series"]
            n = len(s["dates"])
            self.assertGreater(n, 3000)
            self.assertEqual(len(s["opens"]), n)
            self.assertEqual(len(s["highs"]), n)
            self.assertEqual(len(s["lows"]), n)
            self.assertEqual(len(s["closes"]), n)
            self.assertEqual(len(s["volumes"]), n)
            self.assertEqual(len(s["sma50"]), n)
            self.assertEqual(len(s["sma200"]), n)

            m = etf["metrics"]
            self.assertGreater(m["last_close"], 0.0)
            self.assertGreaterEqual(m["rsi2"], 0.0)
            self.assertLessEqual(m["rsi2"], 100.0)
            self.assertIn(m["trend"], ("ALCISTA", "BAJISTA"))
            self.assertGreaterEqual(m["high_52w"], m["low_52w"])

    def test_symbol_normalization_and_soyb_alias(self) -> None:
        self.assertEqual(self.service.normalize_symbol("soyb"), "ZS")
        self.assertEqual(self.service.normalize_symbol(" glD "), "GLD")
        self.assertEqual(self.service.normalize_symbol("INVALID_TICKER"), "SPY")
        self.assertEqual(self.service.normalize_symbol(None), "SPY")

    def test_live_price_override_updates_selected_and_catalog(self) -> None:
        res = self.service.get_etf_payload("SPY", live_prices={"SPY": 999.50})
        self.assertEqual(res["etf"]["metrics"]["last_close"], 999.50)
        self.assertEqual(res["etf"]["metrics"]["trend"], "ALCISTA")
        spy_cat = [c for c in res["catalog"] if c["symbol"] == "SPY"][0]
        self.assertEqual(spy_cat["last_close"], 999.50)

    def test_hourly_timeframe_and_meta_generation(self) -> None:
        res = self.service.get_etf_payload("SPY", timeframe="1h")
        self.assertTrue(res["ok"])
        self.assertEqual(res["timeframe"], "1h")
        self.assertIn("hourly_meta", res)
        meta = res["hourly_meta"]
        self.assertTrue(meta["is_hourly_updated"])
        self.assertIn("last_refresh_human", meta)
        self.assertIn("next_refresh_in_seconds", meta)

        series = res["etf"]["series"]
        self.assertGreater(len(series["dates"]), 10)
        self.assertIn(":", series["dates"][-1])  # Has HH:MM
        self.assertEqual(len(series["closes"]), len(series["dates"]))
        self.assertEqual(len(series["sma50"]), len(series["dates"]))

    def test_default_payload_includes_both_daily_and_hourly_series(self) -> None:
        res = self.service.get_etf_payload("SPY", timeframe="1d")
        self.assertTrue(res["ok"])
        self.assertIn("series", res["etf"])
        self.assertIn("hourly_series", res["etf"])
        self.assertGreater(len(res["etf"]["series"]["dates"]), 4000)
        self.assertGreater(len(res["etf"]["hourly_series"]["dates"]), 10)

    def test_isolation_daily_files_are_never_modified_by_chart_service(self) -> None:
        spy_daily_path = os.path.join(BASE_DIR, "data", "SPY_daily.json")
        mtime_before = os.path.getmtime(spy_daily_path)

        # Ejecutar refresco forzado y peticiones en 1D y 1H
        self.service.get_etf_payload("SPY", timeframe="1d", force_refresh=True)
        self.service.get_etf_payload("SPY", timeframe="1h", force_refresh=False)
        self.service.get_etf_payload("QQQ", timeframe="1d", force_refresh=False)

        mtime_after = os.path.getmtime(spy_daily_path)
        self.assertEqual(
            mtime_before,
            mtime_after,
            "CRITICAL: data/SPY_daily.json was modified by EtfChartService! It must remain read-only.",
        )


if __name__ == "__main__":
    unittest.main()
