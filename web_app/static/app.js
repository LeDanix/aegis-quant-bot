/**
 * Aegis-Quant | Controlador Frontend (app.js)
 * Interfaz Institucional Mobile-First + Estudio Analítico (2007–2026).
 * Arquitectura unificada Modo 3 Élite (6 Motores + VTS) y Módulo Fiscal Automático AEAT.
 */

let APP_DATA = null;
let SUMMARY_LOADING = false;
let SUMMARY_ERROR = null;
let LAST_LIVE_STATUS = null;
let LAST_TAX_AUDIT = null;

const ACTIVE_MODE_ID = 'MODO_3_ELITE';
let ACTIVE_MOTOR_FILTER = 'TOP_IMPACT'; // 'NONE', 'TOP_IMPACT', 'M1_PULLBACK'..'M6_TOTM'
let ACTIVE_PERF_SUBTAB = 'chart'; // 'chart' | 'guide' | 'crisis' | 'simulator' | 'tax'
let ACTIVE_SECTION = 'inicio'; // 'inicio' | 'cartera' | 'etfs' | 'analisis' | 'sistema'
let ACTIVE_MOBILE_TAB = 'inicio';
let LAST_CONTROL_MOBILE_TAB = 'inicio';
let CHART_SCALE = 'value'; // 'value' | 'log'
let LIVE_CONFIG_INITIALIZED = false;

const SECTION_LABELS = {
  inicio: 'Inicio',
  cartera: 'Cartera',
  etfs: 'ETFs',
  analisis: 'Análisis',
  sistema: 'Sistema',
};

// Estado de la sección de gráficas de precios de ETFs
let ETF_CATALOG = [];
let ETF_DATA_CACHE = {};
let ACTIVE_ETF_SYMBOL = 'SPY';
let ETF_RANGE = '1Y'; // '1D' | '1S' | '1M' | '3M' | '6M' | '1Y' | '5Y' | 'ALL'
let ETF_CHART_TYPE = 'candle'; // 'candle' por defecto | 'line'
let etfFetchInFlight = false;

// Estado de sondeo y confirmaciones de seguridad
let livePollTimer = null;
let liveFetchInFlight = false;
let pendingDestructiveAction = null;
let pendingEngineDisconnect = null;

// Instancias Apache ECharts
let mainChart = null;
let ddChart = null;
let subperiodsChart = null;
let monteCarloChart = null;
let frictionChart = null;
let taxChart = null;
let etfChart = null;
let motorExampleChart = null;
let strategyExplainerChart = null;
let ACTIVE_EXPLAINER_MOTOR = 'M1_PULLBACK';
let ACTIVE_EXPLAINER_TOPIC = 'ARCHITECTURE';
let SHOW_BTC_EQUITY_CURVE = false;
let BTC_STUDY_DATA = null;
let btcStudyInFlight = false;

// Metadatos de los 6 Motores Cuantitativos + Núcleo Modo 3 Élite
const MOTOR_META = {
  M1_PULLBACK: {
    id: 'M1_PULLBACK',
    shortName: 'M1 · Pullback Tendencial',
    badge: 'M1 Pullback',
    color: '#065f46',
    pillCls: 'bg-brand-50 text-brand-800 border-brand-200 dark:bg-brand-950 dark:text-brand-200 dark:border-brand-800',
    symbolShape: 'circle',
    plainExplanation: 'Tendencia primaria alcista sobre SMA(200) con sobreventa aguda de corto plazo (RSI(2) < 10 o 3 cierres bajistas consecutivos). Captura la reversión institucional a la media en 3 a 5 sesiones.',
  },
  M2_VIX_DIV: {
    id: 'M2_VIX_DIV',
    shortName: 'M2 · Divergencia VIX',
    badge: 'M2 Divergencia VIX',
    color: '#0f766e',
    pillCls: 'bg-teal-50 text-teal-800 border-teal-200 dark:bg-slate-800 dark:text-teal-300 dark:border-slate-700',
    symbolShape: 'diamond',
    plainExplanation: 'El índice de volatilidad VIX marcó un pico de estrés superior a 20 en las últimas 5 sesiones y comenzó a ceder mientras el precio seguía deprimido, señalando agotamiento vendedor.',
  },
  M3_BEAR_SHORT: {
    id: 'M3_BEAR_SHORT',
    shortName: 'M3 · Corto en Crisis Bajista',
    badge: 'M3 Corto Crisis',
    color: '#b91c1c',
    pillCls: 'bg-red-50 text-red-800 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-900',
    symbolShape: 'triangle',
    plainExplanation: 'Régimen bajista confirmado bajo SMA(200) con alta volatilidad. Tras un rebote técnico sobrecomprado de corto plazo, abre cobertura bajista para rentabilizar caídas sistémicas.',
  },
  M4_CTA_TREND: {
    id: 'M4_CTA_TREND',
    shortName: 'M4 · Tendencia Multi-Activo CTA',
    badge: 'M4 Tendencia CTA',
    color: '#b45309',
    pillCls: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-slate-800 dark:text-amber-300 dark:border-slate-700',
    symbolShape: 'rect',
    plainExplanation: 'Ruptura de canal Donchian de 20 sesiones con alineación de medias en activos descorrelacionados (Oro GLD, Bonos TLT, Petróleo USO, Soja ZS o Bitcoin BTC), protegiendo frente a inflación y crisis.',
  },
  M5_VOL_CRUSH: {
    id: 'M5_VOL_CRUSH',
    shortName: 'M5 · Compresión VIX/VIX3M',
    badge: 'M5 Vol-Crush',
    color: '#4338ca',
    pillCls: 'bg-indigo-50 text-indigo-800 border-indigo-200 dark:bg-slate-800 dark:text-indigo-300 dark:border-slate-700',
    symbolShape: 'pin',
    plainExplanation: 'Tras un episodio de pánico en Backwardation (VIX > VIX3M), la estructura temporal de volatilidad se comprime con fuerza, confirmando el cierre de coberturas institucionales.',
  },
  M6_TOTM: {
    id: 'M6_TOTM',
    shortName: 'M6 · Flujo Fin de Mes (TOTM)',
    badge: 'M6 Fin de Mes',
    color: '#15803d',
    pillCls: 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-slate-800 dark:text-emerald-300 dark:border-slate-700',
    symbolShape: 'roundRect',
    plainExplanation: 'Debilidad moderada (RSI(2) < 35) en los últimos 2 días hábiles del mes bajo Contango, anticipando las aportaciones automáticas de planes de pensiones y nóminas de inicio de mes.',
  },
  CORE_BULL: {
    id: 'CORE_BULL',
    shortName: 'Núcleo Adaptativo Modo 3 (SPY/QQQ)',
    badge: 'Core Modo 3',
    color: '#065f46',
    pillCls: 'bg-brand-50 text-brand-800 border-brand-200 dark:bg-brand-950 dark:text-brand-200 dark:border-brand-800',
    symbolShape: 'circle',
    plainExplanation: 'Asignación base Dual-Momentum con objetivo de volatilidad en regímenes sanos de Contango (VIX < VIX3M), capitalizando tendencias alcistas sin fricción innecesaria.',
  },
};

const ASSET_NAMES = {
  SPY: 'S&P 500 (UCITS: SXR8 / SPYL)',
  QQQ: 'Nasdaq 100 (UCITS: EQQQ)',
  GLD: 'Oro Físico (UCITS: 4GLD / SGLD)',
  TLT: 'Bonos Tesoro 20+ (UCITS: DTLA)',
  USO: 'Petróleo WTI (UCITS: CRUD)',
  SOYB: 'Soja Agrícola (UCITS: SOYB)',
  ZS: 'Soja Agrícola (UCITS: SOYB)',
};

// Formateadores numéricos deterministas
function fmtUSD(val) {
  const n = Number(val || 0);
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function fmtEUR(val) {
  const n = Number(val || 0);
  const sign = n < 0 ? '-' : '';
  const abs = Math.abs(n);
  const parts = abs.toFixed(2).split('.');
  const intPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${sign}${intPart},${parts[1]} €`;
}

function fmtPct(val, sign = true) {
  const n = Number(val || 0);
  const prefix = sign && n > 0 ? '+' : '';
  return prefix + n.toFixed(2) + '%';
}

function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function getEngineMeta(engineKey) {
  if (!engineKey) return MOTOR_META.CORE_BULL;
  if (MOTOR_META[engineKey]) return MOTOR_META[engineKey];
  const upper = String(engineKey).toUpperCase();
  if (upper.includes('M1')) return MOTOR_META.M1_PULLBACK;
  if (upper.includes('M2')) return MOTOR_META.M2_VIX_DIV;
  if (upper.includes('M3')) return MOTOR_META.M3_BEAR_SHORT;
  if (upper.includes('M4')) return MOTOR_META.M4_CTA_TREND;
  if (upper.includes('M5')) return MOTOR_META.M5_VOL_CRUSH;
  if (upper.includes('M6') || upper.includes('TOTM')) return MOTOR_META.M6_TOTM;
  return MOTOR_META.CORE_BULL;
}

// ============================================================================
// GESTIÓN DE TEMA: MODO CLARO (BLANCO + VERDE) POR DEFECTO, OSCURO GRAFITO MATE
// ============================================================================
function isDarkMode() {
  return document.documentElement.classList.contains('dark');
}

function getChartTheme() {
  const dark = isDarkMode();
  return {
    dark,
    bg: 'transparent',
    text: dark ? '#d5dcd8' : '#464e4b',
    axisLabel: dark ? '#8b9490' : '#636c68',
    axisLine: dark ? '#2d3330' : '#dfe4e1',
    splitLine: dark ? '#212624' : '#eef1ef',
    tooltipBg: dark ? 'rgba(25, 29, 27, 0.98)' : 'rgba(255, 255, 255, 0.98)',
    tooltipBorder: dark ? '#2d3330' : '#dfe4e1',
    tooltipText: dark ? '#eef1ef' : '#121514',
    tooltipMuted: dark ? '#8b9490' : '#636c68',
    crosshair: dark ? '#464e4b' : '#c7cfcb',
    zoomBorder: dark ? '#2d3330' : '#dfe4e1',
    spyLine: dark ? '#8b9490' : '#636c68',
    ddSpyLine: dark ? '#636c68' : '#8b9490',
    ddSpyArea: dark ? 'rgba(99, 108, 104, 0.16)' : 'rgba(139, 148, 144, 0.16)',
    botLine: dark ? '#5c9d82' : '#065f46',
    botArea: dark ? 'rgba(92, 157, 130, 0.10)' : 'rgba(6, 95, 70, 0.08)',
    grossLine: dark ? '#8b9490' : '#475569',
    scatterBorder: dark ? '#191d1b' : '#ffffff',
  };
}

function applyTheme(dark, persist = false) {
  const root = document.documentElement;
  if (dark) {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }

  const metaTheme = document.getElementById('meta-theme-color');
  if (metaTheme) {
    metaTheme.setAttribute('content', dark ? '#121514' : '#ffffff');
  }

  if (persist) {
    try {
      localStorage.setItem('aegis_theme', dark ? 'dark' : 'light');
    } catch (e) {}
  }

  if (APP_DATA) {
    initMotorFilterButtons();
    if (mainChart && ddChart) updateMainCharts();
    if (subperiodsChart || monteCarloChart || frictionChart) initCrisisAndRobustnessCharts();
    if (taxChart) initTaxView();
  }
  if (ETF_CATALOG.length > 0) {
    renderEtfQuickCards();
  }
  if (etfChart && ETF_DATA_CACHE[ACTIVE_ETF_SYMBOL]) {
    renderEtfPriceChart(false);
  }
}

function toggleTheme() {
  applyTheme(!isDarkMode(), true);
}

// ============================================================================
// CICLO DE VIDA DE LA APLICACIÓN Y SONDEO INTELIGENTE
// ============================================================================
window.addEventListener('DOMContentLoaded', () => {
  // Cierre rápido de menús y modales con tecla Escape
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeDesktopNavMenu();
      closeMotorDetailModal();
      closeEngineConfirmModal();
      closeDestructiveConfirmModal();
      closeConfigModal();
    }
  });

  // Cerrar el menú desplegable de 3 rayas en escritorio al pulsar fuera
  document.addEventListener('click', (e) => {
    const wrapper = document.getElementById('desktop-nav-wrapper');
    if (wrapper && !wrapper.contains(e.target)) {
      closeDesktopNavMenu();
    }
  });

  window.addEventListener('resize', handleWindowResize);
  window.addEventListener('orientationchange', () => {
    setTimeout(handleWindowResize, 120);
  });

  // Pausar sondeo cuando la pantalla del móvil está apagada o en segundo plano
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopLivePolling();
    } else {
      fetchLiveStatus(false);
      startLivePolling();
      setTimeout(handleWindowResize, 80);
    }
  });

  // 1. Pintado inmediato del estado en vivo
  fetchLiveStatus(true);
  startLivePolling();

  // 2. Carga diferida en segundo plano del histórico 2007–2026
  setTimeout(() => {
    loadSummaryDataInBackground(false);
  }, 40);
});

function startLivePolling() {
  stopLivePolling();
  if (document.hidden) return;
  livePollTimer = setInterval(() => {
    if (!document.hidden) {
      fetchLiveStatus(false);
      // Auto-refresco horario si la sección activa es ETFs y ha pasado 1 hora
      if (typeof ACTIVE_SECTION !== 'undefined' && ACTIVE_SECTION === 'etfs') {
        const lastFetch = ETF_DATA_CACHE[ACTIVE_ETF_SYMBOL]?.fetchedAt || 0;
        if (lastFetch > 0 && (Date.now() - lastFetch > 3600 * 1000) && !etfFetchInFlight) {
          loadEtfData(ACTIVE_ETF_SYMBOL, true);
        }
      }
    }
  }, 5000);
}

function stopLivePolling() {
  if (livePollTimer) {
    clearInterval(livePollTimer);
    livePollTimer = null;
  }
}

async function loadSummaryDataInBackground(isManualRetry = false) {
  if (APP_DATA || SUMMARY_LOADING) return;
  SUMMARY_LOADING = true;
  SUMMARY_ERROR = null;

  const banner = document.getElementById('perf-loading-banner');
  const msgEl = document.getElementById('perf-loading-msg');
  const retryBtn = document.getElementById('perf-retry-btn');

  if (banner) banner.classList.remove('hidden');
  if (msgEl) msgEl.textContent = 'Cargando auditoría histórica cuantitativa 2007–2026...';
  if (retryBtn) retryBtn.classList.add('hidden');

  try {
    const res = await fetch('/api/summary');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    APP_DATA = await res.json();

    if (banner) banner.classList.add('hidden');

    renderHeadlinePerfKpis();
    initMotorFilterButtons();
    renderMotorBreakdownCards();
    renderDefaultTradeStory();
    renderYearlyTable();
    updateCustomSimulator();
    renderTradesTable();
    renderLiveScan();

    const viewPerf = document.getElementById('main-view-performance');
    if (viewPerf && !viewPerf.classList.contains('hidden')) {
      setTimeout(refreshActivePerfSubTabCharts, 40);
    }
  } catch (err) {
    SUMMARY_ERROR = err;
    console.error('Error cargando /api/summary:', err);
    if (msgEl) msgEl.textContent = 'No se pudo cargar el histórico 2007–2026.';
    if (retryBtn) retryBtn.classList.remove('hidden');
    if (isManualRetry && banner) banner.classList.remove('hidden');
  } finally {
    SUMMARY_LOADING = false;
  }
}

function renderHeadlinePerfKpis() {
  if (!APP_DATA || !APP_DATA.modes || !APP_DATA.modes[ACTIVE_MODE_ID]) return;
  const m = APP_DATA.modes[ACTIVE_MODE_ID];

  const setTxt = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setTxt('perf-kpi-final', fmtUSD(Math.round(m.final_equity)));
  setTxt('perf-kpi-spy-ref', `vs ${fmtUSD(Math.round(m.spy_final_equity))} S&P 500`);
  setTxt('perf-kpi-cagr', `${Number(m.cagr_pct).toFixed(2)}%`);
  setTxt('perf-kpi-dd', `${Number(m.max_dd_pct).toFixed(2)}%`);
  setTxt('perf-kpi-sharpe', `${Number(m.sharpe).toFixed(2)} Sharpe`);
  setTxt('perf-kpi-calmar', `Calmar ${Number(m.calmar).toFixed(2)} · Sortino ${Number(m.sortino).toFixed(2)}`);
  setTxt('perf-kpi-trades', `${m.total_trades} trades`);
  setTxt('perf-kpi-winrate', `${Number(m.win_rate).toFixed(1)}% acierto · PF ${Number(m.profit_factor).toFixed(2)}`);
  setTxt('trades-log-heading', `Registro Histórico de Operaciones (${m.total_trades} Operaciones)`);
}

function handleWindowResize() {
  if (mainChart) mainChart.resize();
  if (ddChart) ddChart.resize();
  if (subperiodsChart) subperiodsChart.resize();
  if (monteCarloChart) monteCarloChart.resize();
  if (frictionChart) frictionChart.resize();
  if (taxChart) taxChart.resize();
  if (etfChart) etfChart.resize();
  if (motorExampleChart) motorExampleChart.resize();
}

// ============================================================================
// NAVEGACIÓN UNIFICADA DE 5 SECCIONES (MÓVIL + MENÚ 3 RAYAS ESCRITORIO)
// Secciones: inicio | cartera | etfs | analisis | sistema
// ============================================================================
function updateSectionNavHighlight(sectionId) {
  ACTIVE_SECTION = sectionId;
  ACTIVE_MOBILE_TAB = sectionId;
  const sections = ['inicio', 'cartera', 'etfs', 'analisis', 'sistema'];

  sections.forEach((id) => {
    const mobBtn = document.getElementById(`mobile-tab-${id}`);
    if (mobBtn) {
      if (id === sectionId) mobBtn.classList.add('active');
      else mobBtn.classList.remove('active');
    }

    const deskItem = document.getElementById(`desktop-item-${id}`);
    if (deskItem) {
      if (id === sectionId) deskItem.classList.add('active');
      else deskItem.classList.remove('active');
    }
  });

  const deskLabel = document.getElementById('desktop-nav-current-label');
  if (deskLabel) {
    deskLabel.textContent = SECTION_LABELS[sectionId] || 'Inicio';
  }
}

function toggleDesktopNavMenu(event) {
  if (event) event.stopPropagation();
  const menu = document.getElementById('desktop-nav-menu');
  const btn = document.getElementById('desktop-nav-btn');
  const chevron = document.getElementById('desktop-nav-chevron');
  if (!menu) return;

  const willOpen = menu.classList.contains('hidden');
  if (willOpen) {
    menu.classList.remove('hidden');
    if (btn) btn.setAttribute('aria-expanded', 'true');
    if (chevron) chevron.classList.add('rotate-180');
  } else {
    closeDesktopNavMenu();
  }
}

function closeDesktopNavMenu() {
  const menu = document.getElementById('desktop-nav-menu');
  const btn = document.getElementById('desktop-nav-btn');
  const chevron = document.getElementById('desktop-nav-chevron');
  if (menu) menu.classList.add('hidden');
  if (btn) btn.setAttribute('aria-expanded', 'false');
  if (chevron) chevron.classList.remove('rotate-180');
}

function selectSectionFromMenu(sectionId) {
  closeDesktopNavMenu();
  switchSection(sectionId);
}

function switchSection(sectionId, options = {}) {
  const valid = ['inicio', 'cartera', 'etfs', 'analisis', 'sistema'];
  const target = valid.includes(sectionId) ? sectionId : 'inicio';
  const wasAlreadyEtfs = ACTIVE_SECTION === 'etfs' && target === 'etfs';

  closeDesktopNavMenu();
  updateSectionNavHighlight(target);

  const viewControl = document.getElementById('main-view-control');
  const viewEtfs = document.getElementById('main-view-etfs');
  const viewPerf = document.getElementById('main-view-performance');

  if (target === 'inicio' || target === 'cartera' || target === 'sistema') {
    LAST_CONTROL_MOBILE_TAB = target;
    if (viewControl) {
      viewControl.setAttribute('data-mobile-tab', target);
      viewControl.classList.remove('hidden');
    }
    if (viewEtfs) viewEtfs.classList.add('hidden');
    if (viewPerf) viewPerf.classList.add('hidden');
    fetchLiveStatus(false);
  } else if (target === 'etfs') {
    if (viewControl) viewControl.classList.add('hidden');
    if (viewPerf) viewPerf.classList.add('hidden');
    if (viewEtfs) viewEtfs.classList.remove('hidden');

    loadEtfData(ACTIVE_ETF_SYMBOL);
    setTimeout(() => {
      if (etfChart) etfChart.resize();
  if (motorExampleChart) motorExampleChart.resize();
      if (wasAlreadyEtfs || options.focusSelector) {
        const sel = document.getElementById('etf-symbol-select');
        if (sel) sel.focus();
      }
    }, 45);
  } else if (target === 'analisis') {
    if (viewControl) viewControl.classList.add('hidden');
    if (viewEtfs) viewEtfs.classList.add('hidden');
    if (viewPerf) viewPerf.classList.remove('hidden');

    if (!APP_DATA && !SUMMARY_LOADING) {
      loadSummaryDataInBackground(true);
    }
    setTimeout(refreshActivePerfSubTabCharts, 50);
  }

  window.scrollTo({ top: 0, behavior: 'auto' });
}

function switchMobileTab(tabId) {
  switchSection(tabId);
}

function switchMainView(viewId) {
  if (viewId === 'performance') {
    switchSection('analisis');
  } else if (viewId === 'etfs') {
    switchSection('etfs');
  } else {
    switchSection(LAST_CONTROL_MOBILE_TAB || 'inicio');
  }
}

function openEtfChartForSymbol(symbol) {
  const norm = symbol === 'SOYB' ? 'ZS' : String(symbol || 'SPY').toUpperCase();
  ACTIVE_ETF_SYMBOL = norm;
  switchSection('etfs');
}

// ============================================================================
// SECCIÓN ETFS: SELECTOR INTERACTIVO Y GRÁFICA DE PRECIOS + SMA50/200 + VOLUMEN
// ============================================================================
async function loadEtfData(symbol, forceRefresh = false) {
  const normSym = symbol === 'SOYB' ? 'ZS' : String(symbol || ACTIVE_ETF_SYMBOL || 'SPY').toUpperCase();
  ACTIVE_ETF_SYMBOL = normSym;

  const sel = document.getElementById('etf-symbol-select');
  if (sel && sel.value !== normSym) {
    sel.value = normSym;
  }

  const cachedEntry = ETF_DATA_CACHE[normSym];
  const isExpired = !cachedEntry || (Date.now() - (cachedEntry.fetchedAt || 0)) > 3600 * 1000;

  // Pintado inmediato desde caché en memoria si ya existe la serie y no ha expirado (1 hora)
  if (!forceRefresh && !isExpired && cachedEntry) {
    renderEtfQuickCards();
    renderEtfDetailHeader(cachedEntry);
    if (cachedEntry.hourly_meta) {
      updateEtfHourlyBadge(cachedEntry.hourly_meta);
    }
    renderEtfPriceChart(true);
    return;
  }

  const indicator = document.getElementById('etf-loading-indicator');
  if (indicator) indicator.classList.remove('hidden');
  etfFetchInFlight = true;

  try {
    const res = await fetch(`/api/etf/history?symbol=${encodeURIComponent(normSym)}&refresh=${forceRefresh ? 'true' : 'false'}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    if (!payload || !payload.ok || !payload.etf) {
      throw new Error(payload?.error || 'Respuesta inválida de /api/etf/history');
    }

    if (Array.isArray(payload.catalog) && payload.catalog.length > 0) {
      ETF_CATALOG = payload.catalog;
    }

    const resolvedSym = payload.selected_symbol || normSym;
    payload.etf.fetchedAt = Date.now();
    payload.etf.hourly_meta = payload.hourly_meta;
    ETF_DATA_CACHE[resolvedSym] = payload.etf;
    ACTIVE_ETF_SYMBOL = resolvedSym;

    if (sel && sel.value !== resolvedSym) {
      sel.value = resolvedSym;
    }

    updateEtfHourlyBadge(payload.hourly_meta);
    renderEtfQuickCards();
    renderEtfDetailHeader(payload.etf);

    const viewEtfs = document.getElementById('main-view-etfs');
    if (viewEtfs && !viewEtfs.classList.contains('hidden')) {
      renderEtfPriceChart(true);
    }
  } catch (err) {
    console.error('Error cargando histórico del ETF:', err);
    const chgEl = document.getElementById('etf-kpi-daychg');
    if (chgEl) chgEl.textContent = 'Error cargando serie de precios.';
  } finally {
    etfFetchInFlight = false;
    if (indicator) indicator.classList.add('hidden');
  }
}

function updateEtfHourlyBadge(hourlyMeta) {
  const updateBadge = document.getElementById('etf-last-update-text');
  if (updateBadge && hourlyMeta) {
    const humanTime = hourlyMeta.last_refresh_human || '--';
    updateBadge.textContent = `Actualizado: ${humanTime} (Auto 1h)`;
  }
}

function refreshEtfDataNow() {
  loadEtfData(ACTIVE_ETF_SYMBOL, true);
}

function selectEtfSymbol(symbol) {
  const normSym = symbol === 'SOYB' ? 'ZS' : String(symbol || 'SPY').toUpperCase();
  ACTIVE_ETF_SYMBOL = normSym;
  loadEtfData(normSym, false);
}

function renderEtfQuickCards() {
  const container = document.getElementById('etf-quick-cards');
  if (!container || ETF_CATALOG.length === 0) return;

  container.innerHTML = ETF_CATALOG.map((item) => {
    const isActive = item.symbol === ACTIVE_ETF_SYMBOL;
    const dayChg = Number(item.day_change_pct || 0);
    const chgCls = dayChg >= 0
      ? 'text-brand-700 dark:text-brand-300'
      : 'text-red-700 dark:text-red-400';
    const cardCls = isActive
      ? 'border-brand-700 bg-brand-50/80 dark:bg-slate-800 dark:border-brand-500 ring-1 ring-brand-700/20'
      : 'border-slate-200 dark:border-slate-700 bg-white hover:bg-slate-50 dark:bg-slate-900 dark:hover:bg-slate-800/70';
    const ucitsShort = String(item.ucits_ticker || '').split(' / ')[0];

    return `
      <button type="button" onclick="selectEtfSymbol('${escHtml(item.symbol)}')"
        class="p-2.5 rounded-md border ${cardCls} text-left transition">
        <div class="flex items-center justify-between gap-1 font-mono">
          <span class="text-xs font-bold text-slate-900 dark:text-slate-100">${escHtml(item.symbol)}</span>
          <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">${escHtml(ucitsShort)}</span>
        </div>
        <div class="flex items-baseline justify-between gap-1 mt-1.5 font-mono tabular-nums">
          <span class="text-xs font-bold text-slate-800 dark:text-slate-200">$${Number(item.last_close).toFixed(2)}</span>
          <span class="text-[11px] font-semibold ${chgCls}">${fmtPct(dayChg)}</span>
        </div>
      </button>
    `;
  }).join('');
}

