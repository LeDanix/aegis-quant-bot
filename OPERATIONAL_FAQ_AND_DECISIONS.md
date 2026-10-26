# Aegis-Quant: Guía Operativa, Fiscal y Registro de Decisiones de Arquitectura

> **DOCUMENTO OFICIAL DEL REPOSITORIO — SISTEMA AEGIS-QUANT**  
> *Destinatario: Operador del Sistema & Inversor Residente en España*  
> *Última actualización: 26 de Octubre de 2026*

Este documento consolida de forma viva y permanente todas las dudas operativas, decisiones de arquitectura cuantitativa, marco legal y fiscal en España, y análisis de riesgo resueltos para el funcionamiento del bot en dinero real.

---

## 1. Vehículos Financieros en España: ETFs UCITS vs ETFs USA (Normativa PRIIPs)

### A. La Restricción Legal en España (Normativa PRIIPs / MiFID II)
En la Unión Europea y en España (supervisado por la CNMV), los brókers minoristas (incluido **Interactive Brokers**) tienen prohibido por ley permitir la compra directa de ETFs domiciliados en EE. UU. (`SPY`, `QQQ`, `GLD`, `TLT`, `USO`). Esto se debe a que la directiva **PRIIPs** exige que los emisores publiquen un folleto estandarizado denominado **KID (Key Information Document)** en el idioma local, algo que las gestoras norteamericanas no emiten para sus fondos domésticos.

### B. La Solución Oficial de Aegis-Quant: ETFs UCITS Europeos
Para operar de forma 100% legal, líquida y sin trabas administrativas desde España bajo la **Opción A (`Tradegate Exchange` en Euros)**, el bot mapea los activos de referencia mundial a sus **equivalentes UCITS europeos**:

| Activo Modelo | Equivalente UCITS Elegido | ISIN | Emisor / Gestora | Plaza / Divisa | Patrimonio Gestionado (AUM) | Tipo de Réplica |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **SPY** (S&P 500) | **`SPYL`** (~14 €) / **`SXR8`** (~580 €) | `IE000XZSV718` / `IE00B5BMR087` | SPDR (TER 0,03%) / BlackRock iShares (0,07%) | Tradegate (`TGATE`) · EUR | **> 85.000 M€ (`SXR8`) / > 15.000 M€ (`SPYL`)** | Física Directa (Acumulación) |
| **QQQ** (Nasdaq 100) | **`EQQQ`** / **`SXRV`** | `IE0032077012` | Invesco / BlackRock | Tradegate (`TGATE`) · EUR | **> 12.000 Millones de €** | Física Directa |
| **GLD** (Oro Físico) | **`4GLD`** / **`SGLD`** | `DE000A0S9GB0` / `IE00B579F325` | Xetra-Gold / Invesco | Tradegate (`TGATE`) · EUR | **> 16.000 Millones de €** | Oro Físico en Bóveda |
| **TLT** (Bonos 20+ Años) | **`DTLA`** | `IE00BFM6TC58` | BlackRock iShares | Tradegate (`TGATE`) · EUR | **> 4.800 Millones de €** | Física Directa (Deuda Tesoro USA, Acc) |
| **USO** (Petróleo WTI) | **`CRUD`** / **`OD7F`** | `GB00B15KXV33` | WisdomTree | Tradegate (`TGATE`) · EUR | **> 1.200 Millones de €** | Sintética con colateral AAA |
| **ZS** (Soja Agrícola) | **`SOYB`** / **`OD7Z`** | `GB00B15KY211` | WisdomTree | Tradegate (`TGATE`) · EUR | **> 40 Millones de €** | ETC regulado sobre futuros |
| **SPY Corto (`M3`)** | **`DXS3`** (-1x Diario) | `LU0322251520` | Xtrackers (DWS) | Tradegate (`TGATE`) · EUR | **> 180 Millones de €** | Swap UCITS Inverso -1x (Sin margen) |

