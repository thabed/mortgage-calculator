/**
 * ui.js
 * All DOM-writing functions: summary cards, verdict, rate bars,
 * comparison table, timeline rows, sticky bar.
 */

import { fmt, fmtShort } from './utils.js';
import { effectiveRate, buildScenarios } from './calc.js';

/* ─────────────────────────────────────────────────────────────────────────────
   STICKY BAR
───────────────────────────────────────────────────────────────────────────── */

export function updateStickyBar({ annualSaving, costNow, breakEvenMonths, bestNet, verdictLabel, verdictClass }) {
  set('sAnnual',  fmtShort(annualSaving),  annualSaving > 0 ? 'pos' : 'neg');
  set('sCost',    fmt(costNow),            'neg');
  set('sBreak',   breakEvenMonths === Infinity ? '∞' : breakEvenMonths.toFixed(1) + ' mo', 'neu');
  set('sNet',     fmtShort(bestNet),       bestNet > 0 ? 'pos' : 'neg');
  set('sVerdict', verdictLabel,            verdictClass);

  function set(id, text, cls) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    el.className   = 'sticky-val ' + cls;
  }
}

/* ─────────────────────────────────────────────────────────────────────────────
   SUMMARY CARDS
───────────────────────────────────────────────────────────────────────────── */

export function renderSummaryCards({ rateDiff, annualSaving, costNow, breakEvenMonths, bestNet, totalMonths }) {
  const el = document.getElementById('summaryCards');
  if (!el) return;

  el.innerHTML = `
    <div class="card">
      <div class="card-label">Annual saving (Option A)</div>
      <div class="card-value ${rateDiff > 0 ? 'positive' : 'negative'}">${fmt(annualSaving)}</div>
      <div class="card-sub">${(rateDiff * 100).toFixed(2)}% effective rate diff</div>
    </div>
    <div class="card">
      <div class="card-label">Cost to switch today</div>
      <div class="card-value negative">${fmt(costNow)}</div>
      <div class="card-sub">Penalty + ${fmt(document.getElementById('setupFee')?.value || 0)} fee</div>
    </div>
    <div class="card">
      <div class="card-label">Break-even (Option A)</div>
      <div class="card-value ${breakEvenMonths <= totalMonths ? 'neutral' : 'negative'}">
        ${breakEvenMonths === Infinity ? '∞' : breakEvenMonths.toFixed(1) + ' mo'}
      </div>
      <div class="card-sub">${breakEvenMonths <= totalMonths ? '✓ Within fixed period' : '✗ After fixed period'}</div>
    </div>
    <div class="card">
      <div class="card-label">Best net gain (Option A)</div>
      <div class="card-value ${bestNet > 0 ? 'positive' : 'negative'}">${fmtShort(bestNet)}</div>
      <div class="card-sub">Over ${totalMonths}-month window</div>
    </div>
  `;
}

/* ─────────────────────────────────────────────────────────────────────────────
   VERDICT BOX
───────────────────────────────────────────────────────────────────────────── */