function renderEtfDetailHeader(etfData) {
  if (!etfData || !etfData.meta || !etfData.metrics) return;
  const meta = etfData.meta;
  const m = etfData.metrics;

  const setTxt = (id, txt) => {
    const el = document.getElementById(id);
    if (el) el.textContent = txt;
  };

  setTxt('etf-kpi-price', `$${Number(m.last_close).toFixed(2)}`);

  const dayChgEl = document.getElementById('etf-kpi-daychg');
  if (dayChgEl) {
    const chg = Number(m.day_change_pct || 0);
    dayChgEl.textContent = `Sesión: ${fmtPct(chg)} · ${m.as_of_date}`;
    dayChgEl.className = `text-[11px] mt-1 font-mono tabular-nums truncate ${
      chg >= 0 ? 'text-brand-700 dark:text-brand-300 font-semibold' : 'text-red-700 dark:text-red-400 font-semibold'
    }`;
  }

  const ret1yEl = document.getElementById('etf-kpi-ret1y');
  if (ret1yEl) {
    const r1y = Number(m.ret_1y_pct || 0);
    ret1yEl.textContent = fmtPct(r1y);
    ret1yEl.className = `text-lg sm:text-2xl font-bold font-mono kpi-num mt-1 ${
      r1y >= 0 ? 'text-brand-700 dark:text-brand-300' : 'text-red-700 dark:text-red-400'
    }`;
  }

  setTxt('etf-kpi-retytd', `YTD: ${fmtPct(m.ret_ytd_pct)} · 3M: ${fmtPct(m.ret_3m_pct)}`);
  setTxt('etf-kpi-52w', `$${Number(m.low_52w).toFixed(2)} – $${Number(m.high_52w).toFixed(2)}`);
  setTxt('etf-kpi-ret-total', `5A: ${fmtPct(m.ret_5y_pct)} · Desde ${String(m.start_date).slice(0, 4)}: ${fmtPct(m.ret_total_pct)}`);

  const trendEl = document.getElementById('etf-kpi-trend');
  if (trendEl) {
    const isBull = m.trend === 'ALCISTA';
    trendEl.textContent = isBull ? 'ALCISTA (> SMA 200)' : 'BAJISTA (< SMA 200)';
    trendEl.className = isBull
      ? 'inline-block px-2 py-0.5 rounded text-xs font-mono font-bold bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300 border border-brand-200 dark:border-brand-800'
      : 'inline-block px-2 py-0.5 rounded text-xs font-mono font-bold bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300 border border-red-200 dark:border-red-900';
  }

  setTxt('etf-kpi-rsi2', `RSI(2): ${Number(m.rsi2).toFixed(1)} · SMA200: $${Number(m.sma200).toFixed(2)}`);
  setTxt('etf-chart-title', `${meta.symbol} · ${meta.display_name}`);
  setTxt(
    'etf-chart-subtitle',
    `Equivalente UCITS en Tradegate: ${meta.ucits_ticker} · ${m.bars_count.toLocaleString('es-ES')} sesiones diarias (${m.start_date} a ${m.as_of_date})`
  );

  setTxt('etf-meta-ucits', `${meta.ucits_ticker} · ${meta.venue}`);
  setTxt('etf-meta-isin', `ISIN: ${meta.isin} · TER: ${meta.ter}`);
  setTxt('etf-meta-smas', `SMA(50): $${Number(m.sma50).toFixed(2)} · SMA(200): $${Number(m.sma200).toFixed(2)}`);
  setTxt('etf-meta-dist', `Distancia a SMA(200): ${fmtPct(m.dist_sma200_pct)} · 1M: ${fmtPct(m.ret_1m_pct)}`);
  setTxt('etf-meta-engines', meta.engines);
  setTxt('etf-meta-class', meta.asset_class);
}

function computeEtfZoomStartPct(datesOrCount, rangeKey, isHourly = false) {
  if (!datesOrCount) return 0;
  if (rangeKey === 'ALL') return 0;

  let dates = [];
  let n = 0;
  if (Array.isArray(datesOrCount)) {
    dates = datesOrCount;
    n = dates.length;
  } else if (typeof datesOrCount === 'number') {
    n = datesOrCount;
  }
  if (n <= 1) return 0;

  // Cálculo por ventana temporal rodante exacta (exactamente 1 día, 1 semana, 1 mes... atrás)
  if (dates.length > 0) {
    const lastStr = dates[n - 1];
    const lastD = new Date(String(lastStr).replace(' ', 'T'));
    if (!isNaN(lastD.getTime())) {
      const targetD = new Date(lastD.getTime());
      if (rangeKey === '1D') {
        // 1 día completo rodante (24 horas hacia atrás)
        targetD.setDate(targetD.getDate() - 1);
      } else if (rangeKey === '1S') {
        // 1 semana completa rodante (7 días hacia atrás)
        targetD.setDate(targetD.getDate() - 7);
      } else if (rangeKey === '1M') {
        // 1 mes completo rodante hacia atrás
        targetD.setMonth(targetD.getMonth() - 1);
      } else if (rangeKey === '3M') {
        targetD.setMonth(targetD.getMonth() - 3);
      } else if (rangeKey === '6M') {
        targetD.setMonth(targetD.getMonth() - 6);
      } else if (rangeKey === '1Y') {
        targetD.setFullYear(targetD.getFullYear() - 1);
      } else if (rangeKey === '5Y') {
        targetD.setFullYear(targetD.getFullYear() - 5);
      }

      let idx = 0;
      for (let i = 0; i < n; i++) {
        const d = new Date(String(dates[i]).replace(' ', 'T'));
        if (d >= targetD) {
          idx = i;
          break;
        }
      }

      if (idx <= 0) return 0;
      const pct = (idx / n) * 100;
      return Math.max(0, Math.min(99.2, Number(pct.toFixed(2))));
    }
  }

  // Fallback por estimación de barras
  const fallbackBars = isHourly
    ? (rangeKey === '1D' ? 7 : 35)
    : (rangeKey === '1M' ? 22 : (rangeKey === '3M' ? 65 : (rangeKey === '6M' ? 130 : (rangeKey === '1Y' ? 253 : 1260))));
  if (fallbackBars >= n) return 0;
  const pct = ((n - fallbackBars) / n) * 100;
  return Math.max(0, Math.min(99.2, Number(pct.toFixed(2))));
}

function setEtfRange(rangeKey) {
  const wasHourly = (ETF_RANGE === '1D' || ETF_RANGE === '1S');
  const isHourly = (rangeKey === '1D' || rangeKey === '1S');
  ETF_RANGE = rangeKey;

  const keys = ['1D', '1S', '1M', '3M', '6M', '1Y', '5Y', 'ALL'];
  keys.forEach((k) => {
    const btn = document.getElementById(`etf-range-${k}`);
    if (!btn) return;
    if (k === rangeKey) {
      btn.className = 'px-2 py-1 rounded font-semibold bg-brand-700 text-white transition';
    } else {
      btn.className = 'px-2 py-1 rounded font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition';
    }
  });

  if (wasHourly !== isHourly) {
    renderEtfPriceChart(true);
  } else {
    const cached = ETF_DATA_CACHE[ACTIVE_ETF_SYMBOL];
    const s = (isHourly && cached?.hourly_series) ? cached.hourly_series : cached?.series;
    if (etfChart && s?.dates) {
      const startPct = computeEtfZoomStartPct(s.dates, rangeKey, isHourly);
      etfChart.dispatchAction({
        type: 'dataZoom',
        start: startPct,
        end: 100,
      });
    }
  }
}

function setEtfChartType(chartType) {
  ETF_CHART_TYPE = chartType === 'candle' ? 'candle' : 'line';
  const btnLine = document.getElementById('etf-type-line');
  const btnCandle = document.getElementById('etf-type-candle');

  if (btnLine) {
    btnLine.className = ETF_CHART_TYPE === 'line'
      ? 'px-2.5 py-1 rounded font-semibold bg-brand-700 text-white transition'
      : 'px-2.5 py-1 rounded font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition';
  }
  if (btnCandle) {
    btnCandle.className = ETF_CHART_TYPE === 'candle'
      ? 'px-2.5 py-1 rounded font-semibold bg-brand-700 text-white transition'
      : 'px-2.5 py-1 rounded font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition';
  }

  if (ETF_DATA_CACHE[ACTIVE_ETF_SYMBOL]) {
    renderEtfPriceChart(false);
  }
}

function renderEtfPriceChart(resetRange = false) {
  const el = document.getElementById('etf-price-chart');
  const etfData = ETF_DATA_CACHE[ACTIVE_ETF_SYMBOL];
  if (!el || !etfData) return;

  const isHourly = (ETF_RANGE === '1D' || ETF_RANGE === '1S');
  const s = (isHourly && etfData.hourly_series) ? etfData.hourly_series : etfData.series;
  if (!s || !s.dates || s.dates.length === 0) return;

  if (!etfChart) {
    etfChart = echarts.init(el);
  }

  const th = getChartTheme();
  const n = s.dates.length;
  const isMobile = window.innerWidth < 640;

  // Preservar zoom actual al alternar tema o Línea/Velas salvo cambio de ETF o salto horario/diario
  let startPct = computeEtfZoomStartPct(s.dates, ETF_RANGE, isHourly);
  let endPct = 100;
  if (!resetRange) {
    try {
      const currentOpt = etfChart.getOption();
      if (currentOpt && Array.isArray(currentOpt.dataZoom) && currentOpt.dataZoom[0]) {
        if (typeof currentOpt.dataZoom[0].start === 'number') startPct = currentOpt.dataZoom[0].start;
        if (typeof currentOpt.dataZoom[0].end === 'number') endPct = currentOpt.dataZoom[0].end;
      }
    } catch (e) {}
  }

  const upColor = th.dark ? '#5c9d82' : '#065f46';
  const downColor = th.dark ? '#ef4444' : '#b91c1c';
  const volUpColor = th.dark ? 'rgba(92, 157, 130, 0.42)' : 'rgba(6, 95, 70, 0.32)';
  const volDownColor = th.dark ? 'rgba(239, 68, 68, 0.38)' : 'rgba(185, 28, 28, 0.28)';

  const volumeBars = s.volumes.map((v, i) => ({
    value: v,
    itemStyle: {
      color: s.closes[i] >= s.opens[i] ? volUpColor : volDownColor,
    },
  }));

  let primaryPriceSeries;
  if (ETF_CHART_TYPE === 'candle') {
    const ohlcData = s.dates.map((_, i) => [s.opens[i], s.closes[i], s.lows[i], s.highs[i]]);
    primaryPriceSeries = {
      name: etfData.meta.symbol,
      type: 'candlestick',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: ohlcData,
      itemStyle: {
        color: upColor,
        color0: downColor,
        borderColor: upColor,
        borderColor0: downColor,
      },
    };
  } else {
    primaryPriceSeries = {
      name: etfData.meta.symbol,
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: s.closes,
      showSymbol: false,
      smooth: false,
      lineStyle: { width: 2, color: th.botLine },
      itemStyle: { color: th.botLine },
      areaStyle: { color: th.botArea },
    };
  }

  const option = {
    backgroundColor: th.bg,
    animationDuration: 220,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        lineStyle: { color: th.crosshair, width: 1 },
      },
      backgroundColor: th.tooltipBg,
      borderColor: th.tooltipBorder,
      borderWidth: 1,
      textStyle: { color: th.tooltipText, fontSize: 12 },
      formatter: (params) => {
        if (!Array.isArray(params) || params.length === 0) return '';
        const idx = params[0].dataIndex;
        if (idx == null || idx < 0 || idx >= n) return '';

        const d = s.dates[idx];
        const o = s.opens[idx];
        const h = s.highs[idx];
        const l = s.lows[idx];
        const c = s.closes[idx];
        const prev = idx > 0 ? s.closes[idx - 1] : c;
        const chg = prev > 0 ? ((c - prev) / prev) * 100 : 0;
        const chgColor = chg >= 0 ? upColor : downColor;
        const volM = (Number(s.volumes[idx] || 0) / 1e6).toFixed(2);

        return `
          <div style="font-family:'JetBrains Mono',monospace;min-width:195px;">
            <div style="font-weight:700;margin-bottom:4px;border-bottom:1px solid ${th.tooltipBorder};padding-bottom:3px;">
              ${escHtml(etfData.meta.symbol)} · ${escHtml(d)}
            </div>
            <div style="display:flex;justify-content:space-between;gap:12px;">
              <span style="color:${th.tooltipMuted};">Cierre:</span>
              <span style="font-weight:700;">$${Number(c).toFixed(2)} <span style="color:${chgColor};">(${fmtPct(chg)})</span></span>
            </div>
            <div style="display:flex;justify-content:space-between;gap:12px;font-size:11px;margin-top:2px;">
              <span style="color:${th.tooltipMuted};">A / M / m:</span>
              <span>$${Number(o).toFixed(2)} / $${Number(h).toFixed(2)} / $${Number(l).toFixed(2)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;gap:12px;font-size:11px;margin-top:2px;">
              <span style="color:#d97706;">SMA(50):</span>
              <span>$${Number(s.sma50[idx]).toFixed(2)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;gap:12px;font-size:11px;">
              <span style="color:${th.spyLine};">SMA(200):</span>
              <span>$${Number(s.sma200[idx]).toFixed(2)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;gap:12px;font-size:11px;margin-top:2px;">
              <span style="color:${th.tooltipMuted};">Volumen:</span>
              <span>${volM}M</span>
            </div>
          </div>
        `;
      },
    },
    axisPointer: {
      link: [{ xAxisIndex: 'all' }],
    },
    grid: [
      {
        left: isMobile ? 48 : 60,
        right: isMobile ? 12 : 20,
        top: 16,
        height: '64%',
      },
      {
        left: isMobile ? 48 : 60,
        right: isMobile ? 12 : 20,
        top: '82%',
        height: '11%',
      },
    ],
    xAxis: [
      {
        type: 'category',
        gridIndex: 0,
        data: s.dates,
        boundaryGap: ETF_CHART_TYPE === 'candle',
        axisLine: { lineStyle: { color: th.axisLine } },
        axisLabel: { color: th.axisLabel, fontSize: 10, fontFamily: 'JetBrains Mono' },
        min: 'dataMin',
        max: 'dataMax',
      },
      {
        type: 'category',
        gridIndex: 1,
        data: s.dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: th.axisLine } },
        axisTick: { show: false },
        axisLabel: { show: false },
        min: 'dataMin',
        max: 'dataMax',
      },
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        scale: true,
        splitLine: { lineStyle: { color: th.splitLine } },
        axisLabel: {
          color: th.axisLabel,
          fontSize: 10,
          fontFamily: 'JetBrains Mono',
          formatter: (v) => '$' + Math.round(v),
        },
      },
      {
        type: 'value',
        gridIndex: 1,
        scale: true,
        splitNumber: 2,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: startPct,
        end: endPct,
      },
      {
        type: 'slider',
        xAxisIndex: [0, 1],
        bottom: 2,
        height: 18,
        start: startPct,
        end: endPct,
        borderColor: th.zoomBorder,
        fillerColor: th.dark ? 'rgba(92, 157, 130, 0.14)' : 'rgba(6, 95, 70, 0.10)',
        textStyle: { color: th.axisLabel, fontSize: 10, fontFamily: 'JetBrains Mono' },
      },
    ],
    series: [
      primaryPriceSeries,
      {
        name: 'SMA(50)',
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: s.sma50,
        showSymbol: false,
        smooth: false,
        lineStyle: { width: 1.4, type: 'dashed', color: '#d97706' },
        itemStyle: { color: '#d97706' },
      },
      {
        name: 'SMA(200)',
        type: 'line',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: s.sma200,
        showSymbol: false,
        smooth: false,
        lineStyle: { width: 1.6, type: 'dashed', color: th.spyLine },
        itemStyle: { color: th.spyLine },
      },
      {
        name: 'Volumen',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumeBars,
        large: true,
      },
    ],
  };

  etfChart.setOption(option, true);
  etfChart.resize();
}

function refreshActivePerfSubTabCharts() {
  if (ACTIVE_PERF_SUBTAB === 'tax') {
    loadLiveTaxAudit();
  }
  if (!APP_DATA) return;
  if (ACTIVE_PERF_SUBTAB === 'chart') {
    if (!mainChart || !ddChart) {
      initMainCharts();
    } else {
      mainChart.resize();
      ddChart.resize();
      updateMainCharts();
    }
  } else if (ACTIVE_PERF_SUBTAB === 'crisis') {
    initCrisisAndRobustnessCharts();
    if (subperiodsChart) subperiodsChart.resize();
    if (monteCarloChart) monteCarloChart.resize();
    if (frictionChart) frictionChart.resize();
  } else if (ACTIVE_PERF_SUBTAB === 'tax') {
    initTaxView(false);
    if (taxChart) taxChart.resize();
  }
}

function switchPerfSubTab(subId) {
  ACTIVE_PERF_SUBTAB = subId;
  const subtabs = ['chart', 'guide', 'crisis', 'simulator', 'tax'];
  subtabs.forEach((id) => {
    const btn = document.getElementById(`subtab-${id}`);
    const view = document.getElementById(`perf-view-${id}`);
    if (id === subId) {
      if (btn) {
        btn.classList.add('active');
        try {
          btn.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        } catch (e) {}
      }
      if (view) view.classList.remove('hidden');
    } else {
      if (btn) btn.classList.remove('active');
      if (view) view.classList.add('hidden');
    }
  });

  setTimeout(refreshActivePerfSubTabCharts, 50);
}

// ============================================================================
// MODALES: CONFIGURACIÓN, DESCONEXIÓN DE MOTORES Y EMERGENCIA EN 2 PASOS
// ============================================================================
function openConfigModal() {
  const modal = document.getElementById('config-modal');
  if (!modal) return;
  modal.classList.remove('hidden');
  modal.classList.add('flex');
}

function closeConfigModal() {
  const modal = document.getElementById('config-modal');
  if (!modal) return;
  modal.classList.add('hidden');
  modal.classList.remove('flex');
}

function updateEngineStateLabels() {
  for (let i = 1; i <= 6; i++) {
    const chk = document.getElementById(`chk-m${i}`);
    const lbl = document.getElementById(`lbl-state-m${i}`);
    if (!chk || !lbl) continue;
    if (chk.checked) {
      lbl.textContent = 'ACTIVO';
      lbl.className = 'font-mono text-[10px] font-semibold text-brand-700 dark:text-brand-300 shrink-0';
    } else {
      lbl.textContent = 'DESACTIVADO';
      lbl.className = 'font-mono text-[10px] font-semibold text-red-700 dark:text-red-400 shrink-0';
    }
  }
}

function handleEngineToggleChange(checkboxEl, engineId, engineLabel) {
  if (!checkboxEl) return;
  // Si el usuario intenta desmarcar un motor activo, exigir confirmación explícita
  if (!checkboxEl.checked) {
    checkboxEl.checked = true;
    pendingEngineDisconnect = {
      checkboxId: checkboxEl.id,
      engineId,
      engineLabel,
    };
    const modal = document.getElementById('engine-confirm-modal');
    const desc = document.getElementById('engine-confirm-desc');
    if (desc) {
      desc.textContent = `¿Deseas desconectar ${engineLabel}? Al guardar los parámetros operativos, el bot dejará de evaluar y ejecutar señales de este motor hasta que vuelvas a activarlo.`;
    }
    if (modal) {
      modal.classList.remove('hidden');
      modal.classList.add('flex');
    }
  } else {
    updateEngineStateLabels();
  }
}

function confirmEngineDisconnect() {
  if (pendingEngineDisconnect && pendingEngineDisconnect.checkboxId) {
    const chk = document.getElementById(pendingEngineDisconnect.checkboxId);
    if (chk) {
      chk.checked = false;
    }
  }
  closeEngineConfirmModal();
}

