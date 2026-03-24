/**
 * calc.js
 * Core financial calculation engine for the Mortgage Switch Calculator.
 *
 * All rate inputs are already decimals (e.g. 0.0875 for 8.75%).
 * "Effective rate" for index-linked loans = nominal rate + inflation.
 */

/* ─────────────────────────────────────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────────────────────────────────────── */

/**
 * Compute the effective annual rate.
 * For index-linked loans the inflation premium is added to the nominal rate.
 *
 * @param {number} nominalRate  - Annual nominal rate (decimal)
 * @param {string} type         - "fixed" | "variable" | "index"
 * @param {number} inflation    - Annual inflation rate (decimal), used for "index"
 * @returns {number} Effective annual rate (decimal)
 */
export function effectiveRate(nominalRate, type, inflation) {
  return type === 'index' ? nominalRate + inflation : nominalRate;
}

/**
 * Monthly annuity payment given principal, annual rate, and term in years.
 *
 * @param {number} principal
 * @param {number} annualRate   - decimal (e.g. 0.0875)
 * @param {number} totalYears
 * @returns {number} Monthly payment amount
 */
export function monthlyPayment(principal, annualRate, totalYears) {
  if (annualRate <= 0) return principal / (totalYears * 12);
  const r = annualRate / 12;
  const n = totalYears * 12;
  return principal * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1);
}

/**
 * Estimate total interest paid over the full life of a loan.
 *
 * @param {number} principal
 * @param {number} effRate    - Effective annual rate (decimal)
 * @param {number} totalYears
 * @returns {number} Total interest
 */
export function totalInterestEstimate(principal, effRate, totalYears) {
  const mp = monthlyPayment(principal, effRate, totalYears);
  return mp * totalYears * 12 - principal;
}

/**
 * Outstanding principal after monthsElapsed payments on a standard annuity loan.
 * Allows penalty and savings calculations to use the declining balance at each
 * potential switch month rather than the original principal.
 *
 * @param {number} principal
 * @param {number} annualRate    - decimal (e.g. 0.0875)
 * @param {number} totalYears    - remaining amortisation term at the start
 * @param {number} monthsElapsed
 * @returns {number} Outstanding balance (≥ 0)
 */
export function remainingBalance(principal, annualRate, totalYears, monthsElapsed) {
  if (monthsElapsed <= 0) return principal;
  if (annualRate <= 0) {
    const n = Math.round(totalYears * 12);
    return Math.max(0, principal * (1 - monthsElapsed / n));
  }
  const r  = annualRate / 12;
  const n  = Math.round(totalYears * 12);
  const mp = principal * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1);
  return Math.max(0, principal * Math.pow(1 + r, monthsElapsed)
                   - mp * (Math.pow(1 + r, monthsElapsed) - 1) / r);
}

/**
 * Outstanding NOMINAL principal for an index-linked (verðtryggð) loan.
 *
 * For these loans the outstanding balance is CPI-indexed, so it can grow in
 * nominal terms during the early years even as the real balance amortises.
 * Formula: real_remaining(m) × (1 + inflation)^(m / 12)
 *
 * @param {number} principal      - current nominal outstanding balance
 * @param {number} realRate       - real annual interest rate (decimal), NOT effective
 * @param {number} inflation      - expected annual inflation (decimal)
 * @param {number} totalYears
 * @param {number} monthsElapsed
 * @returns {number} Nominal outstanding balance after monthsElapsed months
 */
export function remainingBalanceIndexed(principal, realRate, inflation, totalYears, monthsElapsed) {
  if (monthsElapsed <= 0) return principal;
  const realRemaining = remainingBalance(principal, realRate, totalYears, monthsElapsed);
  return realRemaining * Math.pow(1 + inflation, monthsElapsed / 12);
}

/* ─────────────────────────────────────────────────────────────────────────────
   SINGLE SWITCH
───────────────────────────────────────────────────────────────────────────── */

