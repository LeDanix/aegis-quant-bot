/**
 * Aegis-Quant | Frontend Controller (app.js)
 * Mobile-First Institutional Quant Web App + Desktop Analytics Studio.
 * Unified on Mode 3 Élite vs S&P 500 (2007–2026) with Dark Mode & Smart Polling.
 */

let APP_DATA = null;
let SUMMARY_LOADING = false;
let SUMMARY_ERROR = null;
let LAST_LIVE_STATUS = null;

const ACTIVE_MODE_ID = 'MODO_3_ELITE';
let ACTIVE_MOTOR_FILTER = 'TOP_IMPACT'; // 'NONE', 'TOP_IMPACT', 'M1_PULLBACK', 'M2_VIX_DIV', 'M3_BEAR_SHORT', 'M4_CTA_TREND', 'M5_VOL_CRUSH'
let ACTIVE_PERF_SUBTAB = 'chart'; // 'chart' | 'guide' | 'crisis' | 'simulator' | 'tax'
let ACTIVE_MOBILE_TAB = 'inicio'; // 'inicio' | 'cartera' | 'analisis' | 'sistema'
let LAST_CONTROL_MOBILE_TAB = 'inicio';
let CHART_SCALE = 'value'; // 'value' | 'log'
let LIVE_CONFIG_INITIALIZED = false;

// Polling & Safety State
let livePollTimer = null;
let liveFetchInFlight = false;
let pendingDestructiveAction = null;

// Apache ECharts Instances
let mainChart = null;
let ddChart = null;
let subperiodsChart = null;
let monteCarloChart = null;
let frictionChart = null;
let taxChart = null;

// Engine Metadata & Explanations
const MOTOR_META = {
  M1_PULLBACK: {
    id: 'M1_PULLBACK',
    shortName: 'Engine 1: Oversold Pullback (M1)',
    badge: 'M1 Pullback',
    color: '#059669',
    pillCls: 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-800',
    symbolShape: 'circle',
    plainExplanation: 'Market was in a primary bull trend (above 200-day moving average) but suffered an abrupt 3-day drop (RSI(2) < 10). The engine bought cheap shares expecting a sharp 3 to 5 day mean reversion.',
  },
  M2_VIX_DIV: {
    id: 'M2_VIX_DIV',
    shortName: 'Engine 2: Volatility Divergence (M2)',
    badge: 'M2 VIX Div',
    color: '#0284c7',
    pillCls: 'bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-900/40 dark:text-sky-300 dark:border-sky-800',
    symbolShape: 'diamond',
    plainExplanation: 'The CBOE VIX fear index spiked on institutional panic over the last 5 days but began deflating while index prices remained depressed. Clear sign of selling exhaustion.',
  },
  M3_BEAR_SHORT: {
    id: 'M3_BEAR_SHORT',
    shortName: 'Engine 3: Bear Market Short (M3)',
    badge: 'M3 Crisis Short',
    color: '#e11d48',
    pillCls: 'bg-rose-100 text-rose-800 border-rose-200 dark:bg-rose-900/40 dark:text-rose-300 dark:border-rose-800',
    symbolShape: 'triangle',
    plainExplanation: 'The market was in a confirmed secular bear regime (below 200-day moving average with high volatility). Following a weak 2-day bear rally, the engine shorted the index to profit from the downtrend.',
  },
  M4_CTA_TREND: {
    id: 'M4_CTA_TREND',
    shortName: 'Engine 4: Multi-Asset CTA Trends (M4)',
    badge: 'M4 CTA Trend',
    color: '#d97706',
    pillCls: 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-800',
    symbolShape: 'rect',
    plainExplanation: 'Breakout above 20-day Donchian channels in uncorrelated crisis hedges (Gold GLD, Crude Oil USO, Soybeans SOYB, or Long Treasuries TLT). Captures persistent commodity and safe-haven flows.',
  },
  M5_VOL_CRUSH: {
    id: 'M5_VOL_CRUSH',
    shortName: 'Engine 5: Post-Panic Vol-Crush (M5)',
    badge: 'M5 Vol-Crush',
    color: '#7c3aed',
    pillCls: 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/40 dark:text-purple-300 dark:border-purple-800',
    symbolShape: 'pin',
    plainExplanation: 'The volatility term structure backwardation (VIX over VIX3M) collapsed by more than 5% in a single session. Signals the exact pivot where major institutions re-enter risk assets.',
  },
  CORE_BULL: {
    id: 'CORE_BULL',
    shortName: 'Intelligent Core Indexing (SPY/QQQ)',
    badge: 'Core Modo 3',
    color: '#065f46',
    pillCls: 'bg-brand-100 text-brand-800 border-brand-200 dark:bg-brand-900/40 dark:text-brand-300 dark:border-brand-800',
    symbolShape: 'circle',
    plainExplanation: 'Passive core allocation during healthy Contango regimes (VIX < VIX3M). Capital compounds without turnover drag.',
  },
};

const ASSET_NAMES = {
  SPY: 'S&P 500 ETF',
  QQQ: 'Nasdaq 100 ETF',
  GLD: 'Physical Gold ETF',
  TLT: '20+ Yr Treasury ETF',
  USO: 'WTI Crude Oil ETF',
  SOYB: 'Soybeans ETF',
  ZS: 'Soybeans (ZS/SOYB)',
};

// Numeric & Escape Helpers
function fmtUSD(val) {
  const n = Number(val || 0);
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
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
  return MOTOR_META.CORE_BULL;
}

// ============================================================================
// THEME MANAGEMENT (DARK MODE DEFAULT AT NIGHT + ECHARTS SYNC)
// ============================================================================
function isDarkMode() {
  return document.documentElement.classList.contains('dark');
}

function getChartTheme() {
  const dark = isDarkMode();
  return {
    dark,
    bg: 'transparent',
    text: dark ? '#cbd5e1' : '#475569',
    axisLabel: dark ? '#94a3b8' : '#64748b',
    axisLine: dark ? '#334155' : '#e2e8f0',
    splitLine: dark ? '#1e293b' : '#f1f5f9',
    tooltipBg: dark ? 'rgba(15, 23, 42, 0.96)' : 'rgba(255, 255, 255, 0.98)',
    tooltipBorder: dark ? '#334155' : '#e2e8f0',
    tooltipText: dark ? '#f8fafc' : '#0f172a',
    tooltipMuted: dark ? '#94a3b8' : '#64748b',
    crosshair: dark ? '#475569' : '#cbd5e1',
    zoomBorder: dark ? '#334155' : '#e2e8f0',
    spyLine: dark ? '#94a3b8' : '#64748b',
    ddSpyLine: dark ? '#64748b' : '#cbd5e1',
    ddSpyArea: dark ? 'rgba(100, 116, 139, 0.16)' : 'rgba(203, 213, 225, 0.30)',
    grossLine: dark ? '#60a5fa' : '#1e40af',
    scatterBorder: dark ? '#0f172a' : '#ffffff',
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
    metaTheme.setAttribute('content', dark ? '#0b1120' : '#ffffff');
  }

  if (persist) {
    try {
      localStorage.setItem('aegis_theme', dark ? 'dark' : 'light');
    } catch (e) {}
  }

  // Refresh dynamic button styling & initialized charts
  if (APP_DATA) {
    initMotorFilterButtons();
    if (mainChart && ddChart) updateMainCharts();
    if (subperiodsChart || monteCarloChart || frictionChart) initCrisisAndRobustnessCharts();
    if (taxChart) initTaxView();
  }
}

function toggleTheme() {
  applyTheme(!isDarkMode(), true);
}

