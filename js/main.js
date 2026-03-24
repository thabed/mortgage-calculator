/**
 * main.js
 * Entry point — imports all modules and orchestrates the application.
 *
 * Module graph:
 *   main.js
 *   ├── inputs.js   (read form values, UI toggles)
 *   ├── calc.js     (pure financial calculations)
 *   ├── charts.js   (Chart.js wrappers)
 *   └── ui.js       (DOM rendering: cards, verdict, timeline…)
 */

import { getInputs, updateCurrentTypeUI, updateNewRateTypeUI, updateRate2TypeUI, wireInputs, initToggle } from './inputs.js';
import { calcSingleSwitch, calcDoubleSwitch } from './calc.js';
import { effectiveRate } from './calc.js';
import { renderAllCharts } from './charts.js';
import {
  updateStickyBar,
  renderSummaryCards,
  renderVerdict,
  renderRateBars,
  renderComparisonTable,
  renderTimeline,
  renderTabNav,
} from './ui.js';

/* ─────────────────────────────────────────────────────────────────────────────
   APPLICATION STATE
───────────────────────────────────────────────────────────────────────────── */

let activeTab = 'single';
let show2nd   = false;

/* ─────────────────────────────────────────────────────────────────────────────
   MAIN CALCULATE
───────────────────────────────────────────────────────────────────────────── */

function calculate() {
  const p = getInputs();

  // ── Core calculations ────────────────────────────────────────────────────
  const single = calcSingleSwitch(p);
  const dbl    = show2nd ? calcDoubleSwitch(p) : null;

  const { effCurrent, effNew, totalMonths, bestNet } = single;
  const rateDiff1     = effCurrent - effNew;
  const annualSaving1 = p.principal * rateDiff1;
  const costNow       = single.rows[0].switchCost;
  const breakEvenMonths = annualSaving1 > 0
    ? costNow / (annualSaving1 / 12)
    : Infinity;

  // ── Summary cards ────────────────────────────────────────────────────────
  renderSummaryCards({
    rateDiff:        rateDiff1,
    annualSaving:    annualSaving1,
    costNow,
    breakEvenMonths,
    bestNet,
    totalMonths,
  });

  // ── Verdict box ──────────────────────────────────────────────────────────
  const { verdictLabel = '—', verdictClass = '' } = renderVerdict({
    single, dbl, show2nd, p,
  }) || {};

  // ── Sticky bar ───────────────────────────────────────────────────────────
  updateStickyBar({
    annualSaving:    annualSaving1,
    costNow,
    breakEvenMonths,
    bestNet,
    verdictLabel,
    verdictClass,
  });

  // ── Rate comparison visual ───────────────────────────────────────────────
  renderRateBars({ p, single, dbl, show2nd });

  // ── Strategy comparison table ────────────────────────────────────────────
  renderComparisonTable({ p, single, dbl, show2nd });

  // ── Charts ───────────────────────────────────────────────────────────────
  renderAllCharts(p, single, dbl, breakEvenMonths);

  // ── Tab navigation ───────────────────────────────────────────────────────
  renderTabNav({
    show2nd,
    dbl,
    activeTab,
    onTabChange: (tab) => {
      activeTab = tab;
      calculate();
    },
  });

  // ── Timeline ─────────────────────────────────────────────────────────────
  renderTimeline({ single, dbl, activeTab });
}

/* ─────────────────────────────────────────────────────────────────────────────
   BOOTSTRAP
───────────────────────────────────────────────────────────────────────────── */

// Initialise type-dependent field visibility
updateCurrentTypeUI();
updateNewRateTypeUI();
updateRate2TypeUI();

// Attach type-select change handlers
document.getElementById('currentType').addEventListener('change', () => {
  updateCurrentTypeUI(); calculate();
});
document.getElementById('newRateType').addEventListener('change', () => {
  updateNewRateTypeUI(); calculate();
});
document.getElementById('rateType2').addEventListener('change', () => {
  updateRate2TypeUI(); calculate();
});

// Second-switch toggle
const { getShow2nd } = initToggle((isOn) => {
  show2nd = isOn;
  if (!isOn) activeTab = 'single';
  calculate();
});

// Wire all inputs → recalculate
wireInputs(calculate);

// Initial render
calculate();
