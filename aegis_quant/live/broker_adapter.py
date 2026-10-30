"""
Adaptadores Orientados a Objetos de Brókers para Paper Trading (aegis_quant/live/broker_adapter.py).
Implementa el Patrón Strategy/Adapter:
  1. LocalPaperBrokerAdapter : Simulador Paper Trading instantáneo con precios reales y persistencia local.
  2. AlpacaPaperBrokerAdapter: Conector REST nativo para Alpaca Markets Paper Trading (acciones fraccionadas, $0 comisión, mapeo ZS -> SOYB).
  3. IBKRPaperBrokerAdapter  : Adaptador preparado para Interactive Brokers (IB Gateway) para futuro paso a real en Europa.
"""

import json
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from aegis_quant.live.config_store import BotConfigStore
from aegis_quant.live.order_manager import IdempotentOrderManager
from aegis_quant.tax.spanish_tax_engine import ECBExchangeRateProvider, map_to_ucits_metadata


class BaseBrokerAdapter(ABC):
    """Interfaz común para cualquier bróker de ejecución (Paper o Real)."""

    def __init__(self, store: BotConfigStore, latest_prices: dict[str, float]):
        self.store = store
        self.latest_prices = latest_prices

    def map_symbol(self, internal_symbol: str, config: dict[str, Any]) -> str:
        """Convierte 'ZS' (Futuro Soja) en 'SOYB' (ETF Teucrium Soybean en Alpaca) si está activo."""
        if internal_symbol == "ZS" and config.get("use_soyb_etf_for_zs", True):
            return "SOYB"
        return internal_symbol

    def get_live_price(self, symbol: str) -> float:
        """Devuelve el precio de mercado actual para el símbolo o su equivalente ETF."""
        if symbol == "SOYB":
            # El ETF SOYB cotiza aprox a 1/45 del contrato de futuros ZS en centavos ($28.00 vs 1260.0)
            zs_px = self.latest_prices.get("ZS", 1260.0)
            return round(zs_px / 45.0, 2)
        return round(float(self.latest_prices.get(symbol, 100.0)), 2)

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        pass

    @abstractmethod
    def get_portfolio_snapshot(self) -> dict[str, Any]:
        pass

    @abstractmethod
    def execute_target_weights(
        self, target_weights: dict[str, dict[str, Any]], reason_summary: str
    ) -> tuple[bool, list[dict[str, Any]], str]:
        """
        Ajusta la cartera hacia los pesos objetivo:
        target_weights = {
            "SPY": {"weight": 0.85, "direction": "LONG", "motor": "CORE_BULL", "reason": "Tendencia Alcista Contango"},
            ...
        }
        """
        pass

    @abstractmethod
    def close_all_positions(self, reason: str = "Botón de Pánico / Cierre Total desde Web") -> tuple[bool, str]:
        pass