export function renderVerdict({ single, dbl, show2nd, p }) {
  const box   = document.getElementById('verdictBox');
  const title = document.getElementById('verdictTitle');
  const text  = document.getElementById('verdictText');
  if (!box) return;

  const { effCurrent, effNew, bestNet, firstPositive, bestMonth, totalMonths, monthlySaving } = single;
  const rateDiff1     = effCurrent - effNew;
  const annualSaving1 = p.principal * rateDiff1;
  const costNow       = single.rows[0].switchCost;
  const breakEvenMonths = annualSaving1 > 0 ? costNow / (annualSaving1 / 12) : Infinity;

  let verdictLabel = '—';
  let verdictClass = '';

  if (!show2nd || !dbl) {
    if (rateDiff1 <= 0) {
      _setVerdict(box, title, text, 'no-benefit',
        '✗ No benefit to switching',
        `The effective rate on Option A (<strong>${(effNew * 100).toFixed(2)}%</strong>) is not lower than your current effective rate (<strong>${(effCurrent * 100).toFixed(2)}%</strong>). Stay on your current mortgage.`
      );
      verdictLabel = 'Stay'; verdictClass = 'neg';

    } else if (firstPositive === -1) {
      _setVerdict(box, title, text, 'no-benefit',
        '✗ Not worth switching in this window',
        `Savings of <strong>${fmt(annualSaving1)}/yr</strong> never fully offset switching costs of <strong>${fmt(costNow)}</strong> within your ${p.yearsLeft}-year window. Consider waiting until the penalty decays further.`
      );
      verdictLabel = 'Wait'; verdictClass = 'warn';

    } else if (firstPositive === 0) {
      _setVerdict(box, title, text, '',
        '✓ Switch now — makes sense immediately',
        `Costs <strong>${fmt(costNow)}</strong> today, saves <strong>${fmt(annualSaving1)}/yr</strong>. Break-even in <strong>${breakEvenMonths.toFixed(1)} months</strong>. Net gain over the fixed period: <strong>${fmt(bestNet)}</strong>.<br><br>Monthly payment drops by approximately <strong>${fmt(monthlySaving)}/month</strong>.`
      );
      verdictLabel = 'Switch now ✓'; verdictClass = 'pos';

    } else {
      _setVerdict(box, title, text, 'warn-verdict',
        `⚠ Wait until month ${firstPositive} to switch`,
        `Switching today costs <strong>${fmt(costNow)}</strong> — slightly too much relative to savings. It starts making sense at month <strong>${firstPositive}</strong> as the penalty decays. Best switch point: month <strong>${bestMonth}</strong>, netting <strong>${fmt(bestNet)}</strong>.`
      );
      verdictLabel = `Wait → M${firstPositive}`; verdictClass = 'warn';
    }

  } else {
    const scenarios = buildScenarios(p, single, dbl, totalMonths);
    const sorted    = [...scenarios].sort((a, b) => b.net - a.net);
    const best      = sorted[0];
    const second    = sorted[1];
    const gap       = best.net - second.net;
    const lines     = scenarios.map(s =>
      `<span style="color:${s.color}">●</span> <strong>${s.label}:</strong> ${s.net >= 0 ? '+' : ''}${fmt(s.net)}`
    ).join('<br>');

    _setVerdict(box, title, text,
      best.net > 0 ? '' : 'no-benefit',
      best.net > 0 ? `✓ Best: ${best.label}` : '✗ No strategy produces a net gain',
      `${lines}<br><br>Best strategy leads by <strong>${fmt(gap)}</strong> over the next-best option.`
    );
    verdictLabel = best.label.length > 22 ? best.label.slice(0, 22) + '…' : best.label;
    verdictClass = best.net > 0 ? 'pos' : 'neg';
  }

  return { verdictLabel, verdictClass };
}

function _setVerdict(box, title, text, modifier, titleText, bodyHtml) {
  box.className  = 'verdict' + (modifier ? ' ' + modifier : '');
  title.textContent = titleText;
  text.innerHTML = bodyHtml;
}

/* ─────────────────────────────────────────────────────────────────────────────
   RATE COMPARISON BARS
───────────────────────────────────────────────────────────────────────────── */

export function renderRateBars({ p, single, dbl, show2nd }) {
  const effCurrent = single.effCurrent;
  const effNew     = single.effNew;
  const effB       = dbl ? effectiveRate(p.rate2, p.rateType2, p.inflationB) : null;

  const maxEff = Math.max(
    effCurrent,
    effNew,
    effB ?? 0
  ) * 1.12;

  const rows = [
    { label: 'Current',  eff: effCurrent, type: p.currentType, color: 'var(--red)' },
    { label: 'Option A', eff: effNew,     type: p.newRateType, color: 'var(--accent3)' },
    ...(show2nd && dbl ? [{ label: 'Option B', eff: effB, type: p.rateType2, color: 'var(--purple)' }] : []),
  ];

  document.getElementById('rateCompare').innerHTML = rows.map(r => `
    <div class="rate-row">
      <span class="rate-label">${r.label}</span>
      <div class="rate-bar-wrap">
        <div class="rate-bar" style="width:${((r.eff / maxEff) * 100).toFixed(1)}%;background:${r.color}"></div>
      </div>
      <span class="rate-val" style="color:${r.color}">${(r.eff * 100).toFixed(2)}%</span>
    </div>
  `).join('');

  const typeChip = (type, suffix) => {
    const labels = { index: `⚠ Index-linked (${suffix})`, variable: `~ Variable (${suffix})`, fixed: `🔒 Fixed (${suffix})` };
    return `<span class="chip ${type}">${labels[type] || type}</span>`;
  };

  document.getElementById('loanChips').innerHTML =
    typeChip(p.currentType, 'current') +
    typeChip(p.newRateType, 'A') +
    (show2nd && dbl ? typeChip(p.rateType2, 'B') : '');
}

/* ─────────────────────────────────────────────────────────────────────────────
   STRATEGY COMPARISON TABLE
───────────────────────────────────────────────────────────────────────────── */