function closeEngineConfirmModal() {
  pendingEngineDisconnect = null;
  const modal = document.getElementById('engine-confirm-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
  updateEngineStateLabels();
}

function openDestructiveConfirmModal(actionName) {
  pendingDestructiveAction = actionName;
  const modal = document.getElementById('confirm-action-modal');
  const titleEl = document.getElementById('confirm-modal-title');
  const descEl = document.getElementById('confirm-modal-desc');
  const ctxEl = document.getElementById('confirm-modal-context');
  const chk = document.getElementById('confirm-safety-check');
  const confirmBtn = document.getElementById('btn-confirm-destructive');

  if (!modal) return;
  if (chk) chk.checked = false;
  if (confirmBtn) confirmBtn.disabled = true;

  const state = LAST_LIVE_STATUS?.state || {};
  const acct = state.account || {};
  const posCount = (state.positions || []).length;
  const eq = fmtUSD(acct.total_equity_usd || 10000);
  const posVal = fmtUSD(acct.positions_value_usd || 0);

  if (actionName === 'PANIC_CLOSE_ALL') {
    if (titleEl) titleEl.textContent = 'Liquidar Cartera a Efectivo';
    if (descEl) {
      descEl.textContent = 'Se enviarán órdenes de cierre inmediato sobre el 100% de las posiciones abiertas, pasando toda la cuenta a liquidez.';
    }
    if (ctxEl) {
      ctxEl.textContent = `Posiciones activas: ${posCount} (${posVal}) · Patrimonio actual: ${eq}`;
    }
    if (confirmBtn) confirmBtn.textContent = 'Liquidar Cartera';
  } else if (actionName === 'SCAN_NOW') {
    if (titleEl) titleEl.textContent = 'Forzar Escaneo y Rebalanceo Inmediato';
    if (descEl) {
      descEl.textContent = 'Precaución: El bot opera de forma programada a las 21:55 CET. Forzar un escaneo fuera de hora evaluará precios intradía y ejecutará compras o ventas en el bróker si el modo es Automático.';
    }
    if (ctxEl) {
      ctxEl.textContent = `Bróker: ${LAST_LIVE_STATUS?.config?.broker_provider || 'LOCAL_PAPER'} · Modo: ${LAST_LIVE_STATUS?.config?.execution_mode || 'AUTO_100'}`;
    }
    if (confirmBtn) confirmBtn.textContent = 'Forzar Escaneo Ahora';
  } else {
    if (titleEl) titleEl.textContent = 'Reiniciar Saldo Paper Trading';
    if (descEl) {
      descEl.textContent = 'Se restablecerá el capital inicial de simulación Paper, vaciando las posiciones abiertas y el historial reciente.';
    }
    if (ctxEl) {
      const baseCap = fmtUSD(LAST_LIVE_STATUS?.config?.allocated_capital_usd || 10000);
      ctxEl.textContent = `Patrimonio actual: ${eq} -> Nuevo saldo inicial: ${baseCap}`;
    }
    if (confirmBtn) confirmBtn.textContent = 'Reiniciar Saldo';
  }

  modal.classList.remove('hidden');
  modal.classList.add('flex');
}

function closeDestructiveConfirmModal() {
  pendingDestructiveAction = null;
  const modal = document.getElementById('confirm-action-modal');
  if (!modal) return;
  modal.classList.add('hidden');
  modal.classList.remove('flex');
}

function toggleDestructiveConfirmBtn() {
  const chk = document.getElementById('confirm-safety-check');
  const confirmBtn = document.getElementById('btn-confirm-destructive');
  if (confirmBtn && chk) {
    confirmBtn.disabled = !chk.checked;
  }
}

function executeConfirmedDestructiveAction() {
  const chk = document.getElementById('confirm-safety-check');
  if (!pendingDestructiveAction || !chk || !chk.checked) return;
  const act = pendingDestructiveAction;
  closeDestructiveConfirmModal();
  triggerLiveAction(act, null, true);
}

// ============================================================================
// FILTROS DE LOS 6 MOTORES SOBRE LA CURVA DE EQUITY
// ============================================================================
function initMotorFilterButtons() {
  const container = document.getElementById('motor-filter-buttons');
  if (!container || !APP_DATA) return;

  const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
  const breakdown = modeData.engine_breakdown || {};

  const filters = [
    { id: 'TOP_IMPACT', label: 'Top 35 Mayor Impacto' },
    { id: 'NONE', label: 'Ocultar Marcadores' },
    { id: 'M1_PULLBACK', label: `M1 Pullback (${breakdown.M1_PULLBACK?.trades || 0})` },
    { id: 'M2_VIX_DIV', label: `M2 VIX (${breakdown.M2_VIX_DIV?.trades || 0})` },
    { id: 'M3_BEAR_SHORT', label: `M3 Corto (${breakdown.M3_BEAR_SHORT?.trades || 0})` },
    { id: 'M4_CTA_TREND', label: `M4 CTA (${breakdown.M4_CTA_TREND?.trades || 0})` },
    { id: 'M5_VOL_CRUSH', label: `M5 Vol-Crush (${breakdown.M5_VOL_CRUSH?.trades || 0})` },
    { id: 'M6_TOTM', label: `M6 Fin de Mes (${breakdown.M6_TOTM?.trades || 0})` },
  ];

  container.innerHTML = filters
    .map((f) => {
      const active = f.id === ACTIVE_MOTOR_FILTER;
      const cls = active
        ? 'bg-brand-700 text-white border-brand-700'
        : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 border-slate-300 dark:border-slate-700';
      return `
        <button onclick="setMotorFilter('${f.id}')" class="shrink-0 whitespace-nowrap px-2.5 py-1.5 sm:py-1 rounded-md text-xs font-semibold border transition ${cls}">
          ${f.label}
        </button>
      `;
    })
    .join('');
}

function setMotorFilter(filterId) {
  ACTIVE_MOTOR_FILTER = filterId;
  initMotorFilterButtons();
  updateMainCharts();

  if (filterId !== 'NONE' && APP_DATA) {
    const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
    let candidates = modeData.trades || [];
    if (filterId !== 'TOP_IMPACT') {
      candidates = candidates.filter((t) => t.engine_id === filterId);
    }
    if (candidates.length > 0) {
      const best = [...candidates].sort((a, b) => Math.abs(b.portfolio_ret_pct) - Math.abs(a.portfolio_ret_pct))[0];
      renderTradeStory(best);
    }
  }
}


// ============================================================================
// FICHA TÉCNICA Y ESTUDIO INTERACTIVO DE MOTORES CUANTITATIVOS (M1–M6)
// ============================================================================
const MOTOR_EXPLAINER_DATA = {
  "M1_PULLBACK": {
    "badge": "M1 Pullback",
    "title": "Motor 1: Pullback Tendencial",
    "subtitle": "Reversi\u00f3n a la media en SPY y QQQ dentro de tendencias primarias alcistas",
    "dir": "LONG",
    "assets": "SPY (S&P 500) y QQQ (Nasdaq 100)",
    "holding": "1\u20135 sesiones (m\u00e1x. 10 d\u00edas)",
    "stop": "2.5x ATR(14) din\u00e1mico (~1.8% a 2.5%)",
    "target": "Cierre > SMA(5) o RSI(2) > 75",
    "trades": "328 operaciones",
    "winRate": "72.6%",
    "sumRet": "+74.59%",
    "pf": "1.91",
    "why": "<p><b>\u00bfPor qu\u00e9 existe esta ventaja y qu\u00e9 sentido tiene?</b><br>En \u00edndices burs\u00e1tiles diversificados como el S&P 500 o el Nasdaq 100, las empresas subyacentes no quiebran al un\u00edsono. Cuando el mercado se encuentra en una tendencia secular sana (por encima de su media institucional de 200 d\u00edas), las ca\u00eddas repentinas de 2 o 3 sesiones provocadas por noticias de impacto generan liquidaciones impulsivas de inversores minoristas y saltos de stop-loss automatizados.</p><p>Los creadores de mercado (<i>market makers</i>) e inversores institucionales aprovechan esa sobreelevada prima de liquidez para absorber papel con descuento. La reversi\u00f3n a la media es una ley emp\u00edrica s\u00f3lida en renta variable estadounidense: el precio tiende a rebotar con alta probabilidad hacia su equilibrio de corto plazo en 3 a 5 sesiones.</p>",
    "code": "def _check_entry(self, b: EnrichedBar):\n    # 1. Filtro tendencial macro: precio sobre media de 200 d\u00edas y volatilidad positiva\n    if b.close <= b.sma200 or b.atr14 <= 0:\n        return False, \"\"\n    \n    # 2. Gatillo de capitulaci\u00f3n (basta uno de tres):\n    cond_rsi = b.rsi2 < 10.0                          # Sobreventa extrema\n    cond_band = b.close < b.lower_band30 and b.rsi2 < 25.0  # Perforaci\u00f3n banda Bollinger\n    cond_streak = b.down_streak >= 3 and b.rsi2 < 18.0     # 3 o m\u00e1s d\u00edas rojos seguidos\n    \n    if cond_rsi or cond_band or cond_streak:\n        return True, \"Pullback Tendencial validado\"\n    return False, \"\"\n\n# Salida: Cierre sobre media corta SMA(5) o RSI(2) > 75 (o Stop ATR 2.5x)",
    "sample": {
      "sym": "QQQ",
      "entry": "2020-02-28",
      "entryPrice": "$205.80",
      "exit": "2020-03-02",
      "exitPrice": "$216.42",
      "ret": "+5.16%",
      "days": "1 sesi\u00f3n",
      "story": "Caso Real: El 28-02-2020, durante el inicio del p\u00e1nico por COVID-19, QQQ cay\u00f3 marcando un RSI(2) de 6.2 y perforando su banda de Bollinger, manteniendo a\u00fan soporte sobre SMA(200). El Motor 1 compr\u00f3 en el cierre a $205.80. En la sesi\u00f3n siguiente, el rebote institucional devolvi\u00f3 el precio sobre la SMA(5), cerrando a $216.42 con un +5.16% de beneficio limpio en 24 horas."
    },
    "chartData": {
      "dates": [
        "2020-02-20",
        "2020-02-21",
        "2020-02-24",
        "2020-02-25",
        "2020-02-26",
        "2020-02-27",
        "2020-02-28",
        "2020-03-02",
        "2020-03-03",
        "2020-03-04",
        "2020-03-05",
        "2020-03-06",
        "2020-03-09"
      ],
      "candles": [
        [
          236.46,
          234.78,
          231.88,
          236.95
        ],
        [
          233.61,
          230.27,
          229.32,
          234.01
        ],
        [
          221.68,
          221.39,
          220.26,
          224.25
        ],
        [
          223.25,
          215.37,
          214.74,
          223.99
        ],
        [
          216.71,
          216.48,
          214.9,
          220.28
        ],
        [
          210.9,
          205.64,
          205.5,
          216.42
        ],
        [
          198.64,
          205.8,
          198.17,
          207.17
        ],
        [
          208.88,
          216.42,
          205.94,
          216.57
        ],
        [
          217.11,
          209.48,
          207.62,
          219.61
        ],
        [
          213.32,
          218.22,
          211.37,
          218.33
        ],
        [
          212.69,
          211.59,
          210.1,
          216.36
        ],
        [
          204.67,
          208.02,
          202.91,
          209.15
        ],
        [
          193.48,
          193.57,
          192.11,
          201.16
        ]
      ],
      "entry_date": "2020-02-28",
      "exit_date": "2020-03-02",
      "entry_idx": 6,
      "exit_idx": 7
    }
  },
  "M2_VIX_DIV": {
    "badge": "M2 Divergencia VIX",
    "title": "Motor 2: Divergencia Intermercado VIX",
    "subtitle": "Agotamiento vendedor detectado por desinflado de volatilidad impl\u00edcita en opciones",
    "dir": "LONG",
    "assets": "SPY (S&P 500) y QQQ (Nasdaq 100)",
    "holding": "2\u20136 sesiones (m\u00e1x. 10 d\u00edas)",
    "stop": "2.2x ATR(14) din\u00e1mico",
    "target": "Cierre > SMA(5) con >=2 d\u00edas o RSI(2) > 80",
    "trades": "28 operaciones",
    "winRate": "71.4%",
    "sumRet": "+3.54%",
    "pf": "1.31",
    "why": "<p><b>\u00bfPor qu\u00e9 existe esta ventaja y qu\u00e9 sentido tiene?</b><br>El \u00edndice VIX del CBOE mide la demanda de opciones put para proteger carteras institucionales. Cuando las acciones marcan nuevos m\u00ednimos relativos o permanecen en sobreventa, pero el VIX no logra marcar un nuevo m\u00e1ximo y comienza a caer desde niveles de estr\u00e9s (>=20.0), se produce una <b>divergencia intermercado</b>.</p><p>Significa que los grandes gestores ya han comprado todas las coberturas que necesitaban y ya no est\u00e1n dispuestos a pagar primas caras. Al desaparecer la compra de puts, la presi\u00f3n vendedora en el mercado de futuros se agota, abriendo paso a un rally alcista inminente.</p>",
    "code": "def _check_entry(self, b: EnrichedBar, recent_bars: List[EnrichedBar]):\n    if b.close <= b.sma200 * 0.96 or b.rsi2 >= 20.0:\n        return False, \"\"\n    \n    recent_vix_high = max(x.vix_close for x in recent_bars) # Pico VIX en 5 d\u00edas\n    recent_px_low = min(x.low for x in recent_bars)          # M\u00ednimo del precio\n    \n    # El VIX cae m\u00e1s de un 4% desde su pico mientras el precio sigue deprimido\n    vix_turning_down = (\n        recent_vix_high >= 20.0\n        and b.vix_close < recent_vix_high * 0.96\n        and (b.low <= recent_px_low * 1.008 or b.rsi2 < 12.0)\n    )\n    return (True, \"Divergencia VIX\") if vix_turning_down else (False, \"\")",
    "sample": {
      "sym": "QQQ",
      "entry": "2009-05-21",
      "entryPrice": "$33.65",
      "exit": "2009-05-26",
      "exitPrice": "$34.79",
      "ret": "+3.39%",
      "days": "2 sesiones",
      "story": "Caso Real: El 21-05-2009, tras un pico de volatilidad VIX en 33.1, el \u00edndice comenz\u00f3 a ceder hasta 31.4 mientras el precio de QQQ tocaba m\u00ednimos en sobreventa (RSI 18.5). El Motor 2 detect\u00f3 la divergencia y compr\u00f3 a $33.65. Dos sesiones despu\u00e9s, la normalizaci\u00f3n sobre SMA(5) cerr\u00f3 la operaci\u00f3n a $34.79 con +3.39% de ganancia."
    },
    "chartData": {
      "dates": [
        "2009-05-13",
        "2009-05-14",
        "2009-05-15",
        "2009-05-18",
        "2009-05-19",
        "2009-05-20",
        "2009-05-21",
        "2009-05-22",
        "2009-05-26",
        "2009-05-27",
        "2009-05-28",
        "2009-05-29",
        "2009-06-01",
        "2009-06-02"
      ],
      "candles": [
        [
          33.63,
          33.02,
          32.96,
          33.65
        ],
        [
          33.1,
          33.39,
          33.08,
          33.7
        ],
        [
          33.34,
          33.37,
          33.23,
          33.82
        ],
        [
          33.6,
          34.24,
          33.39,
          34.28
        ],
        [
          34.16,
          34.4,
          33.95,
          34.74
        ],
        [
          34.53,
          34.28,
          34.18,
          35.04
        ],
        [
          34.02,
          33.65,
          33.31,
          34.26
        ],
        [
          33.78,
          33.54,
          33.32,
          33.97
        ],
        [
          33.25,
          34.79,
          33.18,
          34.83
        ],
        [
          34.69,
          34.55,
          34.43,
          35.19
        ],
        [
          34.76,
          34.95,
          34.21,
          35.07
        ],
        [
          34.97,
          35.38,
          34.76,
          35.5
        ],
        [
          35.76,
          36.39,
          35.61,
          36.5
        ],
        [
          36.19,
          36.44,
          36.11,
          36.79
        ]
      ],
      "entry_date": "2009-05-21",
      "exit_date": "2009-05-26",
      "entry_idx": 6,
      "exit_idx": 8
    }
  },
  "M3_BEAR_SHORT": {
    "badge": "M3 Corto en Crisis",
    "title": "Motor 3: Corto en Mercado Bajista (Crisis Alpha)",
    "subtitle": "Monetizaci\u00f3n de ca\u00eddas sist\u00e9micas en reg\u00edmenes bajistas confirmados",
    "dir": "SHORT (ETF inverso DXS3)",
    "assets": "SPY / QQQ (Inverso -1x en Tradegate)",
    "holding": "2\u20138 sesiones (m\u00e1x. 12 d\u00edas)",
    "stop": "2.2x ATR(14) por encima de la entrada",
    "target": "Cierre < SMA(5) o RSI(2) < 20 / 12 sesiones",
    "trades": "114 operaciones",
    "winRate": "58.8%",
    "sumRet": "+16.30%",
    "pf": "1.32",
    "why": "<p><b>\u00bfPor qu\u00e9 existe esta ventaja y qu\u00e9 sentido tiene?</b><br>Durante los grandes mercados bajistas (como el crash de 2008 o el mercado bajista de 2022), los rebotes temporales no son compras institucionales sanas, sino cierres de posiciones cortas (<i>short covering</i>). Al toparse con la resistencia de la media m\u00f3vil de 200 d\u00edas y agotarse el impulso comprador, el precio se desploma de nuevo con virulencia.</p><p>El Motor 3 no opera cortos en mercados normales; espera exclusivamente a que la tendencia estructural sea bajista confirmada (Precio < SMA200 y SMA50 < SMA200) y abre posici\u00f3n corta cuando un rebote t\u00e9cnico se sobrecompra (RSI(2) > 85 con VIX > 18) o se produce una ruptura de m\u00ednimos de 20 d\u00edas con p\u00e1nico.</p>",
    "code": "def _check_entry(self, b: EnrichedBar):\n    # 1. R\u00e9gimen bajista confirmado\n    is_bear = (b.close < b.sma200) and (b.sma50 < b.sma200 or not b.sma200_rising)\n    if not is_bear:\n        return False, \"\"\n    \n    # 2. Gatillo: Rebote sobrecomprado en mercado bajista listo para colapsar\n    cond_bounce = (\n        (b.rsi2 > 85.0 or b.up_streak >= 3)\n        and b.close < b.sma200 * 0.99\n        and b.vix_close > 18.0\n    )\n    return (True, \"Bear Rally Exhaustion\") if cond_bounce else (False, \"\")",
    "sample": {
      "sym": "QQQ",
      "entry": "2008-10-13",
      "entryPrice": "$35.13",
      "exit": "2008-10-15",
      "exitPrice": "$30.60",
      "ret": "+12.90%",
      "days": "2 sesiones",
      "story": "Caso Real: En plena crisis financiera de 2008 (13-10-2008), tras una subida de 3 d\u00edas con RSI(2) en 87.2 y VIX disparado a 55.0, el Motor 3 vendi\u00f3 corto a $35.13. Dos sesiones m\u00e1s tarde, el desplome bajista llev\u00f3 a QQQ a $30.60, cerrando la posici\u00f3n con un rendimiento positivo del +12.90% mientras el mercado se hund\u00eda."
    },
    "chartData": {
      "dates": [
        "2008-10-03",
        "2008-10-06",
        "2008-10-07",
        "2008-10-08",
        "2008-10-09",
        "2008-10-10",
        "2008-10-13",
        "2008-10-14",
        "2008-10-15",
        "2008-10-16",
        "2008-10-17",
        "2008-10-20",
        "2008-10-21",
        "2008-10-22"
      ],
      "candles": [
        [
          37.26,
          36.18,
          36.1,
          38.18
        ],
        [
          35.26,
          34.86,
          32.91,
          35.53
        ],
        [
          35.14,
          32.65,
          32.27,
          35.2
        ],
        [
          31.95,
          32.39,
          31.84,
          34.12
        ],
        [
          33.15,
          31.52,
          30.97,
          33.68
        ],
        [
          30.52,
          31.32,
          29.38,
          32.48
        ],
        [
          32.86,
          35.13,
          32.4,
          35.25
        ],
        [
          36.15,
          33.61,
          33.19,
          36.15
        ],
        [
          33.23,
          30.6,
          30.54,
          33.35
        ],
        [
          30.81,
          32.26,
          29.25,
          32.27
        ],
        [
          31.67,
          32.3,
          31.41,
          33.65
        ],
        [
          32.76,
          33.2,
          31.7,
          33.26
        ],
        [
          32.66,
          31.48,
          31.48,
          33.26
        ],
        [
          31.37,
          30.61,
          29.71,
          31.6
        ]
      ],
      "entry_date": "2008-10-13",
      "exit_date": "2008-10-15",
      "entry_idx": 6,
      "exit_idx": 8
    }
  },
  "M4_CTA_TREND": {
    "badge": "M4 Tendencia CTA",
    "title": "Motor 4: Tendencia Multi-Activo CTA",
    "subtitle": "Seguimiento sistem\u00e1tico de tendencias en Oro, Petr\u00f3leo, Bonos, Soja y Bitcoin",
    "dir": "LONG",
    "assets": "GLD (Oro), USO (Petr\u00f3leo), ZS/SOYB (Soja), TLT (Bonos), BTC (Bitcoin)",
    "holding": "15\u201340 sesiones (m\u00e1x. 45 d\u00edas)",
    "stop": "Trailing stop din\u00e1mico Donchian 10d / 3x ATR",
    "target": "Corte de trailing stop o p\u00e9rdida de SMA(50)",
    "trades": "189 operaciones",
    "winRate": "42.3%",
    "sumRet": "+93.16%",
    "pf": "1.93",
    "why": "<p><b>\u00bfPor qu\u00e9 existe esta ventaja y qu\u00e9 sentido tiene?</b><br>Las materias primas, los bonos soberanos y el Bitcoin responden a ciclos de tendencia y liquidez persistentes: inflaci\u00f3n, shocks de oferta geopol\u00edticos, pol\u00edticas monetarias o adopci\u00f3n de activos digitales con oferta fija. A diferencia de las acciones (que revierten r\u00e1pido a la media), estos activos presentan <i>autocorrelaci\u00f3n positiva de largo plazo</i>: cuando una tendencia arranca, suele extenderse durante semanas o meses.</p><p>El Motor 4 implementa la metodolog\u00eda cl\u00e1sica de los grandes fondos CTA (Commodity Trading Advisors como Winton o AQR): entra en rupturas del canal Donchian de 20 sesiones con confirmaci\u00f3n de medias (SMA50 > SMA200) y deja correr los beneficios con un stop din\u00e1mico que persigue al precio.</p>",
    "code": "def _check_entry(self, b: EnrichedBar, symbol: str):\n    # Ruptura Donchian de 20 d\u00edas con alineaci\u00f3n alcista de medias m\u00f3viles\n    if (\n        b.close > b.sma50\n        and b.sma50 > b.sma200\n        and b.close > b.prev_high_20   # Nuevo m\u00e1ximo de 20 sesiones\n        and b.atr14 > 0\n    ):\n        return True, f\"Ruptura Donchian 20d en {symbol}\"\n    return False, \"\"\n\n# Salida con Trailing Stop: max(Stop Inicial, M\u00ednimo 10 d\u00edas, Cierre M\u00e1x - 3x ATR)",
    "sample": {
      "sym": "USO",
      "entry": "2026-02-27",
      "entryPrice": "$81.95",
      "exit": "2026-04-17",
      "exitPrice": "$114.73",
      "ret": "+40.00%",
      "days": "34 sesiones",
      "story": "Caso Real: En febrero de 2026, el petr\u00f3leo (USO) rompi\u00f3 al alza su canal Donchian de 20 d\u00edas sobre $81.92 con SMA50 sobre SMA200. El Motor 4 abri\u00f3 posici\u00f3n a $81.95. Acompa\u00f1\u00f3 la tendencia alcista durante 34 sesiones elevando continuamente el trailing stop, hasta salir a $114.73 capturando un +40.00% de rentabilidad descorrelacionada de la bolsa."
    },
    "chartData": {
      "dates": [
        "2026-02-19",
        "2026-02-20",
        "2026-02-23",
        "2026-02-24",
        "2026-02-25",
        "2026-02-26",
        "2026-02-27",
        "2026-03-02",
        "2026-03-03",
        "2026-03-04",
        "2026-03-05",
        "2026-03-06",
        "2026-03-09",
        "2026-03-10",
        "2026-03-11",
        "2026-03-12",
        "2026-03-13",
        "2026-03-16",
        "2026-03-17",
        "2026-03-18",
        "2026-03-19",
        "2026-03-20",
        "2026-03-23",
        "2026-03-24",
        "2026-03-25",
        "2026-03-26",
        "2026-03-27",
        "2026-03-30",
        "2026-03-31",
        "2026-04-01",
        "2026-04-02",
        "2026-04-06",
        "2026-04-07",
        "2026-04-08",
        "2026-04-09",
        "2026-04-10",
        "2026-04-13",
        "2026-04-14",
        "2026-04-15",
        "2026-04-16",
        "2026-04-17",
        "2026-04-20",
        "2026-04-21",
        "2026-04-22",
        "2026-04-23",
        "2026-04-24"
      ],
      "candles": [
        [
          80.43,
          81.19,
          79.69,
          81.27
        ],
        [
          80.54,
          80.85,
          80.17,
          81.24
        ],
        [
          81.49,
          80.9,
          80.5,
          81.92
        ],
        [
          81.19,
          80.76,
          79.8,
          81.22
        ],
        [
          80.1,
          79.73,
          79.32,
          80.14
        ],
        [
          78.15,
          79.77,
          78.04,
          81.24
        ],
        [
          82.0,
          81.95,
          80.58,
          82.12
        ],
        [
          87.62,
          87.19,
          83.2,
          88.64
        ],
        [
          94.1,
          90.2,
          87.33,
          94.37
        ],
        [
          90.22,
          91.56,
          89.11,
          91.59
        ],
        [
          94.46,
          96.31,
          94.06,
          98.83
        ],
        [
          105.38,
          108.77,
          104.53,
          109.98
        ],
        [
          119.42,
          104.33,
          98.47,
          124.07
        ],
        [
          107.13,
          105.86,
          94.23,
          107.56
        ],
        [
          105.03,
          108.05,
          100.99,
          108.36
        ],
        [
          115.69,
          118.39,
          113.91,
          119.13
        ],
        [
          115.08,
          119.89,
          114.56,
          121.15
        ],
        [
          116.93,
          115.03,
          114.36,
          118.91
        ],
        [
          117.42,
          118.84,
          116.07,
          119.13
        ],
        [
          121.03,
          121.67,
          117.45,
          122.87
        ],
        [
          120.4,
          117.36,
          114.68,
          125.19
        ],
        [
          118.96,
          121.43,
          118.33,
          123.02
        ],
        [
          113.29,
          110.56,
          106.45,
          114.45
        ],
        [
          115.23,
          114.54,
          112.77,
          116.35
        ],
        [
          109.29,
          113.39,
          109.02,
          114.25
        ],
        [
          116.73,
          117.26,
          115.2,
          118.94
        ],
        [
          120.79,
          124.2,
          120.47,
          125.3
        ],
        [
          126.84,
          129.83,
          126.31,
          130.08
        ],
        [
          129.35,
          127.25,
          124.2,
          130.93
        ],
        [
          124.86,
          124.09,
          122.48,
          125.73
        ],
        [
          139.27,
          137.92,
          131.89,
          140.0
        ],
        [
          138.51,
          138.94,
          136.38,
          140.89
        ],
        [
          141.33,
          138.08,
          130.0,
          143.98
        ],
        [
          119.06,
          124.58,
          118.06,
          125.23
        ],
        [
          127.19,
          126.96,
          123.06,
          129.64
        ],
        [
          125.61,
          124.82,
          123.98,
          127.78
        ],
        [
          133.37,
          128.47,
          127.16,
          133.53
        ],
        [
          127.1,
          123.85,
          122.91,
          127.23
        ],
        [
          123.25,
          122.59,
          122.33,
          125.24
        ],
        [
          124.07,
          125.84,
          124.05,
          128.28
        ],
        [
          114.73,
          116.04,
          110.35,
          116.87
        ],
        [
          119.84,
          121.32,
          119.4,
          122.88
        ],
        [
          121.51,
          128.25,
          121.03,
          128.89
        ],
        [
          127.36,
          129.4,
          127.07,
          131.01
        ],
        [
          131.26,
          134.72,
          129.87,
          137.46
        ],
        [
          132.63,
          132.4,
          129.55,
          133.87
        ]
      ],
      "entry_date": "2026-02-27",
      "exit_date": "2026-04-17",
      "entry_idx": 6,
      "exit_idx": 40
    }
  },
  "M5_VOL_CRUSH": {
    "badge": "M5 Vol-Crush",
    "title": "Motor 5: Compresi\u00f3n VIX/VIX3M Vol-Crush",
    "subtitle": "Captura del flujo de cobertura Vanna de creadores de mercado tras episodios de p\u00e1nico",
    "dir": "LONG",
    "assets": "SPY (S&P 500) y QQQ (Nasdaq 100)",
    "holding": "2\u20138 sesiones (m\u00e1x. 12 d\u00edas)",
    "stop": "2.3x ATR(14) din\u00e1mico",
    "target": "Normalizaci\u00f3n a SMA(20) o RSI(2) > 82",
    "trades": "41 operaciones",
    "winRate": "65.9%",
    "sumRet": "+16.25%",
    "pf": "1.82",
    "why": "<p><b>\u00bfPor qu\u00e9 existe esta ventaja y qu\u00e9 sentido tiene?</b><br>Bajo condiciones normales, la estructura temporal de volatilidad est\u00e1 en Contango (VIX < VIX3M, ratio VTS < 1.00). Durante ventas de p\u00e1nico extremas, la demanda de opciones a corto plazo se dispara y la curva se invierte a Backwardation (VTS >= 1.00). Los creadores de mercado de opciones quedan con <i>gamma negativa</i> y deben vender futuros del \u00edndice para cubrirse a medida que cae el precio.</p><p>En cuanto el p\u00e1nico cede y el ratio VTS se comprime m\u00e1s de un 3.5% desde su pico, la volatilidad impl\u00edcita colapsa (<i>vol-crush</i>). Esta compresi\u00f3n mec\u00e1nica obliga a los creadores de mercado a recomprar agresivamente sus futuros cortos (flujo Vanna positivo), generando rebotes explosivos en 'V' de alt\u00edsima fiabilidad.</p>",
    "code": "def _check_entry(self, b: EnrichedBar, recent_bars: List[EnrichedBar]):\n    peak_vts = max(x.vts_ratio for x in recent_bars) # Pico de estr\u00e9s en 5 d\u00edas\n    \n    # Compresi\u00f3n de Backwardation: el ratio VTS cede > 3.5% y el precio se estabiliza\n    vts_crush = (\n        peak_vts >= 1.00\n        and b.vts_ratio < peak_vts * 0.965\n        and b.rsi2 < 45.0\n        and b.close > prev_bar.low\n    )\n    return (True, \"Vol-Crush + Flujo Vanna\") if vts_crush else (False, \"\")",
    "sample": {
      "sym": "QQQ",
      "entry": "2015-08-25",
      "entryPrice": "$98.09",
      "exit": "2015-08-27",
      "exitPrice": "$105.64",
      "ret": "+7.70%",
      "days": "2 sesiones",
      "story": "Caso Real: Tras el famoso 'Flash Crash' del 24 de agosto de 2015, el ratio VTS marc\u00f3 un pico de 1.31. Al d\u00eda siguiente, la curva se comprimi\u00f3 a 1.22 mientras QQQ se estabilizaba. El Motor 5 entr\u00f3 a $98.09. Dos sesiones despu\u00e9s, la ola de compras mec\u00e1nicas de cobertura impuls\u00f3 el precio a $105.64 (+7.70% de beneficio en 48 horas)."
    },
    "chartData": {
      "dates": [
        "2015-08-17",
        "2015-08-18",
        "2015-08-19",
        "2015-08-20",
        "2015-08-21",
        "2015-08-24",
        "2015-08-25",
        "2015-08-26",
        "2015-08-27",
        "2015-08-28",
        "2015-08-31",
        "2015-09-01",
        "2015-09-02",
        "2015-09-03"
      ],
      "candles": [
        [
          110.24,
          111.43,
          109.96,
          111.46
        ],
        [
          111.28,
          110.86,
          110.71,
          111.37
        ],
        [
          110.52,
          110.13,
          109.49,
          111.11
        ],
        [
          109.11,
          107.08,
          107.07,
          109.46
        ],
        [
          105.57,
          102.4,
          102.4,
          106.47
        ],
        [
          94.23,
          98.46,
          84.74,
          102.53
        ],
        [
          102.07,
          98.09,
          98.01,
          102.74
        ],
        [
          100.96,
          103.03,
          98.93,
          103.23
        ],
        [
          104.52,
          105.64,
          103.28,
          105.71
        ],
        [
          105.08,
          105.62,
          104.85,
          106.0
        ],
        [
          105.03,
          104.31,
          104.05,
          105.61
        ],
        [
          101.71,
          101.05,
          100.63,
          103.29
        ],
        [
          102.88,
          103.9,
          101.7,
          103.92
        ],
        [
          104.31,
          103.39,
          103.1,
          105.02
        ]
      ],
      "entry_date": "2015-08-25",
      "exit_date": "2015-08-27",
      "entry_idx": 6,
      "exit_idx": 8
    }
  },
  "M6_TOTM": {
    "badge": "M6 Fin de Mes",
    "title": "Motor 6: Flujo Institucional Fin de Mes (TOTM)",
    "subtitle": "Monetizaci\u00f3n del flujo pasivo de n\u00f3minas, 401(k) y rebalanceo de pensiones",
    "dir": "LONG",
    "assets": "SPY (S&P 500) y QQQ (Nasdaq 100)",
    "holding": "2\u20134 sesiones (m\u00e1x. T+4)",
    "stop": "2.5x ATR(14) din\u00e1mico",
    "target": "Impulso sobre SMA(5) tras >=2 d\u00edas o cierre ventana T+4",
    "trades": "80 operaciones",
    "winRate": "70.0%",
    "sumRet": "+6.40%",
    "pf": "1.32",
    "why": "<p><b>\u00bfPor qu\u00e9 existe esta ventaja y qu\u00e9 sentido tiene?</b><br>A diferencia de los patrones t\u00e9cnicos tradicionales, el efecto de fin de mes (<i>Turn-of-the-Month</i>, documentado acad\u00e9micamente por Lakonishok & Smidt en 1988 y McConnell & Xu en 2008) est\u00e1 respaldado por <b>flujos de caja estructurales y obligatorios</b>: aportaciones autom\u00e1ticas de planes de pensiones con cada n\u00f3mina mensual, reinversi\u00f3n de dividendos corporativos y rebalanceos de fondos soberanos concentrados entre el \u00faltimo d\u00eda del mes (T-1) y los 4 primeros d\u00edas del nuevo mes (T+1 a T+4).</p><p>El Motor 6 filtra ese flujo con disciplina cuantitativa: entra en los 2 \u00faltimos d\u00edas h\u00e1biles del mes si el mercado presenta una debilidad moderada (RSI(2) < 35) bajo un entorno sano de Contango, comprando inventario con descuento justo antes de que se ejecute la marea compradora institucional.</p>",
    "code": "def _check_entry(self, b: EnrichedBar):\n    rem_bdays = business_days_remaining_in_month(b.date)\n    \n    # \u00daltimos 1-2 d\u00edas h\u00e1biles del mes + Tendencia alcista + Contango + Sobreventa moderada\n    if (\n        rem_bdays <= 1\n        and b.close > b.sma200\n        and b.vts_ratio < 0.98\n        and b.rsi2 < 35.0\n    ):\n        return True, f\"Flujo Fin de Mes (T-{rem_bdays}d)\"\n    return False, \"\"",
    "sample": {
      "sym": "QQQ",
      "entry": "2012-06-28",
      "entryPrice": "$62.20",
      "exit": "2012-07-02",
      "exitPrice": "$64.35",
      "ret": "+3.46%",
      "days": "2 sesiones",
      "story": "Caso Real: El 28-06-2012 (T-1 antes de fin de mes), QQQ retrocedi\u00f3 marcando un RSI(2) de 27.3 en Contango. El Motor 6 compr\u00f3 a $62.20. La inyecci\u00f3n de capital de principios de julio gener\u00f3 un impulso inmediato que super\u00f3 la media de 5 d\u00edas en T+2, cerrando la posici\u00f3n a $64.35 con un +3.46% de rendimiento."
    },
    "chartData": {
      "dates": [
        "2012-06-20",
        "2012-06-21",
        "2012-06-22",
        "2012-06-25",
        "2012-06-26",
        "2012-06-27",
        "2012-06-28",
        "2012-06-29",
        "2012-07-02",
        "2012-07-03",
        "2012-07-05",
        "2012-07-06",
        "2012-07-09",
        "2012-07-10"
      ],
      "candles": [
        [
          64.38,
          64.29,
          63.81,
          64.57
        ],
        [
          64.24,
          62.69,
          62.62,
          64.31
        ],
        [
          62.9,
          63.35,
          62.73,
          63.43
        ],
        [
          62.83,
          62.13,
          61.95,
          62.85
        ],
        [
          62.34,
          62.52,
          62.06,
          62.7
        ],
        [
          62.76,
          62.9,
          62.69,
          63.18
        ],
        [
          62.43,
          62.2,
          61.54,
          62.47
        ],
        [
          63.4,
          64.16,
          63.21,
          64.16
        ],
        [
          64.25,
          64.35,
          63.87,
          64.38
        ],
        [
          64.39,
          64.89,
          64.29,
          64.89
        ],
        [
          64.83,
          64.93,
          64.48,
          65.25
        ],
        [
          64.63,
          64.12,
          63.65,
          64.69
        ],
        [
          64.05,
          64.0,
          63.68,
          64.26
        ],
        [
          64.35,
          63.37,
          63.12,
          64.51
        ]
      ],
      "entry_date": "2012-06-28",
      "exit_date": "2012-07-02",
      "entry_idx": 6,
      "exit_idx": 8
    }
  }
};

function openMotorDetailModal(motorId) {
  const data = MOTOR_EXPLAINER_DATA[motorId] || MOTOR_EXPLAINER_DATA.M1_PULLBACK;
  ACTIVE_EXPLAINER_MOTOR = motorId;
  const modal = document.getElementById('motor-detail-modal');
  if (!modal) return;

  const setTxt = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setTxt('mdm-badge', data.badge);
  setTxt('mdm-title', data.title);
  setTxt('mdm-subtitle', data.subtitle);

  setTxt('mdm-param-dir', data.dir);
  setTxt('mdm-param-assets', data.assets);
  setTxt('mdm-param-hold', data.holding);
  setTxt('mdm-param-stop', data.stop);

  const whyEl = document.getElementById('mdm-why');
  if (whyEl) whyEl.innerHTML = data.why;

  const codeEl = document.getElementById('mdm-code');
  if (codeEl) codeEl.textContent = data.code;

  setTxt('mdm-stat-trades', data.trades);
  setTxt('mdm-stat-winrate', data.winRate);
  setTxt('mdm-stat-sumret', data.sumRet);
  setTxt('mdm-stat-pf', data.pf);

  const s = data.sample;
  setTxt('mdm-trade-meta', `${s.sym} · Entrada: ${s.entry} (${s.entryPrice}) -> Salida: ${s.exit} (${s.exitPrice}) · Duración: ${s.days}`);
  setTxt('mdm-trade-ret', s.ret);
  setTxt('mdm-trade-story', s.story);

  modal.classList.remove('hidden');
  modal.classList.add('flex');

  setTimeout(() => {
    renderMotorExampleCandles(motorId);
  }, 50);
}

function closeMotorDetailModal() {
  const modal = document.getElementById('motor-detail-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
}

function jumpToMotorInSimulator(motorId) {
  const mId = motorId || ACTIVE_EXPLAINER_MOTOR || 'M1_PULLBACK';
  closeMotorDetailModal();
  switchSection('analisis');
  switchPerfSubTab('simulator');
  const sel = document.getElementById('trade-filter-motor');
  if (sel) {
    sel.value = mId;
    renderTradesTable();
    try {
      document.getElementById('perf-view-simulator')?.scrollIntoView({ behavior: 'smooth' });
    } catch (e) {}
  }
}

function renderMotorExampleCandles(motorId) {
  const el = document.getElementById('motor-example-chart');
  const data = MOTOR_EXPLAINER_DATA[motorId] || MOTOR_EXPLAINER_DATA.M1_PULLBACK;
  if (!el || !data || !data.chartData) return;

  if (motorExampleChart) {
    motorExampleChart.dispose();
  }
  motorExampleChart = echarts.init(el);

  const th = getChartTheme();
  const cData = data.chartData;
  const upColor = th.dark ? '#5c9d82' : '#065f46';
  const downColor = th.dark ? '#ef4444' : '#b91c1c';

  const markPoints = [
    {
      name: 'Entrada',
      coord: [cData.entry_date, cData.candles[cData.entry_idx][1]],
      value: data.dir.includes('SHORT') ? 'VENTA CORTO' : 'COMPRA',
      itemStyle: { color: data.dir.includes('SHORT') ? downColor : upColor },
      label: { color: '#fff', fontSize: 10, fontWeight: 'bold' },
    },
    {
      name: 'Salida',
      coord: [cData.exit_date, cData.candles[cData.exit_idx][1]],
      value: data.sample.ret,
      itemStyle: { color: '#d97706' },
      label: { color: '#fff', fontSize: 10, fontWeight: 'bold' },
    }
  ];

  const option = {
    backgroundColor: th.bg,
    animationDuration: 300,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', lineStyle: { color: th.crosshair } },
      backgroundColor: th.tooltipBg,
      borderColor: th.tooltipBorder,
      textStyle: { color: th.tooltipText, fontSize: 11 },
      formatter: (params) => {
        if (!params || !params[0]) return '';
        const idx = params[0].dataIndex;
        const d = cData.dates[idx];
        const [o, c, l, h] = cData.candles[idx];
        return `
          <div style="font-family:'JetBrains Mono',monospace;">
            <b>${data.sample.sym} · ${d}</b><br/>
            Apertura: $${o}<br/>
            Cierre: $${c}<br/>
            Mín: $${l} · Máx: $${h}
          </div>
        `;
      }
    },
    grid: {
      left: 50,
      right: 18,
      top: 25,
      bottom: 25,
    },
    xAxis: {
      type: 'category',
      data: cData.dates,
      axisLine: { lineStyle: { color: th.axisLine } },
      axisLabel: { color: th.axisLabel, fontSize: 10, fontFamily: 'JetBrains Mono' }
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitLine: { lineStyle: { color: th.splitLine } },
      axisLabel: {
        color: th.axisLabel,
        fontSize: 10,
        fontFamily: 'JetBrains Mono',
        formatter: (v) => '$' + Math.round(v)
      }
    },
    series: [
      {
        name: data.sample.sym,
        type: 'candlestick',
        data: cData.candles,
        itemStyle: {
          color: upColor,
          color0: downColor,
          borderColor: upColor,
          borderColor0: downColor
        },
        markPoint: {
          data: markPoints
        }
      }
    ]
  };

  motorExampleChart.setOption(option);
  motorExampleChart.resize();
}


// ============================================================================
// MÓDULO DE ESTUDIO DE ESTRATEGIA (ARQUITECTURA, CONCURRENCIA, TRADEGATE, BITCOIN)
// ============================================================================

async function fetchBtcStudyData(callback) {
  if (BTC_STUDY_DATA) {
    if (callback) callback(BTC_STUDY_DATA);
    return BTC_STUDY_DATA;
  }
  if (btcStudyInFlight) return;
  btcStudyInFlight = true;
  try {
    const res = await fetch('/api/btc/study');
    if (res.ok) {
      BTC_STUDY_DATA = await res.json();
      if (callback) callback(BTC_STUDY_DATA);
    }
  } catch (err) {
    console.error('Error fetching BTC study:', err);
  } finally {
    btcStudyInFlight = false;
  }
  return BTC_STUDY_DATA;
}

async function toggleBtcEquityCurve() {
  // Deprecado: Bitcoin ya está integrado de forma permanente y oficial en Modo 3 Élite
  return;
}

const STRATEGY_TOPICS = {
  ARCHITECTURE: {
    badge: 'Cúspide de la Pirámide',
    title: 'Arquitectura Híbrida Modo 3 Élite (6 Motores + Núcleo Adaptativo)',
    subtitle: 'Simbiosis entre Inversión Pasiva y Cobertura Táctica (0% Apalancamiento / Deuda)',
    render: () => `
      <div class="space-y-4 text-xs leading-relaxed">
        <!-- 1. Tarjetas de parámetros clave -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono tabular-nums">
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Apalancamiento</span>
            <span class="font-bold text-slate-900 dark:text-slate-100">0% (Sin Deuda)</span>
          </div>
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Volatilidad Objetivo</span>
            <span class="font-bold text-brand-700 dark:text-brand-300">16.0% Anual</span>
          </div>
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Escudo en Estrés</span>
            <span class="font-bold text-slate-900 dark:text-slate-100">0% Bolsa Pasiva</span>
          </div>
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Motores Tácticos</span>
            <span class="font-bold text-brand-700 dark:text-brand-300">6 Descorrelacionados</span>
          </div>
        </div>

        <!-- 2. Fundamento y problema que resuelve -->
        <div class="panel p-4 space-y-2 bg-slate-50/70 dark:bg-slate-800/50">
          <div class="text-[10px] font-bold uppercase tracking-wider text-brand-700 dark:text-brand-300">
            El Problema Estructural que Resuelve Modo 3 Élite
          </div>
          <p class="text-slate-700 dark:text-slate-300">
            <b>1. El fallo de la inversión pasiva tradicional (Buy &amp; Hold):</b> Funciona bien durante ciclos alcistas seculares, pero sufre caídas devastadoras superiores al 50% en crisis sistémicas (-56.5% en 2008, -34.1% en 2020), tardando años en recuperar el capital.
          </p>
          <p class="text-slate-700 dark:text-slate-300">
            <b>2. El fallo de los sistemas 100% tácticos de reversión:</b> Esquivan los desplomes con gran eficacia, pero sufren de <i>cash drag</i> (exceso de liquidez en cuenta bancaria perdiendo contra la inflación y perdiéndose grandes tramos de mercados alcistas).
          </p>
          <p class="text-slate-700 dark:text-slate-300">
            <b>La solución híbrida:</b> Modo 3 Élite mantiene el capital 100% productive en mercados alcistas sanos (Capa 1), pero activa un cortafuegos inmediato que reduce la bolsa al 0% en cuanto detecta pánico institucional (Capa 2), dando prioridad absoluta a los 6 motores tácticos.
          </p>
        </div>

        <!-- 3. Explicación detallada de las 2 Capas -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div class="p-3.5 rounded-md border border-brand-200 dark:border-brand-800 bg-brand-50/40 dark:bg-slate-800 space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-bold text-brand-900 dark:text-brand-200 text-xs">Capa 1: Núcleo Adaptativo (Capital Ocioso)</span>
              <span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-brand-100 text-brand-800 dark:bg-brand-950 dark:text-brand-300">Régimen Contango</span>
            </div>
            <p class="text-slate-600 dark:text-slate-300 text-[11px] leading-relaxed">
              En régimen de <b>Contango (VIX &lt; VIX3M)</b> y con el S&amp;P 500 sobre su media de 200 días (SMA200), el dinero que no esté ocupado por operaciones tácticas se asigna a <b>Dual-Momentum entre SPY y QQQ</b>, regulando la exposición hacia una volatilidad anualizada del 16% (Volatility Targeting).
            </p>
          </div>

          <div class="p-3.5 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-900 dark:text-slate-100 text-xs">Capa 2: Escudo en Backwardation y 6 Motores</span>
              <span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300">Régimen Estrés</span>
            </div>
            <p class="text-slate-600 dark:text-slate-300 text-[11px] leading-relaxed">
              Cuando la estructura de volatilidad entra en <b>Backwardation (VIX &ge; VIX3M)</b>, la bolsa pasiva se recorta al <b>0%</b>. La liquidez queda reservada para los 6 motores tácticos (rebotes rápidos M1/M2/M5/M6, cortos M3 y seguimiento CTA en Oro/Bonos/Bitcoin M4).
            </p>
          </div>
        </div>

        <!-- 4. Diagrama visual de flujo -->
        <div class="panel p-4 space-y-2.5">
          <div class="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Diagrama de Decisión Diario (Evaluado a las 21:55 CET)
          </div>
          <div class="p-3 rounded bg-slate-950 text-slate-200 font-mono text-[11px] leading-relaxed border border-slate-800 overflow-x-auto">
[Reloj 21:55 CET] &rarr; Escaneo de Mercado Institucional
       │
       ├─&gt; 1. ¿Hay señales en M1–M6? ──&gt; SÍ: Reserva capital táctico (Sizing Paridad Riesgo 2.5%)
       │
       └─&gt; 2. Capital Restante (Ocioso) = 100% - Exposición Táctica
                 │
                 ├─&gt; VIX/VIX3M &lt; 0.96 &amp; SPY &gt; SMA200 (Contango): Dual-Momentum SPY/QQQ (VolTarget 16%)
                 └─&gt; VIX/VIX3M &ge; 1.00 o SPY &lt; SMA200 (Estrés): 0% Bolsa Pasiva · Refugio en Oro/Bonos
          </div>
        </div>
      </div>
    `
  },

  CAPITAL_CONCURRENCY: {
    badge: 'Paridad de Riesgo & Concurrencia',
    title: 'Gestión de Capital, Paridad de Riesgo y Resolución de Concurrencia',
    subtitle: 'Sizing Sistemático ATR, Techo del 40% en M4 y Política Estricta de No-Liquidación',
    render: () => `
      <div class="space-y-4 text-xs leading-relaxed">
        <!-- 1. Tarjetas clave -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono tabular-nums">
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Riesgo por Operación</span>
            <span class="font-bold text-brand-700 dark:text-brand-300">R = 2.5%</span>
          </div>
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Tope Motor 4 (CTA)</span>
            <span class="font-bold text-slate-900 dark:text-slate-100">Máx. 40% Cartera</span>
          </div>
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Slots Concurrentes</span>
            <span class="font-bold text-slate-900 dark:text-slate-100">Máx. 3 Posiciones</span>
          </div>
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Liquidez Mínima Libre</span>
            <span class="font-bold text-slate-900 dark:text-slate-100">15.0% Efectivo</span>
          </div>
        </div>

        <!-- 2. Cómo decide el algoritmo el tamaño de cada posición -->
        <div class="panel p-4 space-y-2 bg-slate-50/70 dark:bg-slate-800/50">
          <div class="text-[10px] font-bold uppercase tracking-wider text-brand-700 dark:text-brand-300">
            ¿Cómo Decide el Algoritmo qué Cantidad Asignar a Cada ETF?
          </div>
          <p class="text-slate-700 dark:text-slate-300">
            No se utilizan porcentajes arbitrarios (como poner un 20% a todo). Se utiliza el principio de <b>Paridad de Riesgo por Volatilidad</b>:
          </p>
          <div class="p-3 rounded bg-slate-950 text-slate-200 font-mono text-[11px] leading-relaxed border border-slate-800">
Peso de la Posición = (Riesgo Base 2.5% × Convicción Meta-Labeling) / Distancia al Stop Loss %
          </div>
          <p class="text-slate-700 dark:text-slate-300">
            <b>Ejemplo Práctico Accesible:</b>
          </p>
          <ul class="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-300 pl-1">
            <li><b>Activo de Baja Volatilidad (SPY):</b> Si el stop loss está ceñido a un 2.5% de caída, el bot asigna hasta un <b>50% del capital</b>. Si la operación toca el stop, la cartera pierde un 2.5% × 50% = <b>1.25%</b>.</li>
            <li><b>Activo de Alta Volatilidad (Petróleo o Bitcoin):</b> Si el stop loss está a un 8.0% de distancia por su alta oscilación, el bot <b>reduce automáticamente el tamaño de la posición al 15%</b>. Si toca el stop, la cartera pierde 8.0% × 15% = <b>1.20%</b>.</li>
          </ul>
          <p class="text-[11px] text-brand-700 dark:text-brand-300 font-semibold pt-1">
            &rarr; Conclusión: Da igual lo volátil que sea un activo, el algoritmo ajusta el capital para que el riesgo en dólares sea siempre idéntico y seguro.
          </p>
        </div>

        <!-- 3. Resolución de concurrencia: M1 vs M4 -->
        <div class="panel p-4 space-y-2.5">
          <div class="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Concurrencia: Si M4 da señal y todo el capital está invertido por M1, ¿qué ocurre?
          </div>
          <p class="text-slate-700 dark:text-slate-300 font-semibold text-red-700 dark:text-red-400">
            Respuesta: La nueva señal de M4 se descarta. NUNCA se desinvierte forzosamente M1.
          </p>
          <div class="space-y-2 text-slate-600 dark:text-slate-300 text-[11px]">
            <p>El algoritmo aplica la regla: <code>if avail_weight &lt; 0.15: continue</code>. Si no hay al menos un 15% de efectivo libre en caja, la señal se rechaza. Esta decisión matemática responde a 4 motivos cuantitativos:</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
              <div class="p-2.5 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                <span class="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">1. Esperanza Matemática</span>
                M1 tiene un 72.6% de acierto y busca un rebote estadístico en 2–3 días. Cortarlo antes destruye el ratio riesgo/beneficio planificado.
              </div>
              <div class="p-2.5 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                <span class="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">2. Costes de Horquilla (Spreads)</span>
                Vender una posición prematura y abrir otra genera dobles comisiones y pérdidas por la horquilla entre precio de compra y venta.
              </div>
              <div class="p-2.5 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                <span class="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">3. Fricción Fiscal en España</span>
                Cada venta genera un hecho imponible inmediato en el IRPF y activa el bloqueo de minusvalías por la regla de los 2 meses.
              </div>
              <div class="p-2.5 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                <span class="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">4. Rotación Natural Rápida</span>
                M1 dura de media 2 a 3 sesiones. El capital se libera en cuestión de 48–72 horas, y M4 tiene un tope del 40% para nunca bloquear la cartera.
              </div>
            </div>
          </div>
        </div>
      </div>
    `
  },

  EXECUTION_SPAIN: {
    badge: 'Opción A: Tradegate (TGATE)',
    title: 'Ejecución Real en España — Tradegate e Integración Fiscal AEAT',
    subtitle: 'Cumplimiento PRIIPs/MiFID II, Órdenes Limit DAY a las 21:55 CET y Módulo Fiscal',
    render: () => `
      <div class="space-y-4 text-xs leading-relaxed">
        <!-- 1. Tarjetas clave -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono tabular-nums">
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Hora de Ejecución</span>
            <span class="font-bold text-brand-700 dark:text-brand-300">21:55 CET (15:55 NY)</span>
          </div>
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Mercado Oficial</span>
            <span class="font-bold text-slate-900 dark:text-slate-100">Tradegate (TGATE)</span>
          </div>
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Tipo de Orden</span>
            <span class="font-bold text-slate-900 dark:text-slate-100">Limit DAY (+0.08%)</span>
          </div>
          <div class="p-2.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-400 font-sans block">Moneda de Liquidación</span>
            <span class="font-bold text-brand-700 dark:text-brand-300">EUR (€) Sin FX Drag</span>
          </div>
        </div>

        <!-- 2. La rutina diaria de las 21:55 CET -->
        <div class="panel p-4 space-y-2 bg-slate-50/70 dark:bg-slate-800/50">
          <div class="text-[10px] font-bold uppercase tracking-wider text-brand-700 dark:text-brand-300">
            La Rutina Diaria de las 21:55 CET
          </div>
          <p class="text-slate-700 dark:text-slate-300">
            Exactamente 5 minutos antes del cierre de Wall Street, el bot ejecuta el escaneo de mercado sobre los 6 motores. Si se activa una señal, genera una propuesta con el número exacto de participaciones en Euros para enviar a Interactive Brokers.
          </p>
          <p class="text-slate-700 dark:text-slate-300">
            <b>Por qué Tradegate Exchange:</b> La directiva europea PRIIPs prohíbe comercializar fondos estadounidenses directos (como SPY o QQQ) a minoristas en Europa por no tener folleto KID en español. Tradegate opera hasta las 22:00 CET y negocia réplicas UCITS acumulativas en Euros, permitiendo operar a la vez que Wall Street sin apalancamiento de futuros y sin comisiones de cambio de divisa.
          </p>
        </div>

        <!-- 3. Catálogo de los 7 ETFs UCITS -->
        <div class="panel p-4 space-y-2.5">
          <div class="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Catálogo Oficial de Réplicas UCITS Acumulativas en Tradegate
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-[11px] font-mono tabular-nums">
              <thead class="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                <tr>
                  <th class="p-2 font-semibold font-sans">Activo EE. UU.</th>
                  <th class="p-2 font-semibold font-sans">Réplica Tradegate</th>
                  <th class="p-2 font-semibold font-sans">ISIN Homogéneo</th>
                  <th class="p-2 font-semibold font-sans">Emisor Oficial</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
                <tr><td class="p-2 font-bold text-slate-900 dark:text-slate-100">SPY (S&amp;P 500)</td><td class="p-2 text-brand-700 dark:text-brand-300">SPYL / SXR8</td><td class="p-2">IE000XZSV718</td><td class="p-2 text-slate-500">SPDR S&amp;P 500 UCITS ETF</td></tr>
                <tr><td class="p-2 font-bold text-slate-900 dark:text-slate-100">QQQ (Nasdaq 100)</td><td class="p-2 text-brand-700 dark:text-brand-300">EQQQ</td><td class="p-2">IE0032077012</td><td class="p-2 text-slate-500">Invesco EQQQ Nasdaq-100 UCITS</td></tr>
                <tr><td class="p-2 font-bold text-slate-900 dark:text-slate-100">GLD (Oro Físico)</td><td class="p-2 text-brand-700 dark:text-brand-300">4GLD / SGLD</td><td class="p-2">DE000A0S9GB0</td><td class="p-2 text-slate-500">Xetra-Gold / Invesco Physical Gold</td></tr>
                <tr><td class="p-2 font-bold text-slate-900 dark:text-slate-100">TLT (Bonos 20+)</td><td class="p-2 text-brand-700 dark:text-brand-300">DTLA</td><td class="p-2">IE00BFM6TC58</td><td class="p-2 text-slate-500">iShares $ Treasury Bond 20+yr</td></tr>
                <tr><td class="p-2 font-bold text-slate-900 dark:text-slate-100">USO (Petróleo)</td><td class="p-2 text-brand-700 dark:text-brand-300">CRUD</td><td class="p-2">GB00B15KXV33</td><td class="p-2 text-slate-500">WisdomTree WTI Crude Oil ETC</td></tr>
                <tr><td class="p-2 font-bold text-slate-900 dark:text-slate-100">ZS (Soja Agrícola)</td><td class="p-2 text-brand-700 dark:text-brand-300">SOYB</td><td class="p-2">GB00B15KY211</td><td class="p-2 text-slate-500">WisdomTree Soybeans ETC</td></tr>
                <tr><td class="p-2 font-bold text-slate-900 dark:text-slate-100">M3 Cortos (-1x)</td><td class="p-2 text-brand-700 dark:text-brand-300">DXS3</td><td class="p-2">LU0322251520</td><td class="p-2 text-slate-500">Xtrackers S&amp;P 500 Inverse Daily (-1x)</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 4. Fiscalidad en España -->
        <div class="panel p-4 space-y-2 bg-slate-50/70 dark:bg-slate-800/50">
          <div class="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Módulo Fiscal Español Integrado (AEAT / IRPF)
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1 text-[11px] text-slate-600 dark:text-slate-300">
            <div class="p-2.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <span class="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">Criterio FIFO por ISIN</span>
              Consume estrictamente las participaciones más antiguas agrupadas por código ISIN homogéneo, incorporando comisiones al valor de adquisición.
            </div>
            <div class="p-2.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <span class="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">Regla de los 2 Meses (Art. 33.5.f)</span>
              Vigila la ventana de ±60 días naturales. Si se recompra un ISIN vendido con pérdida, bloquea la minusvalía y muestra el contador de días para liberarla.
            </div>
            <div class="p-2.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <span class="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">Tipo de Cambio Diario BCE</span>
              Aplica los tipos oficiales del Banco Central Europeo de cada fecha exacta para compras y ventas si existiese divisa en dólares.
            </div>
            <div class="p-2.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <span class="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">Renta WEB (Casillas 0326–0335)</span>
              Genera los totales por emisor para copiar directamente en el Apartado F2 de Hacienda y vigila el umbral de 50.000 € del Modelo 720.
            </div>
          </div>
        </div>
      </div>
    `
  },

  BITCOIN_STUDY: {
    badge: 'M4 CTA Experimental',
    title: 'Estudio Cuantitativo: Inclusión de Bitcoin en Motor 4 (Cap Prudencial 15%)',
    subtitle: 'Simulación Empírica de Seguimiento de Tendencia Donchian, Asimetría Alcista y Blindaje en Crisis',
    render: () => {
      const btc = BTC_STUDY_DATA?.summary;
      const m07Base = btc?.metrics_07_baseline;
      const m07Btc = btc?.metrics_07_with_btc;
      const m20Base = btc?.metrics_20_baseline;
      const m20Btc = btc?.metrics_20_with_btc;

      const finalEq07 = m07Btc?.final_equity?.toLocaleString('en-US') || '601,284';
      const baseEq07 = m07Base?.final_equity?.toLocaleString('en-US') || '342,365';
      const cagr07 = m07Btc?.cagr_pct?.toFixed(2) || '23.00';
      const baseCagr07 = m07Base?.cagr_pct?.toFixed(2) || '19.55';

      const finalEq20 = m20Btc?.final_equity?.toLocaleString('en-US') || '60,368';
      const baseEq20 = m20Base?.final_equity?.toLocaleString('en-US') || '47,969';
      const cagr20 = m20Btc?.cagr_pct?.toFixed(2) || '30.24';
      const baseCagr20 = m20Base?.cagr_pct?.toFixed(2) || '25.91';

      return `
        <div class="space-y-4 text-xs leading-relaxed">
          <!-- 1. Doble bloque de KPIs por horizonte temporal -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <!-- Horizonte Completo 2007-2026 -->
            <div class="panel p-3 space-y-2 bg-slate-50/70 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
              <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-700/60 pb-1.5">
                <span class="text-[10px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200">
                  1. Horizonte Completo (2007–2026)
                </span>
                <span class="text-[10px] font-mono text-amber-700 dark:text-amber-300 font-semibold">BTC activo desde Sep 2014</span>
              </div>
              <div class="grid grid-cols-3 gap-2 font-mono tabular-nums text-center pt-1">
                <div class="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <span class="text-[10px] text-slate-400 font-sans block">Capital Final</span>
                  <span class="font-bold text-amber-800 dark:text-amber-200 text-xs sm:text-sm">$${finalEq07}</span>
                  <span class="text-[9px] text-slate-400 font-sans block">vs $${baseEq07} base</span>
                </div>
                <div class="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <span class="text-[10px] text-slate-400 font-sans block">CAGR Anual</span>
                  <span class="font-bold text-amber-800 dark:text-amber-200 text-xs sm:text-sm">${cagr07}%</span>
                  <span class="text-[9px] text-slate-400 font-sans block">+3.45% neto</span>
                </div>
                <div class="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <span class="text-[10px] text-slate-400 font-sans block">Max Drawdown</span>
                  <span class="font-bold text-slate-800 dark:text-slate-200 text-xs sm:text-sm">${m07Btc?.max_dd_pct || '-15.56'}%</span>
                  <span class="text-[9px] text-slate-400 font-sans block">vs -14.86% base</span>
                </div>
              </div>
              <div class="text-[10px] text-slate-500 font-sans flex justify-between pt-0.5">
                <span>34 operaciones de Bitcoin (2014–2026)</span>
                <span>64.7% Win Rate · Profit Factor 6.67</span>
              </div>
            </div>

            <!-- Horizonte Reciente 2020-2026 -->
            <div class="panel p-3 space-y-2 bg-amber-50/40 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/60">
              <div class="flex items-center justify-between border-b border-amber-200 dark:border-amber-800/60 pb-1.5">
                <span class="text-[10px] font-bold uppercase tracking-wider text-amber-900 dark:text-amber-200">
                  2. Horizonte Reciente (2020–2026)
                </span>
                <span class="text-[10px] font-mono text-amber-800 dark:text-amber-300 font-semibold">Mercado Maduro / ETPs</span>
              </div>
              <div class="grid grid-cols-3 gap-2 font-mono tabular-nums text-center pt-1">
                <div class="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <span class="text-[10px] text-slate-400 font-sans block">Capital Final</span>
                  <span class="font-bold text-amber-800 dark:text-amber-200 text-xs sm:text-sm">$${finalEq20}</span>
                  <span class="text-[9px] text-slate-400 font-sans block">vs $${baseEq20} base</span>
                </div>
                <div class="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <span class="text-[10px] text-slate-400 font-sans block">CAGR Anual</span>
                  <span class="font-bold text-amber-800 dark:text-amber-200 text-xs sm:text-sm">${cagr20}%</span>
                  <span class="text-[9px] text-slate-400 font-sans block">+4.33% neto</span>
                </div>
                <div class="p-2 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <span class="text-[10px] text-slate-400 font-sans block">Max Drawdown</span>
                  <span class="font-bold text-brand-700 dark:text-brand-300 text-xs sm:text-sm">${m20Btc?.max_dd_pct || '-13.07'}%</span>
                  <span class="text-[9px] text-brand-700 dark:text-brand-300 font-sans block">Idéntico</span>
                </div>
              </div>
              <div class="text-[10px] text-slate-500 font-sans flex justify-between pt-0.5">
                <span>17 operaciones de Bitcoin (2020–2026)</span>
                <span>61.5% Win Rate · Profit Factor 2.11</span>
              </div>
            </div>
          </div>

          <!-- Nota Técnica de Riesgo: Cap del 15% y Validación Histórica -->
          <div class="panel p-3.5 bg-slate-50/90 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
            <div class="text-[10px] font-bold uppercase tracking-wider text-brand-700 dark:text-brand-300">
              ¿Por qué se aplica un Techo Máximo Prudencial del 15% a Bitcoin?
            </div>
            <p class="text-slate-700 dark:text-slate-300 text-[11px] leading-relaxed">
              En el Motor 4 clásico (materias primas y bonos), el sizing por volatilidad permite que activos con poco ATR ocupen hasta el 40% de la cartera. En Bitcoin, debido a su extrema convexidad, si se le permitiese un 40% de peso su beneficio aumentaría drásticamente, pero el riesgo de sufrir un hueco de mercado (*gap*) durante un fin de semana pondría en riesgo la preservación del capital.
            </p>
            <p class="text-slate-700 dark:text-slate-300 text-[11px] leading-relaxed">
              Fijando un <b>cap prudente del 15%</b>, se obtiene un incremento sustancial de retorno (+3.45% anual en el horizonte completo y +4.33% anual en el periodo 2020–2026) <b>manteniendo el drawdown estrictamente contenido en el -15.56%</b>.
            </p>
          </div>

          <!-- 2. Gráfica interactiva de velas con compras y ventas -->
          <div class="panel p-4 space-y-3">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-2.5">
              <div>
                <h4 class="text-xs font-bold text-slate-900 dark:text-slate-100">
                  Gráfica Diaria de Velas OHLC de Bitcoin (2014–2026) · Puntos de Entrada y Salida
                </h4>
                <p class="text-[11px] text-slate-500 dark:text-slate-400">
                  Rupturas Donchian 20d (flechas verdes) y salidas por Trailing Stop ATR o rotación 45 sesiones (flechas ámbar/rojas)
                </p>
              </div>
              <div class="flex items-center gap-2">
                <span class="inline-flex items-center gap-1 text-[11px] font-mono text-brand-700 dark:text-brand-300">
                  <span class="w-2 h-2 rounded-full bg-brand-600 inline-block"></span> Compra M4
                </span>
                <span class="inline-flex items-center gap-1 text-[11px] font-mono text-amber-600 dark:text-amber-400">
                  <span class="w-2 h-2 rounded-full bg-amber-600 inline-block"></span> Salida Ganadora
                </span>
                <span class="inline-flex items-center gap-1 text-[11px] font-mono text-red-600 dark:text-red-400">
                  <span class="w-2 h-2 rounded-full bg-red-600 inline-block"></span> Stop Loss
                </span>
              </div>
            </div>

            <!-- Contenedor ECharts para velas de Bitcoin -->
            <div id="btc-candlestick-chart" class="w-full h-[280px] sm:h-[320px]"></div>

            <div class="p-3 rounded-md bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/60 text-slate-700 dark:text-slate-300 text-[11px] leading-relaxed">
              <b>Blindaje Cuantitativo en 2022:</b> Durante el desplome de 2022, Bitcoin cayó de $69.000 a $15.500 (-76.6%). Dado que el Motor 4 exige como condición previa que el precio cotice por encima de la SMA(200) y que la SMA(50) esté ascendiendo, <b>el bot NO abrió ni una sola compra en Bitcoin durante todo 2022 (0% de exposición)</b>, esquivando el crash en su totalidad mientras el Buy &amp; Hold colapsaba.
            </div>
          </div>

          <!-- 3. Tabla comparativa de Bitcoin frente a los otros activos de M4 -->
          <div class="panel p-4 space-y-2.5">
            <div class="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Comparativa Diferencial: Bitcoin frente a los Otros Activos del Motor 4 CTA
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-[11px] font-mono tabular-nums">
                <thead class="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                  <tr>
                    <th class="p-2 font-semibold font-sans">Activo CTA</th>
                    <th class="p-2 font-semibold font-sans">Volatilidad</th>
                    <th class="p-2 font-semibold font-sans">Max Drawdown</th>
                    <th class="p-2 font-semibold font-sans">Trades M4</th>
                    <th class="p-2 font-semibold font-sans">Naturaleza Cuantitativa</th>
                    <th class="p-2 font-semibold font-sans">Rol en Cartera</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
                  <tr class="bg-amber-50/40 dark:bg-amber-950/20 font-bold">
                    <td class="p-2 text-amber-800 dark:text-amber-300">BTC (Bitcoin)</td>
                    <td class="p-2 text-amber-700 dark:text-amber-400">54.2%</td>
                    <td class="p-2 text-red-600">-76.6%</td>
                    <td class="p-2">17 trades</td>
                    <td class="p-2 font-sans font-normal text-slate-700 dark:text-slate-200">Megatendencia exponencial asimétrica</td>
                    <td class="p-2 font-sans font-normal text-amber-800 dark:text-amber-200">Acelera retorno con trailing stop estricto</td>
                  </tr>
                  <tr>
                    <td class="p-2 font-bold text-slate-900 dark:text-slate-100">GLD (Oro Físico)</td>
                    <td class="p-2">14.1%</td>
                    <td class="p-2 text-slate-600">-21.8%</td>
                    <td class="p-2">62 trades</td>
                    <td class="p-2 font-sans text-slate-600 dark:text-slate-400">Refugio monetario soberano</td>
                    <td class="p-2 font-sans text-slate-600 dark:text-slate-400">Crisis Alpha descorrelacionada</td>
                  </tr>
                  <tr>
                    <td class="p-2 font-bold text-slate-900 dark:text-slate-100">USO (Petróleo WTI)</td>
                    <td class="p-2">38.4%</td>
                    <td class="p-2 text-red-600">-88.2%</td>
                    <td class="p-2">48 trades</td>
                    <td class="p-2 font-sans text-slate-600 dark:text-slate-400">Shock de oferta geopolítico</td>
                    <td class="p-2 font-sans text-slate-600 dark:text-slate-400">Cobertura frente a picos de inflación</td>
                  </tr>
                  <tr>
                    <td class="p-2 font-bold text-slate-900 dark:text-slate-100">SOYB (Soja Agrícola)</td>
                    <td class="p-2">21.6%</td>
                    <td class="p-2 text-slate-600">-44.9%</td>
                    <td class="p-2">40 trades</td>
                    <td class="p-2 font-sans text-slate-600 dark:text-slate-400">Materia prima blanda alimentaria</td>
                    <td class="p-2 font-sans text-slate-600 dark:text-slate-400">Descorrelación total de tipos y bolsa</td>
                  </tr>
                  <tr>
                    <td class="p-2 font-bold text-slate-900 dark:text-slate-100">TLT (Bonos 20+ Años)</td>
                    <td class="p-2">15.3%</td>
                    <td class="p-2 text-slate-600">-48.5%</td>
                    <td class="p-2">39 trades</td>
                    <td class="p-2 font-sans text-slate-600 dark:text-slate-400">Renta fija soberana largo plazo</td>
                    <td class="p-2 font-sans text-slate-600 dark:text-slate-400">Vuelo a la calidad en shocks deflacionarios</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 4. Resumen de las 17 operaciones -->
          <div class="panel p-4 space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Registro Auditado de las 17 Operaciones de Bitcoin (2020–2026)
              </span>
              <span class="text-[10px] font-mono text-slate-400">Cap 15% por trade</span>
            </div>
            <div class="max-h-48 overflow-y-auto border border-slate-100 dark:border-slate-800 rounded">
              <table class="w-full text-left text-[11px] font-mono tabular-nums">
                <thead class="bg-slate-50 dark:bg-slate-800 text-slate-500 sticky top-0">
                  <tr>
                    <th class="p-1.5 font-sans">Entrada</th>
                    <th class="p-1.5 font-sans">Salida</th>
                    <th class="p-1.5 font-sans">Días</th>
                    <th class="p-1.5 font-sans text-right">Ret. Activo</th>
                    <th class="p-1.5 font-sans text-right">Ret. Cartera</th>
                    <th class="p-1.5 font-sans">Motivo Salida</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 dark:divide-slate-800 text-[10px]">
                  ${(BTC_STUDY_DATA?.trades || []).map(t => {
                    const isWin = (t.portfolio_ret_pct || 0) >= 0;
                    const col = isWin ? 'text-brand-700 dark:text-brand-300 font-bold' : 'text-red-600 dark:text-red-400 font-bold';
                    return `
                      <tr>
                        <td class="p-1.5">${t.entry_date}</td>
                        <td class="p-1.5">${t.exit_date}</td>
                        <td class="p-1.5">${t.days}d</td>
                        <td class="p-1.5 text-right ${col}">${(t.raw_ret_pct > 0 ? '+' : '') + Number(t.raw_ret_pct).toFixed(1)}%</td>
                        <td class="p-1.5 text-right ${col}">${(t.portfolio_ret_pct > 0 ? '+' : '') + Number(t.portfolio_ret_pct).toFixed(2)}%</td>
                        <td class="p-1.5 text-slate-500 truncate max-w-[150px]">${t.exit_reason || '--'}</td>
                      </tr>
                    `;
                  }).join('')}
                </tbody>
              </table>
            </div>
          </div>

          <!-- 5. Viabilidad operativa y fiscal en España -->
          <div class="panel p-4 space-y-2 bg-slate-50/70 dark:bg-slate-800/50">
            <div class="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Viabilidad Operativa en IBKR y Fiscalidad en España
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-[11px] text-slate-600 dark:text-slate-300">
              <div class="p-2.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                <span class="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">Operativa en IBKR vía ETP Europeo</span>
                No se pueden comprar ETFs de EE. UU. (IBIT), pero sí ETPs físicos en XETRA en EUR (ej. <b>BTCE</b>, ISIN <code>DE000A27Z304</code>). Se compra como un ETF normal sin riesgo divisa.
              </div>
              <div class="p-2.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                <span class="font-bold text-slate-900 dark:text-slate-100 block mb-0.5">Tributación Renta WEB (Casillas 0326–0335)</span>
                Al ser un valor cotizado en bolsa europea, tributa en la Base del Ahorro (19%–28%) y computa en el Modelo 720 tradicional, <b>sin requerir el complejo Modelo 721 de criptomonedas</b>.
              </div>
            </div>
          </div>
        </div>
      `;
    }
  }
};

function openStrategyExplainer(topicId) {
  const data = STRATEGY_TOPICS[topicId] || STRATEGY_TOPICS.ARCHITECTURE;
  ACTIVE_EXPLAINER_TOPIC = topicId;
  const modal = document.getElementById('strategy-explainer-modal');
  if (!modal) return;

  const setTxt = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setTxt('sem-badge', data.badge);
  setTxt('sem-title', data.title);
  setTxt('sem-subtitle', data.subtitle);

  const contentEl = document.getElementById('sem-content');
  if (contentEl) {
    contentEl.innerHTML = data.render();
  }

  const actionsEl = document.getElementById('sem-actions');
  if (actionsEl) {
    actionsEl.innerHTML = '';
  }

  modal.classList.remove('hidden');
  modal.classList.add('flex');

  if (topicId === 'BITCOIN_STUDY') {
    fetchBtcStudyData(() => {
      // Re-render content once data is in place
      if (ACTIVE_EXPLAINER_TOPIC === 'BITCOIN_STUDY') {
        const cEl = document.getElementById('sem-content');
        if (cEl) cEl.innerHTML = STRATEGY_TOPICS.BITCOIN_STUDY.render();
        setTimeout(() => {
          renderBtcExplainerChart();
        }, 60);
      }
    });
  }
}

function closeStrategyExplainerModal() {
  const modal = document.getElementById('strategy-explainer-modal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
  if (strategyExplainerChart) {
    strategyExplainerChart.dispose();
    strategyExplainerChart = null;
  }
}

function renderBtcExplainerChart() {
  const el = document.getElementById('btc-candlestick-chart');
  if (!el || !BTC_STUDY_DATA || !BTC_STUDY_DATA.chart_data) return;

  if (strategyExplainerChart) {
    strategyExplainerChart.dispose();
  }
  strategyExplainerChart = echarts.init(el);

  const th = getChartTheme();
  const cData = BTC_STUDY_DATA.chart_data;
  const isMobile = window.innerWidth < 640;

  const upColor = th.dark ? '#5c9d82' : '#065f46';
  const downColor = th.dark ? '#ef4444' : '#b91c1c';

  // MarkPoints para las 17 operaciones
  const markPoints = [];
  (BTC_STUDY_DATA.trades || []).forEach((t, i) => {
    markPoints.push({
      name: `Entrada #${i + 1}`,
      coord: [t.entry_date, t.entry_price],
      value: `COMPRA`,
      itemStyle: { color: upColor },
      label: { color: '#fff', fontSize: 9, fontWeight: 'bold' }
    });
    markPoints.push({
      name: `Salida #${i + 1}`,
      coord: [t.exit_date, t.exit_price],
      value: `${t.portfolio_ret_pct > 0 ? '+' : ''}${t.portfolio_ret_pct.toFixed(1)}%`,
      itemStyle: { color: t.portfolio_ret_pct >= 0 ? '#d97706' : downColor },
      label: { color: '#fff', fontSize: 9, fontWeight: 'bold' }
    });
  });

  const option = {
    backgroundColor: th.bg,
    animationDuration: 300,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', lineStyle: { color: th.crosshair } },
      backgroundColor: th.tooltipBg,
      borderColor: th.tooltipBorder,
      textStyle: { color: th.tooltipText, fontSize: 11 },
      formatter: (params) => {
        if (!params || !params[0]) return '';
        const idx = params[0].dataIndex;
        const d = cData.dates[idx];
        const [o, c, l, h] = cData.candles[idx];
        const s50 = cData.sma50[idx];
        const s200 = cData.sma200[idx];
        return `
          <div style="font-family:'JetBrains Mono',monospace;">
            <b>BTC-USD · ${d}</b><br/>
            Apertura: $${Number(o).toLocaleString('en-US')}<br/>
            Cierre: $${Number(c).toLocaleString('en-US')}<br/>
            Mín: $${Number(l).toLocaleString('en-US')} · Máx: $${Number(h).toLocaleString('en-US')}<br/>
            <span style="color:#d97706">SMA50: $${Number(s50).toLocaleString('en-US')}</span> · <span style="color:#64748b">SMA200: $${Number(s200).toLocaleString('en-US')}</span>
          </div>
        `;
      }
    },
    grid: {
      left: isMobile ? 48 : 58,
      right: isMobile ? 14 : 20,
      top: 25,
      bottom: 25,
    },
    xAxis: {
      type: 'category',
      data: cData.dates,
      axisLine: { lineStyle: { color: th.axisLine } },
      axisLabel: { color: th.axisLabel, fontSize: 10 },
    },
    yAxis: {
      type: 'log',
      scale: true,
      splitLine: { lineStyle: { color: th.splitLine } },
      axisLabel: {
        color: th.axisLabel,
        fontSize: 10,
        formatter: (v) => '$' + (v >= 1000 ? Math.round(v / 1000) + 'k' : v)
      }
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: [0] },
      { type: 'slider', xAxisIndex: [0], bottom: '0px', height: 16, borderColor: th.zoomBorder }
    ],
    series: [
      {
        name: 'Bitcoin OHLC',
        type: 'candlestick',
        data: cData.candles,
        itemStyle: {
          color: upColor,
          color0: downColor,
          borderColor: upColor,
          borderColor0: downColor,
        },
        markPoint: {
          data: markPoints,
          symbolSize: 45,
        }
      },
      {
        name: 'SMA(50)',
        type: 'line',
        data: cData.sma50,
        smooth: false,
        showSymbol: false,
        lineStyle: { color: '#d97706', width: 1.5, type: 'dashed' },
      },
      {
        name: 'SMA(200)',
        type: 'line',
        data: cData.sma200,
        smooth: false,
        showSymbol: false,
        lineStyle: { color: '#64748b', width: 1.5, type: 'dashed' },
      }
    ]
  };

  strategyExplainerChart.setOption(option);
  strategyExplainerChart.resize();
}

