"""Tests unitarios para StateReconciliationService e IdempotentOrderManager."""

import unittest

from aegis_quant.live.order_manager import IdempotentOrderManager
from aegis_quant.live.reconciliation_service import StateReconciliationService


class TestReconciliationAndOrderManager(unittest.TestCase):
    def test_reconciliation_perfect_sync(self):
        local_state = {
            "positions": [{"broker_symbol": "SPY", "shares": 10.0, "weight_pct": 50.0}],
            "account": {"cash_usd": 5000.0, "total_equity_usd": 10000.0},
        }
        broker_snapshot = {
            "positions": [{"broker_symbol": "SPY", "shares": 10.0, "weight_pct": 50.0}],
            "account": {"cash_usd": 5000.0, "total_equity_usd": 10000.0},
        }
        res = StateReconciliationService.reconcile(local_state, broker_snapshot)
        self.assertTrue(res.in_sync)
        self.assertEqual(len(res.discrepancies), 0)
        self.assertEqual(res.action_taken, "NONE")

    def test_reconciliation_missing_in_broker(self):
        # Local cree tener QQQ pero en bróker no está
        local_state = {
            "positions": [
                {"broker_symbol": "SPY", "shares": 10.0},
                {"broker_symbol": "QQQ", "shares": 5.0},
            ],
            "account": {"cash_usd": 5000.0, "total_equity_usd": 10000.0},
        }
        broker_snapshot = {
            "positions": [{"broker_symbol": "SPY", "shares": 10.0}],
            "account": {"cash_usd": 7500.0, "total_equity_usd": 10000.0},
        }
        res = StateReconciliationService.reconcile(local_state, broker_snapshot)
        self.assertFalse(res.in_sync)
        self.assertEqual(res.action_taken, "AUTO_ALIGNED")
        self.assertEqual(len(res.reconciled_state["positions"]), 1)
        self.assertEqual(res.reconciled_state["positions"][0]["broker_symbol"], "SPY")

    def test_reconciliation_ghost_in_broker(self):
        # Bróker tiene GLD que local no tenía registrado
        local_state = {
            "positions": [{"broker_symbol": "SPY", "shares": 10.0}],
            "account": {"cash_usd": 5000.0, "total_equity_usd": 10000.0},
        }
        broker_snapshot = {
            "positions": [
                {"broker_symbol": "SPY", "shares": 10.0},
                {"broker_symbol": "GLD", "shares": 15.0},
            ],
            "account": {"cash_usd": 2000.0, "total_equity_usd": 10000.0},
        }
        res = StateReconciliationService.reconcile(local_state, broker_snapshot)
        self.assertFalse(res.in_sync)
        self.assertEqual(len(res.reconciled_state["positions"]), 2)
        syms = [p["broker_symbol"] for p in res.reconciled_state["positions"]]
        self.assertIn("GLD", syms)

    def test_idempotent_order_generation(self):
        order_id = IdempotentOrderManager.generate_client_order_id("2026-10-30", "M1_PULLBACK", "SPYL", "BUY")
        self.assertEqual(order_id, "AEGIS-20261030-M1PULLBA-SPYL-BUY")

    def test_idempotent_deduplication(self):
        mgr = IdempotentOrderManager()
        oid = "AEGIS-20261030-M1-SPY-BUY"
        self.assertFalse(mgr.is_already_executed(oid))
        mgr.register_execution(oid)
        self.assertTrue(mgr.is_already_executed(oid))

    def test_discrete_shares_and_safety_caps(self):
        # Caps
        self.assertEqual(IdempotentOrderManager.apply_safety_caps("SPY", 0.60), 0.40)
        self.assertEqual(IdempotentOrderManager.apply_safety_caps("BTC", 0.30), 0.15)
        self.assertEqual(IdempotentOrderManager.apply_safety_caps("GLD", 0.25), 0.25)

        # Discrete shares (floor)
        # 100 € budget, 18 € per share -> 5 shares (90 €), not 5.55
        shares = IdempotentOrderManager.calculate_discrete_shares(100.0, 18.0)
        self.assertEqual(shares, 5)

        # Budget less than single share -> 0 shares
        shares_zero = IdempotentOrderManager.calculate_discrete_shares(15.0, 18.0)
        self.assertEqual(shares_zero, 0)

    def test_prepare_orders_workflow(self):
        mgr = IdempotentOrderManager()
        targets = {
            "SPY": {"weight": 0.50, "motor": "CORE", "reason": "Alloc"},  # capped to 0.40
            "BTC": {"weight": 0.20, "motor": "M4", "reason": "CTA"},  # capped to 0.15
        }
        current_pos = {"SPY": 0.0, "BTC": 0.0}
        prices = {"SPY": 500.0, "BTC": 40.0}
        total_equity = 10000.0

        orders = mgr.prepare_orders(targets, current_pos, total_equity, prices, date_str="20261030")
        self.assertEqual(len(orders), 2)
        # SPY: 0.40 * 10000 = 4000 / 500 = 8 shares
        spy_ord = next(o for o in orders if o.symbol == "SPY")
        self.assertEqual(spy_ord.shares, 8)
        self.assertEqual(spy_ord.side, "BUY")

        # Re-evaluating after registering execution prevents duplicate
        mgr.register_execution(spy_ord.order_id)
        orders_second_pass = mgr.prepare_orders(targets, current_pos, total_equity, prices, date_str="20261030")
        self.assertEqual(len(orders_second_pass), 1)
        self.assertEqual(orders_second_pass[0].symbol, "BTC")


if __name__ == "__main__":
    unittest.main()