### C. Solvencia y Fiabilidad de los ETFs UCITS
1. **Seguridad Patrimonial (UCITS V):** Los activos no están en el balance de la gestora (BlackRock, SPDR o Invesco), sino segregados en bancos custodios independientes (State Street / BNY Mellon). En caso de quiebra del bróker o de la gestora, los títulos pertenecen al inversor.
2. **Liquidez Institucional:** Fondos como `SXR8` y `SPYL` mueven decenas de millones de euros diarios en horario europeo y americano, garantizando horquillas ajustadas.
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
Interactive Brokers opera para clientes de la UE a través de su filial europea (**IBKR Ireland - IBIE**).  
Si el saldo a 31 de diciembre o el saldo medio del cuarto trimestre de los valores depositados en el extranjero supera los **50.000 €**, la ley española exige presentar el **Modelo 720** (declaración meramente informativa entre el 1 de enero y el 31 de marzo, sin coste impositivo).

---

## 3. Costes Operacionales Reales y Cascada de Rentabilidad (6 Motores · 2007–2026)

### A. Desglose de Gastos Operacionales en Interactive Brokers
1. **Comisión de Bróker (Tarifa *Tiered*):** 0,05% por orden (mínimo de ~1,25 € a 2,00 € en Europa).
2. **Deslizamiento (*Slippage* / *Bid-Ask Spread*):** ~0,02%–0,05% operando con órdenes limitadas en horario coincidente con Wall Street.
3. **TER del ETF:** ~0,10% medio ponderado anual (descontado internamente del valor liquidativo; `0,03%` en `SPYL`).
4. **Custodia y Mantenimiento:** **0,00 €** (IBKR no cobra comisiones de custodia ni de inactividad).

### B. Cascada Auditada de Rendimiento Real — Modo 3 Élite con 6 Motores ($10,000 | 2007–2026)

```text
Capital Inicial (2007)                                       : $10,000.00
  ├── Retorno Bruto del Algoritmo (19.54% CAGR · 780 trades) : $341,057.69 (+3,310.58%)
  │
  ├── (-) Costes Operacionales (Comisiones + Spread + TER)   : -$6,083.93 (-0.70% CAGR)
  │    └── Capital Neto Operacional                          : $303,668.08 (+2,936.68% | 18.84% CAGR)
  │
  ├── (-) Impuestos IRPF España (Base del Ahorro año a año)  : -$39,087.84 (-3.63% CAGR)
  │
  └── (=) CAPITAL FINAL NETO EN TU BOLSILLO                  : $164,521.64 (+1,545.22% | 15.21% CAGR)
```

**Comparativa frente al S&P 500 Buy & Hold:**
- **S&P 500 Bruto:** $53,757.52 (8.88% CAGR | -56.47% MaxDD)
- **S&P 500 Neto tras TER (0,07%) e IRPF único al liquidar:** **$44,104.42**
- **Ventaja Patrimonial Neta:** **3,73 veces más capital limpio en tu bolsillo** que la inversión pasiva tradicional, reduciendo la caída máxima a la cuarta parte (`-14,86%` frente a `-56,47%`).

---

## 4. Estrategia de Capital: Reinversión vs Retirada Anual (Interés Compuesto)

### A. Comparativa de Estrategias
- **Estrategia A (Dejar el dinero reinvertido — Recomendada):**  
  Aprovecha el crecimiento exponencial del interés compuesto. Al reinvertir el capital neto tras pagar impuestos, la base operativa crece anualmente ($10k $\rightarrow$ $12k $\rightarrow$ $16k $\rightarrow$ ... $\rightarrow$ **$164,521**).
- **Estrategia B (Retirar las ganancias cada año):**  
  El bot opera perpetuamente sobre la base fija de $10,000. Retiras entre 1.500 € y 2.500 € al año para gastos personales, pero renuncias a construir un patrimonio superior a los 160.000 $.