function confirmScanNowModal() {
  openDestructiveConfirmModal('SCAN_NOW');
}

function jumpToMotorOnChart(motorId) {
  switchMainView('performance');
  switchPerfSubTab('chart');
  setMotorFilter(motorId);
}

// ============================================================================
// GRÁFICAS ECHARTS 5: EQUITY Y DRAWDOWN (ESTILO MATE SIN BRILLOS)
// ============================================================================
function initMainCharts() {
  const chartEl = document.getElementById('main-equity-chart');
  const ddEl = document.getElementById('drawdown-chart');
  if (!chartEl || !ddEl || !APP_DATA) return;

  if (mainChart) mainChart.dispose();
  if (ddChart) ddChart.dispose();

  mainChart = echarts.init(chartEl);
  ddChart = echarts.init(ddEl);

  echarts.connect([mainChart, ddChart]);

  let isZoomSyncing = false;
  mainChart.on('datazoom', (params) => {
    if (isZoomSyncing || !ddChart) return;
    isZoomSyncing = true;
    try {
      if (params.batch && params.batch.length > 0) {
        const b = params.batch[0];
        ddChart.dispatchAction({
          type: 'dataZoom',
          start: b.start,
          end: b.end,
          startValue: b.startValue,
          endValue: b.endValue,
        });
      } else if (params.start !== undefined && params.end !== undefined) {
        ddChart.dispatchAction({
          type: 'dataZoom',
          start: params.start,
          end: params.end,
        });
      }
    } finally {
      setTimeout(() => { isZoomSyncing = false; }, 20);
    }
  });

  ddChart.on('datazoom', (params) => {
    if (isZoomSyncing || !mainChart) return;
    isZoomSyncing = true;
    try {
      if (params.batch && params.batch.length > 0) {
        const b = params.batch[0];
        mainChart.dispatchAction({
          type: 'dataZoom',
          start: b.start,
          end: b.end,
          startValue: b.startValue,
          endValue: b.endValue,
        });
      } else if (params.start !== undefined && params.end !== undefined) {
        mainChart.dispatchAction({
          type: 'dataZoom',
          start: params.start,
          end: params.end,
        });
      }
    } finally {
      setTimeout(() => { isZoomSyncing = false; }, 20);
    }
  });

  mainChart.on('click', (params) => {
    if (params.componentType === 'series' && params.seriesType === 'scatter' && params.data && params.data.tradeObj) {
      renderTradeStory(params.data.tradeObj);
    }
  });

  updateMainCharts();
}

