/**
 * inputs.js
 * Reads all form values and manages input-related UI visibility.
 */

/* ─────────────────────────────────────────────────────────────────────────────
   READ ALL INPUTS
───────────────────────────────────────────────────────────────────────────── */

/**
 * Read the current state of every form field and return a normalised
 * inputs object. Rates are converted from % to decimal here.
 *
 * @returns {object} Inputs object consumed by calc.js
 */
export function getInputs() {
  const currentType = document.getElementById('currentType').value;
  const newRateType = document.getElementById('newRateType').value;
  const rateType2   = document.getElementById('rateType2').value;

  return {
    // ── Current mortgage ──────────────────────────────
    principal:        +document.getElementById('principal').value,
    currentRate:      +document.getElementById('currentRate').value       / 100,
    yearsLeft:        +document.getElementById('yearsLeft').value,
    penaltyRate:      +document.getElementById('penaltyRate').value       / 100,
    currentType,
    inflationCurrent: +document.getElementById('inflationRate').value     / 100,
    totalTerm:        +document.getElementById('totalTerm').value,

    // ── Option A ─────────────────────────────────────
    setupFee:         +document.getElementById('setupFee').value,
    newRate:          +document.getElementById('newRate').value           / 100,
    newRateType,
    newFixedTerm:     +document.getElementById('newFixedTerm').value,
    penaltyRateNew:   +document.getElementById('penaltyRateNew').value    / 100,
    inflationA:       +document.getElementById('inflationA').value        / 100,

    // ── Option B ─────────────────────────────────────
    rate2:            +document.getElementById('rate2').value             / 100,
    switchMonth2:     +document.getElementById('switchMonth2').value,
    penaltyRate2:     +document.getElementById('penaltyRate2').value      / 100,
    setupFee2:        +document.getElementById('setupFee2').value,
    rateType2,
    fixedTerm2:       +document.getElementById('fixedTerm2').value,
    inflationB:       +document.getElementById('inflationB').value        / 100,
  };
}

/* ─────────────────────────────────────────────────────────────────────────────
   VISIBILITY HELPERS
───────────────────────────────────────────────────────────────────────────── */

function show(id)  { const el = document.getElementById(id); if (el) el.style.display = ''; }
function hide(id)  { const el = document.getElementById(id); if (el) el.style.display = 'none'; }

/** Show/hide fields that depend on the current loan type */
export function updateCurrentTypeUI() {
  const type = document.getElementById('currentType').value;
  type === 'index' ? show('currentInflationGroup') : hide('currentInflationGroup');
}

/** Show/hide fields that depend on Option A rate type */
export function updateNewRateTypeUI() {
  const type = document.getElementById('newRateType').value;
  const isFixed = type === 'fixed';
  isFixed ? show('newFixedTermGroup')  : hide('newFixedTermGroup');
  isFixed ? show('newPenaltyGroup')    : hide('newPenaltyGroup');
  type === 'index' ? show('newInflationGroup') : hide('newInflationGroup');
}

/** Show/hide fields that depend on Option B rate type */
export function updateRate2TypeUI() {
  const type = document.getElementById('rateType2').value;
  type === 'fixed'  ? show('fixedTerm2Group')  : hide('fixedTerm2Group');
  type === 'index'  ? show('inflationB_group') : hide('inflationB_group');
}

/* ─────────────────────────────────────────────────────────────────────────────
   WIRE ALL INPUTS → CALLBACK
───────────────────────────────────────────────────────────────────────────── */

/**
 * Attach input event listeners to every form element.
 * Calls the provided onChange callback whenever any value changes.
 *
 * @param {function} onChange
 */
export function wireInputs(onChange) {
  document.querySelectorAll('input[type="number"], select')
    .forEach(el => el.addEventListener('input', onChange));
}

/* ─────────────────────────────────────────────────────────────────────────────
   SECOND-SWITCH TOGGLE
───────────────────────────────────────────────────────────────────────────── */

/**
 * Initialise the second-switch toggle row.
 *
 * @param {function} onChange - called whenever toggle state changes
 * @returns {{ getShow2nd: function }} accessor for current toggle state
 */
export function initToggle(onChange) {
  let show2nd = false;

  document.getElementById('toggleRow2').addEventListener('click', () => {
    show2nd = !show2nd;
    document.getElementById('toggle2').classList.toggle('on', show2nd);
    document.getElementById('secondSwitchInputs').classList.toggle('visible', show2nd);
    onChange(show2nd);
  });

  return {
    getShow2nd: () => show2nd,
  };
}