// ============================================================================
// APPLICATION LIFECYCLE: INSTANT LIVE PAINT + DEFERRED SUMMARY + SMART POLLING
// ============================================================================
window.addEventListener('DOMContentLoaded', () => {
  // Listen for OS theme changes if user hasn't locked a manual preference
  try {
    const mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
    if (mq && mq.addEventListener) {
      mq.addEventListener('change', (e) => {
        if (!localStorage.getItem('aegis_theme')) {
          applyTheme(e.matches, false);
        }
      });
    }
  } catch (e) {}

  // Global keyboard Escape handler for modals
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeDestructiveConfirmModal();
      closeConfigModal();
    }
  });

  window.addEventListener('resize', handleWindowResize);
  window.addEventListener('orientationchange', () => {
    setTimeout(handleWindowResize, 120);
  });

  // Smart visibility-aware polling (saves battery & Tailscale traffic when phone screen is off)
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopLivePolling();
    } else {
      fetchLiveStatus(false);
      startLivePolling();
      setTimeout(handleWindowResize, 80);
    }
  });

  // 1. Immediate <150ms paint of Live Bot Status & Equity on Mobile
  fetchLiveStatus(true);
  startLivePolling();

  // 2. Load ~4 MB historical backtest summary asynchronously after first paint
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

    initMotorFilterButtons();
    renderMotorBreakdownCards();
    renderDefaultTradeStory();
    renderYearlyTable();
    updateCustomSimulator();
    renderTradesTable();
    renderLiveScan();

    // If user already navigated to Performance Analytics while loading, render charts immediately
    const viewPerf = document.getElementById('main-view-performance');
    if (viewPerf && !viewPerf.classList.contains('hidden')) {
      setTimeout(refreshActivePerfSubTabCharts, 40);
    }
  } catch (err) {
    SUMMARY_ERROR = err;
    console.error('Error loading /api/summary:', err);
    if (msgEl) msgEl.textContent = 'No se pudo cargar el histórico 2007–2026 en segundo plano.';
    if (retryBtn) retryBtn.classList.remove('hidden');
    if (isManualRetry && banner) banner.classList.remove('hidden');
  } finally {
    SUMMARY_LOADING = false;
  }
}

function handleWindowResize() {
  if (mainChart) mainChart.resize();
  if (ddChart) ddChart.resize();
  if (subperiodsChart) subperiodsChart.resize();
  if (monteCarloChart) monteCarloChart.resize();
  if (frictionChart) frictionChart.resize();
  if (taxChart) taxChart.resize();
}

// ============================================================================
// NAVIGATION: MOBILE BOTTOM BAR + DESKTOP TOP TABS + 5 ANALYTICS SUB-TABS
// ============================================================================
function updateMobileNavHighlight(tabId) {
  ACTIVE_MOBILE_TAB = tabId;
  const tabs = ['inicio', 'cartera', 'analisis', 'sistema'];
  tabs.forEach((id) => {
    const btn = document.getElementById(`mobile-tab-${id}`);
    if (!btn) return;
    if (id === tabId) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

function switchMobileTab(tabId) {
  if (tabId === 'analisis') {
    updateMobileNavHighlight('analisis');
    switchMainView('performance', true);
  } else {
    LAST_CONTROL_MOBILE_TAB = tabId;
    const viewControl = document.getElementById('main-view-control');
    if (viewControl) viewControl.setAttribute('data-mobile-tab', tabId);
    updateMobileNavHighlight(tabId);
    switchMainView('control', true);
  }
  window.scrollTo({ top: 0, behavior: 'auto' });
}

function switchMainView(viewId, fromMobile = false) {
  const tabControl = document.getElementById('main-tab-control');
  const tabPerf = document.getElementById('main-tab-performance');
  const viewControl = document.getElementById('main-view-control');
  const viewPerf = document.getElementById('main-view-performance');

  if (viewId === 'control') {
    if (tabControl) tabControl.classList.add('active');
    if (tabPerf) tabPerf.classList.remove('active');
    if (viewControl) viewControl.classList.remove('hidden');
    if (viewPerf) viewPerf.classList.add('hidden');

    if (!fromMobile) {
      const targetMob = LAST_CONTROL_MOBILE_TAB || 'inicio';
      if (viewControl) viewControl.setAttribute('data-mobile-tab', targetMob);
      updateMobileNavHighlight(targetMob);
    }
    fetchLiveStatus(false);
  } else {
    if (tabPerf) tabPerf.classList.add('active');
    if (tabControl) tabControl.classList.remove('active');
    if (viewPerf) viewPerf.classList.remove('hidden');
    if (viewControl) viewControl.classList.add('hidden');

    if (!fromMobile) {
      updateMobileNavHighlight('analisis');
    }

    if (!APP_DATA && !SUMMARY_LOADING) {
      loadSummaryDataInBackground(true);
    }

    setTimeout(refreshActivePerfSubTabCharts, 50);
  }
}

function refreshActivePerfSubTabCharts() {
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
    initTaxView();
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
// MODALS: CONFIGURATION & TWO-STEP DESTRUCTIVE CONFIRMATION
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
    if (titleEl) titleEl.textContent = 'Panic: Cerrar Todas las Posiciones';
    if (descEl) {
      descEl.textContent = 'Se enviarán órdenes inmediatas a mercado para liquidar el 100% de las posiciones abiertas y pasar toda la cartera a liquidez (Cash).';
    }
    if (ctxEl) {
      ctxEl.textContent = `Posiciones activas: ${posCount} (${posVal}) · Equity actual: ${eq}`;
    }
    if (confirmBtn) confirmBtn.textContent = 'Liquidar Cartera';
  } else {
    if (titleEl) titleEl.textContent = 'Reiniciar Cuenta (Reset Balance)';
    if (descEl) {
      descEl.textContent = 'Se restablecerá el saldo inicial de Paper Trading, vaciando las posiciones simuladas y el registro de órdenes.';
    }
    if (ctxEl) {
      const baseCap = fmtUSD(LAST_LIVE_STATUS?.config?.allocated_capital_usd || 10000);
      ctxEl.textContent = `Equity actual: ${eq} → Nuevo saldo base: ${baseCap}`;
    }
    if (confirmBtn) confirmBtn.textContent = 'Reiniciar Cuenta';
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
// ENGINE FILTERS ON CHART
// ============================================================================
function initMotorFilterButtons() {
  const container = document.getElementById('motor-filter-buttons');
  if (!container || !APP_DATA) return;

  const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
  const breakdown = modeData.engine_breakdown || {};

  const filters = [
    { id: 'TOP_IMPACT', label: 'Top 35 Key Trades' },
    { id: 'NONE', label: 'Hide Markers' },
    { id: 'M1_PULLBACK', label: `M1 Pullback (${breakdown.M1_PULLBACK?.trades || 0})` },
    { id: 'M2_VIX_DIV', label: `M2 VIX Div (${breakdown.M2_VIX_DIV?.trades || 0})` },
    { id: 'M3_BEAR_SHORT', label: `M3 Crisis Short (${breakdown.M3_BEAR_SHORT?.trades || 0})` },
    { id: 'M4_CTA_TREND', label: `M4 CTA Trend (${breakdown.M4_CTA_TREND?.trades || 0})` },
  ];

  if (breakdown.M5_VOL_CRUSH) {
    filters.push({
      id: 'M5_VOL_CRUSH',
      label: `M5 Vol-Crush (${breakdown.M5_VOL_CRUSH.trades})`,
    });
  }

  container.innerHTML = filters
    .map((f) => {
      const active = f.id === ACTIVE_MOTOR_FILTER;
      const cls = active
        ? 'bg-emerald-700 text-white border-emerald-700 shadow-xs'
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

function jumpToMotorOnChart(motorId) {
  switchMainView('performance');
  switchPerfSubTab('chart');
  setMotorFilter(motorId);
}

// ============================================================================
// APACHE ECHARTS 5 EQUITY & DRAWDOWN CHARTS (RESPONSIVE + DARK THEME AWARE)
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
  const activeCls = 'px-2.5 py-1.5 sm:py-1 rounded-md text-xs font-semibold bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm';
  const idleCls = 'px-2.5 py-1.5 sm:py-1 rounded-md text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white';

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
      el.className = 'shrink-0 px-2.5 py-1.5 sm:py-1 rounded text-xs font-semibold bg-emerald-700 text-white shadow-xs';
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
        color: isWin ? mMeta.color : '#e11d48',
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

  const scatterData = getFilteredScatterTrades(modeData, dates, th.scatterBorder);

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
      data: ['Mode 3 Élite (5 Engines + VTS)', 'S&P 500 (Buy & Hold)'],
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
        lineStyle: { color: th.spyLine, width: 1.8, type: 'dashed' },
        itemStyle: { color: th.spyLine },
      },
      {
        name: 'Mode 3 Élite (5 Engines + VTS)',
        type: 'line',
        data: modeValues,
        smooth: false,
        showSymbol: false,
        lineStyle: { color: '#10b981', width: 2.3 },
        itemStyle: { color: '#10b981' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: th.dark ? 'rgba(16, 185, 129, 0.22)' : 'rgba(5, 150, 105, 0.12)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0.00)' },
          ]),
        },
      },
      {
        name: 'Trade Executions',
        type: 'scatter',
        data: scatterData,
        z: 10,
        tooltip: {
          confine: true,
          formatter: function (p) {
            const t = p.data.tradeObj;
            const gainCol = t.portfolio_ret_pct >= 0 ? '#10b981' : '#f43f5e';
            return `
              <div style="font-size:12px">
                <div style="font-weight:700;color:${th.tooltipText}">${t.engine_id} · ${t.direction} ${t.symbol}</div>
                <div style="color:${th.tooltipMuted};font-size:11px">${t.entry_date} → ${t.exit_date} (${t.days}d)</div>
                <div style="margin-top:4px;font-family:JetBrains Mono,monospace;font-weight:700;color:${gainCol}">
                  Portfolio Gain: ${fmtPct(t.portfolio_ret_pct)} ($${t.eq_at_exit.toFixed(2)})
                </div>
              </div>
            `;
          },
        },
      },
    ],
  };

  mainChart.setOption(mainOption, true);

  // Drawdown Sub-Chart
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
        name: 'S&P 500 Drawdown',
        type: 'line',
        data: spDdValues,
        showSymbol: false,
        lineStyle: { color: th.ddSpyLine, width: 1.2 },
        areaStyle: { color: th.ddSpyArea },
      },
      {
        name: 'Mode 3 Élite Drawdown',
        type: 'line',
        data: ddValues,
        showSymbol: false,
        lineStyle: { color: '#10b981', width: 1.5 },
        areaStyle: { color: th.dark ? 'rgba(16, 185, 129, 0.20)' : 'rgba(5, 150, 105, 0.15)' },
      },
    ],
  };

  ddChart.setOption(ddOption, true);
}

