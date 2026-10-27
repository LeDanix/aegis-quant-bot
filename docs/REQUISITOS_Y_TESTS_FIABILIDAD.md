# Especificación de Requisitos de Fiabilidad de Sistema, UX y Resiliencia Operativa
**Proyecto:** Aegis-Quant Trading Bot & Web Studio  
**Entorno:** Ubuntu Server 24.04 · Python 3.12 · Interactive Brokers / Tradegate / Paper Trading  
**Última actualización:** 27 de Octubre de 2026

---

## 1. Persistencia de Sesión SSH (Termius Móvil & PowerShell PC)

### A. Diagnóstico del Problema
Al conectarse por SSH estándar, cualquier cierre de la aplicación Termius en el móvil (por suspensión en segundo plano de Android/iOS o pérdida de cobertura) envía una señal `SIGHUP` a la pseudoterminal (`pts`), terminando la sesión interactiva del CLI de Antigravity (`agy`). Al volver a abrir la terminal, se inicia un proceso limpio y se requiere pedir al modelo que reexplore el historial.

### B. Solución de Persistencia con `tmux` + Banderas de Antigravity
El servidor cuenta con `tmux` instalado de forma nativa. Al correr dentro de un multiplexor, los procesos siguen ejecutándose en segundo plano aunque el cliente SSH se desconecte abruptamente.

1. **Reconexión Automática con `tmux`:**
   ```bash
   tmux new -A -s agy
   ```
   *La opción `-A` (attach) se conecta a la sesión existente `agy` si ya está viva; si no existe, la crea.*

2. **Reanudación del Contexto de Antigravity CLI:**
   * Antigravity cuenta con la bandera nativa `-c` (`--continue`):
     ```bash
     agy -c
     ```
     Reanuda de forma inmediata la conversación más reciente sin necesidad de pedir reconstrucción de contexto.
   * Si se desea volver a una conversación concreta del pasado:
     ```bash
     agy --conversation <CONVERSATION_ID>
     ```

3. **Configuración en Termius (Móvil):**
   * Editar el Host en Termius.
   * En el apartado **SSH -> Startup Snippet** (o comando inicial), escribir:
     ```bash
     tmux new -A -s agy
     ```
   * Cada vez que se abra Termius y se toque el servidor, la terminal volverá automáticamente a la sesión abierta con todo el historial.

4. **Configuración en PowerShell (PC):**
   ```powershell
   ssh -t dani@192.168.1.150 "tmux new -A -s agy"
   ```
   *(O mediante la IP de Tailscale `100.100.3.20`).*

---

## 2. Requisitos de Fiabilidad del Sistema y Experiencia de Usuario (REQ-01 a REQ-05)

### REQ-01: Hot-Swapping y Desconexión de Motores en Caliente (M1–M6)
* **Descripción:** El usuario puede activar o desactivar cualquiera de los 6 motores tácticos (`M1_PULLBACK`, `M2_VIX_DIV`, `M3_BEAR_SHORT`, `M4_CTA_TREND`, `M5_VOL_CRUSH`, `M6_TOTM`) desde la web o móvil en cualquier momento.
* **Criterios de Aceptación:**
  1. Si un motor se apaga (`enabled_motors[M] = false`), el bot **nunca** debe abrir nuevas órdenes para ese motor ni emitir señales tácticas asociadas.
  2. Si el mercado reunía condiciones para ese motor desactivado, el capital disponible no queda en un limbo ni se generan excepciones: el capital ocioso es absorbido limpiamente por el **Core Adaptativo Modo 3 Élite** (SPY, QQQ, TLT, GLD según régimen VTS).
  3. La ponderación total de la cartera objetivo debe sumar exactamente $1.0$ (100%), sin exceder jamás los topes de slot rápido (55%) o slot CTA (40%).

### REQ-02: Liquidación Total Inmediata (Botón de Pánico) y Reanudación Operativa Limpia
* **Descripción:** En situaciones de emergencia o a petición voluntaria del usuario, el botón de liquidación debe cerrar la totalidad de posiciones abiertas y dejar el sistema en un estado coherente listo para seguir operando.
* **Criterios de Aceptación:**
  1. Todas las posiciones abiertas en cartera pasan a $0$ de volumen.
  2. El saldo de efectivo se actualiza inmediatamente al capital total propio (`cash_usd = total_equity_usd`), y la valoración de posiciones queda en $\$0.00$.
  3. Todas las órdenes de cierre se graban en el libro contable de órdenes con etiqueta `side = "LIQUIDATE_ALL"` y motivo trazable.
  4. La acción es **idempotente**: pulsarla repetidamente cuando la cuenta ya está al 100% en liquidez responde con éxito sin generar errores ni duplicar operaciones.
  5. **Reanudación sin anomalías:** En el siguiente ciclo de escaneo o tras un rebalanceo posterior, el bot es capaz de generar nuevas órdenes de compra y reactivar posiciones sin estados zombi, variables nulas ni excepciones de memoria.