function setChartScale(scaleType) {
  CHART_SCALE = scaleType;
  const btnLin = document.getElementById('scale-linear');
  const btnLog = document.getElementById('scale-log');
  const activeCls = 'px-2.5 py-1.5 sm:py-1 rounded text-xs font-semibold bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100';
  const idleCls = 'px-2.5 py-1.5 sm:py-1 rounded text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white';

  if (btnLin && btnLog) {
    btnLin.className = scaleType === 'value' ? activeCls : idleCls;
    btnLog.className = scaleType === 'log' ? activeCls : idleCls;
  }
  updateMainCharts();
}

function zoomToPeriod(startDate, endDate, btnId = '') {
  if (!mainChart || !APP_DATA) return;
  const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
  const curve = modeData.monthly_curve || [];
  if (curve.length === 0) return;
  const dates = curve.map((pt) => pt.date);

  let sIdx = dates.findIndex((d) => d >= startDate);
  if (sIdx === -1) sIdx = 0;

  let eIdx = -1;
  for (let i = dates.length - 1; i >= 0; i--) {
    if (dates[i] <= endDate) {
      eIdx = i;
      break;
    }
  }
  if (eIdx === -1 || eIdx < sIdx) eIdx = dates.length - 1;

  const zoomAction = {
    type: 'dataZoom',
    startValue: dates[sIdx],
    endValue: dates[eIdx],
  };

  mainChart.dispatchAction(zoomAction);
  if (ddChart) {
    ddChart.dispatchAction(zoomAction);
  }

  const periodBtns = ['btn-period-all', 'btn-period-2008', 'btn-period-2011', 'btn-period-2020', 'btn-period-2022'];
  periodBtns.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (id === btnId) {
      el.className = 'shrink-0 px-2.5 py-1.5 sm:py-1 rounded text-xs font-semibold bg-brand-700 text-white';
    } else {
      el.className = 'shrink-0 px-2.5 py-1.5 sm:py-1 rounded text-xs font-medium bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 text-slate-700 dark:text-slate-200';
    }
  });
}

function getFilteredScatterTrades(modeData, curveDates, scatterBorder) {
  if (ACTIVE_MOTOR_FILTER === 'NONE') return [];

  let trades = modeData.trades || [];
  if (ACTIVE_MOTOR_FILTER === 'TOP_IMPACT') {
    trades = [...trades]
      .sort((a, b) => Math.abs(b.portfolio_ret_pct) - Math.abs(a.portfolio_ret_pct))
      .slice(0, 35);
  } else {
    trades = trades.filter((t) => t.engine_id === ACTIVE_MOTOR_FILTER);
  }

  return trades.map((t) => {
    let closestDate = curveDates[0];
    for (let i = 0; i < curveDates.length; i++) {
      if (curveDates[i] <= t.exit_date) {
        closestDate = curveDates[i];
      } else {
        break;
      }
    }
    const mMeta = MOTOR_META[t.engine_id] || MOTOR_META.M1_PULLBACK;
    const isWin = t.portfolio_ret_pct >= 0;

    return {
      name: `${t.engine_id} (${t.symbol})`,
      value: [closestDate, t.eq_at_exit],
      tradeObj: t,
      itemStyle: {
        color: isWin ? mMeta.color : '#b91c1c',
        borderColor: scatterBorder,
        borderWidth: 1.5,
      },
      symbol: mMeta.symbolShape || 'circle',
      symbolSize: window.innerWidth < 640 ? 9 : 8,
    };
  });
}

function updateMainCharts() {
  if (!mainChart || !ddChart || !APP_DATA) return;

  const th = getChartTheme();
  const isMobile = window.innerWidth < 640;
  const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
  const curve = modeData.monthly_curve || [];
  if (curve.length === 0) return;

  const dates = curve.map((pt) => pt.date);
  const modeValues = curve.map((pt) => pt.bot_eq);
  const sp500Values = curve.map((pt) => pt.spy_eq);

  // Superposición opcional de Simulación Bitcoin M4 (2020-2026)
  let btcModeValues = [];
  let btcDdValues = [];
  let btcScatterData = [];

  if (SHOW_BTC_EQUITY_CURVE && BTC_STUDY_DATA && Array.isArray(BTC_STUDY_DATA.monthly_curve_btc)) {
    const btcCurveMap = {};
    BTC_STUDY_DATA.monthly_curve_btc.forEach((pt) => {
      btcCurveMap[pt.date] = pt;
    });

    let lastKnownBtcEq = modeValues[0] || 10000;
    let lastKnownBtcDd = 0;

    dates.forEach((d, i) => {
      if (btcCurveMap[d]) {
        lastKnownBtcEq = Math.round(btcCurveMap[d].bot_eq);
        lastKnownBtcDd = btcCurveMap[d].bot_dd;
      }
      btcModeValues.push(lastKnownBtcEq);
      btcDdValues.push(lastKnownBtcDd);
    });

    if (Array.isArray(BTC_STUDY_DATA.trades)) {
      BTC_STUDY_DATA.trades.forEach((t) => {
        let closestDate = dates[0];
        for (let i = 0; i < dates.length; i++) {
          if (dates[i] <= t.exit_date) closestDate = dates[i];
          else break;
        }
        const cIdx = dates.indexOf(closestDate);
        const eqAtPt = cIdx >= 0 ? btcModeValues[cIdx] : 0;
        const isWin = (t.portfolio_ret_pct || 0) >= 0;
        btcScatterData.push({
          name: 'M4 CTA (BTC)',
          value: [closestDate, eqAtPt],
          tradeObj: {
            ...t,
            engine_id: 'M4_CTA_TREND',
            symbol: 'BTC (Bitcoin)',
            direction: 'LONG',
          },
          itemStyle: {
            color: isWin ? '#d97706' : '#b91c1c',
            borderColor: '#ffffff',
            borderWidth: 1.5,
          },
          symbol: 'diamond',
          symbolSize: 10,
        });
      });
    }
  }

  const baseScatter = getFilteredScatterTrades(modeData, dates, th.scatterBorder);
  const scatterData = SHOW_BTC_EQUITY_CURVE ? [...baseScatter, ...btcScatterData] : baseScatter;

  const mainOption = {
    backgroundColor: th.bg,
    animation: false,
    grid: {
      left: isMobile ? '46px' : '56px',
      right: isMobile ? '12px' : '24px',
      top: '34px',
      bottom: '36px',
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      backgroundColor: th.tooltipBg,
      borderColor: th.tooltipBorder,
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: th.tooltipText, fontSize: 12, fontFamily: 'Inter' },
      axisPointer: { type: 'cross', lineStyle: { color: th.crosshair } },
      formatter: function (params) {
        if (!params || params.length === 0) return '';
        const d = params[0].axisValue;
        let html = `<div style="font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;color:${th.tooltipMuted};padding-bottom:4px;border-bottom:1px solid ${th.tooltipBorder}">${d}</div><div style="margin-top:4px;font-size:12px">`;
        params.forEach((p) => {
          if (p.seriesType === 'line') {
            const val = Number(p.value).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
            html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;font-family:JetBrains Mono,monospace;font-variant-numeric:tabular-nums"><span style="color:${p.color}">${p.seriesName}:</span><span style="font-weight:700;color:${th.tooltipText}">$${val}</span></div>`;
          }
        });
        html += `</div>`;
        return html;
      },
    },
    legend: {
      type: 'scroll',
      data: ['Modo 3 Élite (6 Motores + VTS)', 'S&P 500 (Buy & Hold)'],
      right: isMobile ? '4px' : '16px',
      left: isMobile ? '4px' : 'auto',
      top: '4px',
      textStyle: { color: th.text, fontSize: isMobile ? 10 : 11, fontFamily: 'Inter' },
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: th.axisLine } },
      axisLabel: { color: th.axisLabel, fontSize: isMobile ? 10 : 11, margin: 10 },
      splitLine: { show: false },
    },
    yAxis: {
      type: CHART_SCALE,
      scale: true,
      splitLine: { lineStyle: { color: th.splitLine } },
      axisLabel: {
        color: th.axisLabel,
        fontSize: isMobile ? 10 : 11,
        formatter: (v) => '$' + (v >= 1000 ? Math.round(v / 1000) + 'k' : v),
      },
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: [0] },
      { type: 'slider', xAxisIndex: [0], bottom: '0px', height: 16, borderColor: th.zoomBorder, handleSize: '100%' },
    ],
    series: [
      {
        name: 'S&P 500 (Buy & Hold)',
        type: 'line',
        data: sp500Values,
        smooth: false,
        showSymbol: false,
        lineStyle: { color: th.spyLine, width: 1.6, type: 'dashed' },
        itemStyle: { color: th.spyLine },
      },
      {
        name: 'Modo 3 Élite (6 Motores + VTS)',
        type: 'line',
        data: modeValues,
        smooth: false,
        showSymbol: false,
        lineStyle: { color: th.botLine, width: 2.2 },
        itemStyle: { color: th.botLine },
        areaStyle: { color: th.botArea },
      },
      {
        name: 'Operaciones Tácticas',
        type: 'scatter',
        data: scatterData,
        z: 10,
        tooltip: {
          confine: true,
          formatter: function (p) {
            const t = p.data.tradeObj;
            const gainCol = t.portfolio_ret_pct >= 0 ? th.botLine : '#b91c1c';
            return `
              <div style="font-size:12px">
                <div style="font-weight:700;color:${th.tooltipText}">${t.engine_id} · ${t.direction} ${t.symbol}</div>
                <div style="color:${th.tooltipMuted};font-size:11px">${t.entry_date} -> ${t.exit_date} (${t.days}d)</div>
                <div style="margin-top:4px;font-family:JetBrains Mono,monospace;font-weight:700;color:${gainCol}">
                  Impacto Cartera: ${fmtPct(t.portfolio_ret_pct)} ($${t.eq_at_exit.toFixed(2)})
                </div>
              </div>
            `;
          },
        },
      },
    ],
  };

  mainChart.setOption(mainOption, true);

  const ddValues = curve.map((pt) => pt.bot_dd);
  const spDdValues = curve.map((pt) => pt.spy_dd);

  const ddOption = {
    backgroundColor: th.bg,
    animation: false,
    grid: {
      left: isMobile ? '46px' : '56px',
      right: isMobile ? '12px' : '24px',
      top: '10px',
      bottom: '22px',
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      backgroundColor: th.tooltipBg,
      borderColor: th.tooltipBorder,
      textStyle: { color: th.tooltipText, fontSize: 11 },
      formatter: function (params) {
        if (!params || params.length === 0) return '';
        const d = params[0].axisValue;
        let html = `<div style="font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;color:${th.tooltipMuted}">${d}</div><div style="margin-top:4px;font-size:11px">`;
        params.forEach((p) => {
          html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;font-family:JetBrains Mono,monospace;font-variant-numeric:tabular-nums"><span style="color:${p.color}">${p.seriesName}:</span><span style="font-weight:700;color:${th.tooltipText}">${p.value}%</span></div>`;
        });
        html += `</div>`;
        return html;
      },
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: th.axisLine } },
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      min: -60,
      max: 5,
      splitLine: { lineStyle: { color: th.splitLine } },
      axisLabel: {
        color: th.axisLabel,
        fontSize: 10,
        formatter: (v) => v + '%',
      },
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: [0] },
    ],
    series: [
      {
        name: 'Drawdown S&P 500',
        type: 'line',
        data: spDdValues,
        showSymbol: false,
        lineStyle: { color: th.ddSpyLine, width: 1.2 },
        areaStyle: { color: th.ddSpyArea },
      },
      {
        name: 'Drawdown Modo 3 Élite',
        type: 'line',
        data: ddValues,
        showSymbol: false,
        lineStyle: { color: th.botLine, width: 1.5 },
        areaStyle: { color: th.botArea },
      },
    ],
  };

  ddChart.setOption(ddOption, true);
}