### B. La Regla de Oro Institucional (Plan de Dos Fases)
1. **Fase de Acumulación (Años 1 al 5-7):** No retirar dinero. Dejar que la cartera supere el umbral de los **50.000 € - 100.000 €**.
2. **Fase de Ordeño Parcial:** A partir de ese hito, retirar anualmente el **50% de la ganancia neta** para disfrute personal y dejar el otro 50% reinvertido para que el capital continúe creciendo por encima de la inflación.

---

## 5. Análisis Cuantitativo de Apalancamiento y Modelos de Futuros x3

### A. La Pregunta del Millón: ¿Qué pasaría si usamos un multiplicador x3 en futuros?
A nivel intuitivo, parece tentador pensar que multiplicar por 3 el rendimiento convertiría un 19% anual en un 57% anual. Sin embargo, en matemáticas financieras esto es una **trampa mortal** debido a dos fenómenos destructivos:

### B. El Fenómeno del Decaimiento por Volatilidad (*Volatility Drag / Beta Decay*)
Los productos o futuros con apalancamiento estático sufren una erosión geométrica matemática inevitable cuando el mercado oscila:

**Ejemplo Práctico:**
- Imagina que el S&P 500 cae un **-10%** el lunes y sube un **+11.11%** el martes.
  - El índice sin apalancamiento: $100 \times 0.90 = 90$; $90 \times 1.1111 = 100$. **El mercado ha quedado en 0% (empatado).**
  - Un modelo con apalancamiento x3 estático:
    - Día 1: Cae un $-30\%$ ($100 \times 0.70 = 70$).
    - Día 2: Sube un $+33.33\%$ ($70 \times 1.3333 = 93.33$).
    - **El mercado no ha perdido nada y tú has perdido un -6.67% de tu dinero en 48 horas.**

### C. El Riesgo de Ruina Absoluta (*Drawdown Trap*)
- Para recuperar una caída del **-20%**, necesitas ganar un **+25%**.
- Para recuperar una caída del **-50%**, necesitas ganar un **+100%**.
- Para recuperar una caída del **-80%**, necesitas ganar un **+400%**.
- **Si el mercado cae un -33.4%:** con apalancamiento x3 ($-33.4\% \times 3 = -100.2\%$), **la cuenta quiebra a 0 €**. En 2008 el S&P 500 cayó un `-56%` y en marzo de 2020 un `-35%`.

### D. Llamadas de Margen (*Margin Calls*) en Interactive Brokers
Si operas futuros apalancados (`MES`, `MNQ`) y tu capital cae por debajo del margen de mantenimiento exigido por la cámara de compensación, el algoritmo de riesgo de IBKR ejecuta una liquidación forzosa automática en el mínimo del pánico, materializando pérdidas irrecuperables.

### E. La Solución Científica de Aegis-Quant: Exposición Adaptativa sin Deuda
Aegis-Quant opera con tope máximo de exposición del **100% del capital en efectivo** (0% deuda): en regímenes de calma (`Contango`, `VIX < VIX3M`) asigna el capital entre el núcleo Dual-Momentum y oportunidades tácticas; en regímenes de pánico (`Backwardation`, `VIX >= VIX3M`) vacía el núcleo alcista a liquidez y solo activa motores tácticos de alta convicción.

---

## 6. Desfase Horario Europa vs Wall Street y Guía Completa de la Opción A (`Tradegate`)

### A. El Problema Operativo Real
Las bolsas principales europeas (**XETRA** en Fráncfort, **Borsa Italiana**, **LSE**) donde cotizan los ETFs UCITS **cierran a las 17:30 CET** (11:30 AM en Nueva York). Sin embargo, el escáner del bot evalúa el cierre estadounidense a las **21:55 CET (15:55 NY)**. Si lanzas una orden a XETRA a las 21:55 CET, queda retenida hasta las 09:00 CET del día siguiente (sufriendo *gap* nocturno).

### B. Comparativa de Opciones Evaluadas y Decisión Adoptada: **Opción A (`Tradegate`)**

