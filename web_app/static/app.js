/**
 * Aegis-Quant | Frontend Controller (app.js)
 * Institutional Minimalist Theme (Green & White), English Language Standard.
 * Unified on Mode 3 Élite vs S&P 500 (2007–2026).
 */

let APP_DATA = null;
const ACTIVE_MODE_ID = 'MODO_3_ELITE';
let ACTIVE_MOTOR_FILTER = 'TOP_IMPACT'; // 'NONE', 'TOP_IMPACT', 'M1_PULLBACK', 'M2_VIX_DIV', 'M3_BEAR_SHORT', 'M4_CTA_TREND', 'M5_VOL_CRUSH'
let CHART_SCALE = 'value'; // 'value' | 'log'
let LIVE_CONFIG_INITIALIZED = false;

// Apache ECharts Instances
let mainChart = null;
let ddChart = null;
let subperiodsChart = null;
let monteCarloChart = null;
let frictionChart = null;

// Engine Metadata & Explanations
const MOTOR_META = {
  M1_PULLBACK: {
    id: 'M1_PULLBACK',
    shortName: 'Engine 1: Oversold Pullback (M1)',
    badge: 'M1 Pullback',
    color: '#059669',
    symbolShape: 'circle',
    plainExplanation: 'Market was in a primary bull trend (above 200-day moving average) but suffered an abrupt 3-day drop (RSI(2) < 10). The engine bought cheap shares expecting a sharp 3 to 5 day mean reversion.',
  },
  M2_VIX_DIV: {
    id: 'M2_VIX_DIV',
    shortName: 'Engine 2: Volatility Divergence (M2)',
    badge: 'M2 VIX Div',
    color: '#0284c7',
    symbolShape: 'diamond',
    plainExplanation: 'The CBOE VIX fear index spiked on institutional panic over the last 5 days but began deflating while index prices remained depressed. Clear sign of selling exhaustion.',
  },
  M3_BEAR_SHORT: {
    id: 'M3_BEAR_SHORT',
    shortName: 'Engine 3: Bear Market Short (M3)',
    badge: 'M3 Crisis Short',
    color: '#e11d48',
    symbolShape: 'triangle',
    plainExplanation: 'The market was in a confirmed secular bear regime (below 200-day moving average with high volatility). Following a weak 2-day bear rally, the engine shorted the index to profit from the downtrend.',
  },
  M4_CTA_TREND: {
    id: 'M4_CTA_TREND',
    shortName: 'Engine 4: Multi-Asset CTA Trends (M4)',
    badge: 'M4 CTA Trend',
    color: '#d97706',
    symbolShape: 'rect',
    plainExplanation: 'Breakout above 20-day Donchian channels in uncorrelated crisis hedges (Gold GLD, Crude Oil USO, Soybeans SOYB, or Long Treasuries TLT). Captures persistent commodity and safe-haven flows.',
  },
  M5_VOL_CRUSH: {
    id: 'M5_VOL_CRUSH',
    shortName: 'Engine 5: Post-Panic Vol-Crush (M5)',
    badge: 'M5 Vol-Crush',
    color: '#7c3aed',
    symbolShape: 'pin',
    plainExplanation: 'The volatility term structure backwardation (VIX over VIX3M) collapsed by more than 5% in a single session. Signals the exact pivot where major institutions re-enter risk assets.',
  },
  CORE_BULL: {
    id: 'CORE_BULL',
    shortName: 'Intelligent Core Indexing (SPY/QQQ)',
    badge: 'Core Bull',
    color: '#065f46',
    symbolShape: 'circle',
    plainExplanation: 'Passive core allocation during healthy Contango regimes (VIX < VIX3M). Capital compounds without turnover drag.',
  },
};

const ASSET_NAMES = {
  SPY: 'S&P 500 ETF (SPY)',
  QQQ: 'Nasdaq 100 ETF (QQQ)',
  GLD: 'Physical Gold ETF (GLD)',
  TLT: '20+ Year Treasury Bond ETF (TLT)',
  USO: 'WTI Crude Oil ETF (USO)',
  SOYB: 'Soybeans Futures ETF (SOYB)',
  ZS: 'Soybeans Futures (ZS / SOYB)',
};

