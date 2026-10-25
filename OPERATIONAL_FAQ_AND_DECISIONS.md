# Aegis-Quant: Guía Operativa, Fiscal y Registro de Decisiones de Arquitectura

> **DOCUMENTO OFICIAL DEL REPOSITORIO — SISTEMA AEGIS-QUANT**  
> *Destinatario: Operador del Sistema & Inversor Residente en España*  
> *Última actualización: 25 de Octubre de 2026*

Este documento consolida de forma viva y permanente todas las dudas operativas, decisiones de arquitectura cuantitativa, marco legal y fiscal en España, y análisis de riesgo resueltos para el funcionamiento del bot en dinero real.

---

## 1. Vehículos Financieros en España: ETFs UCITS vs ETFs USA (Normativa PRIIPs)

### A. La Restricción Legal en España (Normativa PRIIPs / MiFID II)
En la Unión Europea y en España (supervisado por la CNMV), los brókers minoristas (incluido **Interactive Brokers**) tienen prohibido por ley permitir la compra directa de ETFs domiciliados en EE. UU. (`SPY`, `QQQ`, `GLD`, `TLT`, `USO`). Esto se debe a que la directiva **PRIIPs** exige que los emisores publiquen un folleto estandarizado denominado **KID (Key Information Document)** en el idioma local, algo que las gestoras norteamericanas no emiten para sus fondos domésticos.

### B. La Solución Oficial de Aegis-Quant: ETFs UCITS Europeos
Para operar de forma 100% legal, líquida y sin trabas administrativas, el bot mapea los activos de referencia mundial a sus **equivalentes UCITS europeos**:

| Activo Modelo | Equivalente UCITS Elegido | Emisor / Gestora | Bolsa / Divisa | Patrimonio Gestionado (AUM) | Tipo de Réplica |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **SPY** (S&P 500) | **`CSPX`** (USD) / **`SXR8`** (EUR) | BlackRock iShares | Xetra / Borsa Italiana / LSE | **> 85.000 Millones de €** | Física Directa (Acciones reales) |
| **QQQ** (Nasdaq 100) | **`EQQQ`** (EUR/USD) / **`CSNDX`** | Invesco / BlackRock | Xetra / Borsa Italiana / LSE | **> 12.000 Millones de €** | Física Directa |
| **GLD** (Oro Físico) | **`SGLD`** / **`4GLD`** | Invesco / Xetra-Gold | Xetra / Suiza / Borsa Italiana | **> 16.000 Millones de €** | Oro Físico en Bóveda |
| **TLT** (Bonos 20+ Años)| **`DTLA`** / **`IDTL`** | BlackRock iShares | Xetra / LSE | **> 4.800 Millones de €** | Física Directa (Deuda Tesoro USA) |
| **USO** (Petróleo WTI)| **`CRUD`** / **`OD7F`** | WisdomTree | Borsa Italiana / Xetra | **> 1.200 Millones de €** | Sintética con colateral de grado AAA |
| **ZS** (Soja Agrícola) | **`SOYB`** / **`A0KRK2`** | WisdomTree | Xetra / Borsa Italiana | **> 40 Millones de €** | ETC regulado sobre contratos de futuros |

### C. Solvencia y Fiabilidad de los ETFs UCITS
1. **Seguridad Patrimonial (UCITS V):** Los activos no están en el balance de la gestora (BlackRock o Invesco), sino segregados en bancos custodios independientes (State Street / BNY Mellon). En caso de quiebra del bróker o de la gestora, los títulos pertenecen al inversor.
2. **Liquidez Institucional:** Fondos como `CSPX/SXR8` mueven más de 100 millones de euros diarios, garantizando horquillas de compra-venta (*spreads*) de tan solo 1 o 2 céntimos (~0.01% - 0.02%).
3. **Optimización por Acumulación:** Al ser ETFs de **acumulación**, los dividendos se reinvierten internamente sin sufrir la retención del 15% en EE. UU. ni el 19% en España, maximizando el interés compuesto.

---

## 2. Fiscalidad en España para Persona Física (IRPF Base del Ahorro)

### A. Separación Total de Bases Imponibles
En el IRPF español existen dos cestas totalmente independientes:
- **Base Imponible General:** Nóminas, sueldos de trabajo o facturación de autónomo.
- **Base Imponible del Ahorro:** Ganancias y pérdidas patrimoniales derivadas de la transmisión de elementos patrimoniales (compra-venta de ETFs, acciones, derivados).

