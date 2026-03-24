/**
 * charts.js
 * Builds and updates all four Chart.js visualisations.
 */

import { fmtAxis, fmt } from './utils.js';
import { effectiveRate, monthlyPayment, totalInterestEstimate } from './calc.js';

/* ─────────────────────────────────────────────────────────────────────────────
   SHARED CHART DEFAULTS
───────────────────────────────────────────────────────────────────────────── */

const FONT_MONO = "'DM Mono', monospace";
const FONT_SERIF = "'DM Serif Display', serif";

const SHARED_SCALES = {
  x: {
    ticks: { color: '#8b949e', font: { family: FONT_MONO, size: 10 } },
    grid:  { color: 'rgba(255,255,255,0.04)' },
  },
  y: {
    ticks: {
      color: '#8b949e',
      font:  { family: FONT_MONO, size: 10 },
      callback: v => fmtAxis(v) + ' kr',
    },
    grid: { color: 'rgba(255,255,255,0.04)' },
  },
};

const SHARED_TOOLTIP = {
  backgroundColor: '#161b22',
  borderColor:     '#21262d',
  borderWidth:     1,
  titleColor:      '#e6edf3',
  bodyColor:       '#8b949e',
  titleFont: { family: FONT_SERIF, size: 13 },
  bodyFont:  { family: FONT_MONO,  size: 11 },
};

const SHARED_LEGEND = {
  labels: {
    color:     '#8b949e',
    font:      { family: FONT_MONO, size: 10 },
    boxWidth:  10,
  },
};

function baseOptions(extraPlugins = {}) {
  return {
    responsive:          true,
    maintainAspectRatio: false,
    plugins: {
      legend:  SHARED_LEGEND,
      tooltip: { ...SHARED_TOOLTIP, ...extraPlugins.tooltip },
    },
    scales: SHARED_SCALES,
  };
}

/* ─────────────────────────────────────────────────────────────────────────────
   INSTANCE REGISTRY  (so we can destroy before re-creating)
───────────────────────────────────────────────────────────────────────────── */

const registry = {};

function destroyChart(id) {
  if (registry[id]) { registry[id].destroy(); delete registry[id]; }
}

/* ─────────────────────────────────────────────────────────────────────────────
   LABEL HELPERS
───────────────────────────────────────────────────────────────────────────── */

function makeLabels(totalMonths, step) {
  const labels = [];
  for (let m = 0; m <= totalMonths; m += step) labels.push('M' + m);
  return labels;
}

function stepFor(totalMonths) {
  if (totalMonths <= 24) return 1;
  if (totalMonths <= 60) return 3;
  return 6;
}

/* ─────────────────────────────────────────────────────────────────────────────
   1. CUMULATIVE NET SAVINGS
───────────────────────────────────────────────────────────────────────────── */