class LocalPaperBrokerAdapter(BaseBrokerAdapter):
    """
    Motor de Paper Trading Local en Vivo:
    Ejecuta órdenes instantáneamente con precios reales de mercado, soporta acciones fraccionadas
    al céntimo, persiste posiciones y órdenes en disco, y permite probar toda la operativa sin esperar
    a crear claves externas.
    """

    def test_connection(self) -> tuple[bool, str]:
        return True, "Conectado al Motor Paper Trading Local en Vivo (Persistencia SQLite/JSON activa)."

    def get_portfolio_snapshot(self) -> dict[str, Any]:
        cfg = self.store.get_config()
        state = self.store.get_state()
        acct = state.get("account", {})
        positions = state.get("positions", [])

        # Si el usuario cambió el capital asignado y no hay posiciones abiertas, sincronizar base
        alloc_cap = float(cfg.get("allocated_capital_usd", 10000.0))
        if not positions and abs(acct.get("initial_capital", 10000.0) - alloc_cap) > 1.0:
            acct["initial_capital"] = alloc_cap
            acct["cash_usd"] = alloc_cap
            acct["total_equity_usd"] = alloc_cap
            acct["peak_equity_usd"] = alloc_cap

        pos_val = 0.0
        unrealized = 0.0
        for p in positions:
            sym = p["broker_symbol"]
            curr_px = self.get_live_price(sym)
            p["current_price"] = curr_px
            qty = float(p["qty"])
            entry_px = float(p["avg_entry_price"])
            if p.get("direction", "LONG") == "LONG":
                pnl = (curr_px - entry_px) * qty
                mkt_val = curr_px * qty
            else:
                pnl = (entry_px - curr_px) * qty
                mkt_val = (entry_px * qty) + pnl
            p["market_value_usd"] = round(mkt_val, 2)
            p["unrealized_pnl_usd"] = round(pnl, 2)
            p["unrealized_pnl_pct"] = round((pnl / max(1.0, entry_px * qty)) * 100.0, 2)
            pos_val += mkt_val
            unrealized += pnl

        total_eq = round(float(acct.get("cash_usd", alloc_cap)) + pos_val, 2)
        peak_eq = max(float(acct.get("peak_equity_usd", alloc_cap)), total_eq)
        curr_dd = round(((total_eq - peak_eq) / max(1.0, peak_eq)) * 100.0, 2)
        init_cap = float(acct.get("initial_capital", alloc_cap))
        tot_ret = round(((total_eq - init_cap) / max(1.0, init_cap)) * 100.0, 2)

        acct.update(
            {
                "positions_value_usd": round(pos_val, 2),
                "total_equity_usd": total_eq,
                "peak_equity_usd": round(peak_eq, 2),
                "current_dd_pct": curr_dd,
                "unrealized_pnl_usd": round(unrealized, 2),
                "total_return_pct": tot_ret,
            }
        )
        state["account"] = acct
        state["positions"] = positions
        self.store.save_state(state)
        return state

    def _close_exited_positions(
        self,
        old_positions: dict[str, dict[str, Any]],
        target_weights: dict[str, dict[str, Any]],
        now_str: str,
        reason_summary: str,
        acct: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Cierra posiciones existentes que ya no forman parte del objetivo."""
        orders = []
        for int_sym, old_p in old_positions.items():
            if int_sym not in target_weights or target_weights[int_sym]["weight"] <= 0.001:
                side = "SELL" if old_p["direction"] == "LONG" else "BUY_TO_COVER"
                motor = old_p.get("motor", "REBALANCE")
                client_oid = IdempotentOrderManager.generate_client_order_id(
                    now_str[:10], motor, old_p["broker_symbol"], side
                )
                orders.append(
                    {
                        "time": now_str,
                        "broker": "LOCAL_PAPER",
                        "client_order_id": client_oid,
                        "symbol": old_p["broker_symbol"],
                        "side": side,
                        "qty": old_p["qty"],
                        "price": old_p["current_price"],
                        "notional_usd": old_p["market_value_usd"],
                        "motor": motor,
                        "reason": f"Cierre / Salida de posición ({reason_summary})",
                        "status": "FILLED",
                    }
                )
                acct["realized_pnl_usd"] = round(
                    float(acct.get("realized_pnl_usd", 0.0)) + float(old_p.get("unrealized_pnl_usd", 0.0)),
                    2,
                )
        return orders

    def _sync_single_target(
        self,
        int_sym: str,
        info: dict[str, Any],
        target_usd: float,
        old_p: dict[str, Any] | None,
        now_str: str,
        reason_summary: str,
        cfg: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Calcula el estado y la orden para un activo objetivo individual."""
        b_sym = self.map_symbol(int_sym, cfg)
        px = self.get_live_price(b_sym)
        qty = round(target_usd / max(0.01, px), 4)
        w = float(info.get("weight", 0.0))
        old_w = float(old_p["weight_pct"]) / 100.0 if old_p else 0.0

        order = None
        if abs(w - old_w) >= 0.01 or not old_p:
            diff_usd = round(target_usd - (old_p["market_value_usd"] if old_p else 0.0), 2)
            side = "BUY" if diff_usd >= 0 else "SELL_PARTIAL"
            if info.get("direction", "LONG") == "SHORT":
                side = "SELL_SHORT"
            motor = info.get("motor", "CORE_BULL")
            client_oid = IdempotentOrderManager.generate_client_order_id(now_str[:10], motor, b_sym, side)
            order = {
                "time": now_str,
                "broker": "LOCAL_PAPER",
                "client_order_id": client_oid,
                "symbol": b_sym,
                "side": side,
                "qty": round(abs(diff_usd) / max(0.01, px), 4),
                "price": px,
                "notional_usd": round(abs(diff_usd), 2),
                "motor": motor,
                "reason": info.get("reason", reason_summary),
                "status": "FILLED",
            }

        position = {
            "internal_symbol": int_sym,
            "broker_symbol": b_sym,
            "direction": info.get("direction", "LONG"),
            "motor": info.get("motor", "CORE_BULL"),
            "reason": info.get("reason", reason_summary),
            "qty": qty,
            "avg_entry_price": old_p["avg_entry_price"] if old_p else px,
            "current_price": px,
            "market_value_usd": target_usd,
            "weight_pct": round(w * 100.0, 1),
            "unrealized_pnl_usd": old_p["unrealized_pnl_usd"] if old_p else 0.0,
            "unrealized_pnl_pct": old_p["unrealized_pnl_pct"] if old_p else 0.0,
            "opened_at": old_p["opened_at"] if old_p else now_str,
        }
        return position, order

    def _record_ledger_trades(self, executed_orders: list[dict[str, Any]], now_str: str) -> None:
        """Registra transacciones en el libro mayor inmutable para fiscalidad."""
        if not executed_orders:
            return
        fx_rate = ECBExchangeRateProvider(self.store.data_dir, allow_network=False).get_eur_usd_rate(now_str[:10])
        env = self.store.get_config().get("environment", "PAPER")
        for o in executed_orders:
            ucits_meta = map_to_ucits_metadata(o.get("symbol", "SPY"))
            self.store.append_trade_ledger(
                {
                    "timestamp": now_str,
                    "environment": env,
                    "order_id": f"ORD-{int(time.time() * 1000)}",
                    "symbol": o.get("symbol"),
                    "ucits_ticker": ucits_meta["primary_ucits"],
                    "isin": ucits_meta["isin"],
                    "side": o.get("side"),
                    "qty": o.get("qty"),
                    "price_usd": o.get("price"),
                    "notional_usd": o.get("notional_usd"),
                    "currency": "USD",
                    "fx_eur_usd": fx_rate,
                    "commission_usd": 0.0,
                    "motor": o.get("motor"),
                    "reason": o.get("reason"),
                    "status": "FILLED",
                }
            )

    def execute_target_weights(
        self, target_weights: dict[str, dict[str, Any]], reason_summary: str
    ) -> tuple[bool, list[dict[str, Any]], str]:
        cfg = self.store.get_config()
        state = self.get_portfolio_snapshot()
        acct = state["account"]
        total_eq = float(acct["total_equity_usd"])

        # Verificar Kill-Switch diario
        max_dd_limit = float(cfg.get("daily_kill_switch_dd_pct", -8.0))
        if acct["current_dd_pct"] <= max_dd_limit:
            acct["kill_switch_triggered"] = True
            self.store.save_state(state)
            msg = f"CORTAFUEGOS ACTIVADO: Drawdown actual ({acct['current_dd_pct']}%) superó el límite de {max_dd_limit}%."
            self.store.append_log(msg, "WARN")
            return False, [], msg

        old_positions = {p["internal_symbol"]: p for p in state.get("positions", [])}
        new_positions = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Cerrar posiciones que ya no están en target_weights
        executed_orders = self._close_exited_positions(old_positions, target_weights, now_str, reason_summary, acct)

        # 2. Abrir o ajustar posiciones objetivo
        used_cash = 0.0
        active_targets = [
            (int_sym, info) for int_sym, info in target_weights.items() if float(info.get("weight", 0.0)) > 0.001
        ]
        total_weight = sum(float(info.get("weight", 0.0)) for _, info in active_targets)

        for idx, (int_sym, info) in enumerate(active_targets):
            w = float(info.get("weight", 0.0))
            is_last = abs(total_weight - 1.0) < 0.005 and idx == len(active_targets) - 1
            target_usd = round(total_eq - used_cash, 2) if is_last else round(total_eq * w, 2)
            used_cash += target_usd

            pos, ord_item = self._sync_single_target(
                int_sym, info, target_usd, old_positions.get(int_sym), now_str, reason_summary, cfg
            )
            new_positions.append(pos)
            if ord_item:
                executed_orders.append(ord_item)

        acct["cash_usd"] = round(max(0.0, total_eq - used_cash), 2)
        acct["positions_value_usd"] = round(used_cash, 2)
        acct["total_equity_usd"] = round(acct["cash_usd"] + acct["positions_value_usd"], 2)
        state["positions"] = new_positions
        state["orders_history"] = (executed_orders + state.get("orders_history", []))[:100]
        state["last_scan_time"] = now_str
        self.store.save_state(state)

        # 3. Registro contable inmutable para auditoría e IRPF (con metadatos UCITS/ISIN y cambio BCE)
        self._record_ledger_trades(executed_orders, now_str)

        msg = f"Sincronización Paper completada: {len(executed_orders)} órdenes ejecutadas | {len(new_positions)} posiciones activas."
        self.store.append_log(msg, "SUCCESS")
        return True, executed_orders, msg

    def close_all_positions(self, reason: str = "Botón de Pánico / Cierre Total desde Web") -> tuple[bool, str]:
        state = self.get_portfolio_snapshot()
        positions = state.get("positions", [])
        if not positions:
            msg = "No había posiciones abiertas. La cuenta ya está 100% en liquidez."
            self.store.append_log(msg, "INFO")
            return True, msg

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        orders = []
        for p in positions:
            client_oid = IdempotentOrderManager.generate_client_order_id(
                now_str[:10], "KILL_SWITCH", p["broker_symbol"], "LIQUIDATE_ALL"
            )
            orders.append(
                {
                    "time": now_str,
                    "broker": "LOCAL_PAPER",
                    "client_order_id": client_oid,
                    "symbol": p["broker_symbol"],
                    "side": "LIQUIDATE_ALL",
                    "qty": p["qty"],
                    "price": p["current_price"],
                    "notional_usd": p["market_value_usd"],
                    "motor": "KILL_SWITCH",
                    "reason": reason,
                    "status": "FILLED",
                }
            )
            state["account"]["realized_pnl_usd"] = round(
                float(state["account"].get("realized_pnl_usd", 0.0)) + float(p.get("unrealized_pnl_usd", 0.0)),
                2,
            )

        total_eq = float(state["account"]["total_equity_usd"])
        state["account"]["cash_usd"] = total_eq
        state["account"]["positions_value_usd"] = 0.0
        state["account"]["unrealized_pnl_usd"] = 0.0
        state["positions"] = []
        state["orders_history"] = (orders + state.get("orders_history", []))[:100]
        self.store.save_state(state)

        fx_rate = ECBExchangeRateProvider(self.store.data_dir, allow_network=False).get_eur_usd_rate(now_str[:10])
        for o in orders:
            ucits_meta = map_to_ucits_metadata(o.get("symbol", "SPY"))
            self.store.append_trade_ledger(
                {
                    "timestamp": now_str,
                    "environment": self.store.get_config().get("environment", "PAPER"),
                    "order_id": f"ORD-KILL-{int(time.time() * 1000)}",
                    "symbol": o.get("symbol"),
                    "ucits_ticker": ucits_meta["primary_ucits"],
                    "isin": ucits_meta["isin"],
                    "side": o.get("side"),
                    "qty": o.get("qty"),
                    "price_usd": o.get("price"),
                    "notional_usd": o.get("notional_usd"),
                    "currency": "USD",
                    "fx_eur_usd": fx_rate,
                    "commission_usd": 0.0,
                    "motor": o.get("motor"),
                    "reason": o.get("reason"),
                    "status": "FILLED",
                }
            )

        msg = f"Cierre de emergencia ejecutado: {len(orders)} posiciones liquidadas a efectivo (${total_eq:,.2f} en caja)."
        self.store.append_log(msg, "WARN")
        return True, msg


class AlpacaPaperBrokerAdapter(BaseBrokerAdapter):
    """
    Conector Oficial para Alpaca Markets Paper Trading API (v2).
    Utiliza peticiones HTTPS con `APCA-API-KEY-ID` y `APCA-API-SECRET-KEY`.
    Soporta órdenes fraccionadas (`notional` en USD) con $0 de comisión y convierte `ZS` -> `SOYB`.
    """

    def _headers(self, cfg: dict[str, Any]) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": cfg.get("alpaca_api_key", "").strip(),
            "APCA-API-SECRET-KEY": cfg.get("alpaca_secret_key", "").strip(),
            "Content-Type": "application/json",
        }

    def _base_url(self, cfg: dict[str, Any]) -> str:
        return cfg.get("alpaca_endpoint", "https://paper-api.alpaca.markets").rstrip("/")

    def test_connection(self) -> tuple[bool, str]:
        cfg = self.store.get_config()
        if not cfg.get("alpaca_api_key") or not cfg.get("alpaca_secret_key"):
            return (
                False,
                "Faltan las claves de Alpaca Paper Trading. Pégalas en la sección 'Configuración de Bróker' o usa el Simulador Paper Local.",
            )
        req = urllib.request.Request(
            f"{self._base_url(cfg)}/v2/account",
            headers=self._headers(cfg),
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                eq = float(data.get("equity", 0.0))
                status = data.get("status", "UNKNOWN")
                return True, f"Conectado a Alpaca Paper API (Estado: {status} | Equity en Alpaca: ${eq:,.2f})"
        except urllib.error.HTTPError as e:
            return False, f"Alpaca rechazó las credenciales (HTTP {e.code}). Verifica tu API Key y Secret Key."
        except Exception as exc:
            return False, f"Error de red al conectar con Alpaca: {exc}"

    def get_portfolio_snapshot(self) -> dict[str, Any]:
        cfg = self.store.get_config()
        ok, _ = self.test_connection()
        if not ok:
            # Si aún no ha puesto sus claves de Alpaca, mostramos el estado local sin romper nada
            return LocalPaperBrokerAdapter(self.store, self.latest_prices).get_portfolio_snapshot()

        state = self.store.get_state()
        try:
            req_acc = urllib.request.Request(
                f"{self._base_url(cfg)}/v2/account", headers=self._headers(cfg), method="GET"
            )
            req_pos = urllib.request.Request(
                f"{self._base_url(cfg)}/v2/positions", headers=self._headers(cfg), method="GET"
            )
            with urllib.request.urlopen(req_acc, timeout=8) as r1, urllib.request.urlopen(req_pos, timeout=8) as r2:
                acc_data = json.loads(r1.read().decode("utf-8"))
                pos_data = json.loads(r2.read().decode("utf-8"))

            total_eq = float(acc_data.get("equity", 10000.0))
            cash = float(acc_data.get("cash", 10000.0))
            init_cap = float(acc_data.get("last_equity", 10000.0))

            positions = []
            pos_val = 0.0
            unrealized = 0.0
            for p in pos_data:
                mkt_val = float(p.get("market_value", 0.0))
                upnl = float(p.get("unrealized_pl", 0.0))
                pos_val += abs(mkt_val)
                unrealized += upnl
                positions.append(
                    {
                        "internal_symbol": "ZS" if p.get("symbol") == "SOYB" else p.get("symbol"),
                        "broker_symbol": p.get("symbol"),
                        "direction": "LONG" if float(p.get("qty", 0)) >= 0 else "SHORT",
                        "motor": "ALPACA_LIVE",
                        "reason": "Posición sincronizada desde Alpaca Paper API",
                        "qty": abs(round(float(p.get("qty", 0.0)), 4)),
                        "avg_entry_price": round(float(p.get("avg_entry_price", 0.0)), 2),
                        "current_price": round(float(p.get("current_price", 0.0)), 2),
                        "market_value_usd": round(abs(mkt_val), 2),
                        "weight_pct": round((abs(mkt_val) / max(1.0, total_eq)) * 100.0, 1),
                        "unrealized_pnl_usd": round(upnl, 2),
                        "unrealized_pnl_pct": round(float(p.get("unrealized_plpc", 0.0)) * 100.0, 2),
                        "opened_at": "Alpaca Paper",
                    }
                )

            state["account"].update(
                {
                    "cash_usd": round(cash, 2),
                    "positions_value_usd": round(pos_val, 2),
                    "total_equity_usd": round(total_eq, 2),
                    "unrealized_pnl_usd": round(unrealized, 2),
                    "total_return_pct": round(((total_eq - init_cap) / max(1.0, init_cap)) * 100.0, 2),
                }
            )
            state["positions"] = positions
            self.store.save_state(state)
        except Exception as exc:
            self.store.append_log(f"Aviso al leer cartera de Alpaca: {exc}", "WARN")
        return state

    def execute_target_weights(
        self, target_weights: dict[str, dict[str, Any]], reason_summary: str
    ) -> tuple[bool, list[dict[str, Any]], str]:
        cfg = self.store.get_config()
        ok, conn_msg = self.test_connection()
        if not ok:
            self.store.append_log(
                f"Alpaca sin credenciales válidas ({conn_msg}). Ejecutando en Simulador Paper Local.", "WARN"
            )
            return LocalPaperBrokerAdapter(self.store, self.latest_prices).execute_target_weights(
                target_weights, reason_summary
            )

        # Enviar órdenes fraccionadas por valor nocional (USD) sobre el patrimonio total dinámico (Interés Compuesto)
        state = self.get_portfolio_snapshot()
        total_live_eq = float(state.get("account", {}).get("total_equity_usd", 0.0))
        alloc_cap = total_live_eq if total_live_eq > 10.0 else float(cfg.get("allocated_capital_usd", 10000.0))
        executed_orders = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for int_sym, info in target_weights.items():
            w = float(info.get("weight", 0.0))
            if w <= 0.001:
                continue
            b_sym = self.map_symbol(int_sym, cfg)
            notional_usd = round(alloc_cap * w, 2)
            side = "buy" if info.get("direction", "LONG") == "LONG" else "sell"
            motor = info.get("motor", "CORE_BULL")
            client_oid = IdempotentOrderManager.generate_client_order_id(now_str[:10], motor, b_sym, side.upper())

            order_payload = json.dumps(
                {
                    "symbol": b_sym,
                    "notional": str(notional_usd),
                    "side": side,
                    "type": "market",
                    "time_in_force": "day",
                    "client_order_id": client_oid,
                }
            ).encode("utf-8")

            req = urllib.request.Request(
                f"{self._base_url(cfg)}/v2/orders",
                data=order_payload,
                headers=self._headers(cfg),
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    o_resp = json.loads(resp.read().decode("utf-8"))
                    executed_orders.append(
                        {
                            "time": now_str,
                            "broker": "ALPACA_PAPER",
                            "client_order_id": client_oid,
                            "symbol": b_sym,
                            "side": side.upper(),
                            "qty": o_resp.get("qty") or "Fraccional",
                            "price": self.get_live_price(b_sym),
                            "notional_usd": notional_usd,
                            "motor": motor,
                            "reason": info.get("reason", reason_summary),
                            "status": o_resp.get("status", "ACCEPTED").upper(),
                        }
                    )
            except Exception as exc:
                self.store.append_log(f"Error al enviar orden {b_sym} a Alpaca: {exc}", "ERROR")

        state = self.get_portfolio_snapshot()
        state["orders_history"] = (executed_orders + state.get("orders_history", []))[:100]
        state["last_scan_time"] = now_str
        self.store.save_state(state)
        msg = f"Alpaca Paper API: {len(executed_orders)} órdenes enviadas correctamente."
        self.store.append_log(msg, "SUCCESS")
        return True, executed_orders, msg

    def close_all_positions(self, reason: str = "Botón de Pánico / Cierre Total desde Web") -> tuple[bool, str]:
        cfg = self.store.get_config()
        ok, _ = self.test_connection()
        if not ok:
            return LocalPaperBrokerAdapter(self.store, self.latest_prices).close_all_positions(reason)

        req = urllib.request.Request(
            f"{self._base_url(cfg)}/v2/positions?cancel_orders=true",
            headers=self._headers(cfg),
            method="DELETE",
        )
        try:
            with urllib.request.urlopen(req, timeout=8):
                msg = "Alpaca Paper API: Todas las posiciones y órdenes abiertas han sido liquidadas."
                self.store.append_log(msg, "WARN")
                return True, msg
        except Exception as exc:
            return False, f"Error al liquidar en Alpaca: {exc}"