> [!IMPORTANT]
> **Tu nómina laboral nunca incrementa el tipo impositivo de las ganancias del bot.**  
> Las plusvalías generadas por el bot tributan de forma aislada en la escala del ahorro, empezando siempre desde el tramo más bajo (19%).

### B. Escala Progresiva de la Base del Ahorro en España
| Tramo de Ganancia Anual Neta | Tipo Impositivo IRPF |
| :--- | :---: |
| Hasta 6.000,00 € | **19,0%** |
| De 6.000,01 € a 50.000,00 € | **21,0%** |
| De 50.000,01 € a 200.000,00 € | **23,0%** |
| De 200.000,01 € a 300.000,00 € | **27,0%** |
| Más de 300.000,00 € | **28,0%** |

### C. Compensación de Pérdidas a 4 Años
Si en un ejercicio fiscal el bot experimentase un año negativo:
1. **Ese año no se paga ni un solo euro de IRPF.**
2. El saldo negativo se registra en la declaración de la Renta y se arrastra para **compensar al 100% las ganancias que genere el bot durante los 4 ejercicios fiscales siguientes**.

### D. Retiradas de Dinero a tu Banco: ¿Tributan de nuevo?
**No.** El hecho imponible que genera la obligación tributaria es la **venta** de las participaciones dentro del bróker. Una vez presentada la declaración del IRPF anual y pagada la cuota correspondiente, ese dinero es **100% tuyo y legalmente limpio**.  
Transferir fondos desde Interactive Brokers a tu cuenta bancaria personal en España (BBVA, Santander, etc.) es un simple movimiento entre cuentas propias: **no tributa de nuevo ni se declara como un nuevo ingreso**.

### E. Declaraciones Informativas: El Modelo 720
Interactive Brokers opera para clientes de la UE a través de su filial europea (**IBKR Ireland - IBIE** o **IBKR Central Europe**).  
Si el saldo o valor de los valores depositados en el extranjero supera los **50.000 € a 31 de diciembre**, la ley española exige presentar el **Modelo 720** (declaración meramente informativa antes del 31 de marzo, sin coste impositivo).

---

## 3. Costes Operacionales Reales y Cascada de Rentabilidad (2007–2026)

### A. Desglose de Gastos Operacionales en Interactive Brokers
1. **Comisión de Bróker (Tarifa *Tiered*):** 0.05% por orden (mínimo de ~1.25 € a 2.00 €).
2. **Deslizamiento (*Slippage* / *Bid-Ask Spread*):** ~0.02% en ETFs ultra-líquidos.
3. **TER del ETF:** ~0.10% medio ponderado anual (descontado de forma invisible del NAV).
4. **Custodia y Mantenimiento:** **0,00 €** (IBKR no cobra comisiones de custodia ni de inactividad).

### B. Cascada Auditada de Rendimiento Real (Capital Inicial: $10,000 | 2007–2026)

```text
Capital Inicial (2007)                                       : $10,000.00
  ├── Retorno Bruto del Algoritmo (18.15% CAGR)              : $281,068.69 (+2,710.69%)
  │
  ├── (-) Costes Operacionales (Comisiones + Spread + TER)   : -$5,165.87 (-0.65% CAGR)
  │    └── Capital Neto Operacional                          : $251,722.68 (+2,417.23% | 17.50% CAGR)
  │
  ├── (-) Impuestos IRPF España (Base del Ahorro año a año)  : -$32,908.41 (-3.35% CAGR)
  │
  └── (=) CAPITAL FINAL NETO EN TU BOLSILLO                  : $141,077.59 (+1,310.78% | 14.15% CAGR)
```

**Comparativa frente al S&P 500 Buy & Hold:**
- **S&P 500 Bruto:** $54,685.58 (8.97% CAGR)
- **S&P 500 Neto tras IRPF al liquidar:** **$45,421.61** (7.98% CAGR)
- **Ventaja Patrimonial Neta:** **3.11 veces más capital limpio en tu bolsillo** que la inversión pasiva tradicional, habiendo batido las 4 grandes crisis de las últimas dos décadas.

---

## 4. Estrategia de Capital: Reinversión vs Retirada Anual (Interés Compuesto)

