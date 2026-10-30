"""
Generador del Dashboard Interactivo de Aegis-Quant v2.5 (build_dashboard.py).
Incluye:
  1. Gráfico Multi-Modo (Modos 1, 2, 3 Base, 3 Élite y S&P 500) con marcadores interactivos
     de los 5 Motores sobre la curva, Zoom por Etapas Macro y Filtro Anti-Colapso.
  2. Laboratorio de Pruebas de Robustez (Monte Carlo 1,000 sims, Estrés de Fricción,
     Walk-Forward por Sub-periodos y Sensibilidad Paramétrica).
  3. Tabla Anual, Desglose de la Pirámide Cuantitativa, Auditoría de Trades y Escáner en Vivo.
"""

import json
import os


def build_html_dashboard(summary_path: str, output_paths: list):
    with open(summary_path, encoding="utf-8") as f:
        data = json.load(f)

    # Compactamos los trades de cada modo para que incluyan todos los 725 trades sin sobrecargar el tamaño del archivo
    compact_modes = {}
    for k, m in data["modes"].items():
        cm = dict(m)
        compact_trades = []
        for t in m["trades"]:
            compact_trades.append(
                {
                    "e": t["engine_id"],
                    "s": t["symbol"],
                    "d": t["direction"],
                    "in_d": t["entry_date"],
                    "in_p": t["entry_price"],
                    "out_d": t["exit_date"],
                    "out_p": t["exit_price"],
                    "w": round(t["position_weight"], 2),
                    "mc": t["meta_confidence"],
                    "rr": round(t["raw_ret_pct"], 2),
                    "pr": round(t["portfolio_ret_pct"], 2),
                    "win": 1 if t["win"] else 0,
                    "eq": round(t.get("eq_at_exit", 10000.0), 1),
                    "rsn": t["entry_reason"][:58],
                    "xrsn": t["exit_reason"][:42],
                }
            )
        cm["trades"] = compact_trades
        compact_modes[k] = cm

    payload = {
        "generated_at": data["generated_at"],
        "benchmark": data["benchmark"],
        "modes": compact_modes,
        "robustness": data["robustness"],
        "live_scan": data["live_scan"],
    }
    json_str = json.dumps(payload, separators=(",", ":"))

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Aegis-Quant | Mapa Multi-Modo de Motores & Pruebas de Robustez</title>
<script src="https://www.gstatic.com/external_hosted/tailwind_css/tailwind.js"></script>
<style>
  :root {{
    color-scheme: light dark;
    --bg-card: light-dark(#ffffff, #0f172a);
    --bg-sub: light-dark(#f8fafc, #1e293b);
    --text-main: light-dark(#0f172a, #f8fafc);
    --text-muted: light-dark(#475569, #94a3b8);
    --border-col: light-dark(#e2e8f0, #334155);
  }}
  body {{
    margin: 0;
    padding: 10px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg-card);
    color: var(--text-main);
  }}
  .card {{
    background: var(--bg-sub);
    border: 1px solid var(--border-col);
    border-radius: 10px;
  }}
  .tab-btn {{
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 600;
    border-radius: 6px;
    border: 1px solid var(--border-col);
    cursor: pointer;
    transition: all 0.12s;
  }}
  .tab-btn.active {{
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
  }}
  .mode-btn {{
    padding: 4px 8px;
    font-size: 10.5px;
    font-weight: 600;
    border-radius: 6px;
    border: 1px solid var(--border-col);
    cursor: pointer;
  }}
  .mode-btn.active {{
    background: #10b981;
    color: #052e16;
    border-color: #10b981;
  }}
  .pill-btn {{
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 600;
    border-radius: 999px;
    border: 1px solid var(--border-col);
    cursor: pointer;
    opacity: 0.75;
  }}
  .pill-btn.active {{
    opacity: 1;
    box-shadow: 0 0 0 1px currentColor;
  }}
  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-thumb {{ background: #64748b; border-radius: 3px; }}
</style>
</head>
<body>
<div class="max-w-6xl mx-auto flex flex-col gap-2" style="max-height: 488px; overflow-y: auto; padding-right: 4px;">
  <!-- Cabecera y Selector de Modo Activo -->
  <div class="card p-2 flex flex-wrap items-center justify-between gap-2">
    <div>
      <div class="flex items-center gap-2">
        <span class="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Aegis-Quant OOP v2.5</span>
        <h1 class="text-xs sm:text-sm font-bold m-0">Mapa Multi-Modo de Ejecución de Motores y Pruebas de Robustez (2007–2026)</h1>
      </div>
    </div>
    <div class="flex flex-wrap gap-1" id="modeSelector">
      <button class="mode-btn active" onclick="selectMode('MODO_3_ELITE')">★ Modo 3 Élite ($281k)</button>
      <button class="mode-btn" onclick="selectMode('MODO_3_BASE')">Modo 3 Base ($138k)</button>
      <button class="mode-btn" onclick="selectMode('MODO_2_SCHERMAN')">Modo 2 Puro ($68.5k)</button>
      <button class="mode-btn" onclick="selectMode('MODO_1_BASE')">Modo 1 Inicial ($41k)</button>
    </div>
  </div>

  <!-- Fila de KPIs del Modo Seleccionado -->
  <div class="grid grid-cols-3 sm:grid-cols-6 gap-1.5" id="kpiRow"></div>

  <!-- Pestañas de Navegación -->
  <div class="flex flex-wrap items-center justify-between gap-1 border-b pb-1" style="border-color: var(--border-col);">
    <div class="flex flex-wrap gap-1">
      <button class="tab-btn active" id="tab-curve" onclick="switchTab('curve')">1. Gráfico Multi-Modo + Puntos de Motores</button>
      <button class="tab-btn" id="tab-robust" onclick="switchTab('robust')">2. Pruebas de Robustez (Monte Carlo & Fricción)</button>
      <button class="tab-btn" id="tab-years" onclick="switchTab('years')">3. Tabla Anual (2007–2026)</button>
      <button class="tab-btn" id="tab-motors" onclick="switchTab('motors')">4. Los 5 Motores & Pirámide</button>
      <button class="tab-btn" id="tab-trades" onclick="switchTab('trades')">5. Historial de Trades</button>
      <button class="tab-btn" id="tab-live" onclick="switchTab('live')">6. Escáner Hoy</button>
    </div>
  </div>

  <!-- VISTA 1: GRÁFICO MULTI-MODO CON MARCADORES DE EJECUCIÓN POR MOTOR -->
  <div id="view-curve" class="card p-2 flex flex-col gap-1.5">
    <!-- Barra de Controles de Zoom, Escala y Filtro de Motores -->
    <div class="flex flex-wrap items-center justify-between gap-1.5 text-[10px]">
      <!-- Selector de Periodo (Zoom para no colapsar el gráfico) -->
      <div class="flex flex-wrap items-center gap-1">
        <span class="opacity-70 font-semibold">Zoom:</span>
        <button class="pill-btn active" id="zoom-ALL" onclick="setZoom('ALL')">Todo 2007–26</button>
        <button class="pill-btn" id="zoom-GFC" onclick="setZoom('GFC')">Crisis 2007–11</button>
        <button class="pill-btn" id="zoom-QE" onclick="setZoom('QE')">QE 2012–16</button>
        <button class="pill-btn" id="zoom-COV" onclick="setZoom('COV')">COVID 2017–21</button>
        <button class="pill-btn" id="zoom-INF" onclick="setZoom('INF')">Inflación/IA 2022–26</button>
      </div>
      <!-- Controles de Visualización -->
      <div class="flex flex-wrap items-center gap-1.5">
        <button class="pill-btn active text-emerald-400" id="btnAllModes" onclick="toggleAllModes()">Ver 4 Modos Juntos: SÍ</button>
        <button class="pill-btn active text-amber-400" id="btnDensity" onclick="toggleDensity()">Filtro Anti-Colapso (&gt;1.2%): SÍ</button>
        <button class="pill-btn text-blue-400" id="scaleBtn" onclick="toggleLogScale()">Escala: Logarítmica</button>
      </div>
    </div>

    <!-- Filtro de Motores (Colores y Formas) -->
    <div class="flex flex-wrap items-center justify-between gap-1 text-[10px] px-1 py-1 rounded border" style="border-color: var(--border-col);">
      <div class="flex flex-wrap items-center gap-1">
        <span class="opacity-75 font-semibold">Puntos del Modo Activo:</span>
        <button class="pill-btn active" id="mot-ALL" onclick="setMotorFilter('ALL')">Todos</button>
        <button class="pill-btn text-emerald-400" id="mot-M1_PULLBACK" onclick="setMotorFilter('M1_PULLBACK')">● M1 Pullback</button>
        <button class="pill-btn text-cyan-400" id="mot-M2_VIX_DIV" onclick="setMotorFilter('M2_VIX_DIV')">◆ M2 VIX Div</button>
        <button class="pill-btn text-rose-400" id="mot-M3_BEAR_SHORT" onclick="setMotorFilter('M3_BEAR_SHORT')">▲ M3 Bear Short</button>
        <button class="pill-btn text-amber-400" id="mot-M4_CTA_TREND" onclick="setMotorFilter('M4_CTA_TREND')">■ M4 CTA Materias Primas</button>
        <button class="pill-btn text-purple-400" id="mot-M5_VOL_CRUSH" onclick="setMotorFilter('M5_VOL_CRUSH')">★ M5 Vol-Crush VIX/VIX3M</button>
        <button class="pill-btn text-slate-400" id="mot-NONE" onclick="setMotorFilter('NONE')">Ocultar Puntos</button>
      </div>
      <div id="visibleMarkersCount" class="font-mono text-[10px] opacity-80"></div>
    </div>

    <!-- Lienzo SVG del Gráfico -->
    <div class="relative w-full" style="height: 195px;">
      <svg id="equitySvg" class="w-full h-full overflow-visible"></svg>
    </div>

    <!-- Inspector Interactivo de Operación al pasar el ratón o hacer clic sobre un punto -->
    <div id="tradeInspector" class="px-2 py-1 rounded border text-[10.5px] flex flex-wrap items-center justify-between gap-2" style="border-color: var(--border-col); min-height: 26px;">
      <span class="opacity-75">💡 <b>Interactivo:</b> Pasa el ratón o haz clic sobre cualquier punto de color en la curva para inspeccionar qué motor se ejecutó, en qué activo y por qué.</span>
      <div class="flex items-center gap-2 text-[10px]">
        <span class="flex items-center gap-1"><span class="w-2.5 h-0.5 inline-block bg-emerald-400"></span>3 Élite</span>
        <span class="flex items-center gap-1"><span class="w-2.5 h-0.5 inline-block bg-teal-400"></span>3 Base</span>
        <span class="flex items-center gap-1"><span class="w-2.5 h-0.5 inline-block bg-amber-400"></span>Modo 2</span>
        <span class="flex items-center gap-1"><span class="w-2.5 h-0.5 inline-block bg-slate-400"></span>Modo 1</span>
        <span class="flex items-center gap-1"><span class="w-2.5 h-0.5 inline-block bg-blue-500"></span>S&P 500</span>
      </div>
    </div>
  </div>

  <!-- VISTA 2: LABORATORIO DE PRUEBAS DE ROBUSTEZ -->
  <div id="view-robust" class="card p-2.5 hidden" style="max-height: 280px; overflow-y: auto;">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-[11px]">
      <!-- 1. Monte Carlo 1,000 Simulaciones -->
      <div class="p-2 rounded border" style="border-color: var(--border-col);">
        <div class="flex items-center justify-between mb-1">
          <h3 class="font-bold text-emerald-400 m-0">1. Monte Carlo (1,000 Trayectorias | 8% Trades Perdidos)</h3>
          <span class="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold text-[10px]" id="mcBeatBadge"></span>
        </div>
        <p class="text-[10px] opacity-75 m-0 mb-1.5">Remuestreo por bloques con ruido de ejecución y pérdida aleatoria del 8% de las señales ganadoras:</p>
        <table class="w-full text-left border-collapse text-[10.5px]">
          <thead>
            <tr class="border-b opacity-75" style="border-color: var(--border-col);">
              <th class="py-0.5">Escenario Estadístico</th>
              <th class="py-0.5">Capital Final</th>
              <th class="py-0.5">CAGR</th>
              <th class="py-0.5">Max Drawdown</th>
            </tr>
          </thead>
          <tbody id="mcTableBody"></tbody>
        </table>
      </div>

      <!-- 2. Estrés de Fricción (Comisiones + Slippage) -->
      <div class="p-2 rounded border" style="border-color: var(--border-col);">
        <h3 class="font-bold text-blue-400 m-0 mb-1">2. Sensibilidad a Fricción (Comisiones + Slippage)</h3>
        <p class="text-[10px] opacity-75 m-0 mb-1.5">Impacto descontando costes de ida y vuelta en los 725 trades tácticos y rotaciones del Core:</p>
        <table class="w-full text-left border-collapse text-[10.5px]">
          <thead>
            <tr class="border-b opacity-75" style="border-color: var(--border-col);">
              <th class="py-0.5">Fricción por Orden</th>
              <th class="py-0.5">Capital Neto</th>
              <th class="py-0.5">CAGR Neto</th>
              <th class="py-0.5">¿Bate S&P?</th>
            </tr>
          </thead>
          <tbody id="frictionTableBody"></tbody>
        </table>
      </div>

      <!-- 3. Walk-Forward por Sub-Periodos Macro -->
      <div class="p-2 rounded border" style="border-color: var(--border-col);">
        <h3 class="font-bold text-purple-400 m-0 mb-1">3. Walk-Forward por Etapas Macroeconómicas (5 Años)</h3>
        <table class="w-full text-left border-collapse text-[10.5px]">
          <thead>
            <tr class="border-b opacity-75" style="border-color: var(--border-col);">
              <th class="py-0.5">Etapa Histórica</th>
              <th class="py-0.5">S&P 500</th>
              <th class="py-0.5">Modo 3 Élite</th>
              <th class="py-0.5">Alpha</th>
            </tr>
          </thead>
          <tbody id="subperiodTableBody"></tbody>
        </table>
      </div>

      <!-- 4. Sensibilidad Paramétrica (Anti-Overfitting) -->
      <div class="p-2 rounded border" style="border-color: var(--border-col);">
        <h3 class="font-bold text-amber-400 m-0 mb-1">4. Estabilidad Paramétrica (Descarte de Overfitting)</h3>
        <table class="w-full text-left border-collapse text-[10.5px]">
          <thead>
            <tr class="border-b opacity-75" style="border-color: var(--border-col);">
              <th class="py-0.5">Configuración Vecina</th>
              <th class="py-0.5">CAGR</th>
              <th class="py-0.5">Max DD</th>
              <th class="py-0.5">Sharpe / Calmar</th>
            </tr>
          </thead>
          <tbody id="paramTableBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- VISTA 3: TABLA ANUAL -->
  <div id="view-years" class="card p-2.5 hidden" style="max-height: 280px; overflow-y: auto;">
    <table class="w-full text-left border-collapse text-[11px]">
      <thead>
        <tr class="border-b opacity-75" style="border-color: var(--border-col);">
          <th class="py-1 px-1.5">Año</th>
          <th class="py-1 px-1.5">S&P 500 (SPY)</th>
          <th class="py-1 px-1.5">Retorno Bot</th>
          <th class="py-1 px-1.5">Alpha vs S&P</th>
          <th class="py-1 px-1.5">Trades Tácticos</th>
          <th class="py-1 px-1.5">Win Rate</th>
          <th class="py-1 px-1.5 text-right">Capital Acumulado</th>
        </tr>
      </thead>
      <tbody id="yearlyTableBody"></tbody>
    </table>
  </div>

  <!-- VISTA 4: LOS 5 MOTORES Y PIRÁMIDE -->
  <div id="view-motors" class="card p-2.5 hidden" style="max-height: 280px; overflow-y: auto;">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
      <div>
        <h3 class="text-xs font-bold mb-1.5 text-emerald-400">Rendimiento Auditado por Motor Táctico</h3>
        <div id="motorsList" class="flex flex-col gap-1.5"></div>
      </div>
      <div>
        <h3 class="text-xs font-bold mb-1.5 text-blue-400">Arquitectura de la Pirámide Cuantitativa (Aegis-Quant)</h3>
        <div class="flex flex-col gap-1 text-[11px]">
          <div class="p-1.5 rounded border border-emerald-500/40 bg-emerald-500/10">
            <b>Nivel 4 (Cúspide): Meta-Labeling & Kelly Fraccional</b> — Pondera el tamaño de cada operación (0.55x a 1.35x) según el régimen de la curva VIX/VIX3M.
          </div>
          <div class="p-1.5 rounded border border-purple-500/40 bg-purple-500/10">
            <b>Nivel 3: Microestructura de Volatilidad (VIX / VIX3M)</b> — Detecta Backwardation (&gt;1.0) para cortar exposición antes de crashes y activar el <b>Motor 5 (★ Vol-Crush Vanna)</b>.
          </div>
          <div class="p-1.5 rounded border border-blue-500/40 bg-blue-500/10">
            <b>Nivel 2: Core Cross-Asset Dual-Momentum + Vol Targeting</b> — Elimina el Cash Drag invirtiendo la liquidez ociosa en SPY/QQQ (Contango) o GLD (Crisis).
          </div>
          <div class="p-1.5 rounded border border-slate-500/40 bg-slate-500/10">
            <b>Nivel 1 (Base): Acción del Precio & Reversión (Scherman + CTA)</b> — RSI(2), Bandas de Bollinger(30,2σ), ATR(14) y Rupturas Donchian de 20 días.
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- VISTA 5: AUDITORÍA DE TRADES -->
  <div id="view-trades" class="card p-2.5 hidden" style="max-height: 280px; overflow-y: auto;">
    <table class="w-full text-left border-collapse text-[11px]">
      <thead>
        <tr class="border-b opacity-75" style="border-color: var(--border-col);">
          <th class="py-1 px-1">Motor</th>
          <th class="py-1 px-1">Activo</th>
          <th class="py-1 px-1">Dir</th>
          <th class="py-1 px-1">Entrada</th>
          <th class="py-1 px-1">Salida</th>
          <th class="py-1 px-1">Peso</th>
          <th class="py-1 px-1">Ret Activo</th>
          <th class="py-1 px-1">Impacto Cartera</th>
          <th class="py-1 px-1">Gatillo / Salida</th>
        </tr>
      </thead>
      <tbody id="tradesTableBody"></tbody>
    </table>
  </div>

  <!-- VISTA 6: ESCÁNER EN VIVO -->
  <div id="view-live" class="card p-2.5 hidden" style="max-height: 280px; overflow-y: auto;">
    <div id="liveScanContainer" class="flex flex-col gap-2 text-[11px]"></div>
  </div>
</div>

<script>
const DATA = {json_str};
let currentModeId = 'MODO_3_ELITE';
let currentTab = 'curve';
let useLogScale = true; // Logarítmica por defecto para apreciar todos los modos y puntos con nitidez
let showAllModes = true;
let filterDensity = true;
let currentZoom = 'ALL';
let currentMotorFilter = 'ALL';

const MOTOR_STYLE = {{
  'M1_PULLBACK':   {{ color: '#10b981', name: 'M1: Pullback Long',       symbol: '●' }},
  'M2_VIX_DIV':    {{ color: '#06b6d4', name: 'M2: Divergencia VIX',     symbol: '◆' }},
  'M3_BEAR_SHORT': {{ color: '#f43f5e', name: 'M3: Bear Short Crisis',   symbol: '▲' }},
  'M4_CTA_TREND':  {{ color: '#f59e0b', name: 'M4: CTA Materias Primas', symbol: '■' }},
  'M5_VOL_CRUSH':  {{ color: '#a855f7', name: 'M5: VIX/VIX3M Vol-Crush', symbol: '★' }},
}};

const ZOOM_RANGES = {{
  'ALL': ['2007-01-01', '2026-12-31'],
  'GFC': ['2007-01-01', '2011-12-31'],
  'QE':  ['2012-01-01', '2016-12-31'],
  'COV': ['2017-01-01', '2021-12-31'],
  'INF': ['2022-01-01', '2026-12-31'],
}};

function selectMode(modeId) {{
  currentModeId = modeId;
  document.querySelectorAll('.mode-btn').forEach(btn => {{
    btn.classList.toggle('active', btn.getAttribute('onclick').includes(modeId));
  }});
  renderAll();
}}

function switchTab(tabId) {{
  currentTab = tabId;
  ['curve', 'robust', 'years', 'motors', 'trades', 'live'].forEach(t => {{
    document.getElementById('view-' + t).classList.toggle('hidden', t !== tabId);
    document.getElementById('tab-' + t).classList.toggle('active', t === tabId);
  }});
  renderAll();
}}

function setZoom(z) {{
  currentZoom = z;
  ['ALL', 'GFC', 'QE', 'COV', 'INF'].forEach(k => {{
    document.getElementById('zoom-' + k).classList.toggle('active', k === z);
  }});
  // Al hacer zoom en una etapa de 5 años, podemos mostrar todos los puntos sin filtro de densidad
  if (z !== 'ALL') {{
    filterDensity = false;
  }} else {{
    filterDensity = true;
  }}
  updateControlButtons();
  renderCurve();
}}

function setMotorFilter(mf) {{
  currentMotorFilter = mf;
  ['ALL', 'M1_PULLBACK', 'M2_VIX_DIV', 'M3_BEAR_SHORT', 'M4_CTA_TREND', 'M5_VOL_CRUSH', 'NONE'].forEach(k => {{
    const el = document.getElementById('mot-' + k);
    if (el) el.classList.toggle('active', k === mf);
  }});
  renderCurve();
}}

function toggleAllModes() {{
  showAllModes = !showAllModes;
  updateControlButtons();
  renderCurve();
}}

function toggleDensity() {{
  filterDensity = !filterDensity;
  updateControlButtons();
  renderCurve();
}}

function toggleLogScale() {{
  useLogScale = !useLogScale;
  updateControlButtons();
  renderCurve();
}}

function updateControlButtons() {{
  const bAll = document.getElementById('btnAllModes');
  bAll.textContent = 'Ver 4 Modos Juntos: ' + (showAllModes ? 'SÍ' : 'NO');
  bAll.classList.toggle('active', showAllModes);

  const bDen = document.getElementById('btnDensity');
  bDen.textContent = 'Filtro Anti-Colapso (>1.2%): ' + (filterDensity ? 'SÍ' : 'NO (100%)');
  bDen.classList.toggle('active', filterDensity);

  const bSc = document.getElementById('scaleBtn');
  bSc.textContent = 'Escala: ' + (useLogScale ? 'Logarítmica' : 'Lineal ($)');
}}

function renderKPIs() {{
  const m = DATA.modes[currentModeId];
  const b = DATA.benchmark;
  const kpis = [
    {{ label: 'Capital Final ($10k)', val: '$' + m.final_equity.toLocaleString(), sub: 'S&P 500: $' + b.final_equity.toLocaleString(), col: 'text-emerald-400' }},
    {{ label: 'Retorno Total', val: (m.total_return_pct >= 0 ? '+' : '') + m.total_return_pct + '%', sub: 'S&P 500: +' + b.total_return_pct + '%', col: 'text-emerald-400' }},
    {{ label: 'CAGR (Anual)', val: m.cagr_pct + '%', sub: 'S&P 500: ' + b.cagr_pct + '%', col: 'text-blue-400' }},
    {{ label: 'Max Drawdown', val: m.max_dd_pct + '%', sub: 'S&P 500: ' + b.max_dd_pct + '%', col: 'text-amber-400' }},
    {{ label: 'Sharpe / Calmar', val: m.sharpe + ' / ' + m.calmar, sub: 'Sortino: ' + m.sortino, col: 'text-purple-400' }},
    {{ label: 'Crisis S&P Batidas', val: m.bear_years_beaten + '/' + m.total_bear_years + ' Años', sub: m.positive_years + '/' + m.total_years + ' Años Positivos', col: 'text-emerald-400' }},
  ];

  document.getElementById('kpiRow').innerHTML = kpis.map(k => `
    <div class="card p-1.5">
      <div class="text-[9.5px] opacity-70">${{k.label}}</div>
      <div class="text-xs sm:text-sm font-bold ${{k.col}}">${{k.val}}</div>
      <div class="text-[9.5px] opacity-65">${{k.sub}}</div>
    </div>
  `).join('');
}}

function showTradeDetails(idx) {{
  const m = DATA.modes[currentModeId];
  const t = m.trades[idx];
  if (!t) return;
  const st = MOTOR_STYLE[t.e] || {{ color: '#10b981', name: t.e, symbol: '●' }};
  const retSign = t.pr >= 0 ? '+' : '';
  const retCol = t.win ? 'text-emerald-400' : 'text-rose-400';
  document.getElementById('tradeInspector').innerHTML = `
    <div class="flex flex-wrap items-center gap-2">
      <span class="px-1.5 py-0.5 rounded font-bold text-[10px]" style="background:${{st.color}}25; color:${{st.color}}; border:1px solid ${{st.color}}60;">
        ${{st.symbol}} ${{st.name}}
      </span>
      <b>${{t.d}} ${{t.s}}</b>
      <span class="font-mono text-[10px]">Entrada: ${{t.in_d}} ($${{t.in_p}}) → Salida: ${{t.out_d}} ($${{t.out_p}})</span>
      <span class="font-bold ${{retCol}}">Cartera: ${{retSign}}${{t.pr}}% (Activo: ${{t.rr >= 0 ? '+' : ''}}${{t.rr}}%)</span>
      <span class="font-mono text-[10px] opacity-85">Capital en curva: <b>$${{t.eq.toLocaleString()}}</b></span>
    </div>
    <div class="text-[10px] opacity-80">${{t.rsn}} → <b>${{t.xrsn}}</b></div>
  `;
}}

function renderCurve() {{
  const svg = document.getElementById('equitySvg');
  const w = svg.clientWidth || 780;
  const h = svg.clientHeight || 195;
  const padL = 50, padR = 14, padT = 10, padB = 20;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const [zStart, zEnd] = ZOOM_RANGES[currentZoom];
  const activeMode = DATA.modes[currentModeId];

  // Filtrar puntos de la curva por el rango de Zoom
  const baseCurve = activeMode.monthly_curve.filter(p => p.date >= zStart && p.date <= zEnd);
  if (baseCurve.length < 2) return;

  const startDate = baseCurve[0].date;
  const endDate = baseCurve[baseCurve.length - 1].date;
  const tStart = new Date(startDate).getTime();
  const tEnd = new Date(endDate).getTime();
  const xMapDate = (dStr) => {{
    const t = new Date(dStr).getTime();
    const frac = Math.max(0, Math.min(1, (t - tStart) / Math.max(1, tEnd - tStart)));
    return padL + frac * plotW;
  }};

  // Determinar valores mínimo y máximo en la ventana de Zoom
  const allVals = [];
  const modesToDraw = showAllModes
    ? ['MODO_1_BASE', 'MODO_2_SCHERMAN', 'MODO_3_BASE', 'MODO_3_ELITE']
    : [currentModeId];

  modesToDraw.forEach(mKey => {{
    DATA.modes[mKey].monthly_curve.forEach(p => {{
      if (p.date >= zStart && p.date <= zEnd) {{
        allVals.push(p.bot_eq, p.spy_eq);
      }}
    }});
  }});

  const minVal = Math.max(4000, Math.min(...allVals) * 0.92);
  const maxVal = Math.max(...allVals) * 1.06;

  const yMap = (v) => {{
    const clV = Math.max(minVal, Math.min(maxVal, v));
    if (useLogScale) {{
      const lMin = Math.log10(minVal);
      const lMax = Math.log10(maxVal);
      const lv = Math.log10(clV);
      return padT + plotH - ((lv - lMin) / Math.max(0.0001, lMax - lMin)) * plotH;
    }}
    return padT + plotH - ((clV - minVal) / Math.max(1, maxVal - minVal)) * plotH;
  }};

  // Rejilla horizontal y etiquetas Y
  let gridHtml = '';
  const steps = 4;
  for (let s = 0; s <= steps; s++) {{
    const frac = s / steps;
    const val = useLogScale
      ? Math.pow(10, Math.log10(minVal) + frac * (Math.log10(maxVal) - Math.log10(minVal)))
      : minVal + frac * (maxVal - minVal);
    const y = yMap(val).toFixed(1);
    const lbl = val >= 1000 ? '$' + (val >= 100000 ? Math.round(val / 1000) : (val / 1000).toFixed(0)) + 'k' : '$' + Math.round(val);
    gridHtml += `<line x1="${{padL}}" y1="${{y}}" x2="${{w - padR}}" y2="${{y}}" stroke="currentColor" stroke-opacity="0.12" stroke-dasharray="3,3" />`;
    gridHtml += `<text x="${{padL - 5}}" y="${{Number(y) + 3}}" text-anchor="end" font-size="9" fill="currentColor" opacity="0.65">${{lbl}}</text>`;
  }}

  // Etiquetas de años en el eje X
  const seenYr = new Set();
  baseCurve.forEach((p) => {{
    const yr = p.date.slice(0, 4);
    if (!seenYr.has(yr)) {{
      seenYr.add(yr);
      if (currentZoom !== 'ALL' || ['2007','2009','2011','2013','2015','2017','2019','2021','2023','2025'].includes(yr)) {{
        const x = xMapDate(p.date).toFixed(1);
        gridHtml += `<line x1="${{x}}" y1="${{padT}}" x2="${{x}}" y2="${{h - padB}}" stroke="currentColor" stroke-opacity="0.08" />`;
        gridHtml += `<text x="${{x}}" y="${{h - 5}}" text-anchor="middle" font-size="9" fill="currentColor" opacity="0.65">${{yr}}</text>`;
      }}
    }}
  }});

  // Curva Benchmark S&P 500
  let spyPath = '';
  baseCurve.forEach((p, i) => {{
    const x = xMapDate(p.date).toFixed(1);
    const y = yMap(p.spy_eq).toFixed(1);
    spyPath += (i === 0 ? `M${{x}},${{y}}` : ` L${{x}},${{y}}`);
  }});

  // Colores de cada modo
  const modeColors = {{
    'MODO_1_BASE':     '#94a3b8',
    'MODO_2_SCHERMAN': '#fbbf24',
    'MODO_3_BASE':     '#2dd4bf',
    'MODO_3_ELITE':    '#10b981',
  }};

  let modesPathsHtml = `<path d="${{spyPath}}" fill="none" stroke="#3b82f6" stroke-width="1.6" stroke-dasharray="3,2" opacity="0.85" />`;

  modesToDraw.forEach(mKey => {{
    const mCurve = DATA.modes[mKey].monthly_curve.filter(p => p.date >= zStart && p.date <= zEnd);
    let dPath = '';
    mCurve.forEach((p, i) => {{
      const x = xMapDate(p.date).toFixed(1);
      const y = yMap(p.bot_eq).toFixed(1);
      dPath += (i === 0 ? `M${{x}},${{y}}` : ` L${{x}},${{y}}`);
    }});
    const isSel = (mKey === currentModeId);
    const sw = isSel ? '2.4' : '1.3';
    const op = isSel ? '1.0' : '0.55';
    modesPathsHtml += `<path d="${{dPath}}" fill="none" stroke="${{modeColors[mKey]}}" stroke-width="${{sw}}" opacity="${{op}}" />`;
  }});

  // Dibujar los puntos de ejecución de cada motor sobre la curva del Modo Activo
  let markersHtml = '';
  let shownCount = 0;
  let totalInZoom = 0;

  if (currentMotorFilter !== 'NONE') {{
    activeMode.trades.forEach((t, idx) => {{
      if (t.out_d < zStart || t.out_d > zEnd) return;
      if (currentMotorFilter !== 'ALL' && t.e !== currentMotorFilter) return;
      totalInZoom++;

      // Filtro anti-colapso: en vista global de 20 años muestra trades con impacto >= 1.2% o todos los de M2/M5
      if (filterDensity && currentMotorFilter === 'ALL' && Math.abs(t.pr) < 1.2 && t.e !== 'M5_VOL_CRUSH' && t.e !== 'M2_VIX_DIV') {{
        return;
      }}

      shownCount++;
      const cx = xMapDate(t.out_d).toFixed(1);
      const cy = yMap(t.eq).toFixed(1);
      const st = MOTOR_STYLE[t.e] || {{ color: '#10b981' }};
      const col = st.color;
      const strokeCol = t.win ? '#ffffff' : '#ef4444';

      // Forma geométrica distinta según el motor para distinguirlos visualmente
      if (t.e === 'M3_BEAR_SHORT') {{
        // Triángulo para Cortos Bear Market
        const p1 = `${{cx}},${{Number(cy) - 4.2}}`;
        const p2 = `${{Number(cx) - 3.8}},${{Number(cy) + 3.2}}`;
        const p3 = `${{Number(cx) + 3.8}},${{Number(cy) + 3.2}}`;
        markersHtml += `<polygon points="${{p1}} ${{p2}} ${{p3}}" fill="${{col}}" stroke="${{strokeCol}}" stroke-width="0.7" class="cursor-pointer" onmouseenter="showTradeDetails(${{idx}})" onclick="showTradeDetails(${{idx}})" />`;
      }} else if (t.e === 'M4_CTA_TREND') {{
        // Cuadrado para Materias Primas CTA
        markersHtml += `<rect x="${{Number(cx) - 3}}" y="${{Number(cy) - 3}}" width="6" height="6" fill="${{col}}" stroke="${{strokeCol}}" stroke-width="0.7" class="cursor-pointer" onmouseenter="showTradeDetails(${{idx}})" onclick="showTradeDetails(${{idx}})" />`;
      }} else if (t.e === 'M5_VOL_CRUSH') {{
        // Rombo grande violeta para Motor 5 (Vol-Crush VIX/VIX3M)
        const p1 = `${{cx}},${{Number(cy) - 5}}`;
        const p2 = `${{Number(cx) + 4.5}},${{cy}}`;
        const p3 = `${{cx}},${{Number(cy) + 5}}`;
        const p4 = `${{Number(cx) - 4.5}},${{cy}}`;
        markersHtml += `<polygon points="${{p1}} ${{p2}} ${{p3}} ${{p4}}" fill="${{col}}" stroke="#ffffff" stroke-width="0.9" class="cursor-pointer" onmouseenter="showTradeDetails(${{idx}})" onclick="showTradeDetails(${{idx}})" />`;
      }} else {{
        // Círculo para M1 Pullback / M2 Divergencia VIX
        const r = t.e === 'M2_VIX_DIV' ? 3.8 : 3.0;
        markersHtml += `<circle cx="${{cx}}" cy="${{cy}}" r="${{r}}" fill="${{col}}" stroke="${{strokeCol}}" stroke-width="0.6" class="cursor-pointer" onmouseenter="showTradeDetails(${{idx}})" onclick="showTradeDetails(${{idx}})" />`;
      }}
    }});
  }}

  document.getElementById('visibleMarkersCount').textContent =
    currentMotorFilter === 'NONE'
      ? 'Puntos ocultos'
      : `Mostrando ${{shownCount}} de ${{totalInZoom}} ejecuciones en ventana`;

  svg.innerHTML = gridHtml + modesPathsHtml + markersHtml;
}}

function renderRobustness() {{
  const r = DATA.robustness;
  const mc = r.monte_carlo;
  document.getElementById('mcBeatBadge').textContent = `Bate al S&P 500 en el ${{mc.prob_beat_sp500_pct}}% de los casos`;

  const mcRows = [
    {{ lbl: 'Percentil 5% (Escenario Pesimista P5)', eq: mc.p5_pessimistic.final_equity, cagr: mc.p5_pessimistic.cagr_pct, dd: mc.p5_pessimistic.worst_dd_p95_pct, col: 'text-amber-400' }},
    {{ lbl: 'Percentil 25% (Conservador P25)', eq: mc.p25_conservative.final_equity, cagr: mc.p25_conservative.cagr_pct, dd: mc.p25_conservative.dd_pct, col: 'text-blue-300' }},
    {{ lbl: '★ Mediana Estadística (P50)', eq: mc.p50_median.final_equity, cagr: mc.p50_median.cagr_pct, dd: mc.p50_median.median_dd_pct, col: 'text-emerald-400 font-bold' }},
    {{ lbl: 'Percentil 75% (Favorable P75)', eq: mc.p75_optimistic.final_equity, cagr: mc.p75_optimistic.cagr_pct, dd: mc.p75_optimistic.dd_pct, col: 'text-emerald-300' }},
    {{ lbl: 'Percentil 95% (Optimista P95)', eq: mc.p95_extreme.final_equity, cagr: mc.p95_extreme.cagr_pct, dd: mc.p95_extreme.best_dd_pct, col: 'text-purple-400' }},
  ];
  document.getElementById('mcTableBody').innerHTML = mcRows.map(x => `
    <tr class="border-b" style="border-color: var(--border-col);">
      <td class="py-1 ${{x.col}}">${{x.lbl}}</td>
      <td class="py-1 font-mono">$${{x.eq.toLocaleString()}}</td>
      <td class="py-1 font-bold">${{x.cagr}}%</td>
      <td class="py-1 text-rose-400">${{x.dd}}%</td>
    </tr>
  `).join('');

  document.getElementById('frictionTableBody').innerHTML = r.friction_test.map(f => `
    <tr class="border-b" style="border-color: var(--border-col);">
      <td class="py-1">${{f.scenario}}</td>
      <td class="py-1 font-mono font-bold text-emerald-400">$${{f.final_equity.toLocaleString()}}</td>
      <td class="py-1 font-bold">${{f.cagr_pct}}%</td>
      <td class="py-1">${{f.beats_sp500 ? '<span class="text-emerald-400 font-bold">✔ SÍ</span>' : 'NO'}}</td>
    </tr>
  `).join('');

  document.getElementById('subperiodTableBody').innerHTML = r.subperiods.map(sp => `
    <tr class="border-b" style="border-color: var(--border-col);">
      <td class="py-1">${{sp.period}}</td>
      <td class="py-1 font-mono">${{sp.spy_cum_ret_pct >= 0 ? '+' : ''}}${{sp.spy_cum_ret_pct}}%</td>
      <td class="py-1 font-mono font-bold text-emerald-400">+${{sp.bot_cum_ret_pct}}%</td>
      <td class="py-1 font-mono font-bold text-blue-400">+${{sp.alpha_pct}}%</td>
    </tr>
  `).join('');

  document.getElementById('paramTableBody').innerHTML = r.parameter_sensitivity.map(p => `
    <tr class="border-b" style="border-color: var(--border-col);">
      <td class="py-1 ${{(p.config.includes('★')) ? 'font-bold text-emerald-400' : ''}}">${{p.config}}</td>
      <td class="py-1 font-bold">${{p.cagr_pct}}%</td>
      <td class="py-1 text-amber-400">${{p.max_dd_pct}}%</td>
      <td class="py-1 font-mono">${{p.sharpe}} / ${{p.calmar}}</td>
    </tr>
  `).join('');
}}

function renderYears() {{
  const m = DATA.modes[currentModeId];
  const tbody = document.getElementById('yearlyTableBody');
  tbody.innerHTML = m.yearly.map(y => {{
    const isBear = y.spy_ret_pct < 0;
    const rowBg = isBear ? 'bg-red-500/10 font-semibold' : '';
    const spyCol = y.spy_ret_pct >= 0 ? 'text-blue-400' : 'text-red-400 font-bold';
    const botCol = y.bot_ret_pct >= 0 ? 'text-emerald-400 font-bold' : 'text-amber-400';
    const alphaCol = y.alpha_pct >= 0 ? 'text-emerald-400' : 'text-red-400';
    return `
      <tr class="border-b ${{rowBg}}" style="border-color: var(--border-col);">
        <td class="py-1 px-1.5">${{y.year}} ${{isBear ? '<span class="text-[9px] px-1 py-0.2 bg-red-500/20 text-red-400 rounded">CRISIS S&P</span>' : ''}}</td>
        <td class="py-1 px-1.5 ${{spyCol}}">${{y.spy_ret_pct >= 0 ? '+' : ''}}${{y.spy_ret_pct}}%</td>
        <td class="py-1 px-1.5 ${{botCol}}">${{y.bot_ret_pct >= 0 ? '+' : ''}}${{y.bot_ret_pct}}%</td>
        <td class="py-1 px-1.5 ${{alphaCol}}">${{y.alpha_pct >= 0 ? '+' : ''}}${{y.alpha_pct}}%</td>
        <td class="py-1 px-1.5">${{y.trades}}</td>
        <td class="py-1 px-1.5">${{y.win_rate}}%</td>
        <td class="py-1 px-1.5 text-right font-mono">$${{y.end_eq.toLocaleString()}}</td>
      </tr>
    `;
  }}).join('');
}}

function renderMotors() {{
  const m = DATA.modes[currentModeId];
  const container = document.getElementById('motorsList');
  container.innerHTML = Object.entries(m.engine_breakdown).map(([k, eng]) => {{
    const st = MOTOR_STYLE[k] || {{ color: '#10b981', symbol: '●' }};
    return `
      <div class="p-2 rounded border" style="border-color: var(--border-col);">
        <div class="flex items-center justify-between font-bold text-[11px]">
          <span style="color:${{st.color}}">${{st.symbol}} ${{eng.name}}</span>
          <span class="text-emerald-400">PF: ${{eng.profit_factor}}</span>
        </div>
        <div class="flex items-center justify-between text-[10px] opacity-80 mt-0.5">
          <span>Trades: <b>${{eng.trades}}</b></span>
          <span>Win Rate: <b>${{eng.win_rate}}%</b></span>
          <span>Ret Medio Cartera: <b>+${{eng.avg_ret_pct}}%</b></span>
          <span>Suma: <b>+${{eng.sum_ret_pct}}%</b></span>
        </div>
      </div>
    `;
  }}).join('');
}}

function renderTrades() {{
  const m = DATA.modes[currentModeId];
  const tbody = document.getElementById('tradesTableBody');
  const rev = [...m.trades].slice(-150).reverse();
  tbody.innerHTML = rev.map(t => {{
    const winCol = t.win ? 'text-emerald-400 font-bold' : 'text-red-400';
    const dirCol = t.d === 'LONG' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400';
    const st = MOTOR_STYLE[t.e] || {{ color: '#10b981', symbol: '●' }};
    return `
      <tr class="border-b" style="border-color: var(--border-col);">
        <td class="py-1 px-1 font-mono text-[10px]" style="color:${{st.color}}">${{st.symbol}} ${{t.e}}</td>
        <td class="py-1 px-1 font-bold">${{t.s}}</td>
        <td class="py-1 px-1"><span class="px-1 py-0.5 rounded text-[9px] font-bold ${{dirCol}}">${{t.d}}</span></td>
        <td class="py-1 px-1 font-mono text-[10px]">${{t.in_d}} ($${{t.in_p}})</td>
        <td class="py-1 px-1 font-mono text-[10px]">${{t.out_d}} ($${{t.out_p}})</td>
        <td class="py-1 px-1 font-mono text-[10px]">${{Math.round(t.w * 100)}}% (${{t.mc}}x)</td>
        <td class="py-1 px-1 ${{winCol}}">${{t.rr >= 0 ? '+' : ''}}${{t.rr}}%</td>
        <td class="py-1 px-1 ${{winCol}}">${{t.pr >= 0 ? '+' : ''}}${{t.pr}}%</td>
        <td class="py-1 px-1 text-[10px] opacity-80">${{t.rsn}} → <b>${{t.xrsn}}</b></td>
      </tr>
    `;
  }}).join('');
}}

function renderLive() {{
  const s = DATA.live_scan;
  const c = document.getElementById('liveScanContainer');
  const coreHtml = Object.entries(s.core_allocation).map(([sym, w]) =>
    `<span class="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 font-bold">${{sym}}: ${{w}}%</span>`
  ).join(' ');

  const assetsRows = s.assets.map(a => `
    <tr class="border-b" style="border-color: var(--border-col);">
      <td class="py-1 px-1.5 font-bold">${{a.symbol}}</td>
      <td class="py-1 px-1.5 font-mono">$${{a.close}}</td>
      <td class="py-1 px-1.5 font-mono">$${{a.sma200}}</td>
      <td class="py-1 px-1.5"><span class="px-1.5 py-0.5 rounded text-[9px] font-bold ${{a.trend === 'ALCISTA' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}}">${{a.trend}}</span></td>
      <td class="py-1 px-1.5 font-mono">${{a.rsi2}}</td>
      <td class="py-1 px-1.5 font-mono">${{a.realized_vol20}}%</td>
      <td class="py-1 px-1.5 font-mono">${{a.mom60_vol_adj >= 0 ? '+' : ''}}${{a.mom60_vol_adj}}</td>
      <td class="py-1 px-1.5 font-bold text-blue-400">${{a.core_weight_pct}}%</td>
    </tr>
  `).join('');

  c.innerHTML = `
    <div class="flex flex-wrap items-center justify-between gap-2 p-2 rounded border" style="border-color: var(--border-col);">
      <div>
        <div><b>Régimen Macro Detectado:</b> <span class="text-emerald-400 font-mono">${{s.regime}}</span></div>
        <div class="text-[10px] opacity-80">Estructura VIX/VIX3M: VIX=${{s.vix_close}} | VIX3M=${{s.vix3m_close}} | <b>Ratio VTS=${{s.vts_ratio}}</b> (${{s.vts_state}})</div>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="text-[10px] opacity-75">Asignación Core Élite Hoy:</span>
        ${{coreHtml || '<span class="opacity-70">100% Liquidez Defensiva</span>'}}
      </div>
    </div>
    <table class="w-full text-left border-collapse text-[11px]">
      <thead>
        <tr class="border-b opacity-75" style="border-color: var(--border-col);">
          <th class="py-1 px-1.5">Activo</th>
          <th class="py-1 px-1.5">Precio</th>
          <th class="py-1 px-1.5">SMA(200)</th>
          <th class="py-1 px-1.5">Régimen</th>
          <th class="py-1 px-1.5">RSI(2)</th>
          <th class="py-1 px-1.5">Vol 20d</th>
          <th class="py-1 px-1.5">Mom 60d Adj</th>
          <th class="py-1 px-1.5">Peso Core</th>
        </tr>
      </thead>
      <tbody>${{assetsRows}}</tbody>
    </table>
  `;
}}

function renderAll() {{
  renderKPIs();
  updateControlButtons();
  if (currentTab === 'curve') renderCurve();
  if (currentTab === 'robust') renderRobustness();
  if (currentTab === 'years') renderYears();
  if (currentTab === 'motors') renderMotors();
  if (currentTab === 'trades') renderTrades();
  if (currentTab === 'live') renderLive();
}}

window.addEventListener('resize', () => {{ if (currentTab === 'curve') renderCurve(); }});
renderAll();
</script>
</body>
</html>
"""

    for out_p in output_paths:
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[AegisDashboard] Generado: {out_p}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    summary_file = os.path.join(base_dir, "data", "aegis_backtest_summary.json")
    local_dash = os.path.join(base_dir, "dashboard.html")
    build_html_dashboard(summary_file, [local_dash])