// ============================================================================
// TRADE STORY DETAIL CARD
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

  const meta = MOTOR_META[t.engine_id] || MOTOR_META.M1_PULLBACK;
  const isWin = t.portfolio_ret_pct >= 0;
  const retColor = isWin ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400';
  const badgeBg = isWin
    ? 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-800'
    : 'bg-red-50 text-red-800 border-red-200 dark:bg-red-900/40 dark:text-red-300 dark:border-red-800';

  container.innerHTML = `
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <span class="px-2.5 py-0.5 rounded text-xs font-semibold border ${badgeBg}">${meta.badge}</span>
        <span class="text-xs font-mono tabular-nums text-slate-500 dark:text-slate-400">${t.direction} · ${t.symbol}</span>
      </div>

      <div class="border-t border-b border-slate-100 dark:border-slate-800 py-2.5 space-y-1.5 font-mono tabular-nums text-xs">
        <div class="flex justify-between gap-2">
          <span class="text-slate-500 dark:text-slate-400 font-sans">Holding Period:</span>
          <span class="font-medium text-slate-800 dark:text-slate-200 text-right">${t.entry_date} → ${t.exit_date} (${t.days}d)</span>
        </div>
        <div class="flex justify-between gap-2">
          <span class="text-slate-500 dark:text-slate-400 font-sans">Portfolio Return:</span>
          <span class="font-bold ${retColor}">${fmtPct(t.portfolio_ret_pct)}</span>
        </div>
        <div class="flex justify-between gap-2">
          <span class="text-slate-500 dark:text-slate-400 font-sans">Asset Price Move:</span>
          <span class="font-medium text-slate-800 dark:text-slate-200 text-right">${fmtPct(t.raw_ret_pct)} ($${t.entry_price} → $${t.exit_price})</span>
        </div>
        <div class="flex justify-between gap-2">
          <span class="text-slate-500 dark:text-slate-400 font-sans">Exit Rule:</span>
          <span class="font-medium text-slate-800 dark:text-slate-200 text-[11px] text-right">${escHtml(t.exit_reason || 'Target Profit Exit')}</span>
        </div>
      </div>

      <div>
        <h4 class="font-semibold text-slate-900 dark:text-slate-100 uppercase tracking-wider text-[11px]">Quantitative Edge:</h4>
        <p class="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">${meta.plainExplanation}</p>
      </div>
    </div>
  `;
}

// ============================================================================
// ENGINE BREAKDOWN CARDS
// ============================================================================
function renderMotorBreakdownCards() {
  const container = document.getElementById('motor-breakdown-cards');
  if (!container || !APP_DATA) return;

  const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
  const breakdown = modeData.engine_breakdown || {};
  const order = ['M1_PULLBACK', 'M2_VIX_DIV', 'M3_BEAR_SHORT', 'M4_CTA_TREND', 'M5_VOL_CRUSH'];

  container.innerHTML = order
    .map((mKey) => {
      const b = breakdown[mKey];
      const meta = MOTOR_META[mKey];
      if (!b) return '';

      const winColor = b.win_rate >= 60 ? 'text-emerald-700 dark:text-emerald-400' : 'text-slate-700 dark:text-slate-200';

      return `
        <div class="p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 hover:border-brand-500 transition cursor-pointer" onclick="jumpToMotorOnChart('${mKey}')">
          <div class="flex items-center justify-between gap-2">
            <span class="text-xs font-semibold text-slate-900 dark:text-slate-100">${meta.shortName}</span>
            <span class="text-[11px] font-mono tabular-nums font-bold text-brand-800 dark:text-brand-300 bg-brand-50 dark:bg-brand-900/40 px-2 py-0.5 rounded border border-brand-100 dark:border-brand-800 shrink-0">${b.trades} trades</span>
          </div>
          <div class="grid grid-cols-3 gap-2 mt-2 font-mono tabular-nums text-xs text-slate-600 dark:text-slate-300">
            <div>
              <span class="text-[10px] text-slate-400 block font-sans">Win Rate</span>
              <span class="font-bold ${winColor}">${b.win_rate}%</span>
            </div>
            <div>
              <span class="text-[10px] text-slate-400 block font-sans">Net P&amp;L</span>
              <span class="font-bold text-slate-900 dark:text-white">${fmtUSD(b.total_pnl_usd)}</span>
            </div>
            <div>
              <span class="text-[10px] text-slate-400 block font-sans">Profit Factor</span>
              <span class="font-bold text-slate-900 dark:text-white">${b.profit_factor}</span>
            </div>
          </div>
        </div>
      `;
    })
    .join('');
}

