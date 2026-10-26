# Manual de Uso y Guía Operativa de Aegis-Quant

Este documento describe la arquitectura, el funcionamiento de cada una de las pantallas de la interfaz web, los controles operativos y las directrices para operar el bot cuantitativo **Aegis-Quant (Modo 3 Élite · 6 Motores + VTS)** tanto en entorno simulado (*Paper Trading*) como en ejecución real en Interactive Brokers mediante la **Opción A (`Tradegate`)**.

---

## Índice de Contenidos

1. [Arquitectura General y Rutina Diaria](#1-arquitectura-general-y-rutina-diaria)
2. [Sección 1: Inicio (Centro de Mando)](#2-sección-1-inicio-centro-de-mando)
3. [Sección 2: Cartera (Posiciones y Órdenes)](#3-sección-2-cartera-posiciones-y-órdenes)
4. [Sección 3: ETFs (Gráficas de Precios y Ficha Europea)](#4-sección-3-etfs-gráficas-de-precios-y-ficha-europea)
5. [Sección 4: Análisis (Auditoría Histórica 2007–2026 e IRPF)](#5-sección-4-análisis-auditoría-histórica-20072026-e-irpf)
6. [Sección 5: Sistema (Diagnóstico, Motores y Consola)](#6-sección-5-sistema-diagnóstico-motores-y-consola)
7. [Panel Superior de Configuración](#7-panel-superior-de-configuración)
8. [Preguntas Frecuentes y Dudas Clave](#8-preguntas-frecuentes-y-dudas-clave)
   - [¿Por qué aparece una pérdida de -62,51 € si hice reset a $10.000?](#a-por-qué-aparece-una-pérdida-de--6251--si-hice-reset-a-10000)
   - [¿Operamos en Dólares ($) o en Euros (€) en la realidad?](#b-operamos-en-dólares--o-en-euros--en-la-realidad)
   - [¿Qué ocurre si pulso sincronizar fuera de la hora de mercado?](#c-qué-ocurre-si-pulso-sincronizar-fuera-de-la-hora-de-mercado)

---

## 1. Arquitectura General y Rutina Diaria

Aegis-Quant es un sistema de inversión sistemática diseñado para ejecutarse **una sola vez al día**, 5 minutos antes del cierre de las bolsas estadounidenses:
- **Hora fija:** **15:55 America/New_York** (habitualmente **21:55 CET en Madrid**, ajustándose dinámicamente a 20:55 CET durante las dos semanas de desincronización horaria DST entre EE. UU. y Europa).
- **Vehículos de Inversión:** ETFs UCITS de réplica física y acumulación negociados en la bolsa alemana **Tradegate Exchange (TGATE)** en **Euros (€)**, evitando la conversión de divisas en Interactive Brokers y cumpliendo al 100% la normativa europea PRIIPs / MiFID II.
- **Estructura de Capital:** Sin apalancamiento financiero, sin deuda y sin derivados sintéticos x3. La exposición total nunca supera el 100% del capital.

---

## 2. Sección 1: Inicio (Centro de Mando)

La pantalla de **Inicio** ofrece una visión ejecutiva inmediata del estado del sistema:

### A. Barra Superior de Estado
- **Indicador de Conexión:** Muestra si el bot está activo (verde) o pausado (ámbar), el modo de ejecución (`Automático 100%` o `Copiloto`) y el bróker conectado (`Paper Local`, `Alpaca Paper` o `Bróker Real`).
- **Botón "Actualizar Datos":** Realiza una lectura segura y en tiempo real de las cotizaciones y saldos sin emitir órdenes jamás.
- **Botón "Pausar / Reanudar Bot":** Detiene la ejecución automática de la rutina diaria.
- **Control de Emergencia ("Liquidar Cartera a Efectivo"):** Botón de pánico protegido por confirmación en 2 pasos que vende todas las posiciones abiertas a mercado en caso de evento imprevisto.

### B. Tarjetas de Patrimonio (KPIs)
- **Patrimonio Total:** Valor neto liquidativo de la cuenta (Efectivo + Valor de mercado de posiciones).
- **Capital Invertido:** Suma del valor de las posiciones actualmente en cartera.
- **Liquidez Disponible:** Saldo en efectivo disponible para rebalanceos o nuevos motores tácticos.
- **Drawdown Actual & Cortafuegos:** Porcentaje de caída desde el máximo histórico de la cuenta. Si alcanza el cortafuegos diario (-8.0%), el bot congela compras adicionales.

### C. Motores Tácticos en Vivo (M1–M6)
Muestra si hoy hay alguna señal táctica activa (Pullback, Divergencia VIX, Corto, CTA, Vol-Crush o Fin de Mes) y la asignación resultante del núcleo Dual-Momentum (SPY y QQQ).

### D. Monitor de Régimen VTS (Estructura de Volatilidad)
- **Ratio VIX / VIX3M:** Mide la salud estructural del mercado.
  - **Ratio < 1.00 (Contango):** Régimen normal. La bolsa está en calma o tendencia alcista sana; el núcleo invierte al 100% en SPY/QQQ modulado por volatilidad.
  - **Ratio >= 1.00 (Backwardation):** Régimen de estrés o pánico sistémico. El escudo de volatilidad se activa, la bolsa pasiva pasa al 0% y el capital queda reservado para motores tácticos y activos refugio (Oro, Bonos, etc.).
- **Enlace directo a ETFs:** Permite saltar directamente a la sección interactiva de ETFs para analizar precios y medias.

---

## 3. Sección 2: Cartera (Posiciones y Órdenes)

Esta sección permite auditar en todo momento los activos que posee el bot:
- **Resumen Rápido:** Patrimonio, Invertido y Liquidez, con botón "Actualizar" para refrescar valoraciones sin enviar órdenes al bróker.
- **Posiciones Abiertas:** Tabla detallada que muestra el activo, ticker de bróker, dirección (`LONG` / `SHORT`), precio medio de compra, cotización actual, valor de mercado, peso porcentual en cartera y beneficio/pérdida no realizado (PnL latente).
- **Historial Reciente de Órdenes:** Registro cronológico de las últimas órdenes enviadas, indicando fecha, símbolo, lado (`BUY`, `SELL`, `SELL_SHORT`, `BUY_TO_COVER`), cantidad, precio de ejecución, motor que generó la orden y motivo de la decisión.

---

## 4. Sección 3: ETFs (Gráficas de Precios y Ficha Europea)

Dedicada al seguimiento visual y cuantitativo del universo de los 6 ETFs operados:
- **Selector Superior:** Permite elegir el ETF a visualizar (`SPY`, `QQQ`, `GLD`, `TLT`, `USO`, `ZS`/`SOYB`).
- **Tarjetas de Acceso Rápido:** 6 botones con cotización de cierre y variación diaria en tiempo real para cambiar de gráfico con un solo clic.
- **Indicadores Técnicos:**
  - Cotización actual y variación diaria.
  - Rentabilidad a 1 año y en lo que va de año (YTD).
  - Rango de 52 semanas (mínimo y máximo anual).
  - Régimen técnico: Tendencia `ALCISTA` (> SMA 200) o `BAJISTA` (< SMA 200) y oscilador `RSI(2)` de Wilder.
- **Gráfica Interactiva con ECharts:**
  - Alternador de tipo de gráfico: **Línea** suave con área sombreada o **Velas japonesas OHLC**.
  - Medias móviles institucionales: **SMA(50)** (ámbar) y **SMA(200)** (gris discontinuo).
  - Subgráfico de **Volumen Diario**.
  - Selectores de horizonte temporal: `1M`, `3M`, `6M`, `1A` (por defecto), `5A` y `Todo` (histórico completo desde 2006).
  - Zoom interactivo mediante rueda de ratón o gesto táctil de pellizco en móvil.
- **Ficha de Ejecución Europea (Opción A · Tradegate):** Muestra el ticker UCITS en Alemania (ej. `SPYL / SXR8`), código ISIN oficial, TER (comisión de gestión del fondo), bolsa (`Tradegate TGATE en EUR`) y motores del bot que lo operan.

---

## 5. Sección 4: Análisis (Auditoría Histórica 2007–2026 e IRPF)

Contiene la verificación científica del algoritmo durante los últimos 20 años de historia bursátil:

### Subpestaña 1: Equity y Motores
- Curva de capital compuesta que muestra el crecimiento de una cuenta base de **$10.000 hasta $341.057** (+3.310% neto) frente al S&P 500 Buy & Hold ($67.756).
- Gráfica de Drawdown subyacente que demuestra cómo Aegis-Quant limita la caída máxima al **-14,86%**, frente al **-55,19%** sufrido por el S&P 500 en 2008.
- Selector de filtros por motor y visualización en escala lineal o logarítmica.

### Subpestaña 2: Estrategia (Fichas Interactivas M1–M6)
Presenta los 6 motores cuantitativos en una cuadrícula simétrica 3x2. Al pasar el ratón (hover verde) o pulsar en cualquier tarjeta, se abre una **Ficha Técnica Detallada**:
1. **Fundamento Financiero y Microestructura:** Explicación rigurosa de por qué existe la anomalía y quién pierde el dinero que el motor captura.
2. **Ejemplo Práctico Real con Velas Japonesas:** Gráfica interactiva de un trade real del backtest (ej. QQQ en el crash del COVID de marzo 2020 con +5.16% en 24h, o Petróleo USO con +40.0% en 34 sesiones), mostrando vela de entrada, vela de salida y explicación de la operación.
3. **Reglas Algorítmicas:** Condiciones exactas de entrada y salida programadas en Python.
4. **Métricas Consolidadas (2007–2026):** Trades totales, tasa de acierto %, rentabilidad acumulada y profit factor.
5. **Acceso directo al Simulador:** Botón para ver todas las operaciones históricas de ese motor filtradas al instante.

### Subpestaña 3: Crisis y Robustez
- Comparativa en ciclos de estrés: Crisis Subprime 2008, Flash Crash 2010, Guerra Comercial 2018, COVID 2020 y Mercado Bajista 2022.
- Simulación Monte Carlo (1.000 trayectorias aleatorias con 8% de señales perdidas) para verificar la robustez estadística.
- Sensibilidad a costes de fricción (0 a 35 puntos básicos de spread y comisiones).
- Tabla de rentabilidad año a año con cálculo de Alpha generado frente al S&P 500.

### Subpestaña 4: Simulador e Histórico de 780 Operaciones
- Tabla completa y filtrable de todas y cada una de las 780 operaciones ejecutadas por el modelo desde 2007, con fecha de entrada, precio, fecha de salida, duración en días, resultado % y capital tras la operación.

### Subpestaña 5: Módulo Fiscal Automático AEAT / IRPF
Motor de liquidación tributaria oficial para inversores en España:
- **Criterio FIFO Oficial:** Convierte cada compra y venta a Euros mediante el tipo de cambio diario oficial publicado por el Banco Central Europeo (BCE).
- **Detector Automático de la Regla de los 2 Meses (`Art. 33.5.f LIRPF`):** Identifica automáticamente recompras dentro de la ventana de $\pm 60$ días naturales. Si aplica la regla, bloquea la minusvalía como "Diferida 2M" y calcula la fecha exacta en la que quedará desbloqueada tras permanecer 60 días sin posición en ese ISIN.
- **Casillas de Renta WEB (Apartado F2):** Agrupa ganancias y pérdidas por emisor de ETF, listas para copiar directamente en las casillas `0326` a `0335` del borrador de la AEAT.
- **Vigilancia del Modelo 720:** Monitoriza en tiempo real el saldo frente al umbral legal de 50.000 € en cuentas en el extranjero.
- **Exportación CSV:** Descarga un fichero compatible con Excel en España (UTF-8 con BOM y separador `;`) para entregar a la gestoría o archivar.

---

## 6. Sección 5: Sistema (Diagnóstico, Motores y Consola)

Diseñada para la supervisión técnica, configuración de motores y mantenimiento:

### A. Registro Operativo en Vivo (Logs en Tiempo Real)
Consola que muestra los eventos registrados por el bot con fecha, nivel (`INFO`, `WARN`, `ERROR`, `SUCCESS`) y mensaje descriptivo.

### B. Interruptores de Motores Tácticos (M1–M6)
Permite activar o desactivar individualmente cualquiera de los 6 motores.
- **Seguridad anti-toque accidental:** Si intentas desactivar un motor, se abre un diálogo modal de confirmación explicando qué supone desconectarlo.

### C. Consola Operativa y Diagnóstico
- **Forzar Escaneo y Rebalanceo:** Permite disparar la rutina de rebalanceo manualmente. Al pulsarlo, requiere confirmación modal expresa advirtiendo de que ejecutar fuera de las 21:55 CET evalúa precios intradía.
- **Simulador Rápido de Motores (Sandbox Paper):** Permite inyectar una señal sintética de cualquiera de los motores en la cuenta de Paper Trading para comprobar que las alertas y la cartera responden adecuadamente.
- **Reiniciar Saldo Paper Trading ($10.000):** Restablece el saldo simulado a $10.000 en efectivo. **Este botón se oculta automáticamente si el bróker configurado es real**, protegiendo la cuenta contra errores.

---

## 7. Panel Superior de Configuración

Accesible desde el botón **"Configuración"** en la barra superior:
1. **Proveedor de Ejecución:** Selección entre `Simulador Paper Local`, `Alpaca Paper API` o `Alpaca Live / Conector Real`.
2. **Modo de Operación:**
   - `100% Automático`: El bot envía las órdenes al bróker automáticamente a las 21:55 CET.
   - `Modo Copiloto`: El bot genera la propuesta a las 21:55 CET, te envía una alerta por Signal y muestra un banner en la pantalla de Inicio para que apruebes las órdenes con un clic antes de enviarlas.
3. **Capital Asignado ($ / €):**
   - En Paper Trading define el saldo virtual de partida ($10.000).
   - En Trading Real fija el techo nocional máximo sobre el que el bot calculará los porcentajes de asignación (por ejemplo, si tienes 40.000 € en IBKR pero solo quieres destinar 15.000 € al bot).
4. **Parámetros de Riesgo:** Riesgo por operación (2.5%), límite de motores rápidos (55%), límite de motores CTA (40%), cortafuegos diario (-8%) y hora programada (21:55 CET).
5. **Notificaciones Móviles (Signal Messenger):** Configuración de número de teléfono y API Key de CallMeBot para recibir avisos de compras, ventas y cierres directamente en Signal. Telegram ha sido completamente retirado para simplificar la infraestructura.

---

## 8. Preguntas Frecuentes y Dudas Clave

### A. ¿Por qué aparece una pérdida de -62,51 € si hice reset a $10.000?

Esta duda es muy común. La pérdida **no proviene del botón de reset en sí**, sino de una venta real ejecutada en el simulador Paper Trading el 25 de octubre:
1. **Compra el 23-10-2026:** El bot compró 5,174 títulos de SPY a $773,09 (coste: $3.999,99 = **3.683,21 €** según el tipo de cambio oficial del BCE de 1,0860 USD/EUR).
2. **Venta el 25-10-2026:** La posición se cerró a $759,97 (ingreso: $3.932,08 = **3.620,70 €**).
3. **Cálculo Fiscal AEAT (FIFO en Euros):**
   $$\text{Ganancia / Pérdida} = 3.620,70 \text{ €} - 3.683,21 \text{ €} = \mathbf{-62,51 \text{ €}}$$

El botón de "Reset de Cuenta" restablece el saldo en efectivo de la cuenta virtual en `bot_live_state.json` a $10.000, pero el **Módulo Fiscal AEAT audita el libro contable inmutable** (`ledger_paper_trades.jsonl`). En dicho libro contable quedó registrada la transmisión patrimonial. De acuerdo con la Ley del IRPF española (artículo 33), esa pérdida de 62,51 € es real dentro del ejercicio fiscal 2026 y queda registrada para **compensarse con futuras plusvalías durante los próximos 4 años**.

Si deseas reiniciar también el libro contable de simulación a cero absoluto para comenzar limpio, basta con vaciar el fichero `data/ledger_paper_trades.jsonl`.

### B. ¿Operamos en Dólares ($) o en Euros (€) en la realidad?

- **En los modelos históricos y en Wall Street:** Se utilizan dólares ($) porque los índices S&P 500 y Nasdaq 100 cotizan originalmente en Nueva York en USD.
- **En la ejecución real desde España (Opción A · Tradegate):** **¡Operarás al 100% en EUROS (€)!**
  - Tu cuenta en Interactive Brokers estará denominada en **Euros**.
  - Comprarás réplicas UCITS europeas cotizadas en Euros en la bolsa alemana Tradegate (ejemplo: `SPYL` o `SXR8` de iShares para el S&P 500, `EQQQ` para el Nasdaq 100, etc.).
  - **Ventaja fiscal y operativa:** No pagas comisiones por cambio de divisa, eliminas el riesgo de fricción por spread de divisas y cumples directamente con la normativa de Hacienda, que exige liquidar el IRPF en Euros según la cotización oficial del BCE.

### C. ¿Qué ocurre si pulso sincronizar fuera de la hora de mercado?

El algoritmo de Aegis-Quant está matemáticamente calibrado para operar sobre los precios de cierre diarios (**15:55 NY / 21:55 CET**).
- Si ejecutas un escaneo a las 12:00 del mediodía o con mercado cerrado, los precios intradía pueden generar señales prematuras o falsas rupturas. Además, los spreads de compra/venta en Tradegate son más amplios fuera del horario regular.
- Por esta razón, el botón de la pantalla de Inicio se ha configurado como **"Actualizar Datos"** (solo lectura de cotizaciones y saldos, sin riesgo de lanzar órdenes).
- El botón de rebalanceo manual se encuentra protegido en la sección **Sistema** bajo confirmación expresa, reservado únicamente para situaciones en las que el servidor haya estado apagado a las 21:55 CET y necesites forzar la ejecución al reanudarlo.