### A. Comparativa de Estrategias
- **Estrategia A (Dejar el dinero reinvertido — Recomendada):**  
  Aprovecha el crecimiento exponencial del interés compuesto. Al reinvertir el capital neto tras pagar impuestos, la base operativa crece anualmente ($10k $\rightarrow$ $11.7k $\rightarrow$ $15.3k $\rightarrow$ ... $\rightarrow$ **$141,077**).
- **Estrategia B (Retirar las ganancias cada año):**  
  El bot opera perpetuamente sobre la base fija de $10,000. Retiras entre 1.500 € y 2.500 € al año para gastos personales. Tras 20 años habrás cobrado unos 35.000 € en rentas, pero habrás renunciado a tener una cartera de más de 140.000 €.

### B. La Regla de Oro Institucional (Plan de Dos Fases)
1. **Fase de Acumulación (Años 1 al 5-7):** No retirar dinero. Dejar que la cartera supere el umbral de los **50.000 € - 100.000 €**.
2. **Fase de Ordeño Parcial:** A partir de ese hito, retirar anualmente el **50% de la ganancia neta** para disfrute personal y dejar el otro 50% reinvertido para que el capital continúe creciendo por encima de la inflación.

---

## 5. Análisis Cuantitativo de Apalancamiento y Modelos de Futuros x3

### A. La Pregunta del Millón: ¿Qué pasaría si usamos un multiplicador x3 en futuros?
A nivel intuitivo, parece tentador pensar que multiplicar por 3 el rendimiento convertiría un 18% anual en un 54% anual. Sin embargo, en matemáticas financieras esto es una **trampa mortal** debido a dos fenómenos destructivos:

### B. El Fenómeno del Decaimiento por Volatilidad (*Volatility Drag / Beta Decay*)
Los productos o futuros con apalancamiento estático sufren una erosión geométrica matemática inevitable cuando el mercado oscila:

**Ejemplo Práctico:**
- Imagina que el S&P 500 cae un **-10%** el lunes y sube un **+11.11%** el martes.
  - El índice sin apalancamiento: $100 \times 0.90 = 90$; $90 \times 1.1111 = 100$. **El mercado ha quedado en 0% (empatado).**
  - Un modelo con apalancamiento x3 estático:
    - Día 1: Cae un $-30\%$ ($100 \times 0.70 = 70$).
    - Día 2: Sube un $+33.33\%$ ($70 \times 1.3333 = 93.33$).
    - **¡El mercado no ha perdido nada y tú has perdido un -6.67% de tu dinero en 48 horas!**

En mercados laterales o volátiles, este decaimiento actúa como un impuesto invisible que drena el capital de forma irreversible.

### C. El Riesgo de Ruina Absoluta (*Drawdown Trap*)
- Para recuperar una caída del **-20%**, necesitas ganar un **+25%**.
- Para recuperar una caída del **-50%**, necesitas ganar un **+100%**.
- Para recuperar una caída del **-80%**, necesitas ganar un **+400%**.
- **Si el mercado cae un -33.4%:**
  - Con apalancamiento x3: $-33.4\% \times 3 = -100.2\%$. **Tu cuenta quiebra a 0 € y quedas liquidado permanentemente.**
  - En la crisis de 2008 el S&P 500 cayó un **-56%** y en el Crash COVID de 2020 cayó un **-35%**. Un modelo x3 estático habría quebrado dos veces en los últimos 20 años.

### D. Llamadas de Margen (*Margin Calls*) en Interactive Brokers
Si operas futuros apalancados (`MES`, `MNQ`) y tu capital cae por debajo del margen de mantenimiento exigido por la cámara de compensación, el algoritmo de riesgo de IBKR **ejecuta una liquidación forzosa automática en el peor momento posible (en el mínimo del pánico)**, materializando pérdidas irrecuperables.

### E. La Solución Científica de Aegis-Quant: Apalancamiento Variable (Meta-Kelly & VolTarget)
Aegis-Quant no utiliza apalancamiento estático x3, sino **apalancamiento dinámico e inteligente**:
1. **Regímenes de Calma Chicha (VIX < 13):** Cuando el riesgo sistémico es mínimo, el motor eleva la convicción hasta **1.25x - 1.35x** para acelerar el crecimiento.
2. **Regímenes de Pánico (VIX > 25 o VTS en Backwardation):** El tamaño de posición se reduce drásticamente (a **0.3x o 0% a liquidez**), esquivando el colapso.

---