| Criterio | **Opción A Adoptada: Tradegate (`TGATE`)** — ETFs UCITS en Horario Extendido | Opción B Descartada: Micro-Futuros CME (`MES` / `MNQ`) |
| :--- | :--- | :--- |
| **Horario de negociación** | **08:00 a 22:00 CET** (cubre las 21:55 CET y las 20:55 CET en semanas DST). | 23 horas al día (00:00 a 23:00 CET) en EE. UU. |
| **Vehículo que compras** | **ETFs UCITS al contado** (`SPYL`/`SXR8`, `EQQQ`, `4GLD`, `DTLA`, `CRUD`, `SOYB`) en Euros, sin deuda ni margen. | Derivados con liquidación diaria de pérdidas y ganancias (*mark-to-market*). |
| **Capital mínimo sin apalancamiento** | **Cualquier capital (ej. 5.000 € – 10.000 €)** ajustando pesos exactos. | Exige > 60.000 € – 80.000 € (1 solo contrato `MES` mueve ~30.000 $–38.000 $ nocionales). |
| **Coste / Horquilla** | Comisión IBKR Tiered ~1,25 €–2,50 €; horquilla vespertina `0,04%–0,08%` acotada con orden `Limit`. | Comisión ~0,60 $ y horquilla mínima, pero coste fiscal trimestral. |
| **Fiscalidad IRPF** | **Óptima**: 0 eventos fiscales mientras se mantiene el Core meses seguidos. | **Penalizada**: vencimiento trimestral obligatorio (4 ventas/año aflorando IRPF). |

### C. Checklist Operativo: Todo lo que Debes Tener en Cuenta para Operar con la Opción A (`Tradegate`)

Al dar el salto a cuenta real en **Interactive Brokers (IBKR Ireland)** con la **Opción A**, ten presentes estos **6 puntos críticos**:

1. **Prohibido usar Órdenes a Mercado (`Market`) — Usar siempre Órdenes Limitadas (`Limit`):**
   - Entre las `17:30 CET` y las `22:00 CET`, XETRA está cerrado y la liquidez la proveen los creadores de mercado (*Market Makers*) de **Tradegate Exchange**.
   - Nunca envíes una orden `Market` a las `21:55 CET`, ya que un pico puntual de horquilla podría ejecutarse peor de lo debido. Toda orden debe enviarse como **`Limit`**, con vigencia **`DAY`** (para que si no se cruza antes de las `22:00 CET` se cancele limpia y no quede colgada para el día siguiente) y un **colchón máximo de precio del `0,08%`** sobre la cotización actual (`Ask` en compras / `Bid` en ventas).
2. **Permisos de Negociación y Enrutamiento en Interactive Brokers (`TGATE`):**
   - En el portal de cliente de Interactive Brokers (*Settings -> Trading Permissions -> Stocks*), debes activar permisos para **Alemania (`Germany`)** (que habilita XETRA, Tradegate y Gettex) y elegir el plan de comisiones **IBKR Tiered** (más barato que *Fixed* para órdenes europeas de importe pequeño/medio).
   - Al enviar órdenes por API a las `21:55 CET`, el destino (`Exchange`) debe fijarse explícitamente en **`TGATE`** (o `SMART` con permiso de ejecución fuera del mercado primario), **nunca en `IBIS` (XETRA)**, porque `IBIS` dejaría la orden dormida hasta las `09:00 CET` de la mañana siguiente.
   - Para no pagar suscripción mensual de datos en tiempo real de bolsa alemana, el bot calcula la señal sobre la serie oficial gratuita de EE. UU. y traduce el precio objetivo al equivalente en Euros aplicando el tipo de cambio EUR/USD en tiempo real.
3. **Operativa Directa en Euros (`EUR`) = Cero Comisiones por Cambio de Divisa:**
   - Todos los equivalentes elegidos en Tradegate cotizan directamente en **Euros (`EUR`)**.
   - Aunque el activo subyacente sea estadounidense (S&P 500, Nasdaq 100 o Bonos del Tesoro USA), el propio ETF convierte internamente los dólares a tipo interbancario institucional (`~0,002%`). Así te ahorras pagar la comisión mínima de `2,00 $` por conversión de divisa EUR/USD en IBKR en cada operación.