// Numeric Formatters
function fmtUSD(val) {
  return '$' + Number(val).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function fmtPct(val, sign = true) {
  const n = Number(val);
  const prefix = sign && n > 0 ? '+' : '';
  return prefix + n.toFixed(2) + '%';
}

// Application Lifecycle
window.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch('/api/summary');
    APP_DATA = await res.json();

    initMotorFilterButtons();
    renderMotorBreakdownCards();
    renderDefaultTradeStory();
    renderYearlyTable();
    updateCustomSimulator();
    renderTradesTable();
    renderLiveScan();
    await fetchLiveStatus(true);

    // Live status polling every 5 seconds
    setInterval(() => {
      fetchLiveStatus(false);
    }, 5000);

    window.addEventListener('resize', handleWindowResize);
  } catch (err) {
    console.error('Initialization error:', err);
  }
});

function handleWindowResize() {
  if (mainChart) mainChart.resize();
  if (ddChart) ddChart.resize();
  if (subperiodsChart) subperiodsChart.resize();
  if (monteCarloChart) monteCarloChart.resize();
  if (frictionChart) frictionChart.resize();
}

// ============================================================================
// MAIN VIEW NAVIGATION & SUB-TABS
// ============================================================================
function switchMainView(viewId) {
  const tabControl = document.getElementById('main-tab-control');
  const tabPerf = document.getElementById('main-tab-performance');
  const viewControl = document.getElementById('main-view-control');
  const viewPerf = document.getElementById('main-view-performance');

  if (viewId === 'control') {
    tabControl.classList.add('active');
    tabPerf.classList.remove('active');
    viewControl.classList.remove('hidden');
    viewPerf.classList.add('hidden');
    fetchLiveStatus(false);
  } else {
    tabPerf.classList.add('active');
    tabControl.classList.remove('active');
    viewPerf.classList.remove('hidden');
    viewControl.classList.add('hidden');

    // Wait for container to be rendered with actual width before initializing ECharts
    setTimeout(() => {
      if (!mainChart || !ddChart) {
        initMainCharts();
      } else {
        mainChart.resize();
        ddChart.resize();
        updateMainCharts();
      }
    }, 50);
  }
}

function switchPerfSubTab(subId) {
  const subtabs = ['chart', 'guide', 'crisis', 'simulator'];
  subtabs.forEach((id) => {
    const btn = document.getElementById(`subtab-${id}`);
    const view = document.getElementById(`perf-view-${id}`);
    if (id === subId) {
      if (btn) btn.classList.add('active');
      if (view) view.classList.remove('hidden');
    } else {
      if (btn) btn.classList.remove('active');
      if (view) view.classList.add('hidden');
    }
  });

  if (subId === 'chart') {
    setTimeout(() => {
      if (!mainChart || !ddChart) {
        initMainCharts();
      } else {
        mainChart.resize();
        ddChart.resize();
      }
    }, 50);
  } else if (subId === 'crisis') {
    setTimeout(() => {
      initCrisisAndRobustnessCharts();
    }, 50);
  }
}

// ============================================================================
// CONFIGURATION MODAL
// ============================================================================
function openConfigModal() {
  const modal = document.getElementById('config-modal');
  modal.classList.remove('hidden');
  modal.classList.add('flex');
}