/**
 * Calculate the net position for every month from 0 → totalMonths if the
 * borrower switches to Option A at that month.
 *
 * @param {object} p - inputs object (from inputs.js getInputs())
 * @returns {object} {
 *   rows[]          - {m, switchCost, savings, net, yearsRemaining}
 *   bestMonth       - month at which net is maximised
 *   bestNet         - maximum net value
 *   firstPositive   - first month where net > 0  (-1 if never)
 *   totalMonths     - p.yearsLeft × 12
 *   monthlySaving   - monthly saving after switch
 *   effCurrent      - effective current rate
 *   effNew          - effective Option A rate
 * }
 */
export function calcSingleSwitch(p) {
  const totalMonths   = Math.round(p.yearsLeft * 12);
  const effCurrent    = effectiveRate(p.currentRate,  p.currentType,  p.inflationCurrent);
  const effNew        = effectiveRate(p.newRate,       p.newRateType,  p.inflationA);

  // monthlySaving at m=0 — used for display and verdict text
  const monthlySaving = monthlyPayment(p.principal, effCurrent, p.totalTerm)
                      - monthlyPayment(p.principal, effNew,     p.totalTerm);

  const rows = [];
  let bestMonth = 0, bestNet = -Infinity, firstPositive = -1;

  for (let m = 0; m <= totalMonths; m++) {
    const yearsRemaining = p.yearsLeft - m / 12;

    // Actual outstanding balance at month m.
    // For index-linked loans the nominal balance can grow in early years
    // (CPI indexation outpaces real amortisation), so we use the indexed formula.
    const P_m = p.currentType === 'index'
      ? remainingBalanceIndexed(p.principal, p.currentRate, p.inflationCurrent, p.totalTerm, m)
      : remainingBalance(p.principal, effCurrent, p.totalTerm, m);

    const penalty    = P_m * p.penaltyRate * Math.max(yearsRemaining, 0);
    const switchCost = penalty + p.setupFee;

    // Monthly saving if we switch at month m, using the actual remaining balance
    // and remaining amortisation term at that point.
    const remYears = Math.max(p.totalTerm - m / 12, 1 / 12);
    const mSaving  = monthlyPayment(P_m, effCurrent, remYears)
                   - monthlyPayment(P_m, effNew,     remYears);
    const savings  = mSaving * (totalMonths - m);
    const net      = savings - switchCost;

    if (net > bestNet)                   { bestNet = net; bestMonth = m; }
    if (net > 0 && firstPositive === -1) { firstPositive = m; }

    rows.push({ m, switchCost, savings, net, yearsRemaining });
  }

  return { rows, bestMonth, bestNet, firstPositive, totalMonths, monthlySaving, effCurrent, effNew };
}

/* ─────────────────────────────────────────────────────────────────────────────
   DOUBLE SWITCH  (A now → B at month M2)
───────────────────────────────────────────────────────────────────────────── */

/**
 * Calculate the cumulative net position for the double-switch strategy:
 *   1. Switch to Option A immediately (incurring cost1)
 *   2. At month M2, break Option A and switch to Option B (incurring cost2)
 *
 * @param {object} p - inputs object
 * @returns {object|null} null if M2 >= totalMonths
 */