// ============================================================================
// CRISIS & ROBUSTNESS ANALYTICS (SUB-TAB 3)
// ============================================================================
function initCrisisAndRobustnessCharts() {
  if (!APP_DATA) return;
  const th = getChartTheme();

  // 1. Subperiods Chart
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
      grid: { left: '46px', right: '14px', top: '34px', bottom: '28px' },
      tooltip: {
        trigger: 'axis',
        confine: true,
        backgroundColor: th.tooltipBg,
        borderColor: th.tooltipBorder,
        textStyle: { color: th.tooltipText, fontSize: 12 },
        formatter: (p) => `${p[0].name}<br/>${p[0].seriesName}: +${p[0].value}%<br/>${p[1].seriesName}: ${p[1].value}%`,
      },
      legend: { data: ['Mode 3 Élite', 'S&P 500'], top: 0, textStyle: { color: th.text, fontSize: 11 } },
      xAxis: { type: 'category', data: periods, axisLine: { lineStyle: { color: th.axisLine } }, axisLabel: { color: th.axisLabel, fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}%', color: th.axisLabel, fontSize: 10 }, splitLine: { lineStyle: { color: th.splitLine } } },
      series: [
        { name: 'Mode 3 Élite', type: 'bar', data: m3Vals, itemStyle: { color: '#10b981', borderRadius: [4, 4, 0, 0] } },
        { name: 'S&P 500', type: 'bar', data: spVals, itemStyle: { color: th.spyLine, borderRadius: [4, 4, 0, 0] } },
      ],
    }, true);
  }

  // 2. Monte Carlo Simulation Chart
  const mcEl = document.getElementById('montecarlo-chart');
  if (mcEl) {
    if (monteCarloChart) monteCarloChart.dispose();
    monteCarloChart = echarts.init(mcEl);
    const mc = APP_DATA.robustness?.monte_carlo || {};
    const p5 = mc.p5_pessimistic?.final_equity || 57979;
    const p25 = mc.p25_conservative?.final_equity || 92332;
    const p50 = mc.p50_median?.final_equity || 126900;
    const p75 = mc.p75_optimistic?.final_equity || 173767;
    const p95 = mc.p95_extreme?.final_equity || 263010;

    monteCarloChart.setOption({
      backgroundColor: th.bg,
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
          name: 'Ending Capital',
          type: 'bar',
          data: [p5, p25, p50, p75, p95],
          itemStyle: {
            color: function (params) {
              const colors = ['#f59e0b', '#34d399', '#10b981', '#059669', '#047857'];
              return colors[params.dataIndex];
            },
            borderRadius: [4, 4, 0, 0],
          },
        },
      ],
    }, true);
  }

  // 3. Friction & Slippage Chart
  const frEl = document.getElementById('friction-chart');
  if (frEl) {
    if (frictionChart) frictionChart.dispose();
    frictionChart = echarts.init(frEl);
    const fr = APP_DATA.robustness?.friction_test || [
      { scenario: '0 bps', cagr_pct: 18.35 },
      { scenario: '5 bps', cagr_pct: 17.25 },
      { scenario: '10 bps', cagr_pct: 16.16 },
      { scenario: '20 bps', cagr_pct: 14.01 },
      { scenario: '35 bps', cagr_pct: 10.86 },
    ];

    frictionChart.setOption({
      backgroundColor: th.bg,
      grid: { left: '44px', right: '14px', top: '24px', bottom: '28px' },
      tooltip: {
        trigger: 'axis',
        confine: true,
        backgroundColor: th.tooltipBg,
        borderColor: th.tooltipBorder,
        textStyle: { color: th.tooltipText, fontSize: 12 },
        formatter: (p) => `${p[0].name}<br/>Net CAGR: ${p[0].value}%`,
      },
      xAxis: { type: 'category', data: fr.map((f) => f.scenario.split(' (')[0]), axisLine: { lineStyle: { color: th.axisLine } }, axisLabel: { color: th.axisLabel, fontSize: 10 } },
      yAxis: { type: 'value', min: 8, axisLabel: { formatter: '{value}%', color: th.axisLabel, fontSize: 10 }, splitLine: { lineStyle: { color: th.splitLine } } },
      series: [
        {
          name: 'Net CAGR',
          type: 'line',
          data: fr.map((f) => f.cagr_pct),
          itemStyle: { color: '#10b981' },
          lineStyle: { width: 2.5, color: '#10b981' },
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

      const mColor = mVal >= 0 ? 'text-emerald-700 dark:text-emerald-400 font-semibold' : 'text-red-700 dark:text-red-400 font-semibold';
      const spColor = spVal >= 0 ? 'text-slate-800 dark:text-slate-200' : 'text-red-700 dark:text-red-400';
      const alphaColor = alpha >= 0 ? 'text-emerald-700 dark:text-emerald-400 font-bold' : 'text-red-700 dark:text-red-400 font-bold';

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
// PORTFOLIO SIMULATOR & 725 TRADES TABLE (SUB-TAB 4)
// ============================================================================
function updateCustomSimulator() {
  if (!APP_DATA) return;

  const capSlider = document.getElementById('sim-cap-slider');
  const feeSlider = document.getElementById('sim-fee-slider');
  if (!capSlider || !feeSlider) return;

  const cap = Number(capSlider.value);
  const fee = Number(feeSlider.value);

  document.getElementById('sim-cap-label').textContent = fmtUSD(cap);
  document.getElementById('sim-fee-label').textContent = fee.toFixed(2) + '%';

  const years = 19.8;
  const spCagr = APP_DATA.benchmark.cagr_pct / 100;
  const spFinal = cap * Math.pow(1 + spCagr, years);

  const baseCagr = APP_DATA.modes[ACTIVE_MODE_ID].cagr_pct;
  const netCagr = Math.max(0.01, (baseCagr - (fee * 100 * 0.22)) / 100);
  const m3Final = cap * Math.pow(1 + netCagr, years);

  document.getElementById('sim-res-spy').textContent = fmtUSD(spFinal);
  document.getElementById('sim-res-m3elite').textContent = fmtUSD(m3Final);
  document.getElementById('sim-res-cagr').textContent = `Estimated Net CAGR: ${(netCagr * 100).toFixed(2)}% / year`;
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
    countLabel.textContent = `Displaying ${Math.min(trades.length, 50)} of ${trades.length} recorded trade executions`;
  }

  if (trades.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-slate-400 font-sans">No trades found matching selected filters.</td></tr>`;
    return;
  }

  tbody.innerHTML = trades
    .slice(0, 50)
    .map((t) => {
      const isWin = t.portfolio_ret_pct >= 0;
      const retColor = isWin ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400';
      const dirCls = t.direction === 'LONG'
        ? 'text-emerald-800 bg-emerald-50 dark:bg-emerald-900/40 dark:text-emerald-300'
        : 'text-red-800 bg-red-50 dark:bg-red-900/40 dark:text-red-300';

      return `
        <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition whitespace-nowrap">
          <td class="py-2 px-3 text-slate-500 dark:text-slate-400 text-[11px]">${t.exit_date}</td>
          <td class="py-2 px-3 font-semibold text-slate-800 dark:text-slate-200">${t.engine_id}</td>
          <td class="py-2 px-3 font-bold text-slate-900 dark:text-white">${t.symbol}</td>
          <td class="py-2 px-3"><span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${dirCls}">${t.direction}</span></td>
          <td class="py-2 px-3 text-right ${retColor} font-bold">${fmtPct(t.portfolio_ret_pct)}</td>
          <td class="py-2 px-3 text-right text-slate-700 dark:text-slate-200 font-bold">$${t.eq_at_exit.toFixed(2)}</td>
          <td class="py-2 px-3 text-slate-500 dark:text-slate-400 text-[11px] text-right">${t.days}d</td>
        </tr>
      `;
    })
    .join('');
}

// ============================================================================
// DAILY MARKET PULSE & VTS REGIME RADAR (LIVE + HISTORICAL FALLBACK)
// ============================================================================
function styleVtsPill(el, vtsState, vtsRatio) {
  if (!el) return;
  const raw = String(vtsState || '').toUpperCase();
  const isBackwardation = raw.includes('BACKWARD') || raw.includes('CRISIS') || raw.includes('PANIC') || (Number(vtsRatio) >= 1.0 && vtsRatio != null);
  if (isBackwardation) {
    el.className = 'inline-block mt-0.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-rose-100 dark:bg-rose-950/70 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800';
  } else {
    el.className = 'inline-block mt-0.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-brand-50 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800';
  }
}

function renderLiveScan() {
  const dateEl = document.getElementById('live-date-label');
  const badgeEl = document.getElementById('live-regime-badge');
  const detailEl = document.getElementById('live-vts-detail');
  const gridEl = document.getElementById('live-assets-grid');

  const tac = LAST_LIVE_STATUS?.tactical;
  const live = APP_DATA?.live_scan;

  // Prefer freshest live tactical header telemetry when available
  const asOf = tac?.data_as_of || live?.as_of_date || '--';
  const vtsState = tac?.vts_state || live?.vts_state || 'CONTANGO';
  const vtsRatio = tac?.vts_ratio ?? live?.vts_ratio;

  if (dateEl) dateEl.textContent = asOf;
  if (badgeEl) {
    badgeEl.textContent = vtsState.split(' (')[0];
    styleVtsPill(badgeEl, vtsState, vtsRatio);
  }
  if (detailEl) {
    if (live && live.vix_close !== undefined) {
      const ratioTxt = vtsRatio !== undefined ? Number(vtsRatio).toFixed(3) : live.vts_ratio;
      detailEl.textContent = `VIX ${live.vix_close} · VIX3M ${live.vix3m_close} · VTS ${ratioTxt}`;
    } else if (vtsRatio !== undefined) {
      detailEl.textContent = `VTS Ratio: ${Number(vtsRatio).toFixed(3)}`;
    }
  }

  // Build live price map from open positions so Market Pulse reflects latest tick
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
          const price = livePriceMap[a.symbol] ?? a.last_close;
          const isBull = a.sma200_trend === 'BULL';
          const trendCls = isBull
            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
            : 'bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400';

          return `
            <div class="py-2.5 flex items-center justify-between gap-2">
              <div class="min-w-0">
                <div class="flex items-center gap-1.5">
                  <span class="font-bold font-mono text-slate-900 dark:text-white">${escHtml(a.symbol)}</span>
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${trendCls}">${escHtml(a.sma200_trend)}</span>
                </div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate">${escHtml(ASSET_NAMES[a.symbol] || '')}</div>
              </div>
              <div class="flex items-center gap-2.5 text-[11px] font-mono tabular-nums shrink-0">
                <span class="font-semibold text-slate-800 dark:text-slate-200">$${Number(price).toFixed(2)}</span>
                <span class="font-bold min-w-[62px] text-right ${isCore ? 'text-brand-800 dark:text-brand-300 bg-brand-50 dark:bg-brand-900/40 px-2 py-0.5 rounded' : 'text-slate-400 dark:text-slate-500'}">
                  ${isCore ? coreWeight + '% Core' : '0%'}
                </span>
              </div>
            </div>
          `;
        })
        .join('');
    } else if ((LAST_LIVE_STATUS?.state?.positions || []).length > 0) {
      // Instant live fallback while /api/summary is still downloading over Tailscale
      gridEl.innerHTML = LAST_LIVE_STATUS.state.positions
        .map((p) => `
          <div class="py-2.5 flex items-center justify-between gap-2 font-mono tabular-nums">
            <div>
              <span class="font-bold text-slate-900 dark:text-white">${escHtml(p.broker_symbol)}</span>
              <span class="text-[11px] text-slate-500 dark:text-slate-400 font-sans ml-1.5">${escHtml(ASSET_NAMES[p.internal_symbol] || p.motor || '')}</span>
            </div>
            <div class="flex items-center gap-2 text-[11px]">
              <span class="font-semibold text-slate-800 dark:text-slate-200">$${Number(p.current_price).toFixed(2)}</span>
              <span class="px-2 py-0.5 rounded bg-brand-50 dark:bg-brand-900/40 text-brand-800 dark:text-brand-300 font-bold">${p.weight_pct}%</span>
            </div>
          </div>
        `)
        .join('');
    }
  }
}

