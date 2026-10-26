"""
Unit Tests for Spanish Automated Tax Engine (AEAT FIFO, 2-Month Wash-Sale Rule, ECB FX & Modelo 720)
(tests/test_spanish_tax_engine.py).
"""

import tempfile
import unittest

from aegis_quant.tax.spanish_tax_engine import (
    SpanishTaxAuditor,
    calculate_spanish_savings_irpf,
)


class TestSpanishTaxEngine(unittest.TestCase):
    def test_progressive_spanish_savings_brackets(self):
        self.assertEqual(calculate_spanish_savings_irpf(0.0), 0.0)
        self.assertEqual(calculate_spanish_savings_irpf(-1500.0), 0.0)
        # Primeros 6.000 € al 19% = 1.140 €
        self.assertEqual(calculate_spanish_savings_irpf(6000.0), 1140.0)
        # 10.000 € -> 6.000 * 19% (1.140) + 4.000 * 21% (840) = 1.980 €
        self.assertEqual(calculate_spanish_savings_irpf(10000.0), 1980.0)
        # 60.000 € -> 1.140 + 44.000 * 21% (9.240) + 10.000 * 23% (2.300) = 12.680 €
        self.assertEqual(calculate_spanish_savings_irpf(60000.0), 12680.0)

    def test_fifo_matching_and_daily_ecb_fx_conversion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            auditor = SpanishTaxAuditor(tmpdir, allow_network_fx=False)
            entries = [
                # Lote 1: Compra 10 SPY a $500 con EUR/USD = 1.0000 -> Coste = 5.000 €
                {
                    "timestamp": "2026-01-10 21:55:00",
                    "symbol": "SPY",
                    "side": "BUY",
                    "qty": 10.0,
                    "price_usd": 500.0,
                    "fx_eur_usd": 1.0000,
                    "commission_usd": 5.0,
                    "status": "FILLED",
                },
                # Lote 2: Compra 10 SPY a $550 con EUR/USD = 1.1000 -> Coste = 5.000 €
                {
                    "timestamp": "2026-02-15 21:55:00",
                    "symbol": "SPY",
                    "side": "BUY",
                    "qty": 10.0,
                    "price_usd": 550.0,
                    "fx_eur_usd": 1.1000,
                    "commission_usd": 0.0,
                    "status": "FILLED",
                },
                # Venta parcial de 10 SPY a $605 con EUR/USD = 1.1000 -> Transmisión = 5.500 €
                # Por FIFO debe cerrar el Lote 1 (2026-01-10, coste 5.005 € incl. comisión) -> +495 €
                {
                    "timestamp": "2026-04-20 21:55:00",
                    "symbol": "SPY",
                    "side": "SELL_PARTIAL",
                    "qty": 10.0,
                    "price_usd": 605.0,
                    "fx_eur_usd": 1.1000,
                    "commission_usd": 5.5,
                    "status": "FILLED",
                },
            ]

            res = auditor.audit_entries(entries, env="PAPER", tax_year="2026", current_equity_usd=12000.0)
            self.assertEqual(res["summary"]["closed_lots_count"], 1)
            self.assertEqual(res["summary"]["open_lots_count"], 1)
            tx = res["transmissions"][0]
            self.assertEqual(tx["acquisition_date"], "2026-01-10")
            self.assertEqual(tx["isin"], "IE00B5BMR087")
            # Adquisición: 5000 + 5 = 5005 €; Transmisión: 5500 - 5 = 5495 € -> Plusvalía = +490 €
            self.assertAlmostEqual(tx["acquisition_value_eur"], 5005.0, places=2)
            self.assertAlmostEqual(tx["transmission_value_eur"], 5495.0, places=2)
            self.assertAlmostEqual(tx["gross_gain_eur"], 490.0, places=2)
            self.assertFalse(tx["blocked_2m"])
            self.assertAlmostEqual(res["summary"]["estimated_irpf_eur"], round(490.0 * 0.19, 2), places=2)
            self.assertFalse(res["modelo_720"]["required"])

    def test_two_month_anti_application_rule_blocks_and_unblocks_losses(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            auditor = SpanishTaxAuditor(tmpdir, allow_network_fx=False)
            # Caso A: Venta con pérdida seguida de recompra a los 15 días (mantenida en cartera) -> BLOQUEADA
            entries_blocked = [
                {
                    "timestamp": "2026-03-01 21:55:00",
                    "symbol": "QQQ",
                    "side": "BUY",
                    "qty": 10.0,
                    "price_usd": 400.0,
                    "currency": "EUR",
                    "status": "FILLED",
                },
                {
                    "timestamp": "2026-03-10 21:55:00",
                    "symbol": "QQQ",
                    "side": "SELL",
                    "qty": 10.0,
                    "price_usd": 370.0,
                    "currency": "EUR",
                    "status": "FILLED",
                },
                # Recompra dentro de los 60 días (2026-03-25) del mismo ISIN homogéneo (EQQQ)
                {
                    "timestamp": "2026-03-25 21:55:00",
                    "symbol": "EQQQ",
                    "side": "BUY",
                    "qty": 10.0,
                    "price_usd": 375.0,
                    "currency": "EUR",
                    "status": "FILLED",
                },
            ]
            rep_blocked = auditor.audit_entries(
                entries_blocked,
                env="LIVE_REAL",
                tax_year="2026",
                current_equity_usd=65000.0,
                reference_date="2026-04-05",
            )
            self.assertEqual(rep_blocked["summary"]["deferred_losses_2m_eur"], 300.0)
            self.assertEqual(rep_blocked["summary"]["deductible_losses_eur"], 0.0)
            self.assertTrue(rep_blocked["transmissions"][0]["blocked_2m"])
            self.assertEqual(len(rep_blocked["active_60d_lockouts"]), 1)
            # 65.000 USD / 1.0860 = ~59.852 EUR > 50.000 EUR -> Modelo 720 Obligatorio
            self.assertTrue(rep_blocked["modelo_720"]["required"])

            # Caso B: Si vende toda la posición recomprada y pasan >60 días sin recomprar -> LIBERADA
            entries_unblocked = entries_blocked + [
                {
                    "timestamp": "2026-04-15 21:55:00",
                    "symbol": "EQQQ",
                    "side": "SELL",
                    "qty": 10.0,
                    "price_usd": 395.0,
                    "currency": "EUR",
                    "status": "FILLED",
                }
            ]
            rep_unblocked = auditor.audit_entries(
                entries_unblocked,
                env="LIVE_REAL",
                tax_year="2026",
                current_equity_usd=40000.0,
                reference_date="2026-08-01",
            )
            self.assertEqual(rep_unblocked["summary"]["deferred_losses_2m_eur"], 0.0)
            self.assertEqual(rep_unblocked["summary"]["deductible_losses_eur"], -300.0)
            self.assertEqual(rep_unblocked["summary"]["gross_gains_eur"], 200.0)
            # Neto = +200 - 300 = -100 € -> Base imponible 0 €, arrastre pérdida 4 años = 100 €
            self.assertEqual(rep_unblocked["summary"]["taxable_savings_base_eur"], 0.0)
            self.assertEqual(rep_unblocked["summary"]["loss_carryforward_4y_eur"], 100.0)

    def test_csv_export_contains_aeat_headers_and_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            auditor = SpanishTaxAuditor(tmpdir, allow_network_fx=False)
            csv_content = auditor.export_audit_csv(env="PAPER", tax_year="ALL")
            self.assertIn("ISIN_Homogeneo", csv_content)
            self.assertIn("RESUMEN ANUAL RENTA WEB", csv_content)


if __name__ == "__main__":
    unittest.main()