export function renderComparisonTable({ p, single, dbl, show2nd }) {
  const section = document.getElementById('compSection');
  if (!show2nd || !dbl) { section.style.display = 'none'; return; }
  section.style.display = 'block';

  const { totalMonths } = single;
  const scenarios = buildScenarios(p, single, dbl, totalMonths);
  const sorted    = [...scenarios].sort((a, b) => b.net - a.net);
  const best      = sorted[0];

  let html = `<thead><tr>
    <th>Strategy</th><th>Net gain</th><th>Total switching cost</th><th>vs best</th>
  </tr></thead><tbody>`;

  sorted.forEach(s => {
    const isBest = s.label === best.label;
    const vs     = isBest ? '—' : (s.net - best.net >= 0 ? '+' : '') + fmt(s.net - best.net);
    const netCol = s.net > 0 ? 'var(--green)' : s.net < 0 ? 'var(--red)' : 'var(--muted)';
    html += `
      <tr class="${isBest ? 'best-row' : ''}">
        <td><span class="sdot" style="background:${s.color}"></span>${s.label}${isBest ? ' ★' : ''}</td>
        <td style="color:${netCol}">${s.net >= 0 ? '+' : ''}${fmt(s.net)}</td>
        <td style="color:var(--muted)">${s.cost > 0 ? fmt(s.cost) : '—'}</td>
        <td style="color:${isBest ? 'var(--muted)' : 'var(--red)'};font-size:11px">${vs}</td>
      </tr>`;
  });

  html += '</tbody>';
  document.getElementById('compTable').innerHTML = html;
}

/* ─────────────────────────────────────────────────────────────────────────────
   TIMELINE
───────────────────────────────────────────────────────────────────────────── */

export function renderTimeline({ single, dbl, activeTab }) {
  const useDouble  = activeTab === 'double' && dbl;
  const tRows      = useDouble ? dbl.rows : single.rows;
  const totalMonths = single.totalMonths;
  const step       = totalMonths <= 24 ? 1 : totalMonths <= 60 ? 3 : 6;
  const maxVal     = Math.max(...tRows.map(r => Math.abs(r.net)), 1);

  let html = '';

  for (let m = 0; m <= totalMonths; m += step) {
    const r        = tRows[Math.min(m, tRows.length - 1)];
    const net      = r.net;
    const positive = net > 0;
    const barW     = (Math.abs(net) / maxVal * 100).toFixed(1);
    const barColor = positive ? 'var(--green)' : 'var(--red)';

    const isSwitch2   = useDouble && m === dbl.M2;
    const isBreakeven = !useDouble && single.firstPositive !== -1 && m === single.firstPositive;
    const isOptimal   = !useDouble && m === single.bestMonth && single.bestNet > 0;

    const costDisplay = useDouble
      ? (m === 0 ? fmt(dbl.cost1) : isSwitch2 ? fmt(dbl.cost2) : '—')
      : fmt(tRows[Math.min(m, tRows.length - 1)].switchCost || 0);

    const labelColor = isOptimal   ? 'var(--accent2)'
      :                isSwitch2   ? 'var(--purple)'
      :                              'var(--muted)';

    const rowClass = [
      isBreakeven ? 'breakeven'   : '',
      isSwitch2   ? 'switch2-row' : '',
    ].filter(Boolean).join(' ');

    html += `
      <div class="timeline-row ${rowClass}">
        <span style="color:${labelColor}">M${m}${isOptimal ? ' ★' : ''}${isSwitch2 ? ' ⇄B' : ''}</span>
        <div class="bar-cell">
          <div class="bar-bg"><div class="bar-fill" style="width:${barW}%;background:${barColor}"></div></div>
        </div>
        <span style="color:var(--muted);font-size:11px">${costDisplay}</span>
        <span><span class="tag ${positive ? 'gain' : 'loss'}">${positive ? 'Gain' : 'Loss'}</span></span>
        <span style="color:${positive ? 'var(--green)' : 'var(--red)'};font-size:11px">${net >= 0 ? '+' : ''}${fmt(net)}</span>
      </div>`;
  }

  document.getElementById('timelineRows').innerHTML = html;
}

/* ─────────────────────────────────────────────────────────────────────────────
   TAB NAV
───────────────────────────────────────────────────────────────────────────── */

export function renderTabNav({ show2nd, dbl, activeTab, onTabChange }) {
  const nav = document.getElementById('tabNav');
  if (!nav) return;

  if (show2nd && dbl) {
    nav.innerHTML = `
      <button class="tab-btn ${activeTab === 'single' ? 'active' : ''}" data-tab="single">
        Option A timeline
      </button>
      <button class="tab-btn tab-s2 ${activeTab === 'double' ? 'active' : ''}" data-tab="double">
        Option A → B timeline
      </button>
    `;
    nav.querySelectorAll('.tab-btn').forEach(btn =>
      btn.addEventListener('click', () => onTabChange(btn.dataset.tab))
    );
  } else {
    nav.innerHTML = '';
  }
}
