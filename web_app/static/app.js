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
let ACTIVE_MOBILE_TAB = 'inicio'; // 'inicio' | 'cartera' | 'analisis' | 'sistema'
let LAST_CONTROL_MOBILE_TAB = 'inicio';
let CHART_SCALE = 'value'; // 'value' | 'log'
let LIVE_CONFIG_INITIALIZED = false;

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
    plainExplanation: 'Ruptura de canal Donchian de 20 sesiones con alineación de medias en activos descorrelacionados (Oro GLD, Bonos TLT, Petróleo USO o Soja ZS), protegiendo frente a inflación y crisis.',
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
}

function toggleTheme() {
  applyTheme(!isDarkMode(), true);
}

// ============================================================================
// CICLO DE VIDA DE LA APLICACIÓN Y SONDEO INTELIGENTE
// ============================================================================
window.addEventListener('DOMContentLoaded', () => {
  // Cierre rápido de modales con tecla Escape
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeEngineConfirmModal();
      closeDestructiveConfirmModal();
      closeConfigModal();
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
}

// ============================================================================
// NAVEGACIÓN: BARRA INFERIOR MÓVIL + PESTAÑAS SUPERIORES + 5 SUBPESTAÑAS
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
            <div class="py-2.5 flex items-center justify-between gap-2">
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
      dstBadge.textContent = customLabel || `DST Desfase EU/US (${diffHours}h · ${nyName}/${madName})`;
      dstBadge.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-50 dark:bg-slate-800 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800';
    } else {
      dstBadge.textContent = customLabel || `${nyName} · ${madName} (+${diffHours}h)`;
      dstBadge.className = 'px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700';
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
    sectionsHtml += `
      <div class="space-y-2">
        <div class="text-[11px] font-bold uppercase tracking-wider text-brand-700 dark:text-brand-300">
          Señales Disparadas Hoy (${signalsToday.length})
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
    console.error('Error consultando estado en vivo:', err);
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
    setVal('cfg-tg-token', cfg.telegram_bot_token || '');
    setVal('cfg-tg-chat', cfg.telegram_chat_id || '');
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
  setTxt('aeat-kpi-720-sub', `${fmtEUR(m720.current_equity_eur || 0)} (${m720.threshold_usage_pct || 0}% de 50.000 €)`);

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
        data: ['Modo 3 Élite Bruto (6M)', 'Neto Operativo (Comisiones+TER)', 'Neto en Bolsillo (Tras IRPF)', 'S&P 500 Buy & Hold'],
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
          name: 'Modo 3 Élite Bruto (6M)',
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