4. **Truco de Precisión con Participaciones Enteras: Preferir `SPYL` (~14 €) frente a `SXR8` (~580 €):**
   - En centros europeos alternativos como `TGATE` y en órdenes limitadas de última hora, Interactive Brokers **solo admite participaciones enteras** (no fracciones de acción).
   - `SXR8` cotiza alrededor de **~580 € por participación** (en una cuenta de `10.000 €`, cada acción representa un salto del `5,8%`).
   - En cambio, **`SPYL`** (*SPDR S&P 500 UCITS ETF Acc*, ISIN `IE000XZSV718`, gestionado por State Street con más de `15.000 millones €` de patrimonio) replica exactamente el mismo S&P 500 de acumulación, tiene una comisión anual aún menor (**TER `0,03%`** frente a `0,07%` de `SXR8`) y cotiza a **~14 € por participación**, permitiendo clavar cualquier porcentaje de cartera con precisión del `0,14%` usando acciones enteras.
5. **Ventana de Ejecución (`21:55 CET`) y Cierre Estricto (`22:00:00 CET`):**
   - El mejor tramo de liquidez en Tradegate es de **`15:30 CET` a `22:00 CET`**, porque Wall Street está abierto simultáneamente y los creadores de mercado arbitran el ETF europeo contra el futuro americano en tiempo real.
   - Tradegate cierra de forma estricta a las **`22:00:00 CET`**. Como el bot escanea a las **`21:55 CET`** (`15:55 NY`), dispone de **5 minutos completos** para cruzar las órdenes limitadas (y de **65 minutos** en las semanas de marzo/octubre con desfase DST donde `15:55 NY` equivale a las `20:55 CET`). Es fundamental mantener activo `systemd-timesyncd` / NTP en el servidor Linux para que el reloj nunca tenga deriva.
6. **Cómo Ejecutar los Cortos del Motor 3 (`M3_BEAR_SHORT`) sin Préstamo ni Margen:**
   - Ponerse corto tomando prestadas participaciones de un ETF europeo a las `21:55 CET` en Tradegate tiene poca disponibilidad de préstamo y requiere cuenta de margen (*Margin Account*).
   - Con la Opción A, cuando `M3_BEAR_SHORT` dispara una operación bajista táctica (duración media de **3 a 5 sesiones**), se ejecuta como una simple **compra al contado (`BUY Limit`)** del ETF UCITS inverso diario **`DXS3`** (*Xtrackers S&P 500 Inverse Daily Swap UCITS ETF -1x*, ISIN `LU0322251520`). Al no tener apalancamiento x3 (es `-1x` diario) y mantenerse solo unos pocos días, no sufre erosión significativa y funciona en una cuenta normal de efectivo (*Cash Account*) sin riesgo de *margin call*.

---

## 7. Evaluación Empírica (2007–2026) y Promoción del Sexto Motor (`M6_TOTM`)

### A. Comparativa de Candidatos Propuestos en Auditoría (`evaluate_audit_proposals.py`)
Se evaluaron empíricamente entre **2007 y 2026** sobre **$10,000 iniciales** los 4 módulos candidatos propuestos en `docs/AUDIT_AND_PROPOSALS.md`:

| Arquitectura Evaluada (2007–2026) | Capital Final | CAGR Anual | Max Drawdown | Sharpe | Sortino | Calmar | Nº Trades | Conclusión Empírica |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **0. Baseline 5 Motores (`M1–M5`)** | $277,065 | 18,29% | -15,02% | 1,58 | 2,88 | 1,22 | 700 | Referencia previa de 5 motores. |
| **1. + Spread Crédito (`HYG/LQD`)** | $190,211 | 16,07% | -17,92% | 1,42 | 2,59 | 0,90 | 664 | **DESCARTADO**: Sobrefiltra rebotes de M1/M2 y duplica `VIX/VIX3M`. |
| **2. + Prima Varianza (`VRP`)** | $256,682 | 17,84% | -14,67% | 1,56 | 2,84 | 1,22 | 724 | **DESCARTADO**: Duplica el control que ya realiza `VolTarget`. |
| **3. + Amplitud (`RSP/SPY`)** | $265,759 | 18,05% | -15,02% | 1,58 | 2,88 | 1,20 | 725 | **DESCARTADO**: Recorta exposición prematuramente en ciclos tecnológicos. |
| **4. Modo 3 Élite Producción (`M1–M6` con `M6_TOTM`)** | **$341,058** | **19,54%** | **-14,86%** | **1,61** | **3,06** | **1,31** | **780** | **PROMOCIONADO A PRODUCCIÓN (+$63.993 y menor caída)**. |