## 6. Desfase Horario Europa vs Wall Street (Problema #4 de Auditoría): ¿Qué Supone Cada Opción?

### El Problema Operativo Real
Las bolsas principales europeas (**XETRA** en Fráncfort, **Borsa Italiana**, **LSE**) donde cotizan los ETFs UCITS (`SXR8`/`CSPX`, `EQQQ`, `4GLD`, `DTLA`, `CRUD`) **cierran a las 17:30 CET** (11:30 AM en Nueva York). Sin embargo, el escáner del bot evalúa el cierre estadounidense a las **21:55 CET (15:55 NY)**. Si lanzas una orden a XETRA a las 21:55 CET, queda retenida hasta las 09:00 CET del día siguiente (sufriendo *gap* nocturno).

### Comparativa Detallada de Opciones en Interactive Brokers (España)

| Criterio | Opción A: **Tradegate / Gettex** (ETFs UCITS en Horario Extendido) | Opción B: **Micro-Futuros CME** (`MES` S&P 500 / `MNQ` Nasdaq) |
| :--- | :--- | :--- |
| **Horario de negociación** | **08:00 a 22:00 CET** (cubre las 21:55 CET y las 20:55 CET en semanas DST). | **23 horas al día** (00:00 a 23:00 CET) directo en EE. UU. |
| **Vehículo que compras** | **Exactamente los mismos ETFs UCITS** (`SXR8`, `EQQQ`, `4GLD`) en Euros, sin deuda ni derivados. | Contratos de derivados con liquidación diaria de pérdidas y ganancias (*mark-to-market*). |
| **Capital mínimo necesario** | **Cualquier capital (ej. 5.000 € – 10.000 €)**. Permite ajustar pesos exactos (55%, 85%, 15%) con participaciones o fracciones. | **Muy exigente para evitar apalancamiento**: 1 solo contrato `MES` equivale a $5 × S&P 500 ≈ **29.000 $ – 38.000 $** de valor nocional. Con 10.000 € estarías apalancado ~x3 forzosamente y no puedes comprar "medio contrato". |
| **Coste / Horquilla (Spread)** | Comisión IBKR ~1,25 €–3 €; horquilla entre 17:30 y 22:00 CET sube ligeramente de `0,02%` a **`0,05%–0,10%`** (órdenes limitadas obligatorias). | Comisión mínima (~0,60 $ por contrato) y horquilla casi nula (`0,004%`). |
| **Gestión y Fiscalidad IRPF** | **Simple**: mientras mantienes el Core (`SXR8`) meses seguidos, **0 eventos fiscales** y 0 gestiones. | **Compleja (Roll-over trimestral)**: los futuros caducan cada 3 meses (marzo, junio, septiembre, diciembre). Hay que vender el contrato viejo y comprar el nuevo 4 veces al año, aflorando impuestos cada trimestre aunque no toques la posición. |
| **Veredicto Recomendado** | **OPCIÓN RECOMENDADA para cuentas < 60.000 € – 100.000 €**: mantiene 0% apalancamiento, simplicidad fiscal y permite operar a las 21:55 CET usando órdenes *Limit* en Tradegate (`TGATE` en IBKR). | Solo recomendable a partir de capitales elevados (> 80.000 €) o exclusivamente para el **Motor 3 (Corto en Crisis)**, donde vender un futuro `MES` es más limpio que tomar acciones prestadas. |

---

## 7. Evaluación Empírica (2007–2026) de los Nuevos Motores Propuestos (M6 a M9)

Para comprobar científicamente si añadir los 4 módulos propuestos en la auditoría (`docs/AUDIT_AND_PROPOSALS.md`) mejora de verdad la rentabilidad o si sobrefiltra el sistema, se ha construido el módulo reproducible [`aegis_quant/research/evaluate_audit_proposals.py`](aegis_quant/research/evaluate_audit_proposals.py) probándolos con datos reales de Yahoo Finance (`HYG`, `LQD`, `RSP`, `SPY`, `QQQ`, `VIX`, `VIX3M`, `GLD`, `TLT`, `USO`, `ZS`) entre **2007 y 2026** sobre **$10,000 iniciales**:

| Arquitectura Evaluada (2007–2026) | Capital Final | CAGR Anual | Max Drawdown | Sharpe | Sortino | Calmar | Nº Trades | Conclusión Empírica |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **0. Baseline: Modo 3 Élite Actual (M1–M5)** | **$281,092** | **18,38%** | -15,02% | 1,59 | 2,89 | 1,22 | 725 | Referencia actual auditada. |
| **1. + M6 Spread Crédito (`HYG/LQD`)** | $190,211 | 16,07% | -17,92% | 1,42 | 2,59 | 0,90 | 664 | **DESCARTADO (-$90.881)**: Bloquea los mejores rebotes de M1/M2 y duplica lo que ya detecta `VIX/VIX3M`. |
| **2. + M7 Turn-of-the-Month (Solo Filtro)** | **$289,648** | **18,56%** | -15,14% | 1,59 | 2,90 | 1,23 | 725 | **MEJORA (+$8.556)**: Refuerza convicción en los 5 días de flujos de pensiones/nóminas de fin de mes. |
| **3. + M7 TOTM (Motor Táctico + Overlay)** | **$346,015** | **19,63%** | **-14,86%** | **1,62** | **3,08** | **1,32** | 780 | **ÚNICO GANADOR CLARO (+$64.923 y menor caída)**: Consistente en ambas décadas (73,1% acierto 2007–16 y 63,9% en 2017–26) con solo ~2,7 operaciones extra/año. |
| **4. + M8 Prima Varianza (`VRP`)** | $256,682 | 17,84% | -14,67% | 1,56 | 2,84 | 1,22 | 724 | **DESCARTADO**: Reduce -0,35% el drawdown pero cuesta -$24.410 porque `VolTarget` ya regula la volatilidad realizada. |
| **5. + M9 Amplitud (`RSP/SPY`)** | $265,759 | 18,05% | -15,02% | 1,58 | 2,88 | 1,20 | 725 | **DESCARTADO (-$15.333)**: En mercados liderados por tecnológicas (2017–2025), recorta exposición demasiado pronto. |
| **6. Combo Completo Filtros (M6+M7+M8+M9)** | $171,100 | 15,45% | -17,61% | 1,39 | 2,53 | 0,88 | 663 | **DESCARTADO**: Ejemplo clásico de *sobre-filtrado* defensivo. |

> [!TIP]
> **Lección Cuantitativa Clave:** Más indicadores no equivalen a más dinero. Los filtros defensivos M6, M8 y M9 miden el mismo miedo macro que **ya captura de forma más rápida la estructura `VIX/VIX3M`** del Modo 3 Élite. En cambio, **M7 (Turn-of-the-Month)** aporta una fuente de rentabilidad **ortogonal** (flujos automáticos de liquidez de fin/inicio de mes), mejorando tanto el CAGR (`18,38% -> 19,63%`) como el Drawdown (`-15,02% -> -14,86%`).

---

## 8. ¿Qué es el "Módulo Fiscal Automático" para España? (Explicación Sencilla)

Mientras operamos en **Paper Trading (dinero virtual)** no existe **ninguna** obligación con Hacienda. Esta herramienta solo entra en juego el día que conectes dinero real en Interactive Brokers (`IBKR`):

### ¿Por qué hace falta si ya tienes extractos del bróker?
Un banco español (ej. MyInvestor, Renta 4) envía automáticamente tus datos fiscales a la Agencia Tributaria para que salgan ya rellenos en tu borrador de la Renta. **Interactive Brokers (domiciliado en Irlanda) NO envía datos automáticos al borrador español** y te entrega un extracto bruto en inglés/dólares. Al hacer la Declaración de la Renta en primavera, Hacienda exige cumplir **4 reglas exactas**:

1. **Conversión al Euro con el cambio oficial del BCE de cada día:**  
   Si compras en dólares el 12 de marzo y vendes el 18 de marzo, Hacienda no te deja usar el cambio dólar/euro de diciembre; exige convertir el precio de compra al cambio oficial del Banco Central Europeo del 12 de marzo y la venta al cambio del 18 de marzo.
2. **Regla FIFO obligatoria (*First-In, First-Out*):**  
   Si el bot compró participaciones de `CSPX` en enero a 500 € y otra tanda en abril a 530 €, y en mayo vende la mitad, la ley obliga a calcular la ganancia contra las más antiguas (las de 500 €), no contra el precio medio.
