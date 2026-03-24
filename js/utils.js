/**
 * utils.js
 * Formatting helpers for the Mortgage Switch Calculator
 */

/**
 * Format a number as full ISK currency string
 * e.g. 45000000 → "45.000.000 kr"
 * @param {number} n
 * @returns {string}
 */
export function fmt(n) {
  return new Intl.NumberFormat('is-IS').format(Math.round(n)) + ' kr';
}

/**
 * Format a number as a compact signed string
 * e.g. 1500000 → "+1.50M", -800000 → "-800k"
 * @param {number} n
 * @returns {string}
 */
export function fmtShort(n) {
  const abs  = Math.abs(n);
  const sign = n < 0 ? '-' : '+';
  if (abs >= 1e9) return sign + (abs / 1e9).toFixed(2) + ' mrð';
  if (abs >= 1e6) return sign + (abs / 1e6).toFixed(2) + 'M';
  if (abs >= 1e3) return sign + (abs / 1e3).toFixed(0) + 'k';
  return (n >= 0 ? '+' : '') + Math.round(n) + ' kr';
}

/**
 * Format a number as a compact bare number for chart axis labels
 * e.g. 1500000 → "1.50M", -800000 → "-800k"
 * @param {number} n
 * @returns {string}
 */
export function fmtAxis(n) {
  const abs = Math.abs(n);
  const sign = n < 0 ? '-' : '';
  if (abs >= 1e6) return sign + (abs / 1e6).toFixed(1) + 'M';
  if (abs >= 1e3) return sign + (abs / 1e3).toFixed(0) + 'k';
  return String(Math.round(n));
}

/**
 * Clamp a value between min and max.
 * @param {number} val
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
export function clamp(val, min, max) {
  return Math.min(Math.max(val, min), max);
}