export function calcDoubleSwitch(p) {
  const totalMonths = Math.round(p.yearsLeft * 12);
  const M2          = p.switchMonth2;

  if (M2 >= totalMonths) return null;

  const effCurrent = effectiveRate(p.currentRate, p.currentType,  p.inflationCurrent);
  const effNew     = effectiveRate(p.newRate,      p.newRateType,  p.inflationA);
  const effNew2    = effectiveRate(p.rate2,        p.rateType2,    p.inflationB);

  // Outstanding nominal balance at month M2 (zero-delay first switch uses p.principal)
  const P_M2 = p.currentType === 'index'
    ? remainingBalanceIndexed(p.principal, p.currentRate, p.inflationCurrent, p.totalTerm, M2)
    : remainingBalance(p.principal, effCurrent, p.totalTerm, M2);

  // Monthly savings computed from actual payment differences
  const saving1 = monthlyPayment(p.principal, effCurrent, p.totalTerm)
                - monthlyPayment(p.principal, effNew,     p.totalTerm);

  const remTermAtM2 = Math.max(p.totalTerm - M2 / 12, 1 / 12);
  const saving2 = monthlyPayment(P_M2, effCurrent, remTermAtM2)
                - monthlyPayment(P_M2, effNew2,    remTermAtM2);

  // Cost of first switch (today) — penalty uses current outstanding balance (m = 0)
  const cost1 = p.principal * p.penaltyRate * p.yearsLeft + p.setupFee;

  // Penalty for breaking Option A at month M2 — uses P_M2 (the indexed balance)
  const fixedTermA       = p.newRateType === 'fixed' ? p.newFixedTerm : p.yearsLeft;
  const yearsLeftOnA     = fixedTermA - M2 / 12;
  const penalty2         = yearsLeftOnA > 0
    ? P_M2 * p.penaltyRateNew * yearsLeftOnA
    : 0;
  const cost2            = penalty2 + p.setupFee2;

  const phase1Savings  = saving1 * M2;
  const phase2Savings  = saving2 * (totalMonths - M2);
  const totalNet       = phase1Savings + phase2Savings - cost1 - cost2;

  // Build month-by-month cumulative timeline
  const rows = [];
  let cum = -cost1;

  for (let m = 0; m <= totalMonths; m++) {
    if (m === M2) cum -= cost2;
    rows.push({ m, net: cum });
    const rate = m < M2 ? saving1 : saving2;
    if (m < totalMonths) cum += rate;
  }

  return {
    M2, cost1, cost2, penalty2, yearsLeftOnA,
    phase1Savings, phase2Savings, totalNet,
    saving1perMonth: saving1,
    saving2perMonth: saving2,
    rows, totalMonths,
    effCurrent, effNew, effNew2
  };
}

/* ─────────────────────────────────────────────────────────────────────────────
   SCENARIO BUILDER
───────────────────────────────────────────────────────────────────────────── */

/**
 * Build a list of all comparable strategies with their net outcomes.
 *
 * @param {object}      p           - inputs
 * @param {object}      single      - result of calcSingleSwitch(p)
 * @param {object|null} dbl         - result of calcDoubleSwitch(p), or null
 * @param {number}      totalMonths
 * @returns {Array<{label, net, color, cost}>}
 */
export function buildScenarios(p, single, dbl, totalMonths) {
  const scenarios = [];

  // Baseline
  scenarios.push({ label: 'Stay on current rate', net: 0, color: 'var(--muted)', cost: 0 });

  // Switch A only
  if (single.bestNet !== -Infinity) {
    scenarios.push({
      label: 'Switch to A now, hold',
      net:   single.bestNet,
      color: 'var(--accent3)',
      cost:  single.rows[0].switchCost,
    });
  }

  if (dbl) {
    // Switch A now → B later
    scenarios.push({
      label: `Switch A now → B at month ${dbl.M2}`,
      net:   dbl.totalNet,
      color: 'var(--purple)',
      cost:  dbl.cost1 + dbl.cost2,
    });

    // Wait and switch to B only (skip A)
    const M2            = dbl.M2;
    const effCurrent    = effectiveRate(p.currentRate, p.currentType, p.inflationCurrent);
    const effB          = effectiveRate(p.rate2, p.rateType2, p.inflationB);

    // Use the amortised / indexed balance at month M2 for the penalty and savings
    const P_M2b = p.currentType === 'index'
      ? remainingBalanceIndexed(p.principal, p.currentRate, p.inflationCurrent, p.totalTerm, M2)
      : remainingBalance(p.principal, effCurrent, p.totalTerm, M2);

    const yearsLeftAtM2 = Math.max(p.yearsLeft - M2 / 12, 0);
    const penaltyBOnly  = P_M2b * p.penaltyRate * yearsLeftAtM2;
    const costBOnly     = penaltyBOnly + p.setupFee2;
    const remTermAtM2b  = Math.max(p.totalTerm - M2 / 12, 1 / 12);
    const savingBOnly   = monthlyPayment(P_M2b, effCurrent, remTermAtM2b)
                        - monthlyPayment(P_M2b, effB,       remTermAtM2b);
    const netBOnly      = savingBOnly * (totalMonths - M2) - costBOnly;

    scenarios.push({
      label: `Wait → switch to B only at month ${M2}`,
      net:   netBOnly,
      color: 'var(--accent2)',
      cost:  costBOnly,
    });
  }

  return scenarios;
}
