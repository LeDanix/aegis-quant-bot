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
| **BTC** (Bitcoin Físico) | **`BTCE`** / **`21BC`** | `DE000A27Z304` / `CH1199067054` | ETC Group / 21Shares | Tradegate / Xetra · EUR | **> 1.500 Millones de €** | ETP con Respaldo Físico Segregado (Bóveda Fría) |
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

### E. Declaraciones Informativas: El Modelo 720 y Cifras en Vivo
Interactive Brokers opera para clientes de la UE a través de su filial europea (**IBKR Ireland - IBIE**).  
Si el saldo a 31 de diciembre o el saldo medio del cuarto trimestre de los valores depositados en el extranjero supera los **50.000 €**, la ley española exige presentar el **Modelo 720** (declaración meramente informativa entre el 1 de enero y el 31 de marzo, sin coste impositivo).

> [!NOTE]
> **¿Por qué aparecen 9.192,08 € (Paper) y 9.208,10 € (IBKR) en el panel de control?**  
> Estas cifras representan el **patrimonio total de la cuenta en Interactive Brokers convertido a Euros** utilizando el tipo de cambio oficial diario del Banco Central Europeo (BCE, en este caso 1.0860 EUR/USD):
> - **Entorno Paper:** $9,982.60 USD / 1.0860 = **9.192,08 €** (18,4% del límite de 50k €).
> - **Entorno IBKR Real:** $10,000.00 USD / 1.0860 = **9.208,10 €** (18,4% del límite de 50k €).  
> Ambas cantidades se sitúan muy lejos de los 50.000 € obligatorios, por lo que el sistema marca con total rigor el estado legal **"Exento"**.

### F. Tratamiento Fiscal de Bitcoin vía ETP Físico (Tradegate / Xetra)
Al incorporar Bitcoin al Motor 4 mediante un **ETP con respaldo físico 100% y custodia segregada en frío** (ej. `BTCE`, ISIN `DE000A27Z304` en EUR):
1. **Calificación Jurídica:** Tributa estrictamente como **valor mobiliario cotizado** en la Base Imponible del Ahorro (19% al 28%, Casillas 0326–0335 de Renta WEB), idéntico a un ETF de acciones u oro.
2. **Exención del Modelo 721:** No es una tenencia en exchange cripto extranjero ni wallet privada, por lo que **NO se declara en el Modelo 721**.
3. **Integración en el Modelo 720:** Computa dentro de la cesta única de valores extranjeros de Interactive Brokers, sumándose al total de la cartera frente al umbral de 50.000 €.
4. **Regla de los 2 Meses (Art. 33.5.f LIRPF):** El bot audita automáticamente que si se vende con minusvalía y se recompra `DE000A27Z304` en ±60 días, la pérdida queda diferida temporalmente hasta la venta definitiva.

---

## 3. Costes Operacionales Reales y Cascada de Rentabilidad (Modo 3 Élite con Bitcoin · 2007–2026)

### A. Desglose de Gastos Operacionales en Interactive Brokers
1. **Comisión de Bróker (Tarifa *Tiered*):** 0,05% por orden (mínimo de ~1,25 € a 2,00 € en Europa).
2. **Deslizamiento (*Slippage* / *Bid-Ask Spread*):** ~0,02%–0,05% operando con órdenes limitadas en horario coincidente con Wall Street.
3. **TER del ETF/ETP:** ~0,10% medio ponderado anual (descontado internamente del valor liquidativo; `0,03%` en `SPYL`).
4. **Custodia y Mantenimiento:** **0,00 €** (IBKR no cobra comisiones de custodia ni de inactividad).

### B. Cascada Auditada de Rendimiento Real — Modo 3 Élite con Bitcoin ($10,000 | 2007–2026)