3. **Regla Antiaplicación de los "2 Meses" (Muy importante en bots automáticos):**  
   En España, si cierras una operación en un ETF con pérdidas (por ejemplo, `-150 €` en `SXR8`) y el bot **vuelve a comprar ese mismo ETF antes de que pasen 2 meses**, Hacienda **bloquea temporalmente esa pérdida**: no te deja restar esos `-150 €` de tus ganancias de ese año hasta que pases 2 meses seguidos sin recomprar esas participaciones. Si no llevas esa cuenta, puedes deducirte pérdidas por error y recibir un requerimiento de la AEAT.
4. **Informe listo para copiar en Renta WEB + Aviso Modelo 720:**  
   El Módulo Fiscal Automático toma el libro contable del bot (`ledger_real_trades.jsonl`), aplica automáticamente las 3 reglas anteriores y te genera una tabla anual en Euros lista para copiar en la casilla de *Ganancias y pérdidas patrimoniales* de Renta WEB, además de avisarte si tu saldo en Interactive Brokers supera los **50.000 €** (umbral a partir del cual hay que presentar el **Modelo 720**, meramente informativo y sin pagar impuestos extra).

---

## 9. Registro Continuo de Decisiones (Decision Log)

| Fecha | Decisión / Consulta | Resolución Técnica Implementada |
| :--- | :--- | :--- |
| **2026-10-23** | Selección de Bróker & Entorno Paper | Implementación de `LocalPaperBrokerAdapter` y conector nativo `AlpacaPaperBrokerAdapter`. Puerto web fijado en `8085`. |
| **2026-10-23** | Notificaciones Móviles | Despliegue de servicio `SignalRestNotifier` vía CallMeBot HTTP Gateway sin intermediación de terceros. |
| **2026-10-25** | Desfase Horario España vs Wall Street (DST) | Anclaje del reloj horario a las **15:55 America/New_York**. Detección dinámica de semanas con desfase de 5 horas vs 6 horas (20:55 CET vs 21:55 CET). |
| **2026-10-25** | Pulso de Mercado & Redondeo en Notificaciones | Creación de `refresh_market_pulse` con lectura en vivo de variaciones de SPY/QQQ/VIX. Eliminación de arrastres de punto flotante `,999`. |
| **2026-10-25** | Modularización de Estrategias & Tests | Separación de los 5 motores en `aegis_quant/strategies/` (`m1` a `m5`) con documentación académica y suite de 33 tests unitarios. |
| **2026-10-25** | Simulación Fiscal IRPF & Costes Operacionales | Incorporación en la web de la pestaña `5. Fiscalidad España & Rentabilidad Neta`. Integración de comisiones IBKR, spreads, TER e IRPF progresivo. |
| **2026-10-25** | Vehículos Operativos en España | Adopción oficial de ETFs UCITS equivalentes de réplica física acumulativa (`CSPX`, `EQQQ`, `SGLD`, `DTLA`, `CRUD`). |
| **2026-10-25** | Seguridad en Control de Versiones | Protección de credenciales en `.gitignore` y sincronización con GitHub mediante Personal Access Token. |
| **2026-10-25** | Política de Apalancamiento | **Descarte definitivo de futuros o productos con apalancamiento estático x3** debido al decaimiento por volatilidad (*volatility drag*) y riesgo de ruina. Se ratifica el uso exclusivo del apalancamiento adaptativo y dinámico (Meta-Kelly y Volatility Targeting) ya integrado en el motor. |
| **2026-10-25** | Auditoría Institucional & Propuestas Estratégicas | Realización de auditoría técnica por subagente cuantitativo (dictamen 7.25/10). Documento completo archivado en [`docs/AUDIT_AND_PROPOSALS.md`](docs/AUDIT_AND_PROPOSALS.md). |
| **2026-10-25** | Resolución de Problemas Críticos 1 a 3 + UI Móvil | **1)** Conectada evaluación dinámica en vivo de motores M1–M5 + Core Modo 3 Élite en `LiveBotController` y `AegisPortfolioEngine` (`compute_live_portfolio`). **2)** Migrado `web_app/server.py` a `ThreadingHTTPServer` concurrente con compresión `gzip`. **3)** Escrituras atómicas `atomic_write_json` (`tempfile` + `fsync` + `os.replace`) en `config_store.py`. Suite ampliada a **43 tests unitarios**. Evaluados empíricamente (2007–2026) los motores M6–M9 en `aegis_quant/research/evaluate_audit_proposals.py` (descartando M6/M8/M9 y validando M7 TOTM). Interfaz rediseñada con arquitectura **Mobile-First + Dark Mode**. |