### REQ-03: Persistencia Atómica y Resistencia a Fallos
* **Descripción:** Toda escritura de configuración (`bot_live_config.json`), estado de cartera (`bot_live_state.json`) y libros contables debe ser atómica y resistente a fallos de alimentación, pérdidas de conexión o peticiones concurrentes simultáneas.
* **Criterios de Aceptación:**
  1. Ninguna operación de guardado debe escribir directamente sobre el fichero de destino. Se utiliza siempre un fichero temporal oculto (`.tmp_...`) seguido de un reemplazo atómico a nivel de sistema de ficheros (`os.replace`).
  2. Un fallo en tiempo de serialización JSON nunca trunca ni vacía a $0$ bytes el fichero existente previo.
  3. Múltiples lecturas y escrituras en hilos paralelos (por ejemplo, desde el móvil vía Tailscale y desde el PC) no provocan bloqueos (`deadlocks`) ni excepciones `JSONDecodeError`.

### REQ-04: Trazabilidad y Consistencia Fiscal AEAT (IRPF España)
* **Descripción:** El motor de cálculo tributario español (`SpanishTaxAuditor`) debe computar fielmente todas las operaciones cerradas, tanto manuales como automáticas o de emergencia.
* **Criterios de Aceptación:**
  1. Toda orden ejecutada almacena su ISIN UCITS homogéneo, fecha y tipo de cambio oficial diario EUR/USD del Banco Central Europeo.
  2. El emparejamiento de lotes se realiza estrictamente por antigüedad FIFO (`Art. 37.2 LIRPF`).
  3. Las órdenes de liquidación `LIQUIDATE_ALL` son consumidas correctamente en FIFO tanto para posiciones largas como para cortos (`M3_BEAR_SHORT`).
  4. El detector de la Regla de los 2 Meses (`Art. 33.5.f LIRPF`) vigila recompras en $\pm 60$ días, difiriendo pérdidas si procede y liberándolas al liquidar completamente el valor.
  5. La exportación Renta WEB genera con precisión las casillas del Apartado F2 (`0326` a `0335`), base imponible del ahorro y cálculo de cuota íntegra al 19%–28%.

### REQ-05: Integridad de Contratos de API de la Interfaz Web y Móvil
* **Descripción:** Todos los botones interactivos de la interfaz web (`web_app/static/app.js`) consumen endpoints HTTP estables con validación estricta.
* **Criterios de Aceptación:**
  1. `POST /api/live/action` procesa limpiamente `TOGGLE_BOT`, `SCAN_NOW`, `PANIC_CLOSE_ALL`, `RESET_ACCOUNT`, `TEST_SIGNAL`, etc., devolviendo siempre un objeto `{result, status}` con código HTTP 200.
  2. Acciones no reconocidas devuelven `{ok: false, message: ...}` sin romper el servidor ni causar excepciones no capturadas.
  3. `POST /api/live/config` valida tipos numéricos y actualiza parámetros en memoria y en disco al instante.
  4. `GET /api/live/status` entrega un árbol de estado completo incluso si la cartera está en liquidación absoluta o en inicialización.

### REQ-06: Cortafuegos de Drawdown Diario (Kill-Switch DD Breaker)
* **Descripción:** Cuando el drawdown de la cartera supera el límite diario prefijado (por defecto `-8.0%`), el sistema entra en modo de protección de capital.
* **Criterios de Aceptación:**
  1. `broker.execute_target_weights` calcula el drawdown en vivo contra el capital máximo histórico (`peak_equity_usd`).
  2. Si `current_dd_pct <= daily_kill_switch_dd_pct`, se bloquea de inmediato la emisión de órdenes de compra.
  3. Se marca `kill_switch_triggered = True` en el estado de la cuenta y se emite un log de advertencia en el sistema.

### REQ-07: Flujo Seguro del Modo Copiloto (Aprobación, Rechazo y Cancelación por Pánico)
* **Descripción:** En modo `COPILOT_CONFIRM`, ninguna orden llega al bróker sin el visto bueno explícito del usuario desde la web o el móvil.
* **Criterios de Aceptación:**
  1. Los escaneos (automáticos o manuales) encolan una propuesta inmutable en `state["pending_confirmations"]`.
  2. La acción `REJECT_PENDING` purga la propuesta sin alterar la cartera.
  3. La acción `APPROVE_PENDING` ejecuta las órdenes de la propuesta y limpia la cola.
  4. Si se pulsa `PANIC_CLOSE_ALL` existiendo una propuesta pendiente, esta queda **invalidada de inmediato** para evitar ejecuciones accidentales posteriores de órdenes desfasadas.

### REQ-08: Blindaje de Cuenta Real frente a Reset Accidental (LIVE_REAL Guard)
* **Descripción:** Protección a nivel de backend contra el reinicio inadvertido de estado cuando el bot esté operando con capital real.
* **Criterios de Aceptación:**
  1. Si `environment == "LIVE_REAL"`, la acción `RESET_ACCOUNT` es rechazada taxativamente devolviendo `{ok: false}`.
  2. Ni el saldo ni las posiciones reales son eliminadas, registrándose una alerta de seguridad en el log.

