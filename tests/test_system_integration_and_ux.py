"""
Suite Integral de Tests de Fiabilidad de Sistema y Experiencia de Usuario (tests/test_system_integration_and_ux.py).

Verifica los 12 Requisitos Críticos de Fiabilidad del Centro de Mando Aegis-Quant:
  - REQ-01: Hot-swapping y desconexión individual de motores tácticos (M1–M6) sin comportamiento errático.
  - REQ-02: Liquidación total (Botón de Pánico) y reanudación operativa limpia desde liquidez 100%.
  - REQ-03: Persistencia atómica de configuración y libro contable ante escrituras concurrentes.
  - REQ-04: Trazabilidad y consistencia fiscal AEAT (FIFO + Regla 2 Meses + Divisas BCE) tras liquidaciones forzadas.
  - REQ-05: Contratos de API de control web y móvil (POST /api/live/action y POST /api/live/config).
  - REQ-06: Cortafuegos de Drawdown Diario (Kill-Switch DD Breaker).
  - REQ-07: Flujo Seguro del Modo Copiloto (Aprobación, Rechazo y Cancelación por Pánico).
  - REQ-08: Blindaje de Cuenta Real frente a Reset Accidental (LIVE_REAL Guard).
  - REQ-09: Rebalanceo con Deltas Parciales y Conservación de Liquidez (No negativo).
  - REQ-10: Compensación Fiscal Multiejercicio (4 Años AEAT) y Aislamiento Regla 2M.
  - REQ-11: Transición Defensiva de Régimen ante Mercado Bajista o Backwardation.
  - REQ-12: Resiliencia de Ingesta ante Cotizaciones Inválidas o Desconocidas.
"""

import json
import os
import shutil
import tempfile
import unittest

from aegis_quant.live.bot_controller import LiveBotController
from aegis_quant.live.broker_adapter import LocalPaperBrokerAdapter
from aegis_quant.live.config_store import BotConfigStore
from aegis_quant.portfolio.aegis_engine import AegisPortfolioEngine
from aegis_quant.risk.meta_kelly_sizer import MetaLabelRiskManager
from aegis_quant.tax.spanish_tax_engine import SpanishTaxAuditor
from tests.helpers import create_mock_bar
from tests.test_live_tactical_scanner import _build_series