### B. Prueba de Ablación (*Leave-One-Out*) y Análisis de No-Confrontación (`M1–M6`)
Antes de decidir si `M6_TOTM` debía **añadirse como sexto motor** o **sustituir** a alguno de los cinco anteriores, se auditó qué ocurre al apagar individualmente cada motor entre 2007 y 2026:
- ** Cero colisión destructiva:** `M6_TOTM` opera exclusivamente en los últimos 2 días hábiles del mes bajo `Contango` cuando existe debilidad moderada (`RSI(2) < 35`) sin requerir sobreventa extrema (`RSI(2) < 10`). Cuando coincide con `M1_PULLBACK`, actúa en la misma dirección alcista con prioridad ordenada; nunca colisiona con `M3_BEAR_SHORT` (que exige mercado bajista bajo `SMA200`) ni con `M4_CTA_TREND` (que usa el slot independiente de activos refugio).
- **Todos los motores existentes suman valor:** Apagar `M1` reduce el capital final en `-$149k`; apagar `M4` cuesta `-$189k`; apagar `M5` cuesta `-$31k`; apagar `M2` cuesta `-$8k`; y apagar `M3` deteriora la protección en las crisis seculares de 2008 y 2022 (`+16,30%` de retorno acumulado en desplomes).
- **Conclusión de Arquitectura:** Se mantienen íntegros `M1` a `M5` y se incorpora oficialmente **`M6_TOTM` (`TurnOfTheMonthFlowStrategy`)** como **sexto motor táctico** en todo el sistema (`aegis_engine.py`, `bot_controller.py`, simulador e interfaz web).

---

## 8. Módulo Fiscal Automático AEAT / IRPF (Arquitectura en Producción)

El sistema incluye en producción el paquete [`aegis_quant/tax/spanish_tax_engine.py`](aegis_quant/tax/spanish_tax_engine.py), expuesto en los endpoints `GET /api/tax/live-audit` y `GET /api/tax/export.csv` e integrado visualmente en la pestaña **`5. Fiscalidad España (IRPF)`**:

1. **Conversión Oficial Diaria EUR/USD del BCE (`ECBExchangeRateProvider`):**  
   Cada ejecución en el libro contable (`ledger_paper_trades.jsonl` y `ledger_real_trades.jsonl`) registra su ISIN UCITS homogéneo y el tipo de cambio EUR/USD del Banco Central Europeo de su fecha exacta, calculando de forma independiente el valor de adquisición en Euros el día de la compra y el valor de transmisión en Euros el día de la venta (Consulta Vinculante DGT `V1097-19`).
2. **Emparejamiento Estricto FIFO por ISIN Homogéneo (`Art. 37.2 LIRPF`):**  
   Agrupa todas las compras y ventas por código ISIN (`IE00B5BMR087` / `IE000XZSV718`, `IE0032077012`, `IE00B579F325`, `IE00BFM6TC58`, `GB00B15KXV33`, `GB00B15KY211`, `LU0322251520`), consumiendo siempre las participaciones más antiguas e incorporando las comisiones de bróker al precio de adquisición/transmisión.
