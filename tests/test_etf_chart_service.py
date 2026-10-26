import os
import unittest

from aegis_quant.data.etf_chart_service import EtfChartService, ORDERED_ETF_SYMBOLS


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestEtfChartService(unittest.TestCase):
    def setUp(self) -> None:
        self.service = EtfChartService(base_dir=BASE_DIR)

    def test_all_six_managed_etfs_load_cleanly(self) -> None:
        self.assertEqual(ORDERED_ETF_SYMBOLS, ["SPY", "QQQ", "GLD", "TLT", "USO", "ZS"])
        for sym in ORDERED_ETF_SYMBOLS:
            res = self.service.get_etf_payload(sym)
            self.assertTrue(res["ok"])
            self.assertEqual(res["selected_symbol"], sym)
            self.assertEqual(len(res["catalog"]), 6)

            etf = res["etf"]
            self.assertEqual(etf["meta"]["symbol"], sym)
            self.assertTrue(etf["meta"]["ucits_ticker"])

            s = etf["series"]
            n = len(s["dates"])
            self.assertGreater(n, 4000)
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


if __name__ == "__main__":
    unittest.main()
