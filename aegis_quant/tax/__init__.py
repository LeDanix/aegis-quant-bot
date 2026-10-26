"""
Paquete Fiscal Español de Aegis-Quant (aegis_quant/tax/__init__.py).

Exporta:
  - UCITS_CATALOG y map_to_ucits_metadata
  - ECBExchangeRateProvider (tipos de cambio oficiales EUR/USD del BCE con caché atómica)
  - calculate_spanish_savings_irpf (escala progresiva estatal+autonómica Base del Ahorro)
  - compute_backtest_tax_waterfall (cascada 2007-2026 de costes operativos + IRPF + compensación 4 años)
  - SpanishTaxAuditor (motor automático FIFO + Regla antiaplicación 2 meses Art. 33.5.f LIRPF + Modelo 720 + CSV Renta WEB)
"""

from aegis_quant.tax.spanish_tax_engine import (
    MODELO_720_THRESHOLD_EUR,
    UCITS_CATALOG,
    ECBExchangeRateProvider,
    SpanishTaxAuditor,
    calculate_spanish_savings_irpf,
    compute_backtest_tax_waterfall,
    map_to_ucits_metadata,
)

__all__ = [
    "MODELO_720_THRESHOLD_EUR",
    "UCITS_CATALOG",
    "ECBExchangeRateProvider",
    "SpanishTaxAuditor",
    "calculate_spanish_savings_irpf",
    "compute_backtest_tax_waterfall",
    "map_to_ucits_metadata",
]