### REQ-09: Rebalanceo con Deltas Parciales y Conservación de Liquidez
* **Descripción:** Las reasignaciones de peso entre activos deben ajustar solo las diferencias relativas sin sobregirar la cuenta.
* **Criterios de Aceptación:**
  1. Al recortar la exposición de un activo se emiten órdenes `SELL_PARTIAL`, liberando efectivo antes de ejecutar compras adicionales.
  2. El saldo en efectivo final (`cash_usd`) nunca puede ser inferior a cero ($0.00$), respetando cuentas sin margen o de efectivo.
  3. La suma de efectivo y valor de mercado de las posiciones cuadra exactamente al céntimo con el patrimonio total.

### REQ-10: Compensación Fiscal Multiejercicio (4 Años AEAT) y Aislamiento Regla 2M
* **Descripción:** El auditor tributario aplica automáticamente la compensación de pérdidas pendientes de hasta 4 años según la LIRPF.
* **Criterios de Aceptación:**
  1. Si existen pérdidas previas (`prior_loss_carryforward_eur`), se compensan hasta el 100% de las ganancias netas del ejercicio, reduciendo la base imponible del ahorro (`taxable_savings_base_eur`).
  2. Si una pérdida se produce en una ventana de $\pm 60$ días alrededor de una recompra homogénea, queda identificada como diferida (`blocked_2m = True`) y se excluye de la base imponible de ese año.

### REQ-11: Transición Defensiva de Régimen ante Mercado Bajista o Backwardation
* **Descripción:** Salvaguarda ante desplomes de mercado o inversión de la curva de futuros del VIX.
* **Criterios de Aceptación:**
  1. En régimen de Backwardation institucional ($VIX/VIX3M \ge 1.0$) o cotización bajo `SMA(200)`, el Core Modo 3 retira al 100% la asignación pasiva de bolsa ($0\%$ SPY y $0\%$ QQQ).
  2. El capital ocioso se preserva en liquidez o se rota defensivamente hasta un 30% hacia activos refugio (GLD/TLT) únicamente si mantienen directriz alcista confirmada.

### REQ-12: Resiliencia de Ingesta ante Cotizaciones Inválidas o Desconocidas
* **Descripción:** El subsistema de ejecución y pricing es inmune a valores no numéricos, ceros o símbolos atípicos.
* **Criterios de Aceptación:**
  1. Símbolos no encontrados en el diccionario de precios en vivo se resuelven defensivamente sin excepciones de clave (`KeyError`).
  2. Precios anormalmente bajos o nulos utilizan divisores acotados (`max(0.01, px)`), previniendo excepciones `ZeroDivisionError`.

---

## 3. Matriz de Verificación y Resultados de la Suite Automatizada

La suite completa de tests de integración del sistema y UX está implementada en [`tests/test_system_integration_and_ux.py`](../tests/test_system_integration_and_ux.py).

| Test Unitario / E2E | Requisito Evaluado | Estado | Tiempo |
| :--- | :--- | :---: | :---: |
| `test_req01_engine_hot_disconnect_prevents_signals_and_reallocates_cleanly` | REQ-01 (Hot-Swapping M1–M6) | **PASSED** | 0.82s |
| `test_req02_panic_liquidation_and_clean_trading_resumption` | REQ-02 (Pánico y Reanudación) | **PASSED** | 0.74s |
| `test_req03_atomic_persistence_and_no_file_corruption` | REQ-03 (Persistencia Atómica) | **PASSED** | 0.05s |
| `test_req04_tax_audit_computes_cleanly_after_panic_liquidation` | REQ-04 (Fiscalidad AEAT Post-Pánico) | **PASSED** | 0.41s |
| `test_req05_api_button_actions_contract_integrity` | REQ-05 (Contratos API y Botones) | **PASSED** | 1.95s |
| `test_req06_daily_kill_switch_blocks_orders_on_excessive_drawdown` | REQ-06 (Kill-Switch Drawdown) | **PASSED** | 0.08s |
| `test_req07_copilot_proposal_approval_rejection_and_panic_cancellation` | REQ-07 (Modo Copiloto Completo) | **PASSED** | 3.12s |
| `test_req08_live_real_environment_blocks_account_reset` | REQ-08 (Blindaje LIVE_REAL) | **PASSED** | 0.45s |
| `test_req09_partial_rebalance_deltas_and_non_negative_cash_conservation` | REQ-09 (Deltas & Conservación Caja) | **PASSED** | 0.09s |
| `test_req10_spanish_tax_carryforward_and_2m_rule_isolation` | REQ-10 (Compensación Fiscal 4 Años) | **PASSED** | 0.22s |
| `test_req11_bear_market_and_backwardation_core_defense` | REQ-11 (Defensa en Backwardation) | **PASSED** | 0.01s |
| `test_req12_price_feed_zero_or_nan_resilience` | REQ-12 (Resiliencia Precios Inválidos) | **PASSED** | 0.06s |

### Ejecución Total del Proyecto
```bash
python3 -m unittest discover tests
# Resultado: Ran 71 tests in 21.416s · OK (100% de éxito)
```