// ============================================================================
// INSPECTOR DE OPERACIÓN Y TARJETAS DE LOS 6 MOTORES
// ============================================================================
function renderDefaultTradeStory() {
  if (!APP_DATA) return;
  const trades = APP_DATA.modes[ACTIVE_MODE_ID].trades || [];
  if (trades.length === 0) return;
  const best = [...trades].sort((a, b) => b.portfolio_ret_pct - a.portfolio_ret_pct)[0];
  renderTradeStory(best);
}

function renderTradeStory(t) {
  const container = document.getElementById('trade-story-content');
  if (!container || !t) return;

  const meta = getEngineMeta(t.engine_id);
  const isWin = t.portfolio_ret_pct >= 0;
  const retColor = isWin ? 'text-brand-700 dark:text-brand-300' : 'text-red-700 dark:text-red-400';
  const badgeBg = isWin
    ? 'bg-brand-50 text-brand-800 border-brand-200 dark:bg-brand-950 dark:text-brand-200 dark:border-brand-800'
    : 'bg-red-50 text-red-800 border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-900';

  container.innerHTML = `
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <span class="px-2.5 py-0.5 rounded text-xs font-semibold border ${badgeBg}">${escHtml(meta.badge)}</span>
        <span class="text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">${escHtml(t.direction)} · ${escHtml(t.symbol)}</span>
      </div>

      <div class="border-t border-b border-slate-100 dark:border-slate-800 py-2.5 space-y-1.5 font-mono tabular-nums text-xs">
        <div class="flex justify-between gap-2">
          <span class="text-slate-500 dark:text-slate-400 font-sans">Periodo:</span>
          <span class="font-medium text-slate-800 dark:text-slate-200 text-right">${escHtml(t.entry_date)} -> ${escHtml(t.exit_date)} (${t.days}d)</span>
        </div>
        <div class="flex justify-between gap-2">
          <span class="text-slate-500 dark:text-slate-400 font-sans">Impacto en Cartera:</span>
          <span class="font-bold ${retColor}">${fmtPct(t.portfolio_ret_pct)}</span>
        </div>
        <div class="flex justify-between gap-2">
          <span class="text-slate-500 dark:text-slate-400 font-sans">Variación Activo:</span>
          <span class="font-medium text-slate-800 dark:text-slate-200 text-right">${fmtPct(t.raw_ret_pct)} ($${t.entry_price} -> $${t.exit_price})</span>
        </div>
        <div class="flex justify-between gap-2">
          <span class="text-slate-500 dark:text-slate-400 font-sans">Regla de Salida:</span>
          <span class="font-medium text-slate-800 dark:text-slate-200 text-[11px] text-right">${escHtml(t.exit_reason || 'Objetivo alcanzado')}</span>
        </div>
      </div>

      <div>
        <h4 class="font-semibold text-slate-900 dark:text-slate-100 uppercase tracking-wider text-[11px]">Fundamento Cuantitativo</h4>
        <p class="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">${escHtml(meta.plainExplanation)}</p>
      </div>
    </div>
  `;
}

function renderMotorBreakdownCards() {
  const container = document.getElementById('motor-breakdown-cards');
  if (!container || !APP_DATA) return;

  const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
  const breakdown = modeData.engine_breakdown || {};
  const order = ['M1_PULLBACK', 'M2_VIX_DIV', 'M3_BEAR_SHORT', 'M4_CTA_TREND', 'M5_VOL_CRUSH', 'M6_TOTM'];

  container.innerHTML = order
    .map((mKey) => {
      const b = breakdown[mKey];
      const meta = MOTOR_META[mKey];
      if (!b || !meta) return '';

      const winColor = b.win_rate >= 60 ? 'text-brand-700 dark:text-brand-300' : 'text-slate-800 dark:text-slate-200';
      const sumRetColor = b.sum_ret_pct >= 0 ? 'text-brand-700 dark:text-brand-300' : 'text-red-700 dark:text-red-400';

      return `
        <div class="p-3 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-brand-600 transition cursor-pointer" onclick="jumpToMotorOnChart('${mKey}')">
          <div class="flex items-center justify-between gap-2">
            <span class="text-xs font-semibold text-slate-900 dark:text-slate-100">${escHtml(meta.shortName)}</span>
            <span class="text-[11px] font-mono tabular-nums font-bold text-brand-800 dark:text-brand-200 bg-brand-50 dark:bg-brand-950 px-2 py-0.5 rounded border border-brand-200 dark:border-brand-800 shrink-0">${b.trades} trades</span>
          </div>
          <div class="grid grid-cols-3 gap-2 mt-2 font-mono tabular-nums text-xs text-slate-600 dark:text-slate-300">
            <div>
              <span class="text-[10px] text-slate-400 block font-sans">Acierto</span>
              <span class="font-bold ${winColor}">${b.win_rate}%</span>
            </div>
            <div>
              <span class="text-[10px] text-slate-400 block font-sans">Ret. Acum.</span>
              <span class="font-bold ${sumRetColor}">${fmtPct(b.sum_ret_pct)}</span>
            </div>
            <div>
              <span class="text-[10px] text-slate-400 block font-sans">Profit Factor</span>
              <span class="font-bold text-slate-900 dark:text-slate-100">${b.profit_factor}</span>
            </div>
          </div>
        </div>
      `;
    })
    .join('');
}