export function renderCumulativeChart(single, dbl) {
  const { totalMonths } = single;
  const step   = stepFor(totalMonths);
  const labels = makeLabels(totalMonths, step);

  const singleData = labels.map(l => {
    const m = parseInt(l.slice(1));
    return single.rows[Math.min(m, single.rows.length - 1)].net;
  });

  const datasets = [
    {
      label:           'Switch A (now)',
      data:            singleData,
      borderColor:     '#58a6ff',
      backgroundColor: 'rgba(88,166,255,0.08)',
      borderWidth:     2,
      fill:            true,
      tension:         0.3,
      pointRadius:     0,
    },
  ];

  if (dbl) {
    datasets.push({
      label:           'Switch A → B',
      data:            labels.map(l => {
        const m = parseInt(l.slice(1));
        return dbl.rows[Math.min(m, dbl.rows.length - 1)].net;
      }),
      borderColor:     '#bc8cff',
      backgroundColor: 'rgba(188,140,255,0.06)',
      borderWidth:     2,
      fill:            true,
      tension:         0.3,
      pointRadius:     0,
    });
  }

  destroyChart('chartCumulative');
  registry['chartCumulative'] = new Chart(
    document.getElementById('chartCumulative'),
    {
      type: 'line',
      data: { labels, datasets },
      options: baseOptions({
        tooltip: {
          callbacks: {
            label: ctx => ' ' + ctx.dataset.label + ': ' + fmtAxis(ctx.raw) + ' kr',
          },
        },
      }),
    }
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   2. MONTHLY PAYMENT COMPARISON
───────────────────────────────────────────────────────────────────────────── */

export function renderPaymentChart(p, single, dbl) {
  const effCurrent = single.effCurrent;
  const effNew     = single.effNew;
  const mpCurrent  = monthlyPayment(p.principal, effCurrent, p.totalTerm);
  const mpA        = monthlyPayment(p.principal, effNew,     p.totalTerm);
  const mpB        = dbl
    ? monthlyPayment(p.principal, effectiveRate(p.rate2, p.rateType2, p.inflationB), p.totalTerm)
    : null;

  const labels = ['Current', 'Option A', ...(dbl ? ['Option B'] : [])];
  const data   = [mpCurrent, mpA,        ...(dbl ? [mpB]        : [])];
  const bgCol  = ['rgba(248,81,73,0.65)', 'rgba(88,166,255,0.65)', 'rgba(188,140,255,0.65)'];
  const bdCol  = ['#f85149', '#58a6ff', '#bc8cff'];

  destroyChart('chartPayments');
  registry['chartPayments'] = new Chart(
    document.getElementById('chartPayments'),
    {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label:           'Monthly payment',
          data,
          backgroundColor: bgCol.slice(0, data.length),
          borderColor:     bdCol.slice(0, data.length),
          borderWidth:     1,
          borderRadius:    4,
        }],
      },
      options: {
        ...baseOptions({
          tooltip: { callbacks: { label: ctx => '  ' + fmt(ctx.raw) + '/month' } },
        }),
        plugins: {
          ...baseOptions().plugins,
          legend: { display: false },
          tooltip: {
            ...SHARED_TOOLTIP,
            callbacks: { label: ctx => '  ' + fmt(ctx.raw) + ' /month' },
          },
        },
      },
    }
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   3. BREAK-EVEN ZOOM
───────────────────────────────────────────────────────────────────────────── */

export function renderBreakevenChart(single, breakEvenMonths) {
  const { totalMonths } = single;
  const beMax   = Math.min(totalMonths, Math.ceil(Math.min(breakEvenMonths, totalMonths) * 1.6) + 6);
  const beStep  = totalMonths <= 36 ? 1 : 2;
  const labels  = [];
  const data    = [];

  for (let m = 0; m <= beMax; m += beStep) {
    labels.push('M' + m);
    data.push(single.rows[Math.min(m, single.rows.length - 1)].net);
  }

  const zeroLine = new Array(labels.length).fill(0);

  destroyChart('chartBreakeven');
  registry['chartBreakeven'] = new Chart(
    document.getElementById('chartBreakeven'),
    {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label:           'Net position',
            data,
            borderColor:     '#3fb950',
            backgroundColor: 'rgba(63,185,80,0.08)',
            borderWidth:     2,
            fill:            true,
            tension:         0.3,
            pointRadius:     0,
          },
          {
            label:       'Break-even line',
            data:        zeroLine,
            borderColor: 'rgba(255,255,255,0.15)',
            borderWidth: 1,
            borderDash:  [4, 3],
            pointRadius: 0,
            fill:        false,
          },
        ],
      },
      options: baseOptions({
        tooltip: {
          callbacks: {
            label: ctx => ' ' + ctx.dataset.label + ': ' + fmtAxis(ctx.raw) + ' kr',
          },
        },
      }),
    }
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   4. TOTAL INTEREST OVER LOAN LIFE
───────────────────────────────────────────────────────────────────────────── */

export function renderInterestChart(p, single, dbl) {
  const effCurrent = single.effCurrent;
  const effNew     = single.effNew;
  const tiCurrent  = totalInterestEstimate(p.principal, effCurrent, p.totalTerm);
  const tiA        = totalInterestEstimate(p.principal, effNew,     p.totalTerm);
  const tiB        = dbl
    ? totalInterestEstimate(p.principal, effectiveRate(p.rate2, p.rateType2, p.inflationB), p.totalTerm)
    : null;

  const labels = ['Current', 'Option A', ...(dbl ? ['Option B'] : [])];
  const data   = [tiCurrent, tiA,        ...(dbl ? [tiB]        : [])];
  const bgCol  = ['rgba(248,81,73,0.6)', 'rgba(88,166,255,0.6)', 'rgba(188,140,255,0.6)'];
  const bdCol  = ['#f85149', '#58a6ff', '#bc8cff'];

  destroyChart('chartInterest');
  registry['chartInterest'] = new Chart(
    document.getElementById('chartInterest'),
    {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label:           'Total interest',
          data,
          backgroundColor: bgCol.slice(0, data.length),
          borderColor:     bdCol.slice(0, data.length),
          borderWidth:     1,
          borderRadius:    4,
        }],
      },
      options: {
        ...baseOptions(),
        plugins: {
          legend: { display: false },
          tooltip: {
            ...SHARED_TOOLTIP,
            callbacks: { label: ctx => '  Total interest: ' + fmt(ctx.raw) },
          },
        },
      },
    }
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   RENDER ALL CHARTS AT ONCE
───────────────────────────────────────────────────────────────────────────── */

export function renderAllCharts(p, single, dbl, breakEvenMonths) {
  renderCumulativeChart(single, dbl);
  renderPaymentChart(p, single, dbl);
  renderBreakevenChart(single, breakEvenMonths);
  renderInterestChart(p, single, dbl);
}