function closeConfigModal() {
  const modal = document.getElementById('config-modal');
  modal.classList.add('hidden');
  modal.classList.remove('flex');
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
    { id: 'NONE', label: 'Hide Markers (Lines Only)' },
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
        ? 'bg-emerald-800 text-white border-emerald-800 shadow-xs'
        : 'bg-white text-slate-700 hover:bg-slate-50 border-slate-300';
      return `
        <button onclick="setMotorFilter('${f.id}')" class="px-2.5 py-1 rounded-md text-xs font-semibold border transition ${cls}">
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
// APACHE ECHARTS 5 EQUITY & DRAWDOWN CHARTS
// ============================================================================
function initMainCharts() {
  const chartEl = document.getElementById('main-equity-chart');
  const ddEl = document.getElementById('drawdown-chart');
  if (!chartEl || !ddEl || !APP_DATA) return;

  // Destroy previous instances if any
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
  if (scaleType === 'value') {
    btnLin.className = 'px-2.5 py-1 rounded-md text-xs font-semibold bg-white text-slate-900 shadow-sm';
    btnLog.className = 'px-2.5 py-1 rounded-md text-xs font-medium text-slate-600 hover:text-slate-900';
  } else {
    btnLog.className = 'px-2.5 py-1 rounded-md text-xs font-semibold bg-white text-slate-900 shadow-sm';
    btnLin.className = 'px-2.5 py-1 rounded-md text-xs font-medium text-slate-600 hover:text-slate-900';
  }
  updateMainCharts();
}

function zoomToPeriod(startDate, endDate, btnId = '') {
  if (!mainChart || !APP_DATA) return;
  const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
  const curve = modeData.monthly_curve || [];
  if (curve.length === 0) return;
  const dates = curve.map((pt) => pt.date);

  // Find exact matching / clamped category dates from actual time series
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

  const actualStart = dates[sIdx];
  const actualEnd = dates[eIdx];

  const zoomAction = {
    type: 'dataZoom',
    startValue: actualStart,
    endValue: actualEnd,
  };

  mainChart.dispatchAction(zoomAction);
  if (ddChart) {
    ddChart.dispatchAction(zoomAction);
  }

  // Highlight active period button if btnId is provided
  const periodBtns = ['btn-period-all', 'btn-period-2008', 'btn-period-2011', 'btn-period-2020', 'btn-period-2022'];
  periodBtns.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (id === btnId) {
      el.className = 'px-2.5 py-1 rounded text-xs font-semibold bg-emerald-700 text-white shadow-xs';
    } else {
      el.className = 'px-2.5 py-1 rounded text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700';
    }
  });
}

function getFilteredScatterTrades(modeData, curveDates) {
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
        borderColor: '#ffffff',
        borderWidth: 1.5,
      },
      symbol: mMeta.symbolShape || 'circle',
      symbolSize: 8,
    };
  });
}

function updateMainCharts() {
  if (!mainChart || !ddChart || !APP_DATA) return;

  const modeData = APP_DATA.modes[ACTIVE_MODE_ID];
  const curve = modeData.monthly_curve || [];
  if (curve.length === 0) return;

  const dates = curve.map((pt) => pt.date);
  const modeValues = curve.map((pt) => pt.bot_eq);
  const sp500Values = curve.map((pt) => pt.spy_eq);

  const scatterData = getFilteredScatterTrades(modeData, dates);

  const mainOption = {
    backgroundColor: '#ffffff',
    animation: false,
    grid: {
      left: '56px',
      right: '24px',
      top: '32px',
      bottom: '36px',
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: '#0f172a', fontSize: 12, fontFamily: 'Inter' },
      axisPointer: { type: 'cross', lineStyle: { color: '#cbd5e1' } },
      formatter: function (params) {
        if (!params || params.length === 0) return '';
        const d = params[0].axisValue;
        let html = `<div class="font-mono text-xs font-bold text-slate-700 pb-1 border-b border-slate-100">${d}</div><div class="space-y-1 mt-1 text-xs">`;
        params.forEach((p) => {
          if (p.seriesType === 'line') {
            const val = Number(p.value).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
            html += `<div class="flex items-center justify-between gap-4 font-mono"><span style="color:${p.color}">${p.seriesName}:</span><span class="font-bold text-slate-900">$${val}</span></div>`;
          }
        });
        html += `</div>`;
        return html;
      },
    },
    legend: {
      data: ['Mode 3 Élite (5 Engines + VTS)', 'S&P 500 (Buy & Hold)'],
      right: '16px',
      top: '6px',
      textStyle: { color: '#475569', fontSize: 11, fontFamily: 'Inter' },
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#64748b', fontSize: 11, margin: 10 },
      splitLine: { show: false },
    },
    yAxis: {
      type: CHART_SCALE,
      scale: true,
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: {
        color: '#64748b',
        fontSize: 11,
        formatter: (v) => '$' + (v >= 1000 ? Math.round(v / 1000) + 'k' : v),
      },
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: [0] },
      { type: 'slider', xAxisIndex: [0], bottom: '0px', height: 16, borderColor: '#e2e8f0', handleSize: '100%' },
    ],
    series: [
      {
        name: 'S&P 500 (Buy & Hold)',
        type: 'line',
        data: sp500Values,
        smooth: false,
        showSymbol: false,
        lineStyle: { color: '#94a3b8', width: 1.8, type: 'dashed' },
        itemStyle: { color: '#94a3b8' },
      },
      {
        name: 'Mode 3 Élite (5 Engines + VTS)',
        type: 'line',
        data: modeValues,
        smooth: false,
        showSymbol: false,
        lineStyle: { color: '#059669', width: 2.2 },
        itemStyle: { color: '#059669' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(5, 150, 105, 0.10)' },
            { offset: 1, color: 'rgba(5, 150, 105, 0.00)' },
          ]),
        },
      },
      {
        name: 'Trade Executions',
        type: 'scatter',
        data: scatterData,
        z: 10,
        tooltip: {
          formatter: function (p) {
            const t = p.data.tradeObj;
            return `
              <div class="font-sans text-xs">
                <div class="font-bold text-slate-800">${t.engine_id} · ${t.direction} ${t.symbol}</div>
                <div class="text-slate-500 text-[11px]">${t.entry_date} → ${t.exit_date} (${t.days}d)</div>
                <div class="mt-1 font-mono font-bold ${t.portfolio_ret_pct >= 0 ? 'text-emerald-700' : 'text-red-700'}">
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
    backgroundColor: '#ffffff',
    animation: false,
    grid: {
      left: '56px',
      right: '24px',
      top: '12px',
      bottom: '24px',
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      textStyle: { color: '#0f172a', fontSize: 11 },
      formatter: function (params) {
        if (!params || params.length === 0) return '';
        const d = params[0].axisValue;
        let html = `<div class="font-mono text-xs font-bold text-slate-700">${d}</div><div class="space-y-0.5 mt-1 text-xs">`;
        params.forEach((p) => {
          html += `<div class="flex items-center justify-between gap-4 font-mono"><span style="color:${p.color}">${p.seriesName}:</span><span class="font-bold">${p.value}%</span></div>`;
        });
        html += `</div>`;
        return html;
      },
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      min: -60,
      max: 5,
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: {
        color: '#64748b',
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
        lineStyle: { color: '#cbd5e1', width: 1.2 },
        areaStyle: { color: 'rgba(203, 213, 225, 0.3)' },
      },
      {
        name: 'Mode 3 Élite Drawdown',
        type: 'line',
        data: ddValues,
        showSymbol: false,
        lineStyle: { color: '#059669', width: 1.5 },
        areaStyle: { color: 'rgba(5, 150, 105, 0.15)' },
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
  const retColor = isWin ? 'text-emerald-700' : 'text-red-700';
  const badgeBg = isWin ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-red-50 text-red-800 border-red-200';

  container.innerHTML = `
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <span class="px-2.5 py-0.5 rounded text-xs font-semibold border ${badgeBg}">${meta.badge}</span>
        <span class="text-xs font-mono text-slate-500">${t.direction} · ${t.symbol}</span>
      </div>

      <div class="border-t border-b border-slate-100 py-2.5 space-y-1.5 font-mono text-xs">
        <div class="flex justify-between">
          <span class="text-slate-500 font-sans">Holding Period:</span>
          <span class="font-medium text-slate-800">${t.entry_date} → ${t.exit_date} (${t.days}d)</span>
        </div>
        <div class="flex justify-between">
          <span class="text-slate-500 font-sans">Portfolio Return:</span>
          <span class="font-bold ${retColor}">${fmtPct(t.portfolio_ret_pct)}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-slate-500 font-sans">Asset Price Move:</span>
          <span class="font-medium text-slate-800">${fmtPct(t.raw_ret_pct)} ($${t.entry_price} → $${t.exit_price})</span>
        </div>
        <div class="flex justify-between">
          <span class="text-slate-500 font-sans">Exit Rule:</span>
          <span class="font-medium text-slate-800 text-[11px]">${t.exit_reason || 'Target Profit Exit'}</span>
        </div>
      </div>

      <div>
        <h4 class="text-xs font-semibold text-slate-900 uppercase tracking-wider text-[11px]">Quantitative Edge:</h4>
        <p class="text-xs text-slate-600 mt-1 leading-relaxed">${meta.plainExplanation}</p>
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

      const winColor = b.win_rate >= 60 ? 'text-emerald-700' : 'text-slate-700';

      return `
        <div class="p-3 rounded-lg border border-slate-200 bg-white hover:border-brand-500 transition cursor-pointer" onclick="jumpToMotorOnChart('${mKey}')">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-slate-900">${meta.shortName}</span>
            <span class="text-[11px] font-mono font-bold text-brand-800 bg-brand-50 px-2 py-0.5 rounded border border-brand-100">${b.trades} trades</span>
          </div>
          <div class="grid grid-cols-3 gap-2 mt-2 font-mono text-xs text-slate-600">
            <div>
              <span class="text-[10px] text-slate-400 block font-sans">Win Rate</span>
              <span class="font-bold ${winColor}">${b.win_rate}%</span>
            </div>
            <div>
              <span class="text-[10px] text-slate-400 block font-sans">Net P&amp;L</span>
              <span class="font-bold text-slate-900">${fmtUSD(b.total_pnl_usd)}</span>
            </div>
            <div>
              <span class="text-[10px] text-slate-400 block font-sans">Profit Factor</span>
              <span class="font-bold text-slate-900">${b.profit_factor}</span>
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
      backgroundColor: '#ffffff',
      grid: { left: '48px', right: '16px', top: '32px', bottom: '28px' },
      tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>${p[0].seriesName}: +${p[0].value}%<br/>${p[1].seriesName}: ${p[1].value}%` },
      legend: { data: ['Mode 3 Élite', 'S&P 500'], top: 0, textStyle: { color: '#64748b', fontSize: 11 } },
      xAxis: { type: 'category', data: periods, axisLabel: { color: '#64748b', fontSize: 11 } },
      yAxis: { type: 'value', axisLabel: { formatter: '{value}%', color: '#64748b' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
      series: [
        { name: 'Mode 3 Élite', type: 'bar', data: m3Vals, itemStyle: { color: '#059669', borderRadius: [4, 4, 0, 0] } },
        { name: 'S&P 500', type: 'bar', data: spVals, itemStyle: { color: '#94a3b8', borderRadius: [4, 4, 0, 0] } },
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
      backgroundColor: '#ffffff',
      grid: { left: '60px', right: '16px', top: '24px', bottom: '28px' },
      tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}: $${Number(p[0].value).toLocaleString('en-US', { maximumFractionDigits: 0 })}` },
      xAxis: { type: 'category', data: ['P5 (Worst)', 'P25 (Cons)', 'P50 (Median)', 'P75 (Opt)', 'P95 (Extreme)'], axisLabel: { color: '#64748b', fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { formatter: (v) => '$' + Math.round(v / 1000) + 'k', color: '#64748b' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
      series: [
        {
          name: 'Ending Capital',
          type: 'bar',
          data: [p5, p25, p50, p75, p95],
          itemStyle: {
            color: function (params) {
              const colors = ['#f59e0b', '#10b981', '#059669', '#047857', '#064e3b'];
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
      backgroundColor: '#ffffff',
      grid: { left: '44px', right: '16px', top: '24px', bottom: '28px' },
      tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>Net CAGR: ${p[0].value}%` },
      xAxis: { type: 'category', data: fr.map((f) => f.scenario.split(' (')[0]), axisLabel: { color: '#64748b', fontSize: 11 } },
      yAxis: { type: 'value', min: 8, axisLabel: { formatter: '{value}%', color: '#64748b' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
      series: [
        {
          name: 'Net CAGR',
          type: 'line',
          data: fr.map((f) => f.cagr_pct),
          itemStyle: { color: '#059669' },
          lineStyle: { width: 2.5, color: '#059669' },
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

      const mColor = mVal >= 0 ? 'text-emerald-700 font-semibold' : 'text-red-700 font-semibold';
      const spColor = spVal >= 0 ? 'text-slate-800' : 'text-red-700';
      const alphaColor = alpha >= 0 ? 'text-emerald-700 font-bold' : 'text-red-700 font-bold';

      return `
        <tr class="hover:bg-slate-50 transition">
          <td class="py-2.5 px-4 font-bold text-slate-800">${y.year}</td>
          <td class="py-2.5 px-4 text-right ${mColor}">${fmtPct(mVal)}</td>
          <td class="py-2.5 px-4 text-right ${spColor}">${fmtPct(spVal)}</td>
          <td class="py-2.5 px-4 text-right ${alphaColor}">${fmtPct(alpha)}</td>
        </tr>
      `;
    })
    .join('');
}

// ============================================================================
// PORTFOLIO SIMULATOR (SUB-TAB 4)
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

// ============================================================================
// 725 TRADES TABLE
// ============================================================================
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
      const retColor = isWin ? 'text-emerald-700' : 'text-red-700';
      const dirCls = t.direction === 'LONG' ? 'text-emerald-800 bg-emerald-50' : 'text-red-800 bg-red-50';

      return `
        <tr class="hover:bg-slate-50 transition">
          <td class="py-2 px-3 text-slate-500 text-[11px]">${t.exit_date}</td>
          <td class="py-2 px-3 font-semibold text-slate-800">${t.engine_id}</td>
          <td class="py-2 px-3 font-bold text-slate-900">${t.symbol}</td>
          <td class="py-2 px-3"><span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${dirCls}">${t.direction}</span></td>
          <td class="py-2 px-3 text-right ${retColor} font-bold">${fmtPct(t.portfolio_ret_pct)}</td>
          <td class="py-2 px-3 text-right text-slate-700 font-bold">$${t.eq_at_exit.toFixed(2)}</td>
          <td class="py-2 px-3 text-slate-500 text-[11px] text-right">${t.days}d</td>
        </tr>
      `;
    })
    .join('');
}

// ============================================================================
// DAILY MARKET RADAR
// ============================================================================
function renderLiveScan() {
  if (!APP_DATA || !APP_DATA.live_scan) return;
  const live = APP_DATA.live_scan;

  const dateEl = document.getElementById('live-date-label');
  const badgeEl = document.getElementById('live-regime-badge');
  const detailEl = document.getElementById('live-vts-detail');
  const gridEl = document.getElementById('live-assets-grid');

  if (dateEl) dateEl.textContent = live.as_of_date || '--';
  if (badgeEl) badgeEl.textContent = live.vts_state || 'CONTANGO';
  if (detailEl) detailEl.textContent = `VIX: ${live.vix_close} | VIX3M: ${live.vix3m_close} | VTS Ratio: ${live.vts_ratio}`;

  if (gridEl && live.assets) {
    gridEl.innerHTML = live.assets
      .map((a) => {
        const isCore = a.core_weight_pct > 0;
        const trendCls = a.sma200_trend === 'BULL' ? 'text-emerald-700 font-bold' : 'text-red-700 font-bold';

        return `
          <div class="py-2 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="font-bold font-mono text-slate-900">${a.symbol}</span>
              <span class="text-[11px] text-slate-500">${ASSET_NAMES[a.symbol] || ''}</span>
            </div>
            <div class="flex items-center gap-4 text-[11px] font-mono">
              <span class="text-slate-600">Close: $${a.last_close}</span>
              <span class="${trendCls}">${a.sma200_trend}</span>
              <span class="font-bold ${isCore ? 'text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded' : 'text-slate-400'}">
                ${isCore ? a.core_weight_pct + '% Core' : '0%'}
              </span>
            </div>
          </div>
        `;
      })
      .join('');
  }
}

// ============================================================================
// BOT CONTROL CENTER (LIVE STATE & COMMANDS)
// ============================================================================
async function fetchLiveStatus(initForm = false) {
  try {
    const res = await fetch('/api/live/status');
    const data = await res.json();
    renderLiveControlCenter(data, initForm || !LIVE_CONFIG_INITIALIZED);
    LIVE_CONFIG_INITIALIZED = true;
  } catch (err) {
    console.error('Error fetching live bot status:', err);
  }
}

function renderLiveControlCenter(data, populateForm = false) {
  if (!data || !data.config || !data.state) return;
  const cfg = data.config;
  const state = data.state;
  const acct = state.account || {};
  const conn = data.broker_connection || { ok: true, message: '' };

  // 1. Header Badges
  const hdrDot = document.getElementById('hdr-status-dot');
  const hdrStatus = document.getElementById('hdr-status-text');
  const hdrBroker = document.getElementById('hdr-broker-text');
  const botRunning = cfg.bot_running !== false;

  if (hdrDot) hdrDot.className = `w-2 h-2 rounded-full ${botRunning ? 'bg-brand-600' : 'bg-amber-500'}`;
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

  // 2. Control Bar Badges
  const statusBadge = document.getElementById('pt-bot-status-badge');
  const toggleBtn = document.getElementById('btn-toggle-bot');
  if (statusBadge && toggleBtn) {
    if (botRunning) {
      statusBadge.textContent = 'ACTIVE (24/7)';
      statusBadge.className = 'px-2.5 py-0.5 rounded text-xs font-semibold bg-brand-50 text-brand-800 border border-brand-100 font-mono';
      toggleBtn.textContent = 'Pause Bot';
      toggleBtn.className = 'px-3.5 py-2 rounded-lg text-xs font-semibold bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 transition';
    } else {
      statusBadge.textContent = 'PAUSED';
      statusBadge.className = 'px-2.5 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 font-mono';
      toggleBtn.textContent = 'Resume Bot';
      toggleBtn.className = 'px-3.5 py-2 rounded-lg text-xs font-semibold bg-brand-700 hover:bg-brand-800 text-white transition';
    }
  }

  const modeBadge = document.getElementById('pt-mode-badge');
  if (modeBadge) {
    modeBadge.textContent = cfg.execution_mode === 'AUTO_100' ? '100% Automated Mode' : 'Copilot Mode';
  }

  const brokerBadge = document.getElementById('pt-broker-badge');
  if (brokerBadge) {
    brokerBadge.textContent = cfg.broker_provider === 'ALPACA_PAPER' ? 'Alpaca Paper' : 'Local Paper';
  }

  const connMsg = document.getElementById('pt-connection-msg');
  if (connMsg) {
    connMsg.innerHTML = `<span class="${conn.ok ? 'text-brand-600' : 'text-amber-600'} font-bold">●</span> ${conn.message}`;
  }

  const lastScan = document.getElementById('pt-last-scan');
  if (lastScan) lastScan.textContent = state.last_scan_time || '--';

  const schedLabel = document.getElementById('pt-sched-label');
  if (schedLabel) schedLabel.textContent = (cfg.schedule_time_cet || '21:55') + ' CET';

  // 3. Copilot Banner
  const copilotBanner = document.getElementById('pt-copilot-banner');
  const copilotDesc = document.getElementById('pt-copilot-desc');
  const pending = state.pending_confirmations || [];
  if (copilotBanner && copilotDesc) {
    if (pending.length > 0) {
      const p = pending[0];
      const syms = Object.keys(p.targets || {})
        .map((s) => `${s} (${(p.targets[s].weight * 100).toFixed(0)}%)`)
        .join(', ');
      copilotDesc.textContent = `Pending proposal (${p.trigger_source}): Target Allocation → ${syms}`;
      copilotBanner.classList.remove('hidden');
    } else {
      copilotBanner.classList.add('hidden');
    }
  }

  // 4. Financial Metric Cards
  const totalEq = Number(acct.total_equity_usd || 10000);
  const initialCap = Number(acct.initial_capital || 10000);
  const totalRet = Number(acct.total_return_pct || 0);

  const eqEl = document.getElementById('pt-total-equity');
  if (eqEl) eqEl.textContent = fmtUSD(totalEq);

  const retEl = document.getElementById('pt-total-ret');
  if (retEl) {
    retEl.textContent = `Return: ${fmtPct(totalRet)} (Base: ${fmtUSD(initialCap)})`;
    retEl.className = `text-xs font-mono mt-0.5 font-semibold ${totalRet >= 0 ? 'text-emerald-700' : 'text-red-700'}`;
  }

  const posValEl = document.getElementById('pt-pos-value');
  if (posValEl) posValEl.textContent = fmtUSD(acct.positions_value_usd || 0);

  const positions = state.positions || [];
  const posCountEl = document.getElementById('pt-pos-count');
  if (posCountEl) posCountEl.textContent = `${positions.length} active positions`;

  const cashEl = document.getElementById('pt-cash-value');
  if (cashEl) cashEl.textContent = fmtUSD(acct.cash_usd || 0);

  const ddEl = document.getElementById('pt-dd-value');
  if (ddEl) ddEl.textContent = `${Number(acct.current_dd_pct || 0).toFixed(2)}%`;

  const ddLimitEl = document.getElementById('pt-dd-limit-label');
  if (ddLimitEl) ddLimitEl.textContent = `Kill switch limit: ${cfg.daily_kill_switch_dd_pct || -8.0}%`;

  // 5. Open Positions Table
  const posTbody = document.getElementById('pt-positions-tbody');
  if (posTbody) {
    if (positions.length === 0) {
      posTbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-slate-400 font-sans">100% in cash liquidity. Click "Scan & Sync Now" to evaluate daily entry rules.</td></tr>`;
    } else {
      posTbody.innerHTML = positions
        .map((p) => {
          const dirCls = p.direction === 'LONG' ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-800';
          return `
            <tr class="hover:bg-slate-50 transition">
              <td class="py-2.5 px-3 font-bold text-slate-900">${p.broker_symbol} <span class="text-[11px] text-slate-400 font-sans">(${p.internal_symbol})</span></td>
              <td class="py-2.5 px-3"><span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${dirCls}">${p.direction}</span></td>
              <td class="py-2.5 px-3 font-sans text-xs text-slate-700">${p.motor}</td>
              <td class="py-2.5 px-3 text-right text-slate-700">${p.qty}</td>
              <td class="py-2.5 px-3 text-right text-slate-700">$${p.current_price}</td>
              <td class="py-2.5 px-3 text-right font-bold text-slate-900">${fmtUSD(p.market_value_usd)}</td>
              <td class="py-2.5 px-3 text-right font-bold text-brand-800">${p.weight_pct}%</td>
            </tr>
          `;
        })
        .join('');
    }
  }

  // 6. Orders Table
  const orders = state.orders_history || [];
  const ordTbody = document.getElementById('pt-orders-tbody');
  if (ordTbody) {
    if (orders.length === 0) {
      ordTbody.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-slate-400 font-sans">No orders executed yet.</td></tr>`;
    } else {
      ordTbody.innerHTML = orders
        .slice(0, 25)
        .map((o) => {
          const isBuy = o.side.includes('BUY');
          const sideCls = isBuy ? 'text-emerald-700' : 'text-amber-700';
          return `
            <tr class="hover:bg-slate-50 transition">
              <td class="py-2 px-3 text-slate-500 text-[11px]">${o.time}</td>
              <td class="py-2 px-3 font-bold ${sideCls}">${o.side}</td>
              <td class="py-2 px-3 font-bold text-slate-900">${o.symbol}</td>
              <td class="py-2 px-3 text-right text-slate-700">${fmtUSD(o.notional_usd)}</td>
              <td class="py-2 px-3 font-sans text-[11px] text-slate-600">${o.motor}</td>
              <td class="py-2 px-3"><span class="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 text-[10px] font-bold border border-emerald-100">${o.status}</span></td>
            </tr>
          `;
        })
        .join('');
    }
  }

  // 7. System Logs Console
  const logs = state.logs || [];
  const logsBox = document.getElementById('pt-logs-box');
  if (logsBox) {
    logsBox.innerHTML = logs
      .slice(0, 30)
      .map((l) => {
        let col = 'text-slate-700';
        if (l.level === 'SUCCESS') col = 'text-emerald-800 font-semibold';
        else if (l.level === 'WARN') col = 'text-amber-800 font-semibold';
        else if (l.level === 'ERROR') col = 'text-red-800 font-bold';
        return `<div><span class="text-slate-400">[${l.time}]</span> <span class="${col}">${l.msg}</span></div>`;
      })
      .join('');
  }

  // 8. Populate Form Inputs
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
async function triggerLiveAction(actionName, simulateMotor = null) {
  try {
    const res = await fetch('/api/live/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: actionName, simulate_motor: simulateMotor }),
    });
    const data = await res.json();
    if (data.status) {
      renderLiveControlCenter(data.status, false);
    }
    if (data.result && data.result.message) {
      showConfigFeedback(data.result.message, actionName.includes('TEST_'));
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
      renderLiveControlCenter(data.status, true);
    }
    const msg = 'Configuration saved and hot-reloaded.';
    showConfigFeedback(msg, fromModal);
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