// ============================================================================
// CRISIS Y ROBUSTEZ ESTADÍSTICA (SUBPESTAÑA 3)
// ============================================================================
function initCrisisAndRobustnessCharts() {
  if (!APP_DATA) return;
  const th = getChartTheme();

  // 1. Ciclos Macroeconómicos
  const subEl = document.getElementById('subperiods-chart');
  if (subEl) {
    if (subperiodsChart) subperiodsChart.dispose();
    subperiodsChart = echarts.init(subEl);
    const sp = APP_DATA.robustness?.subperiods || [];
    const periods = sp.map((s) => s.period.split(' (')[0]);
    const m3Vals = sp.map((s) => s.bot_cum_ret_pct);
    const spVals = sp.map((s) => s.spy_cum_ret_pct);

    subperiodsChart.setOption({
      backgroundColor: th.bg,
      animation: false,
      grid: { left: '46px', right: '14px', top: '34px', bottom: '28px' },
      tooltip: {
        trigger: 'axis',
        confine: true,
        backgroundColor: th.tooltipBg,
        borderColor: th.tooltipBorder,
        textStyle: { color: th.tooltipText, fontSize: 12 },
        formatter: (p) => `${p[0].name}<br/>${p[0].seriesName}: ${fmtPct(p[0].value)}<br/>${p[1].seriesName}: ${fmtPct(p[1].value)}`,
      },
      legend: { data: ['Modo 3 Élite (6M)', 'S&P 500'], top: 0, textStyle: { color: th.text, fontSize: 11 } },
      xAxis: { type: 'category', data: periods, axisLine: { lineStyle: { color: th.axisLine } }, axisLabel: { color: th.axisLabel, fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}%', color: th.axisLabel, fontSize: 10 }, splitLine: { lineStyle: { color: th.splitLine } } },
      series: [
        { name: 'Modo 3 Élite (6M)', type: 'bar', data: m3Vals, itemStyle: { color: th.botLine, borderRadius: [3, 3, 0, 0] } },
        { name: 'S&P 500', type: 'bar', data: spVals, itemStyle: { color: th.spyLine, borderRadius: [3, 3, 0, 0] } },
      ],
    }, true);
  }

  // 2. Simulación Monte Carlo (1.000 trayectorias)
  const mcEl = document.getElementById('montecarlo-chart');
  if (mcEl) {
    if (monteCarloChart) monteCarloChart.dispose();
    monteCarloChart = echarts.init(mcEl);
    const mc = APP_DATA.robustness?.monte_carlo || {};
    const p5 = mc.p5_pessimistic?.final_equity || 71110;
    const p25 = mc.p25_conservative?.final_equity || 109133;
    const p50 = mc.p50_median?.final_equity || 154228;
    const p75 = mc.p75_optimistic?.final_equity || 215828;
    const p95 = mc.p95_extreme?.final_equity || 316030;

    monteCarloChart.setOption({
      backgroundColor: th.bg,
      animation: false,
      grid: { left: '54px', right: '14px', top: '24px', bottom: '28px' },
      tooltip: {
        trigger: 'axis',
        confine: true,
        backgroundColor: th.tooltipBg,
        borderColor: th.tooltipBorder,
        textStyle: { color: th.tooltipText, fontSize: 12 },
        formatter: (p) => `${p[0].name}: $${Number(p[0].value).toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
      },
      xAxis: { type: 'category', data: ['P5', 'P25', 'P50 (Med)', 'P75', 'P95'], axisLine: { lineStyle: { color: th.axisLine } }, axisLabel: { color: th.axisLabel, fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { formatter: (v) => '$' + Math.round(v / 1000) + 'k', color: th.axisLabel, fontSize: 10 }, splitLine: { lineStyle: { color: th.splitLine } } },
      series: [
        {
          name: 'Capital Final',
          type: 'bar',
          data: [p5, p25, p50, p75, p95],
          itemStyle: {
            color: function (params) {
              const lightColors = ['#636c68', '#2e7b5d', '#1b6649', '#065f46', '#064e3b'];
              const darkColors = ['#636c68', '#5c9d82', '#5c9d82', '#84b9a1', '#b3d6c5'];
              return (th.dark ? darkColors : lightColors)[params.dataIndex];
            },
            borderRadius: [3, 3, 0, 0],
          },
        },
      ],
    }, true);
  }

  // 3. Sensibilidad a Fricción
  const frEl = document.getElementById('friction-chart');
  if (frEl) {
    if (frictionChart) frictionChart.dispose();
    frictionChart = echarts.init(frEl);
    const fr = APP_DATA.robustness?.friction_test || [];

    frictionChart.setOption({
      backgroundColor: th.bg,
      animation: false,
      grid: { left: '44px', right: '14px', top: '24px', bottom: '28px' },
      tooltip: {
        trigger: 'axis',
        confine: true,
        backgroundColor: th.tooltipBg,
        borderColor: th.tooltipBorder,
        textStyle: { color: th.tooltipText, fontSize: 12 },
        formatter: (p) => `${p[0].name}<br/>CAGR Neto: ${p[0].value}%`,
      },
      xAxis: { type: 'category', data: fr.map((f) => f.scenario.split(' (')[0]), axisLine: { lineStyle: { color: th.axisLine } }, axisLabel: { color: th.axisLabel, fontSize: 10 } },
      yAxis: { type: 'value', min: 8, axisLabel: { formatter: '{value}%', color: th.axisLabel, fontSize: 10 }, splitLine: { lineStyle: { color: th.splitLine } } },
      series: [
        {
          name: 'CAGR Neto',
          type: 'line',
          data: fr.map((f) => f.cagr_pct),
          itemStyle: { color: th.botLine },
          lineStyle: { width: 2.2, color: th.botLine },
        },
      ],
    }, true);
  }
}

function renderYearlyTable() {
  const tbody = document.getElementById('yearly-comparison-tbody');
  if (!tbody || !APP_DATA) return;

  const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
  const yearly = modeData.yearly || [];

  tbody.innerHTML = yearly
    .map((y) => {
      const mVal = y.bot_ret_pct;
      const spVal = y.spy_ret_pct;
      const alpha = y.alpha_pct;

      const mColor = mVal >= 0 ? 'text-brand-700 dark:text-brand-300 font-semibold' : 'text-red-700 dark:text-red-400 font-semibold';
      const spColor = spVal >= 0 ? 'text-slate-800 dark:text-slate-200' : 'text-red-700 dark:text-red-400';
      const alphaColor = alpha >= 0 ? 'text-brand-700 dark:text-brand-300 font-bold' : 'text-red-700 dark:text-red-400 font-bold';

      return `
        <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
          <td class="py-2 px-3 sm:px-4 font-bold text-slate-800 dark:text-slate-100">${y.year}</td>
          <td class="py-2 px-3 sm:px-4 text-right ${mColor}">${fmtPct(mVal)}</td>
          <td class="py-2 px-3 sm:px-4 text-right ${spColor}">${fmtPct(spVal)}</td>
          <td class="py-2 px-3 sm:px-4 text-right ${alphaColor}">${fmtPct(alpha)}</td>
        </tr>
      `;
    })
    .join('');
}

// ============================================================================
// SIMULADOR INTERACTIVO E HISTÓRICO DE 780 OPERACIONES (SUBPESTAÑA 4)
// ============================================================================
function updateCustomSimulator() {
  if (!APP_DATA) return;

  const capSlider = document.getElementById('sim-cap-slider');
  const feeSlider = document.getElementById('sim-fee-slider');
  if (!capSlider || !feeSlider) return;

  const cap = Number(capSlider.value);
  const fee = Number(feeSlider.value);

  const capLbl = document.getElementById('sim-cap-label');
  const feeLbl = document.getElementById('sim-fee-label');
  if (capLbl) capLbl.textContent = fmtUSD(cap);
  if (feeLbl) feeLbl.textContent = fee.toFixed(2) + '%';

  const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
  const baseInit = Number(modeData.initial_capital || 10000);
  const scale = cap / baseInit;

  const spFinal = Number(APP_DATA.benchmark?.final_equity || modeData.spy_final_equity || 53757.52) * scale;

  // Interpolación lineal exacta sobre la curva auditada de fricción (0 a 35 bps)
  const frList = APP_DATA.robustness?.friction_test || [];
  let interpFinalBase = Number(modeData.final_equity || 341057.69);
  let interpCagr = Number(modeData.cagr_pct || 19.54);

  if (frList.length >= 2) {
    let lower = frList[0];
    let upper = frList[frList.length - 1];
    for (let i = 0; i < frList.length - 1; i++) {
      const a = frList[i];
      const b = frList[i + 1];
      if (fee >= a.roundtrip_pct && fee <= b.roundtrip_pct) {
        lower = a;
        upper = b;
        break;
      }
    }
    const span = upper.roundtrip_pct - lower.roundtrip_pct;
    const t = span > 1e-6 ? Math.min(1, Math.max(0, (fee - lower.roundtrip_pct) / span)) : 0;
    interpFinalBase = lower.final_equity + t * (upper.final_equity - lower.final_equity);
    interpCagr = lower.cagr_pct + t * (upper.cagr_pct - lower.cagr_pct);
    if (fee === 0) {
      interpCagr = Number(modeData.cagr_pct || interpCagr);
    }
  }

  const m3Final = interpFinalBase * scale;

  const spyEl = document.getElementById('sim-res-spy');
  const m3El = document.getElementById('sim-res-m3elite');
  const cagrEl = document.getElementById('sim-res-cagr');
  if (spyEl) spyEl.textContent = fmtUSD(Math.round(spFinal));
  if (m3El) m3El.textContent = fmtUSD(Math.round(m3Final));
  if (cagrEl) cagrEl.textContent = `CAGR Neto Estimado: ${interpCagr.toFixed(2)}% anual`;
}

function renderTradesTable() {
  const tbody = document.getElementById('trades-table-tbody');
  const countLabel = document.getElementById('trades-count-label');
  if (!tbody || !APP_DATA) return;

  const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
  let trades = modeData.trades || [];

  const filterMotor = document.getElementById('filter-motor')?.value || 'ALL';
  const filterSymbol = document.getElementById('filter-symbol')?.value || 'ALL';
  const filterResult = document.getElementById('filter-result')?.value || 'ALL';
  const filterYear = document.getElementById('filter-year')?.value.trim() || '';

  if (filterMotor !== 'ALL') {
    trades = trades.filter((t) => t.engine_id === filterMotor);
  }
  if (filterSymbol !== 'ALL') {
    trades = trades.filter((t) => t.symbol === filterSymbol);
  }
  if (filterResult === 'WIN') {
    trades = trades.filter((t) => t.portfolio_ret_pct >= 0);
  } else if (filterResult === 'LOSS') {
    trades = trades.filter((t) => t.portfolio_ret_pct < 0);
  }
  if (filterYear) {
    trades = trades.filter((t) => t.exit_date && t.exit_date.startsWith(filterYear));
  }

  if (countLabel) {
    countLabel.textContent = `Mostrando ${Math.min(trades.length, 60)} de ${trades.length} operaciones filtradas`;
  }

  if (trades.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-slate-400 font-sans">Sin operaciones para los filtros seleccionados.</td></tr>`;
    return;
  }

  tbody.innerHTML = trades
    .slice(0, 60)
    .map((t) => {
      const isWin = t.portfolio_ret_pct >= 0;
      const retColor = isWin ? 'text-brand-700 dark:text-brand-300' : 'text-red-700 dark:text-red-400';
      const dirCls = t.direction === 'LONG'
        ? 'text-brand-800 bg-brand-50 dark:bg-brand-950 dark:text-brand-200'
        : 'text-red-800 bg-red-50 dark:bg-red-950 dark:text-red-300';

      return `
        <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition whitespace-nowrap">
          <td class="py-2 px-3 text-slate-500 dark:text-slate-400 text-[11px]">${escHtml(t.exit_date)}</td>
          <td class="py-2 px-3 font-semibold text-slate-800 dark:text-slate-200">${escHtml(t.engine_id)}</td>
          <td class="py-2 px-3 font-bold text-slate-900 dark:text-slate-100">${escHtml(t.symbol)}</td>
          <td class="py-2 px-3"><span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${dirCls}">${escHtml(t.direction)}</span></td>
          <td class="py-2 px-3 text-right ${retColor} font-bold">${fmtPct(t.portfolio_ret_pct)}</td>
          <td class="py-2 px-3 text-right text-slate-700 dark:text-slate-200 font-bold">$${Number(t.eq_at_exit).toFixed(2)}</td>
          <td class="py-2 px-3 text-slate-500 dark:text-slate-400 text-[11px] text-right">${t.days}d</td>
        </tr>
      `;
    })
    .join('');
}

// ============================================================================
// PULSO DE MERCADO DIARIO Y RÉGIMEN VTS
// ============================================================================
function styleVtsPill(el, vtsState, vtsRatio) {
  if (!el) return;
  const raw = String(vtsState || '').toUpperCase();
  const isBackwardation = raw.includes('BACKWARD') || raw.includes('CRISIS') || raw.includes('PANIC') || (Number(vtsRatio) >= 1.0 && vtsRatio != null);
  if (isBackwardation) {
    el.className = 'inline-block mt-0.5 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-red-50 dark:bg-red-950 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-900';
  } else {
    el.className = 'inline-block mt-0.5 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-200 border border-brand-200 dark:border-brand-800';
  }
}

function renderLiveScan() {
  const dateEl = document.getElementById('live-date-label');
  const badgeEl = document.getElementById('live-regime-badge');
  const detailEl = document.getElementById('live-vts-detail');
  const gridEl = document.getElementById('live-assets-grid');

  const tac = LAST_LIVE_STATUS?.tactical;
  const live = APP_DATA?.live_scan;

  const asOf = tac?.data_as_of || live?.as_of_date || '--';
  const vtsState = tac?.vts_state || live?.vts_state || 'CONTANGO';
  const vtsRatio = tac?.vts_ratio ?? live?.vts_ratio;

  if (dateEl) dateEl.textContent = asOf;
  if (badgeEl) {
    badgeEl.textContent = vtsState.split(' (')[0];
    styleVtsPill(badgeEl, vtsState, vtsRatio);
  }
  const ratioValEl = document.getElementById('live-vts-ratio-val');
  if (ratioValEl) {
    ratioValEl.textContent = vtsRatio !== undefined ? Number(vtsRatio).toFixed(3) : '--';
  }
  const vixLevelsEl = document.getElementById('live-vix-levels');
  if (vixLevelsEl) {
    if (live && live.vix_close !== undefined) {
      vixLevelsEl.textContent = `VIX: ${Number(live.vix_close).toFixed(2)} · VIX3M: ${Number(live.vix3m_close).toFixed(2)}`;
    } else {
      vixLevelsEl.textContent = 'VIX / VIX3M Estructura Temporal';
    }
  }
  const shieldEl = document.getElementById('live-vts-shield-status');
  if (shieldEl) {
    const isBack = String(vtsState).toUpperCase().includes('BACKWARD');
    shieldEl.textContent = isBack ? 'Escudo Activo (Bolsa al 0% · Coberturas)' : 'Escudo Normal (Bolsa al 100% · SPY/QQQ)';
    shieldEl.className = isBack ? 'font-semibold text-red-700 dark:text-red-400' : 'font-semibold text-brand-700 dark:text-brand-300';
  }
  if (detailEl) {
    if (live && live.vix_close !== undefined) {
      const ratioTxt = vtsRatio !== undefined ? Number(vtsRatio).toFixed(3) : live.vts_ratio;
      detailEl.textContent = `VIX ${live.vix_close} · VIX3M ${live.vix3m_close} · VTS ${ratioTxt}`;
    } else if (vtsRatio !== undefined) {
      detailEl.textContent = `Ratio VTS: ${Number(vtsRatio).toFixed(3)}`;
    }
  }

  const livePriceMap = {};
  (LAST_LIVE_STATUS?.state?.positions || []).forEach((p) => {
    if (p.internal_symbol && p.current_price) livePriceMap[p.internal_symbol] = p.current_price;
    if (p.broker_symbol && p.current_price) livePriceMap[p.broker_symbol] = p.current_price;
  });

  if (gridEl) {
    if (live && Array.isArray(live.assets) && live.assets.length > 0) {
      const coreMap = tac?.core_allocation || null;
      gridEl.innerHTML = live.assets
        .map((a) => {
          const coreWeight = coreMap && coreMap[a.symbol] !== undefined ? Number(coreMap[a.symbol]) : Number(a.core_weight_pct || 0);
          const isCore = coreWeight > 0;
          const price = livePriceMap[a.symbol] ?? a.last_close ?? a.close ?? 0;
          const trendVal = a.sma200_trend || (String(a.trend || '').includes('ALCISTA') ? 'BULL' : 'BEAR');
          const isBull = trendVal === 'BULL';
          const trendCls = isBull
            ? 'bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300'
            : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300';

          return `
            <div onclick="openEtfChartForSymbol('${escHtml(a.symbol)}')" title="Ver gráfica de precios de ${escHtml(a.symbol)}"
              class="py-2.5 px-1.5 -mx-1.5 rounded flex items-center justify-between gap-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/60 transition">
              <div class="min-w-0">
                <div class="flex items-center gap-1.5">
                  <span class="font-bold font-mono text-slate-900 dark:text-slate-100">${escHtml(a.symbol)}</span>
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${trendCls}">${isBull ? 'ALCISTA' : 'BAJISTA'}</span>
                </div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate">${escHtml(ASSET_NAMES[a.symbol] || '')}</div>
              </div>
              <div class="flex items-center gap-2.5 text-[11px] font-mono tabular-nums shrink-0">
                <span class="font-semibold text-slate-800 dark:text-slate-200">$${Number(price).toFixed(2)}</span>
                <span class="font-bold min-w-[62px] text-right ${isCore ? 'text-brand-800 dark:text-brand-200 bg-brand-50 dark:bg-brand-950 px-2 py-0.5 rounded' : 'text-slate-400 dark:text-slate-500'}">
                  ${isCore ? coreWeight + '% Core' : '0%'}
                </span>
              </div>
            </div>
          `;
        })
        .join('');
    } else if ((LAST_LIVE_STATUS?.state?.positions || []).length > 0) {
      gridEl.innerHTML = LAST_LIVE_STATUS.state.positions
        .map((p) => `
          <div class="py-2.5 flex items-center justify-between gap-2 font-mono tabular-nums">
            <div>
              <span class="font-bold text-slate-900 dark:text-slate-100">${escHtml(p.broker_symbol)}</span>
              <span class="text-[11px] text-slate-500 dark:text-slate-400 font-sans ml-1.5">${escHtml(ASSET_NAMES[p.internal_symbol] || p.motor || '')}</span>
            </div>
            <div class="flex items-center gap-2 text-[11px]">
              <span class="font-semibold text-slate-800 dark:text-slate-200">$${Number(p.current_price).toFixed(2)}</span>
              <span class="px-2 py-0.5 rounded bg-brand-50 dark:bg-brand-950 text-brand-800 dark:text-brand-200 font-bold">${p.weight_pct}%</span>
            </div>
          </div>
        `)
        .join('');
    }
  }
}

// ============================================================================
// SINCRONIZACIÓN HORARIA NY / MADRID Y DETECTOR DST (SIN EMOJIS)
// ============================================================================
function getTzOffsetMinutes(timeZone, dateObj) {
  try {
    const utcDate = new Date(dateObj.toLocaleString('en-US', { timeZone: 'UTC' }));
    const tzDate = new Date(dateObj.toLocaleString('en-US', { timeZone }));
    return Math.round((tzDate - utcDate) / 60000);
  } catch (e) {
    return null;
  }
}

function getShortTzName(timeZone, dateObj, offsetMin = null) {
  if (timeZone === 'Europe/Madrid') {
    if (offsetMin === 120) return 'CEST';
    if (offsetMin === 60) return 'CET';
  }
  if (timeZone === 'America/New_York') {
    if (offsetMin === -240) return 'EDT';
    if (offsetMin === -300) return 'EST';
  }
  try {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone, timeZoneName: 'short' }).formatToParts(dateObj);
    const tzPart = parts.find((p) => p.type === 'timeZoneName');
    return tzPart ? tzPart.value : '';
  } catch (e) {
    return '';
  }
}

function updateScheduleAndDstUI(data, cfg) {
  const schedLabel = document.getElementById('pt-sched-label');
  const dstBadge = document.getElementById('pt-dst-badge');

  const now = new Date();
  const nyOff = getTzOffsetMinutes('America/New_York', now);
  const madOff = getTzOffsetMinutes('Europe/Madrid', now);
  const nyName = getShortTzName('America/New_York', now, nyOff) || 'ET';
  const madName = getShortTzName('Europe/Madrid', now, madOff) || 'CET';
  const diffHours = nyOff !== null && madOff !== null ? Math.round((madOff - nyOff) / 60) : 6;
  const isDstShift = data?.is_dst_mismatch === true || (diffHours !== 6);

  if (schedLabel) {
    if (data?.schedule_time_ny && data?.schedule_time_madrid) {
      schedLabel.textContent = `${data.schedule_time_ny} (${data.schedule_time_madrid})`;
    } else if (data?.next_run_display) {
      schedLabel.textContent = data.next_run_display;
    } else {
      schedLabel.textContent = `15:55 ${nyName} · ${(cfg?.schedule_time_cet || (diffHours === 5 ? '20:55' : '21:55'))} ${madName}`;
    }
  }

  if (dstBadge) {
    // Determinar si el mercado (NYSE/Nasdaq) está abierto ahora
    let isMarketOpen = false;
    if (typeof data?.is_market_open === 'boolean') {
      isMarketOpen = data.is_market_open;
    } else if (typeof data?.time_info?.is_market_open === 'boolean') {
      isMarketOpen = data.time_info.is_market_open;
    } else {
      // Cálculo de contingencia cliente
      try {
        const nyParts = new Intl.DateTimeFormat('en-US', {
          timeZone: 'America/New_York',
          hour12: false,
          weekday: 'short',
          hour: 'numeric',
          minute: 'numeric',
        }).formatToParts(now);
        const getVal = (t) => nyParts.find((p) => p.type === t)?.value;
        const day = getVal('weekday');
        if (day !== 'Sat' && day !== 'Sun') {
          const hh = parseInt(getVal('hour') || '0', 10);
          const mm = parseInt(getVal('minute') || '0', 10);
          const totalMin = hh * 60 + mm;
          isMarketOpen = totalMin >= 570 && totalMin < 960; // 09:30 a 16:00 ET
        }
      } catch (e) {
        isMarketOpen = false;
      }
    }

    const customLabel = data?.dst_badge || data?.dst_status || null;
    const baseDstText = isDstShift
      ? `DST Desfase EU/US (${diffHours}h · ${nyName}/${madName})`
      : `NYSE · ${nyName}/${madName} (+${diffHours}h)`;

    if (isMarketOpen) {
      // MERCADO ABIERTO -> CUADRO EN VERDE
      dstBadge.textContent = customLabel ? `● ${customLabel}` : `● Mercado Abierto · ${baseDstText}`;
      dstBadge.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 dark:bg-emerald-950/70 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 shadow-xs transition-colors';
      dstBadge.title = `Mercado estadounidense (NYSE/Nasdaq) ABIERTO en horario regular (09:30 a 16:00 ${nyName}). Cotizaciones en vivo activas.`;
    } else {
      // MERCADO CERRADO -> CUADRO EN AMARILLO
      dstBadge.textContent = customLabel ? `○ ${customLabel}` : `○ Mercado Cerrado · ${baseDstText}`;
      dstBadge.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-50 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 shadow-xs transition-colors';
      const reasonDesc = data?.market_status_desc || data?.time_info?.market_status_desc || `Mercado fuera de sesión regular (09:30 a 16:00 ${nyName}).`;
      dstBadge.title = `${reasonDesc} El bot de Aegis vigila 24/7 y ejecutará el rebalanceo al cierre (${data?.schedule_time_madrid || (diffHours === 5 ? '20:55 CET' : '21:55 CET')}).`;
    }
  }
}

// ============================================================================
// TARJETA DE MOTORES TÁCTICOS EN VIVO (M1–M6)
// ============================================================================
function renderTacticalEnginesCard(data, cfg) {
  const asofBadge = document.getElementById('tactical-asof-badge');
  const regimePill = document.getElementById('tactical-regime-pill');
  const corePills = document.getElementById('tactical-core-pills');
  const bodyEl = document.getElementById('tactical-live-body');
  if (!bodyEl) return;

  const tac = data?.tactical || null;
  const enabledMotors = cfg?.enabled_motors || {};

  if (tac) {
    if (asofBadge) asofBadge.textContent = tac.data_as_of ? `Cierre ${tac.data_as_of}` : 'En vivo';

    if (regimePill) {
      const ratioStr = tac.vts_ratio !== undefined && tac.vts_ratio !== null ? ` · VTS ${Number(tac.vts_ratio).toFixed(3)}` : '';
      const shortState = (tac.vts_state || tac.regime || 'CONTANGO').split(' (')[0];
      regimePill.textContent = `${shortState}${ratioStr}`;
      const isBack = String(tac.vts_state || tac.regime || '').toUpperCase().includes('BACKWARD') || Number(tac.vts_ratio) >= 1.0;
      regimePill.className = isBack
        ? 'px-2.5 py-1 rounded text-[11px] font-mono font-bold bg-red-50 dark:bg-red-950 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-900 tabular-nums'
        : 'px-2.5 py-1 rounded text-[11px] font-mono font-bold bg-brand-50 dark:bg-brand-950 text-brand-800 dark:text-brand-200 border border-brand-200 dark:border-brand-800 tabular-nums';
    }

    if (corePills) {
      const coreEntries = Object.entries(tac.core_allocation || {}).filter(([, w]) => Number(w) > 0);
      if (coreEntries.length > 0) {
        corePills.innerHTML = coreEntries
          .map(([sym, w]) => `<span class="px-2 py-0.5 rounded bg-brand-100 dark:bg-brand-900 text-brand-800 dark:text-brand-200 font-semibold">${escHtml(sym)} ${Number(w).toFixed(0)}%</span>`)
          .join('');
      } else {
        const idleTxt = tac.idle_cash_pct !== undefined ? ` · Liquidez Táctica ${Number(tac.idle_cash_pct).toFixed(0)}%` : '';
        corePills.innerHTML = `<span class="px-2 py-0.5 rounded bg-amber-50 dark:bg-slate-800 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800 font-semibold">0% Core · Escudo Volatilidad${idleTxt}</span>`;
      }
    }
  } else {
    if (asofBadge) asofBadge.textContent = APP_DATA?.live_scan?.as_of_date || 'Modo 3';
  }

  const openTrades = Array.isArray(tac?.open_trades) ? tac.open_trades : [];
  const signalsToday = Array.isArray(tac?.signals_today) ? tac.signals_today : [];

  const engineKeys = ['M1_PULLBACK', 'M2_VIX_DIV', 'M3_BEAR_SHORT', 'M4_CTA_TREND', 'M5_VOL_CRUSH', 'M6_TOTM'];
  const armedStrip = `
    <div class="flex flex-wrap items-center gap-1.5 pt-1">
      ${engineKeys
        .map((k) => {
          const on = enabledMotors[k] !== false;
          const m = MOTOR_META[k];
          return `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
            on
              ? 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700'
              : 'opacity-45 bg-slate-50 dark:bg-slate-900 text-slate-400 border-slate-200 dark:border-slate-800 line-through'
          }">${escHtml(m.badge)}</span>`;
        })
        .join('')}
    </div>
  `;

  if (openTrades.length === 0 && signalsToday.length === 0) {
    bodyEl.innerHTML = `
      <div class="p-3.5 rounded-md bg-slate-50 dark:bg-slate-800/60 border border-dashed border-slate-200 dark:border-slate-700 space-y-2">
        <div class="flex items-center gap-2 text-slate-700 dark:text-slate-200 font-medium">
          <span class="w-2 h-2 rounded-full bg-brand-600 shrink-0"></span>
          <span>Sin operaciones tácticas abiertas hoy · Capital asignado según Core Modo 3 Élite</span>
        </div>
        ${armedStrip}
      </div>
    `;
    return;
  }

  let sectionsHtml = '';

  if (openTrades.length > 0) {
    sectionsHtml += `
      <div class="space-y-2">
        <div class="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Posiciones Tácticas Abiertas (${openTrades.length})
        </div>
        <div class="space-y-2">
          ${openTrades
            .map((t) => {
              const meta = getEngineMeta(t.engine_id);
              const ret = Number(t.unrealized_ret_pct || 0);
              const retCls = ret >= 0 ? 'text-brand-700 dark:text-brand-300' : 'text-red-700 dark:text-red-400';
              const dirCls = t.direction === 'SHORT'
                ? 'bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-300'
                : 'bg-brand-50 text-brand-800 dark:bg-brand-950 dark:text-brand-200';
              return `
                <div class="p-3 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 space-y-1.5">
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5">
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${meta.pillCls}">${escHtml(meta.badge)}</span>
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${dirCls}">${escHtml(t.direction || 'LONG')}</span>
                      <span class="font-mono font-bold text-sm text-slate-900 dark:text-slate-100">${escHtml(t.symbol)}</span>
                    </div>
                    <div class="flex items-center gap-2.5 font-mono tabular-nums text-xs">
                      <span class="font-bold ${retCls}">${fmtPct(ret)}</span>
                      <span class="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 font-bold text-slate-800 dark:text-slate-200">${Number(t.weight_pct || 0).toFixed(1)}% peso</span>
                    </div>
                  </div>
                  <div class="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
                    <span>Entrada: $${Number(t.entry_price || 0).toFixed(2)} -> Actual: $${Number(t.current_price || 0).toFixed(2)}</span>
                    <span>${t.days_held ?? 0}d en cartera (${escHtml(t.entry_date || '--')})</span>
                  </div>
                  ${t.reason ? `<p class="text-[11px] text-slate-600 dark:text-slate-300 leading-snug">${escHtml(t.reason)}</p>` : ''}
                </div>
              `;
            })
            .join('')}
        </div>
      </div>
    `;
  }

  if (signalsToday.length > 0) {
    const sigDate = signalsToday[0]?.date || '';
    const headerTitle = sigDate ? `Señales Disparadas (${sigDate})` : `Señales Disparadas (${signalsToday.length})`;
    sectionsHtml += `
      <div class="space-y-2">
        <div class="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-brand-700 dark:text-brand-300">
          <span>${headerTitle}</span>
          <span class="text-[10px] font-mono font-normal text-slate-500">${signalsToday.length} ${signalsToday.length === 1 ? 'señal' : 'señales'}</span>
        </div>
        <div class="space-y-2">
          ${signalsToday
            .map((s) => {
              const meta = getEngineMeta(s.engine_id);
              const confTxt = s.meta_confidence !== undefined && s.meta_confidence !== null
                ? `Convicción ${Number(s.meta_confidence).toFixed(2)}x`
                : '';
              return `
                <div class="p-3 rounded-md border border-brand-300 dark:border-brand-800 bg-brand-50/60 dark:bg-slate-800 space-y-1.5">
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5">
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${meta.pillCls}">${escHtml(meta.badge)}</span>
                      <span class="font-mono font-bold text-slate-900 dark:text-slate-100">${escHtml(s.direction || 'LONG')} ${escHtml(s.symbol)}</span>
                      ${s.date ? `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-white dark:bg-slate-900 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">${escHtml(s.date)}</span>` : ''}
                    </div>
                    ${confTxt ? `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-brand-700 text-white tabular-nums">${confTxt}</span>` : ''}
                  </div>
                  <div class="flex flex-wrap items-center gap-3 text-[11px] font-mono tabular-nums text-slate-700 dark:text-slate-300">
                    <span>Precio Entrada: <b>$${Number(s.entry_price || 0).toFixed(2)}</b></span>
                    ${s.stop_price != null ? `<span class="text-red-700 dark:text-red-400">Stop: <b>$${Number(s.stop_price).toFixed(2)}</b></span>` : ''}
                  </div>
                  ${s.reason ? `<p class="text-[11px] text-slate-600 dark:text-slate-300 leading-snug">${escHtml(s.reason)}</p>` : ''}
                </div>
              `;
            })
            .join('')}
        </div>
      </div>
    `;
  }

  bodyEl.innerHTML = sectionsHtml + armedStrip;
}

// ============================================================================
// CENTRO DE CONTROL EN VIVO (CARTERA, ÓRDENES, LOGS Y PARÁMETROS)
// ============================================================================
async function fetchLiveStatus(initForm = false, forceRefresh = false) {
  if (liveFetchInFlight && !initForm && !forceRefresh) return;
  liveFetchInFlight = true;
  try {
    const url = forceRefresh ? '/api/live/status?refresh=1' : '/api/live/status';
    const res = await fetch(url);
    const data = await res.json();
    LAST_LIVE_STATUS = data;
    renderLiveControlCenter(data, initForm || !LIVE_CONFIG_INITIALIZED);
    LIVE_CONFIG_INITIALIZED = true;
  } catch (err) {
    console.error('Error consultando estado en vivo:', err);
  } finally {
    liveFetchInFlight = false;
  }
}

function renderLiveControlCenter(data, populateForm = false) {
  if (data?.config) {
    const resetPanel = document.getElementById('panel-reset-paper');
    if (resetPanel) {
      const isPaper = data.config.broker_provider === 'LOCAL_PAPER' || data.config.broker_provider === 'ALPACA_PAPER';
      resetPanel.style.display = isPaper ? 'flex' : 'none';
    }
  }
  if (!data || !data.config || !data.state) return;
  const cfg = data.config;
  const state = data.state;
  const acct = state.account || {};
  const conn = data.broker_connection || { ok: true, message: '' };

  // 1. Indicadores de Cabecera
  const hdrDot = document.getElementById('hdr-status-dot');
  const hdrStatus = document.getElementById('hdr-status-text');
  const hdrBroker = document.getElementById('hdr-broker-text');
  const hdrMobDot = document.getElementById('hdr-mobile-dot');
  const hdrMobStatus = document.getElementById('hdr-mobile-status');
  const botRunning = cfg.bot_running !== false;

  if (hdrDot) hdrDot.className = `w-2 h-2 rounded-full ${botRunning ? 'bg-brand-600' : 'bg-amber-600'}`;
  if (hdrMobDot) hdrMobDot.className = `w-1.5 h-1.5 rounded-full shrink-0 ${botRunning ? 'bg-brand-600' : 'bg-amber-600'}`;

  if (hdrStatus) {
    hdrStatus.textContent = botRunning
      ? (cfg.execution_mode === 'AUTO_100' ? 'Activo · Automático' : 'Activo · Copiloto')
      : 'Pausado';
  }
  if (hdrBroker) {
    hdrBroker.textContent = cfg.broker_provider === 'ALPACA_PAPER'
      ? 'Alpaca Paper'
      : (cfg.broker_provider === 'ALPACA_LIVE' ? 'Bróker Real' : 'Paper Local');
  }

  const totalEq = Number(acct.total_equity_usd || 10000);
  const initialCap = Number(acct.initial_capital || 10000);
  const totalRet = Number(acct.total_return_pct || 0);

  if (hdrMobStatus) {
    hdrMobStatus.textContent = `${botRunning ? 'Activo' : 'Pausado'} · ${fmtUSD(totalEq)} (${fmtPct(totalRet)})`;
  }

  // 2. Barra de Estado Operativo
  const statusBadge = document.getElementById('pt-bot-status-badge');
  const toggleBtn = document.getElementById('btn-toggle-bot');
  if (statusBadge && toggleBtn) {
    if (botRunning) {
      statusBadge.textContent = 'ACTIVO (24/7)';
      statusBadge.className = 'px-2.5 py-0.5 rounded text-xs font-semibold bg-brand-50 dark:bg-brand-950 text-brand-800 dark:text-brand-200 border border-brand-200 dark:border-brand-800 font-mono';
      toggleBtn.textContent = 'Pausar Bot';
      toggleBtn.className = 'touch-target px-3.5 py-2.5 sm:py-2 rounded-md text-xs font-semibold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 transition';
    } else {
      statusBadge.textContent = 'PAUSADO';
      statusBadge.className = 'px-2.5 py-0.5 rounded text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 font-mono';
      toggleBtn.textContent = 'Reanudar Bot';
      toggleBtn.className = 'touch-target px-3.5 py-2.5 sm:py-2 rounded-md text-xs font-semibold bg-brand-700 hover:bg-brand-800 text-white transition';
    }
  }

  const modeBadge = document.getElementById('pt-mode-badge');
  if (modeBadge) {
    modeBadge.textContent = cfg.execution_mode === 'AUTO_100' ? '100% Automático' : 'Modo Copiloto';
  }

  const brokerBadge = document.getElementById('pt-broker-badge');
  if (brokerBadge) {
    brokerBadge.textContent = cfg.broker_provider === 'ALPACA_PAPER'
      ? 'Alpaca Paper'
      : (cfg.broker_provider === 'ALPACA_LIVE' ? 'Bróker Real' : 'Paper Local');
  }

  const connMsg = document.getElementById('pt-connection-msg');
  if (connMsg) {
    const dotCls = conn.ok ? 'bg-brand-600' : 'bg-amber-600';
    connMsg.innerHTML = `<span class="inline-block w-2 h-2 rounded-full ${dotCls} mr-1.5 align-middle"></span><span>${escHtml(conn.message)}</span>`;
  }

  const lastScan = document.getElementById('pt-last-scan');
  if (lastScan) lastScan.textContent = state.last_scan_time || '--';

  updateScheduleAndDstUI(data, cfg);

  // 3. Banner Modo Copiloto
  const copilotBanner = document.getElementById('pt-copilot-banner');
  const copilotDesc = document.getElementById('pt-copilot-desc');
  const mobBadgeInicio = document.getElementById('mob-badge-inicio');
  const pending = state.pending_confirmations || [];
  if (copilotBanner && copilotDesc) {
    if (pending.length > 0) {
      const p = pending[0];
      const syms = Object.keys(p.targets || {})
        .map((s) => `${s} (${(p.targets[s].weight * 100).toFixed(0)}%)`)
        .join(', ');
      copilotDesc.textContent = `Propuesta pendiente (${p.trigger_source}): Objetivo -> ${syms}`;
      copilotBanner.classList.remove('hidden');
      if (mobBadgeInicio) mobBadgeInicio.classList.remove('hidden');
    } else {
      copilotBanner.classList.add('hidden');
      if (mobBadgeInicio) mobBadgeInicio.classList.add('hidden');
    }
  }

  // 4. Métricas de Cuenta
  const eqEl = document.getElementById('pt-total-equity');
  if (eqEl) eqEl.textContent = fmtUSD(totalEq);

  const retEl = document.getElementById('pt-total-ret');
  if (retEl) {
    retEl.textContent = `${fmtPct(totalRet)} (Base ${fmtUSD(initialCap)})`;
    retEl.className = `kpi-num text-[11px] sm:text-xs font-mono mt-0.5 font-semibold truncate ${
      totalRet >= 0 ? 'text-brand-700 dark:text-brand-300' : 'text-red-700 dark:text-red-400'
    }`;
  }

  const posValNum = Number(acct.positions_value_usd || 0);
  const cashNum = Number(acct.cash_usd || 0);
  const positions = state.positions || [];

  const posValEl = document.getElementById('pt-pos-value');
  if (posValEl) posValEl.textContent = fmtUSD(posValNum);

  const posCountEl = document.getElementById('pt-pos-count');
  if (posCountEl) posCountEl.textContent = `${positions.length} ${positions.length === 1 ? 'posición activa' : 'posiciones activas'}`;

  const cashEl = document.getElementById('pt-cash-value');
  if (cashEl) cashEl.textContent = fmtUSD(cashNum);

  const ddVal = Number(acct.current_dd_pct || 0);
  const ddEl = document.getElementById('pt-dd-value');
  if (ddEl) {
    ddEl.textContent = `${ddVal.toFixed(2)}%`;
    ddEl.className = `kpi-num text-lg sm:text-2xl font-bold font-mono mt-1 ${
      ddVal <= -4 ? 'text-red-700 dark:text-red-400' : 'text-slate-900 dark:text-slate-100'
    }`;
  }

  const ddLimitEl = document.getElementById('pt-dd-limit-label');
  if (ddLimitEl) ddLimitEl.textContent = `Cortafuegos: ${cfg.daily_kill_switch_dd_pct || -8.0}%`;

  const mobEq = document.getElementById('cartera-mob-equity');
  const mobInv = document.getElementById('cartera-mob-invested');
  const mobCash = document.getElementById('cartera-mob-cash');
  if (mobEq) mobEq.textContent = fmtUSD(totalEq);
  if (mobInv) mobInv.textContent = fmtUSD(posValNum);
  if (mobCash) mobCash.textContent = fmtUSD(cashNum);

  const carteraPosBadge = document.getElementById('cartera-pos-badge');
  if (carteraPosBadge) carteraPosBadge.textContent = `${positions.length} ${positions.length === 1 ? 'abierta' : 'abiertas'}`;

  const mobBadgeCartera = document.getElementById('mob-badge-cartera');
  if (mobBadgeCartera) {
    if (positions.length > 0) {
      mobBadgeCartera.textContent = String(positions.length);
      mobBadgeCartera.classList.remove('hidden');
    } else {
      mobBadgeCartera.classList.add('hidden');
    }
  }

  // 5. Motores Tácticos M1–M6 y Pulso de Mercado
  renderTacticalEnginesCard(data, cfg);
  renderLiveScan();

  // 6. Posiciones Abiertas
  const posTbody = document.getElementById('pt-positions-tbody');
  const posMobCards = document.getElementById('pt-positions-mobile-cards');

  if (positions.length === 0) {
    if (posTbody) {
      posTbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-slate-400 font-sans">100% en liquidez disponible. Pulsa "Escanear y Sincronizar" para evaluar señales diarias.</td></tr>`;
    }
    if (posMobCards) {
      posMobCards.innerHTML = `
        <div class="p-4 rounded-md border border-dashed border-slate-200 dark:border-slate-700 text-center space-y-1.5">
          <div class="text-xs font-medium text-slate-600 dark:text-slate-300">100% en liquidez disponible</div>
          <p class="text-[11px] text-slate-400">Pulsa Sincronizar para evaluar las reglas diarias de entrada.</p>
        </div>
      `;
    }
  } else {
    if (posTbody) {
      posTbody.innerHTML = positions
        .map((p) => {
          const dirCls = p.direction === 'LONG'
            ? 'bg-brand-50 text-brand-800 dark:bg-brand-950 dark:text-brand-200'
            : 'bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-300';
          return `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
              <td class="py-2.5 px-3 font-bold text-slate-900 dark:text-slate-100">${escHtml(p.broker_symbol)} <span class="text-[11px] text-slate-400 font-sans">(${escHtml(p.internal_symbol)})</span></td>
              <td class="py-2.5 px-3"><span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${dirCls}">${escHtml(p.direction)}</span></td>
              <td class="py-2.5 px-3 font-sans text-xs text-slate-700 dark:text-slate-300">${escHtml(p.motor)}</td>
              <td class="py-2.5 px-3 text-right text-slate-700 dark:text-slate-300">${p.qty}</td>
              <td class="py-2.5 px-3 text-right text-slate-700 dark:text-slate-300">$${p.current_price}</td>
              <td class="py-2.5 px-3 text-right font-bold text-slate-900 dark:text-slate-100">${fmtUSD(p.market_value_usd)}</td>
              <td class="py-2.5 px-3 text-right font-bold text-brand-800 dark:text-brand-300">${p.weight_pct}%</td>
            </tr>
          `;
        })
        .join('');
    }

    if (posMobCards) {
      posMobCards.innerHTML = positions
        .map((p) => {
          const meta = getEngineMeta(p.motor);
          const dirCls = p.direction === 'LONG'
            ? 'bg-brand-50 text-brand-800 dark:bg-brand-950 dark:text-brand-200'
            : 'bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-300';
          const barW = Math.min(100, Math.max(2, Math.abs(Number(p.weight_pct || 0))));
          const symNote = p.internal_symbol && p.internal_symbol !== p.broker_symbol ? ` (${p.internal_symbol})` : '';
          return `
            <div class="p-3.5 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 space-y-2">
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <span class="font-mono font-bold text-sm text-slate-900 dark:text-slate-100">${escHtml(p.broker_symbol)}${escHtml(symNote)}</span>
                    <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${dirCls}">${escHtml(p.direction)}</span>
                  </div>
                  <div class="mt-1">
                    <span class="inline-block px-2 py-0.5 rounded text-[10px] font-semibold border ${meta.pillCls}">${escHtml(p.motor)}</span>
                  </div>
                </div>
                <div class="text-right font-mono tabular-nums shrink-0">
                  <div class="text-sm font-bold text-slate-900 dark:text-slate-100">${fmtUSD(p.market_value_usd)}</div>
                  <div class="text-xs font-bold text-brand-700 dark:text-brand-300">${p.weight_pct}% cartera</div>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200 dark:border-slate-700 text-[11px] font-mono tabular-nums text-slate-600 dark:text-slate-300">
                <div>Participaciones: <b class="text-slate-900 dark:text-slate-100">${p.qty}</b></div>
                <div class="text-right">Precio: <b class="text-slate-900 dark:text-slate-100">$${p.current_price}</b></div>
              </div>
              <div class="w-full h-1.5 rounded bg-slate-200 dark:bg-slate-700 overflow-hidden">
                <div class="h-full rounded bg-brand-700 dark:bg-brand-500" style="width:${barW}%"></div>
              </div>
            </div>
          `;
        })
        .join('');
    }
  }

  // 7. Historial de Órdenes Ejecutadas
  const orders = state.orders_history || [];
  const ordTbody = document.getElementById('pt-orders-tbody');
  const ordMobCards = document.getElementById('pt-orders-mobile-cards');
  const carteraOrdBadge = document.getElementById('cartera-ord-badge');
  if (carteraOrdBadge) carteraOrdBadge.textContent = `${orders.length} ${orders.length === 1 ? 'orden' : 'órdenes'}`;

  if (orders.length === 0) {
    if (ordTbody) {
      ordTbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-slate-400 font-sans">Sin órdenes ejecutadas todavía.</td></tr>`;
    }
    if (ordMobCards) {
      ordMobCards.innerHTML = `<div class="p-4 rounded-md border border-dashed border-slate-200 dark:border-slate-700 text-center text-xs text-slate-400">Sin órdenes ejecutadas todavía.</div>`;
    }
  } else {
    const recentOrders = orders.slice(0, 25);
    if (ordTbody) {
      ordTbody.innerHTML = recentOrders
        .map((o) => {
          const isBuy = String(o.side || '').includes('BUY');
          const sideCls = isBuy ? 'text-brand-700 dark:text-brand-300' : 'text-amber-700 dark:text-amber-400';
          return `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
              <td class="py-2 px-3 text-slate-500 dark:text-slate-400 text-[11px]">${escHtml(o.time)}</td>
              <td class="py-2 px-3 font-bold ${sideCls}">${escHtml(o.side)}</td>
              <td class="py-2 px-3 font-bold text-slate-900 dark:text-slate-100">${escHtml(o.symbol)}</td>
              <td class="py-2 px-3 text-right text-slate-700 dark:text-slate-200">${fmtUSD(o.notional_usd)}</td>
              <td class="py-2 px-3 font-sans text-[11px] text-slate-600 dark:text-slate-300">${escHtml(o.motor)}</td>
              <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-brand-50 dark:bg-brand-950 text-brand-800 dark:text-brand-200 text-[10px] font-bold border border-brand-200 dark:border-brand-800">${escHtml(o.status)}</span></td>
            </tr>
          `;
        })
        .join('');
    }

    if (ordMobCards) {
      ordMobCards.innerHTML = recentOrders
        .map((o) => {
          const isBuy = String(o.side || '').includes('BUY');
          const sidePill = isBuy
            ? 'bg-brand-50 text-brand-800 dark:bg-brand-950 dark:text-brand-200'
            : 'bg-amber-50 text-amber-800 dark:bg-slate-900 dark:text-amber-300';
          return `
            <div class="p-3 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 space-y-1.5">
              <div class="flex items-center justify-between gap-2 font-mono tabular-nums">
                <div class="flex items-center gap-1.5">
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${sidePill}">${escHtml(o.side)}</span>
                  <span class="font-bold text-sm text-slate-900 dark:text-slate-100">${escHtml(o.symbol)}</span>
                </div>
                <span class="font-bold text-xs text-slate-900 dark:text-slate-100">${fmtUSD(o.notional_usd)}</span>
              </div>
              <div class="flex items-center justify-between gap-2 text-[11px]">
                <span class="font-mono tabular-nums text-slate-400">${escHtml(o.time)} · ${escHtml(o.motor || '')}</span>
                <span class="px-2 py-0.5 rounded bg-brand-50 dark:bg-brand-950 text-brand-800 dark:text-brand-200 text-[10px] font-mono font-bold">${escHtml(o.status)}</span>
              </div>
            </div>
          `;
        })
        .join('');
    }
  }

  // 8. Registro de Eventos del Sistema
  const logs = state.logs || [];
  const logsBox = document.getElementById('pt-logs-box');
  if (logsBox) {
    logsBox.innerHTML = logs.length === 0
      ? `<div class="text-slate-400">Sin eventos registrados.</div>`
      : logs
          .slice(0, 35)
          .map((l) => {
            let col = 'text-slate-700 dark:text-slate-300';
            if (l.level === 'SUCCESS') col = 'text-brand-700 dark:text-brand-300 font-semibold';
            else if (l.level === 'WARN') col = 'text-amber-700 dark:text-amber-400 font-semibold';
            else if (l.level === 'ERROR') col = 'text-red-700 dark:text-red-400 font-bold';
            return `<div class="leading-relaxed break-words"><span class="text-slate-400 dark:text-slate-500">[${escHtml(l.time)}]</span> <span class="${col}">${escHtml(l.msg)}</span></div>`;
          })
          .join('');
  }

  // 9. Poblar Controles del Formulario Operativo y Modal
  if (populateForm) {
    const setVal = (id, v) => {
      const el = document.getElementById(id);
      if (el && v !== undefined && v !== null) el.value = v;
    };
    const setChk = (id, v) => {
      const el = document.getElementById(id);
      if (el) el.checked = !!v;
    };

    setVal('cfg-exec-mode', cfg.execution_mode || 'AUTO_100');
    setVal('cfg-capital', cfg.allocated_capital_usd || 10000);
    setVal('cfg-risk-pct', cfg.risk_per_trade_pct || 2.5);
    setVal('cfg-fast-cap', cfg.max_fast_slot_pct || 55);
    setVal('cfg-cta-cap', cfg.max_cta_slot_pct || 40);
    setVal('cfg-kill-dd', cfg.daily_kill_switch_dd_pct || -8.0);
    setVal('cfg-sched-time', cfg.schedule_time_cet || '21:55');

    const em = cfg.enabled_motors || {};
    setChk('chk-m1', em.M1_PULLBACK !== false);
    setChk('chk-m2', em.M2_VIX_DIV !== false);
    setChk('chk-m3', em.M3_BEAR_SHORT !== false);
    setChk('chk-m4', em.M4_CTA_TREND !== false);
    setChk('chk-m5', em.M5_VOL_CRUSH !== false);
    setChk('chk-m6', em.M6_TOTM !== false);
    updateEngineStateLabels();

    setVal('cfg-broker-provider', cfg.broker_provider || 'LOCAL_PAPER');
    setVal('cfg-alpaca-endpoint', cfg.alpaca_endpoint || 'https://paper-api.alpaca.markets');
    setVal('cfg-alpaca-key', cfg.alpaca_api_key || '');
    setVal('cfg-alpaca-secret', cfg.alpaca_secret_key || '');

    setVal('cfg-mobile-phone', cfg.mobile_phone || cfg.signal_recipient_phone || '');
    setVal('cfg-sig-url', cfg.signal_api_url || 'https://api.callmebot.com/signal/send.php');
    setVal('cfg-sig-apikey', cfg.signal_apikey || '');
  }
}

// ============================================================================
// ACCIONES EN VIVO Y GUARDADO DE CONFIGURACIÓN
// ============================================================================
async function triggerLiveAction(actionName, simulateMotor = null, confirmed = false) {
  if ((actionName === 'PANIC_CLOSE_ALL' || actionName === 'RESET_ACCOUNT') && !confirmed) {
    openDestructiveConfirmModal(actionName);
    return;
  }

  try {
    const res = await fetch('/api/live/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: actionName, simulate_motor: simulateMotor }),
    });
    const data = await res.json();
    if (data.status) {
      LAST_LIVE_STATUS = data.status;
      renderLiveControlCenter(data.status, false);
    }
    if (data.result && data.result.message) {
      const isAlertTest = actionName.includes('TEST_');
      showConfigFeedback(data.result.message, isAlertTest);
    }
    if (ACTIVE_PERF_SUBTAB === 'tax') {
      loadLiveTaxAudit();
    }
  } catch (err) {
    console.error('Error ejecutando orden en vivo:', err);
  }
}

