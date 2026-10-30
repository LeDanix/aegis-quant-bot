"""Gestor de Órdenes Idempotentes y Control de Ejecución (Idempotent Order Manager).

Garantiza que ninguna orden pueda ejecutarse por duplicado ante caídas de red, reintentos
o reconexiones. Calcula las participaciones enteras discretas y valida techos de asignación.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ValidatedOrder:
    """Representa una orden validada matemáticamente con identificador determinista único."""

    order_id: str
    symbol: str
    side: str  # "BUY" | "SELL"
    shares: int
    target_weight: float
    motor: str
    reason: str
    estimated_price: float
    estimated_notional: float


class IdempotentOrderManager:
    """Generador y validador de órdenes deterministas libre de colisiones."""

    # Techos prudenciales de seguridad institucional
    MAX_GENERAL_ALLOCATION: float = 0.40  # 40% máximo por activo general
    MAX_BTC_ALLOCATION: float = 0.15  # 15% máximo estricto para Bitcoin
    MIN_ORDER_NOTIONAL_USD: float = 10.0  # Menos de 10$ se ignora para evitar comisiones absurdas

    def __init__(self, executed_order_ids: set[str] | None = None) -> None:
        self._executed_ids: set[str] = set(executed_order_ids or [])

    @staticmethod
    def generate_client_order_id(date_str: str, motor: str, symbol: str, side: str) -> str:
        """Genera una clave de idempotencia única y determinista para el bróker.

        Formato: AEGIS-YYYYMMDD-MOTOR-SYMBOL-SIDE (ej. AEGIS-20261030-M1-SPYL-BUY)
        """
        clean_date = date_str.replace("-", "").strip()
        clean_motor = motor.upper().replace("_", "")[:8]
        clean_sym = symbol.upper().replace("/", "").replace("%3DF", "")[:6]
        clean_side = side.upper().strip()
        return f"AEGIS-{clean_date}-{clean_motor}-{clean_sym}-{clean_side}"

    def is_already_executed(self, order_id: str) -> bool:
        """Comprueba si este identificador determinista ya se ejecutó en la sesión."""
        return order_id in self._executed_ids

    def register_execution(self, order_id: str) -> None:
        """Registra la orden en el conjunto en memoria de órdenes consumidas."""
        self._executed_ids.add(order_id)

    @classmethod
    def calculate_discrete_shares(
        cls,
        target_notional: float,
        current_price: float,
        symbol: str = "",
    ) -> int:
        """Calcula el número de participaciones enteras mediante redondeo hacia abajo (floor).

        En brókers europeos como Tradegate / Xetra, no se permiten fracciones en órdenes limitadas.
        """
        if current_price <= 0.0 or target_notional <= 0.0:
            return 0
        shares = math.floor(target_notional / current_price)
        return max(0, int(shares))

    @classmethod
    def apply_safety_caps(cls, symbol: str, raw_weight: float) -> float:
        """Aplica techos de riesgo inviolables a nivel de código antes de enviar órdenes."""
        if raw_weight <= 0.0:
            return 0.0

        upper_cap = cls.MAX_BTC_ALLOCATION if "BTC" in symbol.upper() else cls.MAX_GENERAL_ALLOCATION
        return round(min(raw_weight, upper_cap), 4)

    def prepare_orders(
        self,
        targets: dict[str, dict[str, Any]],
        current_positions: dict[str, float],
        total_equity: float,
        latest_prices: dict[str, float],
        date_str: str | None = None,
    ) -> list[ValidatedOrder]:
        """Transforma una asignación objetivo de pesos en una lista de órdenes idempotentes discretas."""
        if total_equity <= 0.0:
            return []

        if not date_str:
            date_str = datetime.now().strftime("%Y%m%d")

        validated_orders: list[ValidatedOrder] = []

        for sym, t_info in targets.items():
            raw_target_w = float(t_info.get("weight", 0.0))
            capped_w = self.apply_safety_caps(sym, raw_target_w)
            current_w = float(current_positions.get(sym, 0.0))

            delta_w = round(capped_w - current_w, 4)
            if abs(delta_w) < 0.005:  # Desviación menor al 0.5% se considera en equilibrio
                continue

            px = float(latest_prices.get(sym, 0.0))
            if px <= 0.0:
                continue

            side = "BUY" if delta_w > 0 else "SELL"
            motor = str(t_info.get("motor", "CORE"))
            reason = str(t_info.get("reason", "Alineación de cartera"))

            order_id = self.generate_client_order_id(date_str, motor, sym, side)

            # Si ya se ejecutó esta orden exacta hoy, la filtramos para proteger la cuenta
            if self.is_already_executed(order_id):
                continue

            notional = abs(delta_w) * total_equity
            if notional < self.MIN_ORDER_NOTIONAL_USD and side == "BUY":
                continue

            shares = self.calculate_discrete_shares(notional, px, sym)
            if shares <= 0:
                continue

            validated_orders.append(
                ValidatedOrder(
                    order_id=order_id,
                    symbol=sym,
                    side=side,
                    shares=shares,
                    target_weight=capped_w,
                    motor=motor,
                    reason=reason,
                    estimated_price=px,
                    estimated_notional=round(shares * px, 2),
                )
            )

        return validated_orders