// ============================================================================
// NY / MADRID SCHEDULE & DST TRANSITION DETECTOR
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
    if (data.schedule_time_ny && data.schedule_time_madrid) {
      schedLabel.textContent = `${data.schedule_time_ny} (${data.schedule_time_madrid})`;
    } else if (data.next_run_display) {
      schedLabel.textContent = data.next_run_display;
    } else {
      schedLabel.textContent = `15:55 ${nyName} · ${(cfg.schedule_time_cet || (diffHours === 5 ? '20:55' : '21:55'))} ${madName}`;
    }
  }

  if (dstBadge) {
    const customLabel = data.dst_badge || data.dst_status || null;
    if (isDstShift) {
      dstBadge.textContent = customLabel || `⚡ DST Desfase EU/US (${diffHours}h · ${nyName}/${madName})`;
      dstBadge.className = 'px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700';
    } else {
      dstBadge.textContent = customLabel || `${nyName} · ${madName} (+${diffHours}h)`;
      dstBadge.className = 'px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800';
    }
  }
}

// ============================================================================
// LIVE TACTICAL ENGINES M1–M5 RENDERER (status.tactical)
// ============================================================================
function renderTacticalEnginesCard(data, cfg) {
  const asofBadge = document.getElementById('tactical-asof-badge');
  const regimePill = document.getElementById('tactical-regime-pill');
  const corePills = document.getElementById('tactical-core-pills');
  const bodyEl = document.getElementById('tactical-live-body');
  if (!bodyEl) return;

  const tac = data?.tactical || null;
  const enabledMotors = cfg?.enabled_motors || {};

  // Header & Core Allocation Strip
  if (tac) {
    if (asofBadge) asofBadge.textContent = tac.data_as_of ? `Cierre ${tac.data_as_of}` : 'En vivo';

    if (regimePill) {
      const ratioStr = tac.vts_ratio !== undefined && tac.vts_ratio !== null ? ` · VTS ${Number(tac.vts_ratio).toFixed(3)}` : '';
      const shortState = (tac.vts_state || tac.regime || 'CONTANGO').split(' (')[0];
      regimePill.textContent = `${shortState}${ratioStr}`;
      const isBack = String(tac.vts_state || tac.regime || '').toUpperCase().includes('BACKWARD') || Number(tac.vts_ratio) >= 1.0;
      regimePill.className = isBack
        ? 'px-2.5 py-1 rounded-full text-[11px] font-mono font-bold bg-rose-100 dark:bg-rose-950/70 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800 tabular-nums'
        : 'px-2.5 py-1 rounded-full text-[11px] font-mono font-bold bg-brand-50 dark:bg-brand-900/40 text-brand-800 dark:text-brand-300 border border-brand-200 dark:border-brand-800 tabular-nums';
    }

    if (corePills) {
      const coreEntries = Object.entries(tac.core_allocation || {}).filter(([, w]) => Number(w) > 0);
      if (coreEntries.length > 0) {
        corePills.innerHTML = coreEntries
          .map(([sym, w]) => `<span class="px-2 py-0.5 rounded bg-brand-100 dark:bg-brand-900/50 text-brand-800 dark:text-brand-300 font-semibold">${escHtml(sym)} ${Number(w).toFixed(0)}%</span>`)
          .join('');
      } else {
        const idleTxt = tac.idle_cash_pct !== undefined ? ` · Liquidez Táctica ${Number(tac.idle_cash_pct).toFixed(0)}%` : '';
        corePills.innerHTML = `<span class="px-2 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 font-semibold">0% Core · Escudo Volatilidad${idleTxt}</span>`;
      }
    }
  } else {
    if (asofBadge) asofBadge.textContent = APP_DATA?.live_scan?.as_of_date || 'Modo 3';
  }

  const openTrades = Array.isArray(tac?.open_trades) ? tac.open_trades : [];
  const signalsToday = Array.isArray(tac?.signals_today) ? tac.signals_today : [];

  // Armed engines status row
  const engineKeys = ['M1_PULLBACK', 'M2_VIX_DIV', 'M3_BEAR_SHORT', 'M4_CTA_TREND', 'M5_VOL_CRUSH'];
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
          }">${m.badge}</span>`;
        })
        .join('')}
    </div>
  `;

  if (openTrades.length === 0 && signalsToday.length === 0) {
    bodyEl.innerHTML = `
      <div class="p-3.5 rounded-lg bg-slate-50/80 dark:bg-slate-800/40 border border-dashed border-slate-200 dark:border-slate-700 space-y-2">
        <div class="flex items-center gap-2 text-slate-700 dark:text-slate-200 font-medium">
          <span class="w-2 h-2 rounded-full bg-brand-500 shrink-0"></span>
          <span>Sin operaciones tácticas activas hoy · 100% Capital asignado según Core Modo 3 Élite</span>
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
          Posiciones Tácticas Abiertas Hoy (${openTrades.length})
        </div>
        <div class="space-y-2">
          ${openTrades
            .map((t) => {
              const meta = getEngineMeta(t.engine_id);
              const ret = Number(t.unrealized_ret_pct || 0);
              const retCls = ret >= 0 ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-600 dark:text-red-400';
              const dirCls = t.direction === 'SHORT'
                ? 'bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300'
                : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300';
              return `
                <div class="p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/60 space-y-1.5">
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5">
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${meta.pillCls}">${escHtml(meta.badge)}</span>
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${dirCls}">${escHtml(t.direction || 'LONG')}</span>
                      <span class="font-mono font-bold text-sm text-slate-900 dark:text-white">${escHtml(t.symbol)}</span>
                    </div>
                    <div class="flex items-center gap-2.5 font-mono tabular-nums text-xs">
                      <span class="font-bold ${retCls}">${fmtPct(ret)}</span>
                      <span class="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 font-bold text-slate-800 dark:text-slate-200">${Number(t.weight_pct || 0).toFixed(1)}% peso</span>
                    </div>
                  </div>
                  <div class="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono tabular-nums text-slate-500 dark:text-slate-400">
                    <span>Entrada: $${Number(t.entry_price || 0).toFixed(2)} → Actual: $${Number(t.current_price || 0).toFixed(2)}</span>
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
    sectionsHtml += `
      <div class="space-y-2">
        <div class="text-[11px] font-bold uppercase tracking-wider text-brand-700 dark:text-brand-400">
          Señales Disparadas Hoy (${signalsToday.length})
        </div>
        <div class="space-y-2">
          ${signalsToday
            .map((s) => {
              const meta = getEngineMeta(s.engine_id);
              const confTxt = s.meta_confidence !== undefined && s.meta_confidence !== null
                ? `Meta-Conf ${Number(s.meta_confidence).toFixed(2)}x`
                : '';
              return `
                <div class="p-3 rounded-lg border border-brand-300 dark:border-brand-800 bg-brand-50/50 dark:bg-brand-900/20 space-y-1.5">
                  <div class="flex flex-wrap items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5">
                      <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${meta.pillCls}">${escHtml(meta.badge)}</span>
                      <span class="font-mono font-bold text-slate-900 dark:text-white">${escHtml(s.direction || 'LONG')} ${escHtml(s.symbol)}</span>
                    </div>
                    ${confTxt ? `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-brand-700 text-white tabular-nums">${confTxt}</span>` : ''}
                  </div>
                  <div class="flex flex-wrap items-center gap-3 text-[11px] font-mono tabular-nums text-slate-700 dark:text-slate-300">
                    <span>Precio Entrada: <b>$${Number(s.entry_price || 0).toFixed(2)}</b></span>
                    ${s.stop_price != null ? `<span class="text-rose-700 dark:text-rose-400">Stop: <b>$${Number(s.stop_price).toFixed(2)}</b></span>` : ''}
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
// BOT CONTROL CENTER (LIVE STATE, STACKED MOBILE CARDS & COMMANDS)
// ============================================================================
async function fetchLiveStatus(initForm = false) {
  if (liveFetchInFlight && !initForm) return;
  liveFetchInFlight = true;
  try {
    const res = await fetch('/api/live/status');
    const data = await res.json();
    LAST_LIVE_STATUS = data;
    renderLiveControlCenter(data, initForm || !LIVE_CONFIG_INITIALIZED);
    LIVE_CONFIG_INITIALIZED = true;
  } catch (err) {
    console.error('Error fetching live bot status:', err);
  } finally {
    liveFetchInFlight = false;
  }
}

function renderLiveControlCenter(data, populateForm = false) {
  if (!data || !data.config || !data.state) return;
  const cfg = data.config;
  const state = data.state;
  const acct = state.account || {};
  const conn = data.broker_connection || { ok: true, message: '' };

  // 1. Desktop & Mobile Header Badges
  const hdrDot = document.getElementById('hdr-status-dot');
  const hdrStatus = document.getElementById('hdr-status-text');
  const hdrBroker = document.getElementById('hdr-broker-text');
  const hdrMobDot = document.getElementById('hdr-mobile-dot');
  const hdrMobStatus = document.getElementById('hdr-mobile-status');
  const botRunning = cfg.bot_running !== false;

  if (hdrDot) hdrDot.className = `w-2 h-2 rounded-full ${botRunning ? 'bg-brand-500' : 'bg-amber-500'}`;
  if (hdrMobDot) hdrMobDot.className = `w-1.5 h-1.5 rounded-full shrink-0 ${botRunning ? 'bg-brand-500' : 'bg-amber-500'}`;

  if (hdrStatus) {
    hdrStatus.textContent = botRunning
      ? (cfg.execution_mode === 'AUTO_100' ? 'Active · 100% Automated' : 'Active · Copilot Mode')
      : 'Paused';
  }
  if (hdrBroker) {
    hdrBroker.textContent = cfg.broker_provider === 'ALPACA_PAPER'
      ? 'Alpaca Paper API'
      : (cfg.broker_provider === 'ALPACA_LIVE' ? 'Alpaca Live API' : 'Local Paper Broker');
  }

  const totalEq = Number(acct.total_equity_usd || 10000);
  const initialCap = Number(acct.initial_capital || 10000);
  const totalRet = Number(acct.total_return_pct || 0);

  if (hdrMobStatus) {
    hdrMobStatus.textContent = `${botRunning ? 'Activo' : 'Pausado'} · ${fmtUSD(totalEq)} (${fmtPct(totalRet)})`;
  }

  // 2. Control Bar Badges & Schedule/DST
  const statusBadge = document.getElementById('pt-bot-status-badge');
  const toggleBtn = document.getElementById('btn-toggle-bot');
  if (statusBadge && toggleBtn) {
    if (botRunning) {
      statusBadge.textContent = 'ACTIVE (24/7)';
      statusBadge.className = 'px-2.5 py-0.5 rounded text-xs font-semibold bg-brand-50 dark:bg-brand-900/40 text-brand-800 dark:text-brand-300 border border-brand-100 dark:border-brand-800 font-mono';
      toggleBtn.textContent = 'Pause Bot';
      toggleBtn.className = 'touch-target px-3.5 py-2.5 sm:py-2 rounded-lg text-xs font-semibold bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/50 dark:hover:bg-amber-900/50 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800 transition';
    } else {
      statusBadge.textContent = 'PAUSED';
      statusBadge.className = 'px-2.5 py-0.5 rounded text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 font-mono';
      toggleBtn.textContent = 'Resume Bot';
      toggleBtn.className = 'touch-target px-3.5 py-2.5 sm:py-2 rounded-lg text-xs font-semibold bg-brand-700 hover:bg-brand-800 text-white transition';
    }
  }

  const modeBadge = document.getElementById('pt-mode-badge');
  if (modeBadge) {
    modeBadge.textContent = cfg.execution_mode === 'AUTO_100' ? '100% Automated Mode' : 'Copilot Mode';
  }

  const brokerBadge = document.getElementById('pt-broker-badge');
  if (brokerBadge) {
    brokerBadge.textContent = cfg.broker_provider === 'ALPACA_PAPER'
      ? 'Alpaca Paper'
      : (cfg.broker_provider === 'ALPACA_LIVE' ? 'Alpaca Live' : 'Local Paper');
  }

  const connMsg = document.getElementById('pt-connection-msg');
  if (connMsg) {
    connMsg.innerHTML = `<span class="${conn.ok ? 'text-brand-600 dark:text-brand-400' : 'text-amber-600 dark:text-amber-400'} font-bold">●</span> ${escHtml(conn.message)}`;
  }

  const lastScan = document.getElementById('pt-last-scan');
  if (lastScan) lastScan.textContent = state.last_scan_time || '--';

  updateScheduleAndDstUI(data, cfg);

  // 3. Copilot Banner & Mobile Notification Dot
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
      copilotDesc.textContent = `Propuesta pendiente (${p.trigger_source}): Objetivo → ${syms}`;
      copilotBanner.classList.remove('hidden');
      if (mobBadgeInicio) mobBadgeInicio.classList.remove('hidden');
    } else {
      copilotBanner.classList.add('hidden');
      if (mobBadgeInicio) mobBadgeInicio.classList.add('hidden');
    }
  }

  // 4. Financial Metric KPIs (Inicio + Cartera Mobile Summary)
  const eqEl = document.getElementById('pt-total-equity');
  if (eqEl) eqEl.textContent = fmtUSD(totalEq);

  const retEl = document.getElementById('pt-total-ret');
  if (retEl) {
    retEl.textContent = `${fmtPct(totalRet)} (Base ${fmtUSD(initialCap)})`;
    retEl.className = `kpi-num text-[11px] sm:text-xs font-mono mt-0.5 font-semibold truncate ${
      totalRet >= 0 ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400'
    }`;
  }

  const posValNum = Number(acct.positions_value_usd || 0);
  const cashNum = Number(acct.cash_usd || 0);
  const positions = state.positions || [];

  const posValEl = document.getElementById('pt-pos-value');
  if (posValEl) posValEl.textContent = fmtUSD(posValNum);

  const posCountEl = document.getElementById('pt-pos-count');
  if (posCountEl) posCountEl.textContent = `${positions.length} active position${positions.length === 1 ? '' : 's'}`;

  const cashEl = document.getElementById('pt-cash-value');
  if (cashEl) cashEl.textContent = fmtUSD(cashNum);

  const ddVal = Number(acct.current_dd_pct || 0);
  const ddEl = document.getElementById('pt-dd-value');
  if (ddEl) {
    ddEl.textContent = `${ddVal.toFixed(2)}%`;
    ddEl.className = `kpi-num text-lg sm:text-2xl font-bold font-mono mt-1 ${
      ddVal <= -4 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'
    }`;
  }

  const ddLimitEl = document.getElementById('pt-dd-limit-label');
  if (ddLimitEl) ddLimitEl.textContent = `Kill switch: ${cfg.daily_kill_switch_dd_pct || -8.0}%`;

  // Cartera mobile summary strip & bottom-nav badge
  const mobEq = document.getElementById('cartera-mob-equity');
  const mobInv = document.getElementById('cartera-mob-invested');
  const mobCash = document.getElementById('cartera-mob-cash');
  if (mobEq) mobEq.textContent = fmtUSD(totalEq);
  if (mobInv) mobInv.textContent = fmtUSD(posValNum);
  if (mobCash) mobCash.textContent = fmtUSD(cashNum);

  const carteraPosBadge = document.getElementById('cartera-pos-badge');
  if (carteraPosBadge) carteraPosBadge.textContent = `${positions.length} abierta${positions.length === 1 ? '' : 's'}`;

  const mobBadgeCartera = document.getElementById('mob-badge-cartera');
  if (mobBadgeCartera) {
    if (positions.length > 0) {
      mobBadgeCartera.textContent = String(positions.length);
      mobBadgeCartera.classList.remove('hidden');
    } else {
      mobBadgeCartera.classList.add('hidden');
    }
  }

  // 5. Render Live Tactical Engines M1–M5 Card & Refresh Market Pulse
  renderTacticalEnginesCard(data, cfg);
  renderLiveScan();

  // 6. Open Positions: Desktop Table + Stacked Mobile Cards
  const posTbody = document.getElementById('pt-positions-tbody');
  const posMobCards = document.getElementById('pt-positions-mobile-cards');

  if (positions.length === 0) {
    if (posTbody) {
      posTbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-slate-400 font-sans">100% in cash liquidity. Click "Scan & Sync Now" to evaluate daily entry rules.</td></tr>`;
    }
    if (posMobCards) {
      posMobCards.innerHTML = `
        <div class="p-4 rounded-xl border border-dashed border-slate-200 dark:border-slate-700 text-center space-y-2">
          <div class="text-xs font-medium text-slate-600 dark:text-slate-300">100% en liquidez disponible (Cash)</div>
          <p class="text-[11px] text-slate-400">Pulsa Sincronizar para evaluar las reglas diarias de entrada.</p>
        </div>
      `;
    }
  } else {
    if (posTbody) {
      posTbody.innerHTML = positions
        .map((p) => {
          const dirCls = p.direction === 'LONG'
            ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
            : 'bg-red-50 text-red-800 dark:bg-red-900/40 dark:text-red-300';
          return `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
              <td class="py-2.5 px-3 font-bold text-slate-900 dark:text-white">${escHtml(p.broker_symbol)} <span class="text-[11px] text-slate-400 font-sans">(${escHtml(p.internal_symbol)})</span></td>
              <td class="py-2.5 px-3"><span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${dirCls}">${escHtml(p.direction)}</span></td>
              <td class="py-2.5 px-3 font-sans text-xs text-slate-700 dark:text-slate-300">${escHtml(p.motor)}</td>
              <td class="py-2.5 px-3 text-right text-slate-700 dark:text-slate-300">${p.qty}</td>
              <td class="py-2.5 px-3 text-right text-slate-700 dark:text-slate-300">$${p.current_price}</td>
              <td class="py-2.5 px-3 text-right font-bold text-slate-900 dark:text-white">${fmtUSD(p.market_value_usd)}</td>
              <td class="py-2.5 px-3 text-right font-bold text-brand-800 dark:text-brand-400">${p.weight_pct}%</td>
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
            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300'
            : 'bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-300';
          const barW = Math.min(100, Math.max(2, Math.abs(Number(p.weight_pct || 0))));
          const symNote = p.internal_symbol && p.internal_symbol !== p.broker_symbol ? ` (${p.internal_symbol})` : '';
          return `
            <div class="p-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/60 space-y-2">
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <span class="font-mono font-bold text-sm text-slate-900 dark:text-white">${escHtml(p.broker_symbol)}${escHtml(symNote)}</span>
                    <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${dirCls}">${escHtml(p.direction)}</span>
                  </div>
                  <div class="mt-1">
                    <span class="inline-block px-2 py-0.5 rounded text-[10px] font-semibold border ${meta.pillCls}">${escHtml(p.motor)}</span>
                  </div>
                </div>
                <div class="text-right font-mono tabular-nums shrink-0">
                  <div class="text-sm font-bold text-slate-900 dark:text-white">${fmtUSD(p.market_value_usd)}</div>
                  <div class="text-xs font-bold text-brand-700 dark:text-brand-400">${p.weight_pct}% cartera</div>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200/70 dark:border-slate-700/70 text-[11px] font-mono tabular-nums text-slate-600 dark:text-slate-300">
                <div>Participaciones: <b class="text-slate-900 dark:text-slate-100">${p.qty}</b></div>
                <div class="text-right">Precio: <b class="text-slate-900 dark:text-slate-100">$${p.current_price}</b></div>
              </div>
              <div class="w-full h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                <div class="h-full rounded-full bg-brand-600 dark:bg-brand-500" style="width:${barW}%"></div>
              </div>
            </div>
          `;
        })
        .join('');
    }
  }

  // 7. Executed Orders History: Desktop Table + Stacked Mobile Cards
  const orders = state.orders_history || [];
  const ordTbody = document.getElementById('pt-orders-tbody');
  const ordMobCards = document.getElementById('pt-orders-mobile-cards');
  const carteraOrdBadge = document.getElementById('cartera-ord-badge');
  if (carteraOrdBadge) carteraOrdBadge.textContent = `${orders.length} ${orders.length === 1 ? 'orden' : 'órdenes'}`;

  if (orders.length === 0) {
    if (ordTbody) {
      ordTbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-slate-400 font-sans">No orders executed yet.</td></tr>`;
    }
    if (ordMobCards) {
      ordMobCards.innerHTML = `<div class="p-4 rounded-xl border border-dashed border-slate-200 dark:border-slate-700 text-center text-xs text-slate-400">Sin órdenes ejecutadas todavía.</div>`;
    }
  } else {
    const recentOrders = orders.slice(0, 25);
    if (ordTbody) {
      ordTbody.innerHTML = recentOrders
        .map((o) => {
          const isBuy = String(o.side || '').includes('BUY');
          const sideCls = isBuy ? 'text-emerald-700 dark:text-emerald-400' : 'text-amber-700 dark:text-amber-400';
          return `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition">
              <td class="py-2 px-3 text-slate-500 dark:text-slate-400 text-[11px]">${escHtml(o.time)}</td>
              <td class="py-2 px-3 font-bold ${sideCls}">${escHtml(o.side)}</td>
              <td class="py-2 px-3 font-bold text-slate-900 dark:text-white">${escHtml(o.symbol)}</td>
              <td class="py-2 px-3 text-right text-slate-700 dark:text-slate-200">${fmtUSD(o.notional_usd)}</td>
              <td class="py-2 px-3 font-sans text-[11px] text-slate-600 dark:text-slate-300">${escHtml(o.motor)}</td>
              <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300 text-[10px] font-bold border border-emerald-100 dark:border-emerald-800">${escHtml(o.status)}</span></td>
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
            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300'
            : 'bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300';
          return `
            <div class="p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/60 space-y-1.5">
              <div class="flex items-center justify-between gap-2 font-mono tabular-nums">
                <div class="flex items-center gap-1.5">
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${sidePill}">${escHtml(o.side)}</span>
                  <span class="font-bold text-sm text-slate-900 dark:text-white">${escHtml(o.symbol)}</span>
                </div>
                <span class="font-bold text-xs text-slate-900 dark:text-white">${fmtUSD(o.notional_usd)}</span>
              </div>
              <div class="flex items-center justify-between gap-2 text-[11px]">
                <span class="font-mono tabular-nums text-slate-400">${escHtml(o.time)} · ${escHtml(o.motor || '')}</span>
                <span class="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300 text-[10px] font-mono font-bold">${escHtml(o.status)}</span>
              </div>
            </div>
          `;
        })
        .join('');
    }
  }

  // 8. System Logs Console
  const logs = state.logs || [];
  const logsBox = document.getElementById('pt-logs-box');
  if (logsBox) {
    logsBox.innerHTML = logs.length === 0
      ? `<div class="text-slate-400">Sin eventos registrados.</div>`
      : logs
          .slice(0, 35)
          .map((l) => {
            let col = 'text-slate-700 dark:text-slate-300';
            if (l.level === 'SUCCESS') col = 'text-emerald-700 dark:text-emerald-400 font-semibold';
            else if (l.level === 'WARN') col = 'text-amber-700 dark:text-amber-400 font-semibold';
            else if (l.level === 'ERROR') col = 'text-red-700 dark:text-red-400 font-bold';
            return `<div class="leading-relaxed break-words"><span class="text-slate-400 dark:text-slate-500">[${escHtml(l.time)}]</span> <span class="${col}">${escHtml(l.msg)}</span></div>`;
          })
          .join('');
  }

  // 9. Populate Form Inputs (Only on Initial Load or Config Save)
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

    // Modal Inputs
    setVal('cfg-broker-provider', cfg.broker_provider || 'LOCAL_PAPER');
    setVal('cfg-alpaca-endpoint', cfg.alpaca_endpoint || 'https://paper-api.alpaca.markets');
    setVal('cfg-alpaca-key', cfg.alpaca_api_key || '');
    setVal('cfg-alpaca-secret', cfg.alpaca_secret_key || '');

    setVal('cfg-mobile-phone', cfg.mobile_phone || cfg.signal_recipient_phone || '');
    setVal('cfg-sig-url', cfg.signal_api_url || 'https://api.callmebot.com/signal/send.php');
    setVal('cfg-sig-apikey', cfg.signal_apikey || '');
    setVal('cfg-tg-token', cfg.telegram_bot_token || '');
    setVal('cfg-tg-chat', cfg.telegram_chat_id || '');
  }
}

// ============================================================================
// LIVE ACTIONS & SETTINGS PERSISTENCE
// ============================================================================
async function triggerLiveAction(actionName, simulateMotor = null, confirmed = false) {
  // Enforce explicit 2-step confirmation for destructive operations
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
      if (isAlertTest) {
        showQuickSystemFeedback(data.result.message);
      }
    }
  } catch (err) {
    console.error('Error executing live action:', err);
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
    },
    alpaca_endpoint: getVal('cfg-alpaca-endpoint'),
    alpaca_api_key: getVal('cfg-alpaca-key'),
    alpaca_secret_key: getVal('cfg-alpaca-secret'),
    mobile_phone: mobilePhone,
    signal_recipient_phone: mobilePhone,
    signal_api_url: getVal('cfg-sig-url'),
    signal_apikey: getVal('cfg-sig-apikey'),
    telegram_bot_token: getVal('cfg-tg-token'),
    telegram_chat_id: getVal('cfg-tg-chat'),
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
    showConfigFeedback('Configuration saved and hot-reloaded.', fromModal);
  } catch (err) {
    console.error('Error saving configuration:', err);
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

function showQuickSystemFeedback(msg) {
  const el = document.getElementById('sys-quick-feedback');
  if (!el) return;
  el.textContent = msg;
  el.classList.remove('hidden');
  setTimeout(() => {
    el.classList.add('hidden');
  }, 4500);
}

// ============================================================================
// FISCALIDAD ESPAÑA & RENTABILIDAD NETA TRAS IRPF (2007–2026, SUB-TAB 5)
// ============================================================================
function initTaxView() {
  if (!APP_DATA || !APP_DATA.tax_analysis) return;
  const tax = APP_DATA.tax_analysis;
  const m = tax.metrics;
  const th = getChartTheme();
  const isMobile = window.innerWidth < 640;

  // 1. KPI Cards
  const kpiNet = document.getElementById('tax-kpi-net-cap');
  const kpiGross = document.getElementById('tax-kpi-gross-cap');
  const kpiTax = document.getElementById('tax-kpi-total-tax');
  const kpiRatio = document.getElementById('tax-kpi-ratio-spy');
  if (kpiNet) kpiNet.textContent = `$${m.net_final_equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (kpiGross) kpiGross.textContent = `$${m.gross_final_equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (kpiTax) kpiTax.textContent = `$${m.total_tax_paid_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (kpiRatio) kpiRatio.textContent = `${m.net_wealth_ratio_vs_spy_net}x Más Capital`;

  // 2. Render ECharts Curve
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
        data: ['Modo 3 Élite Bruto', 'Neto Operativo (Comisiones+TER)', 'Neto en Bolsillo (Tras IRPF)', 'S&P 500 Buy & Hold'],
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
          name: 'Modo 3 Élite Bruto',
          type: 'line',
          data: grossData,
          showSymbol: false,
          lineStyle: { width: 1.6, color: th.grossLine },
          itemStyle: { color: th.grossLine },
        },
        {
          name: 'Neto Operativo (Comisiones+TER)',
          type: 'line',
          data: opNetData,
          showSymbol: false,
          lineStyle: { width: 1.5, color: '#f59e0b', type: 'dotted' },
          itemStyle: { color: '#f59e0b' },
        },
        {
          name: 'Neto en Bolsillo (Tras IRPF)',
          type: 'line',
          data: netData,
          showSymbol: false,
          lineStyle: { width: 2.5, color: '#10b981' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: th.dark ? 'rgba(16, 185, 129, 0.22)' : 'rgba(5, 150, 105, 0.15)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0.0)' },
            ]),
          },
          itemStyle: { color: '#10b981' },
        },
        {
          name: 'S&P 500 Buy & Hold',
          type: 'line',
          data: spyData,
          showSymbol: false,
          lineStyle: { width: 1.5, color: '#ef4444', type: 'dashed' },
          itemStyle: { color: '#ef4444' },
        },
      ],
    });
  }

  // 3. Render Yearly Table
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
            <td class="py-2 px-3 text-right ${row.gross_ret_pct >= 0 ? 'text-brand-700 dark:text-brand-400' : 'text-rose-600 dark:text-rose-400'}">${grossRetSign}${row.gross_ret_pct.toFixed(2)}%</td>
            <td class="py-2 px-3 text-right text-amber-700 dark:text-amber-400 font-mono">-$${row.operational_fees.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td class="py-2 px-3 text-right ${row.realized_gain_usd >= 0 ? 'text-brand-700 dark:text-brand-400' : 'text-rose-600 dark:text-rose-400'}">$${row.realized_gain_usd.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td class="py-2 px-3 text-right text-slate-500 dark:text-slate-400">${row.loss_offset_used > 0 ? `-$${row.loss_offset_used.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '--'}</td>
            <td class="py-2 px-3 text-right text-slate-700 dark:text-slate-200 font-semibold">$${row.taxable_base.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td class="py-2 px-3 text-right font-bold text-amber-700 dark:text-amber-400">$${row.tax_paid.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td class="py-2 px-3 text-right text-slate-500 dark:text-slate-400">${row.tax_paid > 0 ? `${row.effective_rate_pct.toFixed(1)}%` : '0.0%'}</td>
            <td class="py-2 px-3 text-right ${row.loss_carried_forward > 0 ? 'text-rose-600 dark:text-rose-400 font-semibold' : 'text-slate-400 dark:text-slate-500'}">${row.loss_carried_forward > 0 ? `$${row.loss_carried_forward.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '--'}</td>
            <td class="py-2 px-3 text-right font-bold text-slate-900 dark:text-white">$${row.net_end_equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
            <td class="py-2 px-3 text-right font-bold ${row.net_ret_pct >= 0 ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}">${netRetSign}${row.net_ret_pct.toFixed(2)}%</td>
          </tr>
        `;
      })
      .join('');
  }
}