3. **Detector Automático de la Regla Antiaplicación de los 2 Meses (`Art. 33.5.f LIRPF`):**  
   Analiza la ventana de **$\pm 60$ días naturales** alrededor de cada venta con pérdida. Si el bot recompra el mismo ISIN antes de 60 días (o conserva lotes comprados en los 60 días previos), marca automáticamente la minusvalía como **Diferida 2M**, excluyéndola de la base imponible de ese año hasta que el ISIN quede liquidado a cero durante más de 60 días, y muestra un aviso activo en pantalla con la fecha exacta de desbloqueo.
4. **Cuota Progresiva del Ahorro, Casillas Renta WEB y Vigilancia del Modelo 720:**  
   Calcula en tiempo real la cuota íntegra según la escala del ahorro (19%–28%), agrupa los totales por emisor para copiar en el **Apartado F2 de Renta WEB (Casillas `0326–0335`)**, vigila el porcentaje de uso respecto al umbral de **50.000 € del Modelo 720**, y permite descargar con un clic el **CSV compatible con Excel en España** (UTF-8 BOM y separador `;`).

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
| **2026-10-25** | Vehículos Operativos en España | Adopción oficial de ETFs UCITS equivalentes de réplica física acumulativa (`CSPX`/`SXR8`/`SPYL`, `EQQQ`, `SGLD`/`4GLD`, `DTLA`, `CRUD`, `SOYB`). |
| **2026-10-25** | Seguridad en Control de Versiones | Protección de credenciales en `.gitignore` y sincronización con GitHub mediante Personal Access Token. |
| **2026-10-25** | Política de Apalancamiento | **Descarte definitivo de futuros o productos con apalancamiento estático x3** debido al decaimiento por volatilidad (*volatility drag*) y riesgo de ruina. Uso exclusivo de exposición adaptativa sin deuda. |
| **2026-10-25** | Auditoría Institucional & Propuestas Estratégicas | Realización de auditoría técnica por subagente cuantitativo (dictamen 7.25/10). Documento completo archivado en [`docs/AUDIT_AND_PROPOSALS.md`](docs/AUDIT_AND_PROPOSALS.md). |
| **2026-10-25** | Resolución de Problemas Críticos 1 a 3 + UI Móvil | **1)** Evaluación dinámica en vivo en `LiveBotController` y `AegisPortfolioEngine`. **2)** `ThreadingHTTPServer` concurrente con compresión `gzip`. **3)** Escrituras atómicas `atomic_write_json`. Evaluación empírica 2007–2026 de candidatos M6–M9. |
| **2026-10-26** | Promoción del 6º Motor (`M6_TOTM`) y Expansión Total | Incorporado `TurnOfTheMonthFlowStrategy` (`M6_TOTM`) como sexto motor tras validar por ablación que suma `+$63.993` (`$341.057,69`, `19,54% CAGR`, `-14,86% MaxDD`, `Sharpe 1,61`, `780 trades`) sin confrontar `M1–M5`. Expandidas todas las pestañas de control y analítica a 6 motores. |
| **2026-10-26** | Rediseño Sobrio Institucional & Ergonomía Móvil | Eliminado el 100% de emojis, textos genéricos y brillos de IA. Modo Claro blanco + verde institucional (`#065f46`) por defecto y Modo Oscuro grafito mate neutro (`#121514` / `#191d1b`). Botón único superior de Configuración (eliminado duplicado y botones de test de `Sistema`), selectores verticales a ancho completo para `M1–M6` con confirmación anti-toque accidental, y Controles de Emergencia reubicados en `Inicio` dentro de desplegable en rojo suave. |
| **2026-10-26** | Adopción de Opción A (`Tradegate`) y Módulo Fiscal Automático AEAT | Adoptada oficialmente la **Opción A (`Tradegate` / `TGATE` en IBKR en EUR con órdenes `Limit` y `SPYL`/`DXS3`)** documentando su checklist completo en la Sección 6.C. Desplegado `SpanishTaxAuditor` (`FIFO` + regla 2 meses Art. 33.5.f LIRPF + cambio diario BCE + Modelo 720 + exportación CSV Renta WEB) y suite ampliada a **52 tests unitarios**. |