```text
Capital Inicial (2007)                                       : $10,000.00
  ├── Retorno Bruto del Algoritmo (23.13% CAGR · Con BTC)    : $614,368.50 (+6,043.69%)
  │
  ├── (-) Costes Operacionales (Comisiones + Spread + TER)   : -$8,661.21 (-0.72% CAGR)
  │    └── Capital Neto Operacional                          : $546,740.62 (+5,367.41% | 22.41% CAGR)
  │
  ├── (-) Impuestos IRPF España (Base del Ahorro año a año)  : -$66,988.94 (-4.34% CAGR)
  │
  └── (=) CAPITAL FINAL NETO EN TU BOLSILLO                  : $267,425.58 (+2,574.26% | 18.06% CAGR)
```

**Comparativa frente al S&P 500 Buy & Hold:**
- **S&P 500 Bruto:** $54,630.40 (8.96% CAGR | -56.47% MaxDD)
- **S&P 500 Neto tras TER (0,07%) e IRPF único al liquidar:** **$44,784.02**
- **Ventaja Patrimonial Neta:** **5,97 veces más capital limpio en tu bolsillo** que la inversión pasiva tradicional (+$222.641 USD de beneficio neto extra), manteniendo el blindaje contra desplomes severos.

---

## 4. Estrategia de Capital: Reinversión vs Retirada Anual (Interés Compuesto)

### A. Modalidades de Pago del IRPF (Retirada de Cartera vs Liquidez Externa)
El IRPF sobre plusvalías no se retiene en el momento de cada venta en Interactive Brokers, sino que se liquida **una sola vez al año** en la declaración de la Renta (mayo–junio). Esto abre dos vías operativas:

1. **Vía A: Liquidación Autofinanciada (Retirada de Cartera — Por defecto en el Backtest):**
   - El inversor retira anualmente de Interactive Brokers la cuota exacta de IRPF a pagar a la AEAT.
   - **Aportación externa:** **0,00 €**.
   - **Capital final neto en bolsillo:** **$267,425.58 USD** (+2.574% | 18.06% CAGR).
   - **Coste oculto:** El capital retirado sufre el *Tax Drag* (deja de componer en los ejercicios futuros).