async function saveLiveConfigFromUI(fromModal = false) {
  const getVal = (id) => document.getElementById(id)?.value?.trim();
  const getNum = (id) => Number(document.getElementById(id)?.value);
  const getChk = (id) => document.getElementById(id)?.checked;

  const mobilePhone = getVal('cfg-mobile-phone') || '';

  const payload = {
    execution_mode: getVal('cfg-exec-mode'),
    broker_provider: getVal('cfg-broker-provider'),
    allocated_capital_usd: getNum('cfg-capital'),
    risk_per_trade_pct: getNum('cfg-risk-pct'),
    max_fast_slot_pct: getNum('cfg-fast-cap'),
    max_cta_slot_pct: getNum('cfg-cta-cap'),
    daily_kill_switch_dd_pct: getNum('cfg-kill-dd'),
    schedule_time_cet: getVal('cfg-sched-time'),
    enabled_motors: {
      M1_PULLBACK: getChk('chk-m1'),
      M2_VIX_DIV: getChk('chk-m2'),
      M3_BEAR_SHORT: getChk('chk-m3'),
      M4_CTA_TREND: getChk('chk-m4'),
      M5_VOL_CRUSH: getChk('chk-m5'),
      M6_TOTM: getChk('chk-m6'),
    },
    alpaca_endpoint: getVal('cfg-alpaca-endpoint'),
    alpaca_api_key: getVal('cfg-alpaca-key'),
    alpaca_secret_key: getVal('cfg-alpaca-secret'),
    mobile_phone: mobilePhone,
    signal_recipient_phone: mobilePhone,
    signal_api_url: getVal('cfg-sig-url'),
    signal_apikey: getVal('cfg-sig-apikey'),
  };

  try {
    const res = await fetch('/api/live/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.status) {
      LAST_LIVE_STATUS = data.status;
      renderLiveControlCenter(data.status, true);
    }
    showConfigFeedback('Parámetros guardados y recargados en caliente.', fromModal);
  } catch (err) {
    console.error('Error guardando configuración:', err);
  }
}

function showConfigFeedback(msg, inModal = false) {
  const el = inModal ? document.getElementById('modal-save-feedback') : document.getElementById('cfg-save-feedback');
  if (!el) return;
  el.textContent = msg;
  el.classList.remove('hidden');
  setTimeout(() => {
    el.classList.add('hidden');
  }, 4500);
}

// ============================================================================
// MÓDULO FISCAL AUTOMÁTICO AEAT (FIFO, REGLA 2 MESES, BCE, MODELO 720, CSV)
// ============================================================================
async function loadLiveTaxAudit() {
  const envSelect = document.getElementById('aeat-env-select');
  const yearSelect = document.getElementById('aeat-year-select');
  const env = envSelect?.value || 'PAPER';
  const year = yearSelect?.value || 'ALL';

  try {
    const res = await fetch(`/api/tax/live-audit?env=${encodeURIComponent(env)}&year=${encodeURIComponent(year)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const report = await res.json();
    LAST_TAX_AUDIT = report;
    renderLiveTaxAudit(report);
  } catch (err) {
    console.error('Error ejecutando auditoría fiscal AEAT:', err);
  }
}

function renderLiveTaxAudit(report) {
  if (!report || !report.summary) return;
  const s = report.summary;
  const m720 = report.modelo_720 || {};
  const f2 = report.renta_web_f2 || {};

  // Actualizar selector dinámico de ejercicios disponibles
  const yearSelect = document.getElementById('aeat-year-select');
  if (yearSelect && Array.isArray(report.years_available)) {
    const currentVal = yearSelect.value || 'ALL';
    const opts = ['ALL', ...report.years_available.map(String)];
    const uniqueOpts = [...new Set(opts)];
    yearSelect.innerHTML = uniqueOpts
      .map((y) => {
        const label = y === 'ALL' ? 'Todos los años' : `Ejercicio ${y}`;
        const sel = y === currentVal ? 'selected' : '';
        return `<option value="${escHtml(y)}" ${sel}>${escHtml(label)}</option>`;
      })
      .join('');
  }

  const setTxt = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  const netBeforePrior = Number(s.gross_gains_eur || 0) + Number(s.deductible_losses_eur || 0);
  setTxt('aeat-kpi-base', fmtEUR(s.taxable_savings_base_eur));
  setTxt('aeat-kpi-base-sub', `${s.closed_lots_count} ventas · Saldo ${fmtEUR(netBeforePrior)}`);

  setTxt('aeat-kpi-tax', fmtEUR(s.estimated_irpf_eur));
  setTxt('aeat-kpi-tax-sub', `Tipo efectivo: ${Number(s.effective_rate_pct || 0).toFixed(1)}% (FX BCE ${report.fx_eur_usd_today})`);

  setTxt('aeat-kpi-deferred', fmtEUR(s.deferred_losses_2m_eur));
  setTxt(
    'aeat-kpi-deferred-sub',
    Number(s.loss_carryforward_4y_eur || 0) > 0
      ? `Compensable 4 años: ${fmtEUR(s.loss_carryforward_4y_eur)}`
      : 'Art. 33.5.f LIRPF (±60 días)'
  );

  const el720 = document.getElementById('aeat-kpi-720');
  if (el720) {
    el720.textContent = m720.required ? 'Obligatorio' : 'Exento';
    el720.className = `kpi-num text-base sm:text-xl font-bold font-mono mt-0.5 ${
      m720.required ? 'text-amber-700 dark:text-amber-400' : 'text-slate-900 dark:text-slate-100'
    }`;
  }
  setTxt('aeat-kpi-720-sub', `Patrimonio: ${fmtEUR(m720.current_equity_eur || 0)} (${m720.threshold_usage_pct || 0}% de 50k €)`);

  // Ventanas activas de 60 días (Regla Antiaplicación)
  const lockBanner = document.getElementById('aeat-lockouts-banner');
  const lockouts = Array.isArray(report.active_60d_lockouts) ? report.active_60d_lockouts : [];
  if (lockBanner) {
    if (lockouts.length === 0) {
      lockBanner.classList.add('hidden');
      lockBanner.innerHTML = '';
    } else {
      lockBanner.classList.remove('hidden');
      lockBanner.innerHTML = `
        <div class="font-bold text-amber-900 dark:text-amber-300">
          Vigilancia Regla de los 2 Meses Activa (${lockouts.length} ISIN con venta en pérdida reciente)
        </div>
        ${lockouts
          .map(
            (lk) => `
          <div class="font-mono text-[11px] text-slate-700 dark:text-slate-300">
            ${escHtml(lk.ucits_ticker)} (${escHtml(lk.isin)}): pérdida de ${fmtEUR(lk.loss_at_risk_eur)} vendida el ${escHtml(lk.last_loss_sale_date)} · Liberación sin recompra: ${escHtml(lk.unlock_date)} (${lk.days_remaining}d restantes).
          </div>
        `
          )
          .join('')}
      `;
    }
  }

  // Tabla Renta WEB Apartado F2 por ISIN homogéneo
  const isinTbody = document.getElementById('aeat-isin-tbody');
  const byIsin = Array.isArray(f2.by_isin) ? f2.by_isin : [];
  if (isinTbody) {
    if (byIsin.length === 0) {
      isinTbody.innerHTML = `
        <tr>
          <td colspan="4" class="py-4 px-3 text-center text-slate-400 font-sans">
            Sin transmisiones cerradas en este libro/ejercicio (0 eventos fiscales).
          </td>
        </tr>
      `;
    } else {
      isinTbody.innerHTML = byIsin
        .map((g) => {
          const pnlCls = g.computable_pnl_eur >= 0 ? 'text-brand-700 dark:text-brand-300 font-bold' : 'text-red-700 dark:text-red-400 font-bold';
          return `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50">
              <td class="py-2 px-2.5">
                <div class="font-bold text-slate-900 dark:text-slate-100">${escHtml(g.ucits_ticker)}</div>
                <div class="text-[10px] text-slate-400">${escHtml(g.isin)} · ${g.operations_count} op.</div>
              </td>
              <td class="py-2 px-2.5 text-right text-slate-600 dark:text-slate-300">${fmtEUR(g.total_acquisition_eur)}</td>
              <td class="py-2 px-2.5 text-right text-slate-600 dark:text-slate-300">${fmtEUR(g.total_transmission_eur)}</td>
              <td class="py-2 px-2.5 text-right ${pnlCls}">${fmtEUR(g.computable_pnl_eur)}</td>
            </tr>
          `;
        })
        .join('');
    }
  }

  // Lotes FIFO cerrados y abiertos
  const openLots = Array.isArray(report.open_fifo_lots) ? report.open_fifo_lots : [];
  setTxt('aeat-open-lots-badge', `${openLots.length} ${openLots.length === 1 ? 'lote abierto' : 'lotes abiertos'} en cartera`);

  const txs = Array.isArray(report.transmissions) ? report.transmissions : [];
  const lotsTbody = document.getElementById('aeat-lots-tbody');
  const lotsMobile = document.getElementById('aeat-lots-mobile');

  if (txs.length === 0) {
    const openHint = openLots.length > 0
      ? `Hay ${openLots.length} lote(s) FIFO abiertos en cartera valorados al cambio BCE de compra; en España los ETFs UCITS de acumulación no tributan hasta su venta.`
      : 'Cuando el bot cierre ventas parciales o totales, aparecerá aquí cada emparejamiento FIFO en Euros listo para Renta WEB.';

    if (lotsTbody) {
      lotsTbody.innerHTML = `<tr><td colspan="7" class="py-5 px-3 text-center text-slate-400 font-sans whitespace-normal">${escHtml(openHint)}</td></tr>`;
    }
    if (lotsMobile) {
      lotsMobile.innerHTML = `<div class="p-3.5 rounded-md border border-dashed border-slate-200 dark:border-slate-700 text-center text-slate-400 text-xs">${escHtml(openHint)}</div>`;
    }
    return;
  }

  if (lotsTbody) {
    lotsTbody.innerHTML = txs
      .slice(0, 60)
      .map((tx) => {
        const resVal = tx.blocked_2m ? 0 : tx.computable_gain_eur;
        const resCls = tx.blocked_2m
          ? 'text-amber-700 dark:text-amber-400'
          : (resVal >= 0 ? 'text-brand-700 dark:text-brand-300 font-bold' : 'text-red-700 dark:text-red-400 font-bold');
        const badge2m = tx.blocked_2m
          ? '<span class="px-1.5 py-0.5 rounded bg-amber-50 dark:bg-slate-800 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800 text-[10px] font-semibold">Diferida 2M</span>'
          : '<span class="text-[11px] text-slate-500 dark:text-slate-400">Computable</span>';

        return `
          <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <td class="py-2 px-2.5 text-[11px] text-slate-600 dark:text-slate-300">${escHtml(tx.acquisition_date)} -> ${escHtml(tx.transmission_date)}</td>
            <td class="py-2 px-2.5">
              <span class="font-bold text-slate-900 dark:text-slate-100">${escHtml(tx.ucits_ticker)}</span>
              <span class="text-[10px] text-slate-400 ml-1">${escHtml(tx.isin)}</span>
            </td>
            <td class="py-2 px-2.5 text-right text-slate-700 dark:text-slate-300">${Number(tx.qty).toFixed(4)}</td>
            <td class="py-2 px-2.5 text-right text-slate-600 dark:text-slate-300">${fmtEUR(tx.acquisition_value_eur)}</td>
            <td class="py-2 px-2.5 text-right text-slate-600 dark:text-slate-300">${fmtEUR(tx.transmission_value_eur)}</td>
            <td class="py-2 px-2.5 text-right ${resCls}">${fmtEUR(tx.computable_gain_eur)}</td>
            <td class="py-2 px-2.5">${badge2m}</td>
          </tr>
        `;
      })
      .join('');
  }

  if (lotsMobile) {
    lotsMobile.innerHTML = txs
      .slice(0, 40)
      .map((tx) => {
        const resCls = tx.blocked_2m
          ? 'text-amber-700 dark:text-amber-400'
          : (tx.computable_gain_eur >= 0 ? 'text-brand-700 dark:text-brand-300' : 'text-red-700 dark:text-red-400');
        return `
          <div class="p-3 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 space-y-1 font-mono tabular-nums text-xs">
            <div class="flex items-center justify-between gap-2">
              <span class="font-bold text-slate-900 dark:text-slate-100">${escHtml(tx.ucits_ticker)} · ${escHtml(tx.isin)}</span>
              <span class="font-bold ${resCls}">${fmtEUR(tx.computable_gain_eur)}</span>
            </div>
            <div class="text-[11px] text-slate-500 dark:text-slate-400">
              ${escHtml(tx.acquisition_date)} -> ${escHtml(tx.transmission_date)} · Cant: ${Number(tx.qty).toFixed(4)}
            </div>
            <div class="flex items-center justify-between text-[11px] text-slate-600 dark:text-slate-300">
              <span>Adq: ${fmtEUR(tx.acquisition_value_eur)} | Trans: ${fmtEUR(tx.transmission_value_eur)}</span>
              <span class="font-sans text-[10px]">${tx.blocked_2m ? 'Diferida 2M' : 'Computable'}</span>
            </div>
          </div>
        `;
      })
      .join('');
  }
}

function downloadAeatCsv() {
  const env = document.getElementById('aeat-env-select')?.value || 'PAPER';
  const year = document.getElementById('aeat-year-select')?.value || 'ALL';
  window.location.href = `/api/tax/export.csv?env=${encodeURIComponent(env)}&year=${encodeURIComponent(year)}`;
}

// ============================================================================
// SIMULACIÓN HISTÓRICA IRPF ESPAÑA 2007–2026 (6 MOTORES, SUBPESTAÑA 5)
// ============================================================================
function initTaxView(triggerAudit = true) {
  if (triggerAudit) {
    loadLiveTaxAudit();
  }
  if (!APP_DATA || !APP_DATA.tax_analysis) return;
  const tax = APP_DATA.tax_analysis;
  const m = tax.metrics;
  const th = getChartTheme();
  const isMobile = window.innerWidth < 640;

  const setTxt = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  // 1. Tarjetas KPI Históricas Actualizadas (6 Motores)
  setTxt('tax-drag-badge', `-${Number(m.total_friction_cagr_pct).toFixed(2)}% CAGR`);
  setTxt('tax-kpi-net-cap', `$${m.net_final_equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
  setTxt('tax-kpi-net-sub', `+${Math.round(m.net_total_return_pct).toLocaleString('en-US')}% (${Number(m.net_cagr_pct).toFixed(2)}% CAGR)`);
  setTxt('tax-kpi-gross-cap', `$${m.gross_final_equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
  setTxt('tax-kpi-gross-sub', `+${Math.round(m.gross_total_return_pct).toLocaleString('en-US')}% (${Number(m.gross_cagr_pct).toFixed(2)}% CAGR)`);
  setTxt('tax-kpi-total-tax', `$${m.total_tax_paid_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
  setTxt('tax-kpi-fees-sub', `Costes bróker/TER: ${fmtUSD(Math.round(m.total_operational_fees_usd))}`);
  setTxt('tax-kpi-ratio-spy', `${m.net_wealth_ratio_vs_spy_net}x Capital`);
  setTxt('tax-kpi-ratio-sub', `$${(m.net_final_equity / 1000).toFixed(1)}k vs $${(m.spy_net_final_equity / 1000).toFixed(1)}k SPY neto`);

  // 2. Curva Patrimonial Comparativa (Bruto vs Neto Operativo vs Neto IRPF vs S&P 500)
  const taxEl = document.getElementById('tax-equity-chart');
  if (taxEl) {
    if (taxChart) taxChart.dispose();
    taxChart = echarts.init(taxEl);
    const dates = tax.net_curve.map((p) => p.date);
    const grossData = tax.net_curve.map((p) => p.gross_eq);
    const opNetData = tax.net_curve.map((p) => p.op_net_eq);
    const netData = tax.net_curve.map((p) => p.net_eq);
    const spyData = tax.net_curve.map((p) => p.spy_eq);

    taxChart.setOption({
      backgroundColor: th.bg,
      animation: false,
      grid: {
        left: isMobile ? '48px' : '60px',
        right: isMobile ? '14px' : '30px',
        top: '36px',
        bottom: '54px',
      },
      tooltip: {
        trigger: 'axis',
        confine: true,
        backgroundColor: th.tooltipBg,
        borderColor: th.tooltipBorder,
        textStyle: { color: th.tooltipText, fontSize: 12 },
        formatter: (params) => {
          let html = `<div style="font-weight:700;font-size:11px;margin-bottom:4px;font-family:JetBrains Mono,monospace;color:${th.tooltipMuted}">${params[0].name}</div>`;
          params.forEach((item) => {
            const val = Number(item.value).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
            html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:12px;font-variant-numeric:tabular-nums">
              <span style="color:${item.color}">${item.seriesName}:</span>
              <span style="font-weight:700;font-family:JetBrains Mono,monospace;color:${th.tooltipText}">${val}</span>
            </div>`;
          });
          return html;
        },
      },
      legend: {
        type: 'scroll',
        data: ['Modo 3 Élite Bruto (Con Bitcoin)', 'Neto Operativo (Comisiones+TER)', 'Neto en Bolsillo (Tras IRPF)', 'S&P 500 Buy & Hold'],
        top: 0,
        textStyle: { color: th.text, fontSize: isMobile ? 10 : 11 },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', bottom: 8, height: 18, borderColor: th.zoomBorder },
      ],
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: th.axisLine } },
        axisLabel: { color: th.axisLabel, fontSize: isMobile ? 10 : 11 },
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLabel: {
          formatter: (v) => `$${(v / 1000).toFixed(0)}k`,
          color: th.axisLabel,
          fontSize: isMobile ? 10 : 11,
        },
        splitLine: { lineStyle: { color: th.splitLine } },
      },
      series: [
        {
          name: 'Modo 3 Élite Bruto (Con Bitcoin)',
          type: 'line',
          data: grossData,
          showSymbol: false,
          lineStyle: { width: 1.5, color: th.grossLine },
          itemStyle: { color: th.grossLine },
        },
        {
          name: 'Neto Operativo (Comisiones+TER)',
          type: 'line',
          data: opNetData,
          showSymbol: false,
          lineStyle: { width: 1.5, color: '#b45309', type: 'dotted' },
          itemStyle: { color: '#b45309' },
        },
        {
          name: 'Neto en Bolsillo (Tras IRPF)',
          type: 'line',
          data: netData,
          showSymbol: false,
          lineStyle: { width: 2.3, color: th.botLine },
          areaStyle: { color: th.botArea },
          itemStyle: { color: th.botLine },
        },
        {
          name: 'S&P 500 Buy & Hold',
          type: 'line',
          data: spyData,
          showSymbol: false,
          lineStyle: { width: 1.5, color: '#b91c1c', type: 'dashed' },
          itemStyle: { color: '#b91c1c' },
        },
      ],
    });
  }

  // 3. Tabla Anual de Liquidación IRPF (2007–2026)
  const tbody = document.getElementById('tax-yearly-tbody');
  if (tbody && tax.yearly_breakdown) {
    tbody.innerHTML = tax.yearly_breakdown
      .map((row) => {
        const netRetSign = row.net_ret_pct >= 0 ? '+' : '';
        const grossRetSign = row.gross_ret_pct >= 0 ? '+' : '';
        return `
          <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50">
            <td class="py-2 px-3 font-bold text-slate-800 dark:text-slate-100">${row.year}</td>
            <td class="py-2 px-3 text-right text-slate-600 dark:text-slate-300">$${row.start_capital.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td class="py-2 px-3 text-right ${row.gross_ret_pct >= 0 ? 'text-brand-700 dark:text-brand-300' : 'text-red-700 dark:text-red-400'}">${grossRetSign}${row.gross_ret_pct.toFixed(2)}%</td>
            <td class="py-2 px-3 text-right text-amber-700 dark:text-amber-400 font-mono">-$${row.operational_fees.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td class="py-2 px-3 text-right ${row.realized_gain_usd >= 0 ? 'text-brand-700 dark:text-brand-300' : 'text-red-700 dark:text-red-400'}">$${row.realized_gain_usd.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td class="py-2 px-3 text-right text-slate-500 dark:text-slate-400">${row.loss_offset_used > 0 ? `-$${row.loss_offset_used.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '--'}</td>
            <td class="py-2 px-3 text-right text-slate-700 dark:text-slate-200 font-semibold">$${row.taxable_base.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td class="py-2 px-3 text-right font-bold text-amber-700 dark:text-amber-400">$${row.tax_paid.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td class="py-2 px-3 text-right text-slate-500 dark:text-slate-400">${row.tax_paid > 0 ? `${row.effective_rate_pct.toFixed(1)}%` : '0.0%'}</td>
            <td class="py-2 px-3 text-right ${row.loss_carried_forward > 0 ? 'text-red-700 dark:text-red-400 font-semibold' : 'text-slate-400 dark:text-slate-500'}">${row.loss_carried_forward > 0 ? `$${row.loss_carried_forward.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '--'}</td>
            <td class="py-2 px-3 text-right font-bold text-slate-900 dark:text-slate-100">$${row.net_end_equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td class="py-2 px-3 text-right font-bold ${row.net_ret_pct >= 0 ? 'text-brand-700 dark:text-brand-300' : 'text-red-700 dark:text-red-400'}">${netRetSign}${row.net_ret_pct.toFixed(2)}%</td>
          </tr>
        `;
      })
      .join('');
  }
}
