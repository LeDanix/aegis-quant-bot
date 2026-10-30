"""Servicio de Conciliación de Estado de Cartera (State Reconciliation Service).

Garantiza la verdad absoluta entre lo que el bot cree tener (state.json local)
y lo que el bróker realmente custodia en cuenta (Interactive Brokers / Alpaca).
Resuelve discrepancias por órdenes rechazadas, desincronizaciones de red o ejecuciones manuales.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class DiscrepancyItem:
    """Detalle de una discrepancia detectada entre estado local y bróker."""

    symbol: str
    issue_type: str  # "MISSING_IN_BROKER" | "GHOST_IN_BROKER" | "QTY_MISMATCH" | "CASH_MISMATCH"
    local_val: float
    broker_val: float
    message: str


@dataclass
class ReconciliationResult:
    """Resultado formal del proceso de conciliación."""

    in_sync: bool
    reconciled_state: dict[str, Any]
    discrepancies: list[DiscrepancyItem] = field(default_factory=list)
    action_taken: str = "NONE"  # "NONE" | "AUTO_ALIGNED" | "HALT_EMERGENCY"
    summary_message: str = "Cartera perfectamente sincronizada con el bróker."


class StateReconciliationService:
    """Conciliador bidireccional y guardián de integridad patrimonial."""

    TOLERANCE_QTY: float = 1e-4
    TOLERANCE_CASH_PCT: float = 1.0  # 1% de desviación admisible por comisiones pendientes o tipo de cambio

    @classmethod
    def _check_missing_and_mismatch(
        cls,
        local_map: dict[str, dict[str, Any]],
        broker_map: dict[str, dict[str, Any]],
    ) -> list[DiscrepancyItem]:
        discrepancies: list[DiscrepancyItem] = []
        for sym, l_pos in local_map.items():
            l_qty = float(l_pos.get("shares", 0.0))
            if sym not in broker_map:
                if l_qty > cls.TOLERANCE_QTY:
                    discrepancies.append(
                        DiscrepancyItem(
                            symbol=sym,
                            issue_type="MISSING_IN_BROKER",
                            local_val=l_qty,
                            broker_val=0.0,
                            message=f"Posición {sym} ({l_qty} acciones) registrada localmente pero inexistente en bróker.",
                        )
                    )
            else:
                b_qty = float(broker_map[sym].get("shares", 0.0))
                if abs(l_qty - b_qty) > cls.TOLERANCE_QTY:
                    discrepancies.append(
                        DiscrepancyItem(
                            symbol=sym,
                            issue_type="QTY_MISMATCH",
                            local_val=l_qty,
                            broker_val=b_qty,
                            message=f"Discrepancia en cantidad de {sym}: Local={l_qty} vs Bróker={b_qty}.",
                        )
                    )
        return discrepancies

    @classmethod
    def _check_ghost_positions(
        cls,
        local_map: dict[str, dict[str, Any]],
        broker_map: dict[str, dict[str, Any]],
    ) -> list[DiscrepancyItem]:
        discrepancies: list[DiscrepancyItem] = []
        for sym, b_pos in broker_map.items():
            b_qty = float(b_pos.get("shares", 0.0))
            if sym not in local_map and b_qty > cls.TOLERANCE_QTY:
                discrepancies.append(
                    DiscrepancyItem(
                        symbol=sym,
                        issue_type="GHOST_IN_BROKER",
                        local_val=0.0,
                        broker_val=b_qty,
                        message=f"Posición no registrada detectada en bróker: {sym} ({b_qty} acciones).",
                    )
                )
        return discrepancies

    @classmethod
    def _check_cash_discrepancy(
        cls,
        local_acct: dict[str, Any],
        broker_acct: dict[str, Any],
    ) -> list[DiscrepancyItem]:
        discrepancies: list[DiscrepancyItem] = []
        l_cash = float(local_acct.get("cash_usd", 0.0))
        b_cash = float(broker_acct.get("cash_usd", l_cash))
        l_eq = float(local_acct.get("total_equity_usd", 10000.0))
        b_eq = float(broker_acct.get("total_equity_usd", l_eq))

        cash_diff = abs(l_cash - b_cash)
        if b_eq > 0 and (cash_diff / b_eq) * 100.0 > cls.TOLERANCE_CASH_PCT:
            discrepancies.append(
                DiscrepancyItem(
                    symbol="CASH",
                    issue_type="CASH_MISMATCH",
                    local_val=l_cash,
                    broker_val=b_cash,
                    message=f"Desfase en liquidez: Local=${l_cash:,.2f} vs Bróker=${b_cash:,.2f}.",
                )
            )
        return discrepancies

    @classmethod
    def reconcile(
        cls,
        local_state: dict[str, Any],
        broker_snapshot: dict[str, Any],
    ) -> ReconciliationResult:
        """Compara el estado local con la telemetría viva del bróker y produce un estado conciliado fiel.

        Prioridad: La custodia real del bróker es siempre la verdad suprema.
        """
        local_pos_list = local_state.get("positions", [])
        broker_pos_list = broker_snapshot.get("positions", [])

        # Indexar por símbolo normalizado
        local_pos_map = {
            p.get("broker_symbol") or p.get("internal_symbol"): p
            for p in local_pos_list
            if (p.get("broker_symbol") or p.get("internal_symbol"))
        }
        broker_pos_map = {
            p.get("broker_symbol") or p.get("internal_symbol"): p
            for p in broker_pos_list
            if (p.get("broker_symbol") or p.get("internal_symbol"))
        }

        # 1. Comprobar posiciones faltantes y discrepancias de cantidad
        discrepancies = cls._check_missing_and_mismatch(local_pos_map, broker_pos_map)

        # 2. Comprobar posiciones fantasma
        discrepancies.extend(cls._check_ghost_positions(local_pos_map, broker_pos_map))

        # 3. Comprobar liquidez y patrimonio
        discrepancies.extend(
            cls._check_cash_discrepancy(
                local_state.get("account", {}),
                broker_snapshot.get("account", {}),
            )
        )

        reconciled = dict(local_state)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not discrepancies:
            return ReconciliationResult(
                in_sync=True,
                reconciled_state=reconciled,
                discrepancies=[],
                action_taken="NONE",
                summary_message="Sincronización perfecta: Posiciones y saldos coinciden al 100% con el bróker.",
            )

        # Auto-alinear con la verdad del bróker
        reconciled["positions"] = [dict(p) for p in broker_pos_list]
        broker_acct = broker_snapshot.get("account")
        if broker_acct:
            reconciled["account"] = dict(broker_acct)

        reconciled["last_reconciliation"] = {
            "time": now_str,
            "discrepancies_count": len(discrepancies),
            "discrepancies": [d.message for d in discrepancies],
        }

        logs = reconciled.setdefault("logs", [])
        logs.insert(
            0,
            {
                "time": now_str,
                "level": "WARN",
                "msg": f"Conciliación de estado: {len(discrepancies)} discrepancias auto-alineadas con el bróker.",
            },
        )

        return ReconciliationResult(
            in_sync=False,
            reconciled_state=reconciled,
            discrepancies=discrepancies,
            action_taken="AUTO_ALIGNED",
            summary_message=f"Detectadas {len(discrepancies)} divergencias corregidas automáticamente a la verdad del bróker.",
        )