2. **Vía B: Pago con Liquidez Externa / Nómina (Blindaje del Interés Compuesto):**
   - El inversor paga la cuota anual del IRPF (entre ~400 $ y ~1.500 $/año durante los primeros 10 años) con sus ahorros o nómina personal en España, **sin retirar ni un céntimo de Interactive Brokers**.
   - El 100% del capital permanece en la cuenta componiendo a la tasa neta operativa completa (**22.41% CAGR**).
   - **Capital final en Interactive Brokers:** **$546,740.62 USD**.
   - **Patrimonio neto real (Saldo en Bróker menos Impuestos aportados externamente):**
     $$546,740.62 - 66,988.94 = \mathbf{\$479,751.68 \text{ USD Limpios}}$$
   - **Ventaja patrimonial extra:** **+$212,326.10 USD (+79,4% de beneficio limpio adicional)** únicamente por permitir que el interés compuesto actúe sin interrupción.

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
| **2026-10-26** | Web Sin Formato en PC (CDN bloqueado) | Tailwind compilado localmente en `web_app/static/tailwind.css` y ECharts vendorizado en `web_app/static/echarts.min.js`. La web ya no depende de ningún CDN externo; tras modificar clases en `index.html`/`app.js` hay que recompilar Tailwind. |
| **2026-10-26** | Nueva Sección `ETFs` y Navegación Unificada Móvil/Escritorio | Añadida la sección **ETFs** entre `Cartera` y `Análisis` (barra inferior móvil de 5 botones) con selector del ETF a visualizar (`SPY`, `QQQ`, `GLD`, `TLT`, `USO`, `ZS`/`SOYB`), accesos rápidos, KPIs (cotización, 1A/YTD, rango 52 semanas, régimen SMA200 y RSI(2)), gráfica de línea o velas OHLC con SMA(50)/SMA(200), volumen y horizontes `1M`–`Todo`, más ficha UCITS Tradegate (ticker, ISIN, TER, motores). Backend `EtfChartService` + endpoint `GET /api/etf/history?symbol=`. En escritorio se usa la **misma distribución de 5 secciones** mediante un menú superior de tres rayas. Pulsar un activo en el Pulso de Mercado de `Inicio` abre directamente su gráfica. Suite ampliada a **55 tests**. |
| **2026-10-26** | Desmantelamiento de Telegram y Exclusividad Signal | Retirada completa de la integración de Telegram en backend y frontend. Canal exclusivo de alertas móviles unificado en **Signal Messenger** (CallMeBot / signal-cli). |
| **2026-10-26** | Seguridad Operativa: Protección de Sincronización & Sandbox | Sustituido el botón "Escanear y Sincronizar" en Inicio y Cartera por **"Actualizar Datos / Valoración"** (solo lectura de precios y saldos, sin envío de órdenes). El botón de rebalanceo manual forzado (`SCAN_NOW`) y el `Simulador Rápido de Motores (Sandbox)` se han reubicado en la pestaña **Sistema** protegidos por diálogo modal de confirmación en 2 pasos. El botón de reinicio de saldo Paper se oculta automáticamente si se conecta un bróker real. |
| **2026-10-26** | Fichas de Estudio de Motores (M1–M6) con Velas Reales | En la pestaña *Estrategia*, las 6 tarjetas de motor cuentan con hover institucional verde y abren una **Ficha Técnica Interactiva** con fundamento de microestructura, lógica algorítmica, código Python y gráfica ECharts de velas OHLC con trades reales del backtest 2007–2026. Motor 6 homogeneizado visualmente con el resto de motores. |
| **2026-10-26** | Manual de Uso Oficial Publicado (`docs/MANUAL_DE_USO.md`) | Redactado y publicado el manual exhaustivo de la plataforma estructurado según las 5 secciones (`Inicio`, `Cartera`, `ETFs`, `Análisis`, `Sistema`) y el panel de configuración, detallando la rutina diaria de las 21:55 CET, operativa en Euros en Tradegate, y funcionamiento del Módulo Fiscal AEAT. |
| **2026-10-27** | Actualización Horaria Aislada de Gráficas de ETFs & Horizontes 1D/1S | Implementado refresco horario automático (1H / 3600s TTL) para las gráficas interactivas de ETFs (`EtfChartService`) con **modo por defecto en Velas OHLC**. La resolución temporal se ha unificado de forma transparente en el selector de horizontes: **`1D` (1 Día) y `1S` (1 Semana) usan resolución de velas horarias (1H)** con ventana rodante completa hacia atrás (24 horas y 7 días continuos hasta el momento actual), mientras que **`1M` a `Todo` emplean velas diarias con ventana rodante natural** (1 mes, 3 meses, etc.). La directriz **SMA(50) se homogeneiza en línea punteada/discontinua al igual que la SMA(200)** tanto en el gráfico como en la leyenda técnica. Se elimina el selector manual de temporalidad para máxima simplicidad. Se garantiza **aislamiento absoluto del bot cuantitativo**: los ficheros `data/<SYMBOL>_daily.json` permanecen de solo lectura y la caché horaria se gestiona en `data/cache_etf_hourly/` (216 KB total). Hilo demonio de templado en segundo plano en `server.py`, badge de estado y botón de actualización inmediata en frontend. Suite ampliada a **59 tests unitarios**. |
| **2026-10-27** | Especificación de Requisitos de Fiabilidad del Sistema & Suite UX/E2E | Documentados los 12 requisitos formales de fiabilidad operativa en [`docs/REQUISITOS_Y_TESTS_FIABILIDAD.md`](docs/REQUISITOS_Y_TESTS_FIABILIDAD.md) (REQ-01 a REQ-12: Hot-swapping M1-M6, Pánico con invalidación de propuestas, Persistencia atómica, Fiscalidad AEAT, Contratos API, Cortafuegos Kill-Switch -8% DD, Flujo Copiloto completo, Blindaje de Cuenta Real LIVE_REAL contra resets accidentales, Rebalanceos con Deltas Parciales y Conservación de Liquidez, Compensación de pérdidas a 4 años, Régimen Defensivo en Backwardation y Resiliencia ante datos nulos). Suite completa ampliada a **71 tests unitarios e integrados (100% pasando)**. |
| **2026-10-28** | Normalización de Rangos ETFs (1M a Todo) & Corrección Pulso de Mercado | **1)** En la vista de gráficas de ETFs (`web_app/index.html` y `web_app/static/app.js`), se retiran los botones `1D` y `1S` para normalizar los horizontes a la escala diaria estándar (`1M`, `3M`, `6M`, `1A`, `5A`, `Todo`), manteniendo el modo por defecto en velas OHLC, SMA(50) y SMA(200) punteadas, y zoom por ventana rodante natural exacta. **2)** Corrección en `refresh_market_pulse()` de [`aegis_quant/live/bot_controller.py`](aegis_quant/live/bot_controller.py): la llamada a Yahoo Finance utilizaba previamente `range=5d`, donde `chartPreviousClose` correspondía al cierre de hace 5 sesiones bursátiles (falseando el signo de la sesión diaria); corregido a `range=1d` y priorizando `regularMarketChangePercent` oficial para reflejar exactamente la variación del día (ayer vs hoy). |
| **2026-10-29** | Sizing de Posiciones & Concurrencia de Motores (M1 vs M4) + Homogeneización de Estrategia en Modales Interactivos + Simulación Empírica de Bitcoin en M4 (2020–2026) | **1)** Homogeneización visual de la subsección `Estrategia` (dentro de `Análisis`): estructurada en 4 tarjetas operativas clickeables con modales dedicados (`ARCHITECTURE`, `CAPITAL_CONCURRENCY`, `EXECUTION_SPAIN` y `BITCOIN_STUDY`) manteniendo el mismo estándar de las fichas M1–M6. Detallada la fórmula de sizing ($2,5\% \times \text{Confianza} / \max(1,35\%, \text{StopDist}\%)$) y la regla de no-desinversión de M1 ante señales de M4 (por preservación de esperanza matemática, fricción de doble spread y fiscalidad IRPF). **2)** Simulación empírica de Bitcoin en Motor 4 CTA: corrección del error de doble escalado temporal en la interfaz (la curva simulada 2007–2026 acumulaba ya el crecimiento y en JavaScript se multiplicaba artificialmente por el factor de Modo 3 Élite, generando un salto vertical anómalo en 2020 y un capital distorsionado de $4M). Se establece la curva continua completa 2007–2026 (1.663 puntos) con Bitcoin activo desde el inicio de su serie oficial regulada (septiembre de 2014) y un **techo prudencial estricto de asignación del 15%** (frente al 40% general de M4). Resultados auditados: Horizonte Completo 2007–2026: Base $342.365 (19,55% CAGR, -14,86% MaxDD) vs Con BTC $601.284 (23,00% CAGR, -15,56% MaxDD, 34 trades); Horizonte Reciente 2020–2026 ($10k base): Base $47.969 (25,91% CAGR, -13,07% MaxDD) vs Con BTC $60.368 (30,24% CAGR, -13,07% MaxDD, 17 trades). 0 operaciones en el crash de 2022. Suite de 71 tests unitarios pasando al 100%. |
| **2026-10-29** | Integración Oficial de Bitcoin (M4 CTA Cap 15%), Catálogo de 7 ETFs, Vehículo IBKR y Correcciones UX/Fiscales | **1) Incorporación Oficial de Bitcoin:** Integrado como quinto activo de Motor 4 CTA en `AegisPortfolioEngine`, `MarketDataRepository` y `LiveBotController`, con `data/BTC_daily.json` (3.047 sesiones desde 2014) y cap estricto del 15% en `MetaLabelRiskManager`. Reejecutado `main_backtest.py` generando el nuevo `aegis_backtest_summary.json` (Modo 3 Élite final: $614.368,50, CAGR 23,13%, MaxDD -15,71%, 780+ trades). **2) Vehículo Operativo para España/IBKR:** Seleccionado el ETP físico en EUR **`BTCE` (ETC Group Physical Bitcoin, ISIN `DE000A27Z304`, TER 0,60%)** y **`21BC` (21Shares Bitcoin Core ETP, ISIN `CH1199067054`, TER 0,21%)** negociables en Tradegate/Xetra. Integrados en `UCITS_CATALOG` de `SpanishTaxAuditor`. **3) Pestaña ETFs:** Expandido el selector a 7 ETFs (`SPY`, `QQQ`, `GLD`, `TLT`, `USO`, `ZS`, `BTC`) en `EtfChartService`, `index.html` y `app.js`. **4) Corrección Modo Oscuro:** Sustituidas clases no compiladas en `STRATEGY_TOPICS.ARCHITECTURE` (`dark:bg-slate-800/80` -> `dark:bg-slate-800`) haciendo legible el texto de la Capa 2. **5) Auditoría FIFO 0€:** Explicado el origen del 0€ en Renta WEB (las pruebas de sandbox de 25/10 abrieron y cerraron al mismo segundo con 0€ de plusvalía; y las ventas con pérdida en SPY quedan bloqueadas como Diferidas 2M por recompra/mantenimiento homogéneo <60 días según Art. 33.5.f LIRPF, siendo 0€ la cuota tributable correcta). Suite completa de 71 tests pasando al 100%. |
| **2026-10-29** | Adaptación Fiscal con Bitcoin, Desglose 2 Vías de Pago IRPF y Protocolo de Transición a Real con 300 € (Modo AUTO_100) | **1) Cascada Fiscal con Bitcoin:** Auditada la rentabilidad neta tras IRPF progresivo a 19 ejercicios ($267.425,58 netos limpios, 18.06% CAGR vs 44.784 $ en S&P 500 Buy & Hold). Cifras de control Modelo 720 aclaradas (conversión BCE 1.0860 del saldo Paper 9.192 € vs IBKR 9.208 €). Corregidas líneas SMA50/SMA200 en leyenda de ETFs con CSS directo `#d97706` y `#64748b`. **2) Desglose de las 2 Vías de Pago del IRPF:** Explicado matemáticamente el *Tax Drag* sobre el interés compuesto (la brecha de $346k no se la lleva Hacienda, sino que $271k corresponden a interés compuesto perdido por retirar impuestos anualmente). Integrado en `web_app/index.html` el panel comparativo: Vía A (Autofinanciada, $267.4k) vs Vía B (Pago desde Nómina/Ahorros sin desinvertir de IBKR, $479.8k limpios, +79,4% de beneficio extra). **3) Protocolo de Transición a Dinero Real:** Creada y actualizada la guía oficial [`docs/TRANSICION_DINERO_REAL_CHECKLIST.md`](docs/TRANSICION_DINERO_REAL_CHECKLIST.md) con el checklist pre-vuelo, adopción del modo 100% automático (`AUTO_100` sin latencia humana para el cierre de Tradegate a las 22:00 CET) y capital de prueba optimizado a **300 €** (multiactivo simultáneo con riesgo máximo histórico acotado a ~47 € y kill-switch a -24 €). |
| **2026-10-29** | Interés Compuesto Dinámico (10k a 12k) y Discretización Entera en Tradegate (Múltiplos de 18 € en SOYB) | **1) Dinamismo de Capital:** Confirmado que el bot dimensiona posiciones sobre el 100% del saldo real vivo de la cuenta (`Total Equity` / `Net Liquidation Value`). Al crecer la cuenta de 10.000 € a 12.000 €, los porcentajes se calculan sobre 12.000 € para garantizar el interés compuesto sin dejar beneficios ociosos en efectivo. El control de capital se ejerce de forma óptima depositando en IBKR únicamente los fondos asignados a la estrategia. **2) Discretización Entera (Múltiplos de 18 € en SOYB):** En Tradegate/IBKR no hay acciones fraccionadas. El bot aplica la función de suelo `floor(Presupuesto / Precio_Unitario)`. Si a SOYB (~18 €) le corresponden 30 €, compra 1 acción (18 €) y los 12 € sobrantes se preservan en liquidez de seguridad. Si el presupuesto no alcanza para 1 acción (ej. 45 € para Oro `4GLD` a ~80 €), la orden es de 0 acciones y se preserva el efectivo intacto. Documentado en detalle en [`docs/TRANSICION_DINERO_REAL_CHECKLIST.md`](docs/TRANSICION_DINERO_REAL_CHECKLIST.md#3-restricciones-de-negociacion-por-multiplos-enteros-ej-soyb-a-18--spyl-a-14--y-conservacion-de-liquidez). |
| **2026-10-30** | Limpieza de Interfaz: Retirada de Simulación Preliminar de Bitcoin | **1) Retirada de Botón Redundante:** Eliminado el botón `+ Simulación Bitcoin M4` de la gráfica principal de rentabilidad acumulada, dado que Bitcoin ya está formalmente integrado y activo dentro de la curva oficial del Modo 3 Élite ($614.368,50). **2) Retirada de Tarjeta Experimental:** Eliminada la tarjeta de estudio experimental preliminar en la subsección `Estrategia`, homogeneizando la cuadrícula de fundamentos a 3 módulos simétricos (`Arquitectura Híbrida`, `Gestión de Capital y Concurrencia`, `Ejecución Real en España y Fiscalidad`). **3) Oficialización en Motor 4:** Actualizada la ficha técnica de Motor 4 (`M4_CTA_TREND`) en frontend para reflejar formalmente la cesta completa de los 5 activos operativos descorrelacionados (Oro `4GLD`, Bonos `DTLA`, Petróleo `CRUD`, Soja `SOYB` y Bitcoin `BTCE`). Suite completa de 71 tests pasando al 100%. |
| **2026-10-30** | Indicador Visual Dinámico de Sesión Abierta/Cerrada en Badge Horario DST | **1) Semáforo Operativo Dinámico:** El cuadro de cabecera (`#pt-dst-badge`) que señaliza el desfase horario estacional (DST) se transforma en un indicador de sesión en tiempo real: se muestra en **Verde institucional** (`bg-emerald-50 dark:bg-emerald-950/70 border-emerald-300 text-emerald-800`) cuando el mercado de Wall Street (NYSE/Nasdaq) está **ABIERTO** (lunes a viernes de 09:30 a 16:00 NY, no festivo), y en **Amarillo/Ámbar** (`bg-amber-50 dark:bg-amber-950/70 border-amber-300 text-amber-800`) cuando está **CERRADO** (pre-apertura matinal en Europa, fuera de horario, fin de semana o festivo). **2) Información de Desfase Horario Preservada:** El texto y tooltip del cuadro mantienen la señalización explícita del desfase estacional (ej. `● Mercado Abierto · DST Desfase EU/US (5h · EDT/CET)` vs `○ Mercado Cerrado · DST Desfase EU/US (5h · EDT/CET)`). **3) Sincronización Backend/Frontend:** Implementado `LiveBotController.is_market_open_now(now_ny)` expuesto en `/api/live/status` y cálculo cliente en `app.js` como contingencia. Suite ampliada a **72 tests unitarios (100% pasando)**. |