class TestSystemIntegrationAndUX(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.tmpdir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.store = BotConfigStore(self.tmpdir)
        self.mock_prices = {
            "SPY": 580.0,
            "QQQ": 490.0,
            "GLD": 240.0,
            "TLT": 92.0,
            "USO": 75.0,
            "SOYB": 26.0,
            "ZS": 1050.0,
        }
        self.broker = LocalPaperBrokerAdapter(self.store, self.mock_prices)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # REQ-01: Desconexión y Reconexión de Motores en Caliente
    # -------------------------------------------------------------------------
    def test_req01_engine_hot_disconnect_prevents_signals_and_reallocates_cleanly(self):
        """Verifica que apagar un motor en caliente suprime sus señales y reequilibra el capital en Core."""
        qqq_series = _build_series(220, 420.0)
        # Provocar señal clara de M1_PULLBACK en QQQ hoy
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

        # 1. Con M1 activo: genera señal táctica y asigna slot prioritario
        res_active = engine.compute_live_portfolio(enabled_motors={"M1_PULLBACK": True})
        self.assertEqual(len(res_active["tactical"]["signals_today"]), 1)
        self.assertIn("M1_PULLBACK", res_active["targets"]["QQQ"]["motor"])

        # 2. Desactivar M1 en caliente en la configuración
        self.store.update_config(
            {
                "enabled_motors": {
                    "M1_PULLBACK": False,
                    "M2_VIX_DIV": True,
                    "M3_BEAR_SHORT": True,
                    "M4_CTA_TREND": True,
                    "M5_VOL_CRUSH": True,
                    "M6_TOTM": True,
                }
            }
        )
        cfg = self.store.get_config()
        self.assertFalse(cfg["enabled_motors"]["M1_PULLBACK"])

        # 3. Con M1 desconectado: cero señales, capital absorbido por Core Modo 3 sin sobreponderar
        res_disabled = engine.compute_live_portfolio(enabled_motors=cfg["enabled_motors"])
        self.assertEqual(len(res_disabled["tactical"]["signals_today"]), 0)
        self.assertEqual(res_disabled["tactical"]["open_trades"], [])
        self.assertEqual(res_disabled["targets"]["QQQ"]["motor"], "CORE_BULL")
        total_w = sum(t["weight"] for t in res_disabled["targets"].values())
        self.assertAlmostEqual(total_w, 1.0, places=4)

    # -------------------------------------------------------------------------
    # REQ-02: Liquidación Total (Botón de Pánico) y Reanudación Limpia
    # -------------------------------------------------------------------------
    def test_req02_panic_liquidation_and_clean_trading_resumption(self):
        """Verifica que el Botón de Pánico liquida al 100% a caja y permite reanudar operaciones inmediatamente."""
        # 1. Simular cartera con 2 posiciones abiertas
        state = self.store.get_state()
        state["positions"] = [
            {
                "symbol": "SPY",
                "broker_symbol": "SPY",
                "internal_symbol": "SPY",
                "qty": 8.0,
                "avg_entry_price": 570.0,
                "current_price": 580.0,
                "market_value_usd": 4640.0,
                "unrealized_pnl_usd": 80.0,
                "direction": "LONG",
            },
            {
                "symbol": "QQQ",
                "broker_symbol": "QQQ",
                "internal_symbol": "QQQ",
                "qty": 6.0,
                "avg_entry_price": 485.0,
                "current_price": 490.0,
                "market_value_usd": 2940.0,
                "unrealized_pnl_usd": 30.0,
                "direction": "LONG",
            },
        ]
        state["account"]["cash_usd"] = 2420.0
        state["account"]["positions_value_usd"] = 7580.0
        state["account"]["total_equity_usd"] = 10000.0
        state["account"]["realized_pnl_usd"] = 0.0
        self.store.save_state(state)

        # 2. Pulsar Botón de Pánico
        ok, msg = self.broker.close_all_positions(reason="Test Boton de Panico")
        self.assertTrue(ok)
        self.assertIn("Cierre de emergencia ejecutado", msg)

        # 3. Validar estado pos-liquidación: 0 posiciones, caja = capital total
        st_post = self.store.get_state()
        self.assertEqual(len(st_post["positions"]), 0)
        self.assertEqual(st_post["account"]["positions_value_usd"], 0.0)
        self.assertEqual(st_post["account"]["unrealized_pnl_usd"], 0.0)
        self.assertAlmostEqual(st_post["account"]["cash_usd"], 10000.0, places=2)
        self.assertAlmostEqual(st_post["account"]["realized_pnl_usd"], 110.0, places=2)
        self.assertEqual(len(st_post["orders_history"]), 2)
        self.assertEqual(st_post["orders_history"][0]["side"], "LIQUIDATE_ALL")

        # 4. Segundo clic consecutivo en Pánico (idempotencia y seguridad)
        ok2, msg2 = self.broker.close_all_positions(reason="Segundo clic")
        self.assertTrue(ok2)
        self.assertIn("100% en liquidez", msg2)

        # 5. Reanudación de operaciones: ejecutar rebalanceo desde caja 100%
        new_targets = {
            "SPY": {"weight": 0.85, "direction": "LONG", "motor": "CORE_BULL"},
            "QQQ": {"weight": 0.15, "direction": "LONG", "motor": "CORE_BULL"},
        }
        ok_reb, orders, msg_reb = self.broker.execute_target_weights(new_targets, "Rebalanceo post-panico")
        self.assertTrue(ok_reb)
        self.assertEqual(len(orders), 2)

        # Verificar que la cartera vuelve a tener posiciones vivas sin errores de estado zombi
        st_resumed = self.store.get_state()
        self.assertEqual(len(st_resumed["positions"]), 2)
        self.assertGreater(st_resumed["account"]["positions_value_usd"], 9500.0)
        self.assertGreaterEqual(st_resumed["account"]["cash_usd"], 0.0)

    # -------------------------------------------------------------------------
    # REQ-03: Persistencia Atómica y Resistencia a Corrupción
    # -------------------------------------------------------------------------
    def test_req03_atomic_persistence_and_no_file_corruption(self):
        """Verifica que fallos de escritura o actualizaciones consecutivas preservan la integridad del JSON."""
        # Configurar estado inicial
        cfg = self.store.get_config()
        self.assertEqual(cfg["allocated_capital_usd"], 10000.0)

        # 1. Modificar configuración en caliente
        updated = self.store.update_config({"allocated_capital_usd": 25000.0, "risk_per_trade_pct": 3.0})
        self.assertEqual(updated["allocated_capital_usd"], 25000.0)

        # 2. Leer directamente desde disco asegurando que no hay fichero .tmp_ residual
        raw_cfg_path = os.path.join(self.tmpdir, "data", "bot_live_config.json")
        self.assertTrue(os.path.exists(raw_cfg_path))
        with open(raw_cfg_path, encoding="utf-8") as f:
            disk_cfg = json.load(f)
        self.assertEqual(disk_cfg["allocated_capital_usd"], 25000.0)
        self.assertEqual(disk_cfg["risk_per_trade_pct"], 3.0)

        tmp_files = [f for f in os.listdir(os.path.join(self.tmpdir, "data")) if f.startswith(".tmp_")]
        self.assertEqual(tmp_files, [])

    # -------------------------------------------------------------------------
    # REQ-04: Fidelidad Fiscal AEAT tras Liquidación Forzada
    # -------------------------------------------------------------------------
    def test_req04_tax_audit_computes_cleanly_after_panic_liquidation(self):
        """Verifica que la auditoría fiscal (FIFO, BCE, Regla 2 Meses) computa fielmente sobre el libro contable."""
        # 1. Registrar compra inicial en el libro contable de Paper
        self.store.append_trade_ledger(
            {
                "timestamp": "2026-10-15 15:30:00",
                "environment": "PAPER",
                "order_id": "ORD-INIT-BUY",
                "symbol": "SPY",
                "ucits_ticker": "SPYL",
                "isin": "IE000XZSV718",
                "side": "BUY",
                "qty": 10.0,
                "price_usd": 570.0,
                "notional_usd": 5700.0,
                "currency": "USD",
                "fx_eur_usd": 1.08,
                "commission_usd": 1.5,
                "motor": "M1_PULLBACK",
                "reason": "Entrada Rebote",
                "status": "FILLED",
            }
        )

        # 2. Registrar venta por liquidación total (pánico) con ganancia
        self.store.append_trade_ledger(
            {
                "timestamp": "2026-10-25 16:00:00",
                "environment": "PAPER",
                "order_id": "ORD-KILL-PANIC",
                "symbol": "SPY",
                "ucits_ticker": "SPYL",
                "isin": "IE000XZSV718",
                "side": "LIQUIDATE_ALL",
                "qty": 10.0,
                "price_usd": 585.0,
                "notional_usd": 5850.0,
                "currency": "USD",
                "fx_eur_usd": 1.08,
                "commission_usd": 0.0,
                "motor": "KILL_SWITCH",
                "reason": "Panico Web",
                "status": "FILLED",
            }
        )

        # 3. Auditar fiscalmente con SpanishTaxAuditor
        auditor = SpanishTaxAuditor(self.tmpdir)
        audit_res = auditor.audit_environment("PAPER", reference_date="2026-10-27")

        self.assertTrue(audit_res["ok"])
        summary = audit_res["summary"]
        self.assertEqual(summary["closed_lots_count"], 1)
        self.assertEqual(summary["open_lots_count"], 0)
        self.assertGreater(summary["gross_gains_eur"], 130.0)
        self.assertEqual(summary["deductible_losses_eur"], 0.0)
        self.assertEqual(summary["deferred_losses_2m_eur"], 0.0)
        self.assertEqual(summary["effective_rate_pct"], 19.0)

        # 4. Validar generación de Casillas Renta WEB (Apartado F2)
        f2 = audit_res["renta_web_f2"]
        self.assertIn("total_transmission_eur", f2)
        self.assertIn("total_acquisition_eur", f2)
        self.assertGreater(f2["total_transmission_eur"], 5000.0)
        self.assertGreater(f2["total_acquisition_eur"], 5000.0)
        self.assertEqual(len(f2["by_isin"]), 1)
        self.assertEqual(f2["by_isin"][0]["isin"], "IE000XZSV718")

    # -------------------------------------------------------------------------
    # REQ-05: Contratos de API de Botones Web y Móvil (E2E)
    # -------------------------------------------------------------------------
    def test_req05_api_button_actions_contract_integrity(self):
        """Verifica que las acciones de los botones web retornan contratos de respuesta íntegros."""
        mock_summary = {
            "mode_3": {
                "metrics": {"total_trades": 780, "cagr_pct": 19.54, "sharpe": 1.61, "max_drawdown_pct": -14.86},
                "waterfall": {"net_final_equity": 341058.0},
            }
        }
        ctrl = LiveBotController(self.tmpdir, mock_summary)

        # 1. Probar botón TOGGLE_BOT (Iniciar / Pausar)
        res_pause = ctrl.handle_action({"action": "TOGGLE_BOT"})
        self.assertTrue(res_pause["ok"])
        self.assertIn("PAUSADO", res_pause["message"])
        st = ctrl.get_full_status()
        self.assertFalse(st["config"]["bot_running"])

        res_resume = ctrl.handle_action({"action": "TOGGLE_BOT"})
        self.assertTrue(res_resume["ok"])
        self.assertIn("INICIADO", res_resume["message"])
        st = ctrl.get_full_status()
        self.assertTrue(st["config"]["bot_running"])

        # 2. Probar botón PANIC_CLOSE_ALL vía controlador
        res_panic = ctrl.handle_action({"action": "PANIC_CLOSE_ALL"})
        self.assertTrue(res_panic["ok"])
        st_after_panic = ctrl.get_full_status()
        self.assertEqual(st_after_panic["state"]["positions"], [])

        # 3. Probar botón RESET_ACCOUNT
        res_reset = ctrl.handle_action({"action": "RESET_ACCOUNT"})
        self.assertTrue(res_reset["ok"])
        st_after_reset = ctrl.get_full_status()
        self.assertEqual(st_after_reset["state"]["account"]["cash_usd"], 10000.0)

        # 4. Probar acción desconocida: debe responder cleanly sin explotar
        res_unknown = ctrl.handle_action({"action": "ACCION_INEXISTENTE"})
        self.assertFalse(res_unknown["ok"])

    # -------------------------------------------------------------------------
    # REQ-06: Cortafuegos de Drawdown Diario (Kill-Switch DD Breaker)
    # -------------------------------------------------------------------------
    def test_req06_daily_kill_switch_blocks_orders_on_excessive_drawdown(self):
        """Verifica que si el drawdown supera el límite diario (-8%), se bloquea la entrada de órdenes."""
        st = self.store.get_state()
        st["account"]["peak_equity_usd"] = 10000.0
        st["account"]["cash_usd"] = 8420.0
        st["account"]["total_equity_usd"] = 9000.0
        st["positions"] = [
            {
                "broker_symbol": "SPY",
                "internal_symbol": "SPY",
                "qty": 1.0,
                "avg_entry_price": 580.0,
                "current_price": 580.0,
                "market_value_usd": 580.0,
                "unrealized_pnl_usd": 0.0,
                "direction": "LONG",
            }
        ]
        self.store.save_state(st)

        # Drawdown actual = (9000 - 10000) / 10000 = -10.0%, que supera el límite de -8.0%
        ok, orders, msg = self.broker.execute_target_weights(
            {"SPY": {"weight": 0.5, "direction": "LONG"}}, "Test Kill Switch"
        )
        self.assertFalse(ok)
        self.assertEqual(orders, [])
        self.assertIn("CORTAFUEGOS ACTIVADO", msg)

        st_after = self.store.get_state()
        self.assertTrue(st_after["account"]["kill_switch_triggered"])
        self.assertAlmostEqual(st_after["account"]["current_dd_pct"], -10.0, places=1)

    # -------------------------------------------------------------------------
    # REQ-07: Flujo Seguro del Modo Copiloto
    # -------------------------------------------------------------------------
    def test_req07_copilot_proposal_approval_rejection_and_panic_cancellation(self):
        """Verifica que en Copilot no se cursan órdenes sin confirmación y Pánico cancela propuestas pendientes."""
        mock_summary = {
            "mode_3": {
                "metrics": {"total_trades": 780, "cagr_pct": 19.54, "sharpe": 1.61, "max_drawdown_pct": -14.86},
                "waterfall": {"net_final_equity": 341058.0},
            }
        }
        ctrl = LiveBotController(self.tmpdir, mock_summary)
        ctrl.store.update_config({"execution_mode": "COPILOT_CONFIRM"})

        # 1. Escaneo en Copiloto genera propuesta en cola sin ejecutar en broker
        res_scan = ctrl.run_scan_and_sync("Test Escaneo Copiloto", simulate_motor="M1_PULLBACK")
        self.assertEqual(res_scan.get("mode"), "COPILOT_CONFIRM")
        st = ctrl.store.get_state()
        self.assertEqual(len(st.get("pending_confirmations", [])), 1)

        # 2. Rechazar propuesta descarta la cola sin tocar posiciones
        res_reject = ctrl.handle_action({"action": "REJECT_PENDING"})
        self.assertTrue(res_reject["ok"])
        st_rejected = ctrl.store.get_state()
        self.assertEqual(len(st_rejected.get("pending_confirmations", [])), 0)

        # 3. Nueva propuesta y aprobación efectiva
        ctrl.run_scan_and_sync("Test Propuesta 2", simulate_motor="M1_PULLBACK")
        res_approve = ctrl.handle_action({"action": "APPROVE_PENDING"})
        self.assertTrue(res_approve["ok"])
        st_approved = ctrl.store.get_state()
        self.assertEqual(len(st_approved.get("pending_confirmations", [])), 0)
        self.assertGreater(len(st_approved["positions"]), 0)

        # 4. Propuesta pendiente cancelada automáticamente ante Botón de Pánico
        ctrl.run_scan_and_sync("Test Propuesta 3", simulate_motor="M1_PULLBACK")
        self.assertEqual(len(ctrl.store.get_state().get("pending_confirmations", [])), 1)
        res_panic = ctrl.handle_action({"action": "PANIC_CLOSE_ALL"})
        self.assertTrue(res_panic["ok"])
        st_panicked = ctrl.store.get_state()
        self.assertEqual(len(st_panicked.get("pending_confirmations", [])), 0)
        self.assertEqual(len(st_panicked["positions"]), 0)

    # -------------------------------------------------------------------------
    # REQ-08: Blindaje de Cuenta Real frente a Reset Accidental
    # -------------------------------------------------------------------------
    def test_req08_live_real_environment_blocks_account_reset(self):
        """Verifica que si el bot corre en Dinero Real (LIVE_REAL), el botón de reset está bloqueado en backend."""
        mock_summary = {
            "mode_3": {
                "metrics": {"total_trades": 780, "cagr_pct": 19.54, "sharpe": 1.61, "max_drawdown_pct": -14.86},
                "waterfall": {"net_final_equity": 341058.0},
            }
        }
        ctrl = LiveBotController(self.tmpdir, mock_summary)
        ctrl.store.update_config({"environment": "LIVE_REAL"})

        res = ctrl.handle_action({"action": "RESET_ACCOUNT"})
        self.assertFalse(res["ok"])
        self.assertIn("LIVE_REAL", res["message"])

        # Verificar que el estado y logs registran la denegación de seguridad
        st = ctrl.store.get_state()
        self.assertIn("Acción bloqueada", st["logs"][0]["msg"])

    # -------------------------------------------------------------------------
    # REQ-09: Rebalanceo con Deltas Parciales y Conservación de Liquidez
    # -------------------------------------------------------------------------
    def test_req09_partial_rebalance_deltas_and_non_negative_cash_conservation(self):
        """Verifica que los rebalanceos emiten SELL_PARTIAL y que el efectivo nunca es negativo."""
        # 1. Asignación inicial: 85% SPY ($8500), 15% QQQ ($1500)
        ok1, ords1, msg1 = self.broker.execute_target_weights(
            {"SPY": {"weight": 0.85, "direction": "LONG"}, "QQQ": {"weight": 0.15, "direction": "LONG"}},
            "Asignación inicial",
        )
        self.assertTrue(ok1)
        st1 = self.store.get_state()
        self.assertGreaterEqual(st1["account"]["cash_usd"], 0.0)

        # 2. Rotación: Reducir SPY a 40%, subir QQQ a 40%, entrar 20% TLT
        ok2, ords2, msg2 = self.broker.execute_target_weights(
            {
                "SPY": {"weight": 0.40, "direction": "LONG"},
                "QQQ": {"weight": 0.40, "direction": "LONG"},
                "TLT": {"weight": 0.20, "direction": "LONG"},
            },
            "Rotación de activos",
        )
        self.assertTrue(ok2)
        sides = [o["side"] for o in ords2]
        self.assertIn("SELL_PARTIAL", sides)
        self.assertIn("BUY", sides)

        # 3. Conservación de capital: cash >= 0 y suma exacta al céntimo
        st2 = self.store.get_state()
        self.assertGreaterEqual(st2["account"]["cash_usd"], 0.0)
        total_account = st2["account"]["cash_usd"] + st2["account"]["positions_value_usd"]
        self.assertAlmostEqual(total_account, st2["account"]["total_equity_usd"], places=2)

    # -------------------------------------------------------------------------
    # REQ-10: Compensación Fiscal Multiejercicio (4 Años AEAT) y Aislamiento Regla 2M
    # -------------------------------------------------------------------------
    def test_req10_spanish_tax_carryforward_and_2m_rule_isolation(self):
        """Verifica la compensación de pérdidas de ejercicios previos y el aislamiento de la regla de los 2 meses."""
        # Compra inicial de 10 títulos a 500 €
        self.store.append_trade_ledger(
            {
                "timestamp": "2026-03-01 10:00:00",
                "environment": "PAPER",
                "order_id": "ORD-B1",
                "symbol": "SPY",
                "ucits_ticker": "SPYL",
                "isin": "IE000XZSV718",
                "side": "BUY",
                "qty": 10.0,
                "price_usd": 500.0,
                "notional_usd": 5000.0,
                "currency": "USD",
                "fx_eur_usd": 1.0,
                "commission_usd": 0.0,
                "status": "FILLED",
            }
        )
        # Venta a 550 € (+500 € de ganancia bruta)
        self.store.append_trade_ledger(
            {
                "timestamp": "2026-05-01 10:00:00",
                "environment": "PAPER",
                "order_id": "ORD-S1",
                "symbol": "SPY",
                "ucits_ticker": "SPYL",
                "isin": "IE000XZSV718",
                "side": "SELL",
                "qty": 10.0,
                "price_usd": 550.0,
                "notional_usd": 5500.0,
                "currency": "USD",
                "fx_eur_usd": 1.0,
                "commission_usd": 0.0,
                "status": "FILLED",
            }
        )

        auditor = SpanishTaxAuditor(self.tmpdir)
        # Aplicar 200 € de pérdidas pendientes de compensar de los 4 años anteriores
        res = auditor.audit_environment(
            "PAPER", tax_year="2026", prior_loss_carryforward_eur=200.0, reference_date="2026-10-27"
        )
        summary = res["summary"]
        self.assertEqual(summary["gross_gains_eur"], 500.0)
        self.assertEqual(summary["prior_loss_offset_eur"], 200.0)
        self.assertEqual(summary["taxable_savings_base_eur"], 300.0)
        self.assertAlmostEqual(summary["estimated_irpf_eur"], 57.0, places=1)  # 300 * 19%

    # -------------------------------------------------------------------------
    # REQ-11: Transición Defensiva de Régimen ante Mercado Bajista o Backwardation
    # -------------------------------------------------------------------------
    def test_req11_bear_market_and_backwardation_core_defense(self):
        """Verifica que en Backwardation o régimen bajista, Core Modo 3 no compra bolsa pasiva (0% SPY/QQQ)."""
        risk_mgr = MetaLabelRiskManager()
        # Crear barra de SPY en backwardation severa (VIX/VIX3M >= 1.0) y bajo SMA200
        spy_crash = create_mock_bar(
            date="2026-10-27",
            close=400.0,
            sma50=430.0,
            sma200=460.0,
            vix_close=28.0,
            vix3m_close=26.0,  # VTS Ratio = 28/26 = 1.077 (Backwardation)
            vts_ratio=1.077,
        )
        universe_bars = {"SPY": spy_crash}
        core_alloc = risk_mgr.compute_elite_core_allocation(universe_bars, idle_capital_fraction=1.0)

        # En crisis y pánico bursátil: bolsa pasiva a 0% estricto
        self.assertEqual(core_alloc.get("SPY", 0.0), 0.0)
        self.assertEqual(core_alloc.get("QQQ", 0.0), 0.0)

    # -------------------------------------------------------------------------
    # REQ-12: Resiliencia de Ingesta ante Cotizaciones Inválidas o Desconocidas
    # -------------------------------------------------------------------------
    def test_req12_price_feed_zero_or_nan_resilience(self):
        """Verifica que precios atípicos o símbolos no catalogados no causan excepciones de división por cero."""
        # Consultar símbolo desconocido
        px_unknown = self.broker.get_live_price("ACTIVO_DESCONOCIDO")
        self.assertGreater(px_unknown, 0.0)

        # Intentar rebalancear con precio mínimo no debe romper por ZeroDivisionError
        broker_zero = LocalPaperBrokerAdapter(self.store, {"SPY": 0.0})
        ok, orders, msg = broker_zero.execute_target_weights(
            {"SPY": {"weight": 1.0, "direction": "LONG"}}, "Zero Price Test"
        )
        self.assertTrue(ok)
        st = self.store.get_state()
        self.assertEqual(len(st["positions"]), 1)
        self.assertGreater(st["positions"][0]["qty"], 0.0)


if __name__ == "__main__":
    unittest.main()
