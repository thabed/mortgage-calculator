# Húsnæðislán · Mortgage Switch Calculator

A client-side mortgage decision tool designed for the **Icelandic housing market**. Model single and double switch scenarios, compare fixed vs. variable vs. index-linked (verðtryggð) loans, and find your break-even date — all in ISK.

**Live demo:** `https://<your-username>.github.io/mortgage-calculator/`

---

## Features

- **Current mortgage configuration** — principal, rate, years left on fixed term, penalty rate, loan type
- **Index-linked loan support** — inflation is added to the nominal rate to compute a true effective cost
- **Option A (first switch)** — new fee, rate, type (fixed / variable / index), fixed term, penalty rate
- **Option B (second switch toggle)** — model a future switch from A → B at any future month
- **4 charts** powered by Chart.js:
  - Cumulative net savings over time
  - Monthly payment comparison
  - Break-even zoom view
  - Total interest over loan life
- **Verdict engine** — colour-coded recommendation with specific advice (switch now / wait / don't switch)
- **Strategy comparison table** — ranks all strategies when Option B is enabled
- **Month-by-month timeline** — tabbed view for single and double-switch scenarios
- **Sticky header bar** — key metrics follow you while scrolling

---

## Project Structure

```
mortgage-calculator/
├── index.html              # Entry point — markup only, no inline JS/CSS
├── css/
│   ├── tokens.css          # Design tokens (colours, fonts, spacing, radii)
│   ├── layout.css          # Reset, container, grid, header, sticky bar
│   └── components.css      # All UI components (cards, inputs, charts, timeline…)
├── js/
│   ├── main.js             # Entry point — bootstraps and orchestrates
│   ├── calc.js             # Pure financial calculation engine
│   ├── charts.js           # Chart.js wrappers
│   ├── inputs.js           # Form reading and UI toggle management
│   └── utils.js            # Formatting helpers (fmt, fmtShort, fmtAxis)
└── README.md
```

### Module responsibilities

| Module | Responsibility |
|--------|---------------|
| `calc.js` | Pure functions — no DOM access. `calcSingleSwitch`, `calcDoubleSwitch`, `buildScenarios`, `effectiveRate`, `monthlyPayment`, `totalInterestEstimate` |
| `inputs.js` | Reads all form values, manages visibility of conditional fields, wires input listeners |
| `charts.js` | Creates/destroys Chart.js instances; `renderAllCharts` is the public API |
| `ui.js` | All DOM writes — sticky bar, cards, verdict, rate bars, comparison table, timeline |
| `utils.js` | Formatting utilities — `fmt`, `fmtShort`, `fmtAxis`, `clamp` |
| `main.js` | Imports everything, holds `activeTab` / `show2nd` state, calls `calculate()` |

---

## How calculations work

### Effective rate
For **index-linked** loans the effective annual rate is:
```
effectiveRate = nominalRate + inflation
```
This is used in all comparisons so index-linked and non-index loans are directly comparable.

### Penalty
```
penalty = principal × penaltyRate × yearsRemaining
```
Typical Icelandic values: **0.10–0.50% per remaining year**.

### Single switch — net at month M
```
switchCost(M) = principal × penaltyRate × (yearsLeft − M/12) + setupFee
savings(M)    = monthlySaving × (totalMonths − M)
net(M)        = savings(M) − switchCost(M)
```
The calculator sweeps all M from 0 → totalMonths to find `bestMonth` and `firstPositive`.

### Double switch — cumulative net
```
cost1     = penalty(yearsLeft) + setupFee          # switching to A today
cost2     = penaltyA(yearsLeftOnA at M2) + setupFee2  # breaking A at month M2

phase1    = saving1/month × M2
phase2    = saving2/month × (totalMonths − M2)
totalNet  = phase1 + phase2 − cost1 − cost2
```

---

## Deploying to GitHub Pages

1. Push the project to a GitHub repository.
2. Go to **Settings → Pages**.
3. Under *Source*, select **Deploy from a branch** → `main` / `(root)`.
4. Save. Your site will be live at `https://<username>.github.io/<repo-name>/`.

> The project is entirely static — no build step, no Node.js, no bundler needed.

---

## Development

Open `index.html` directly in a browser **or** use a local dev server (required for ES module imports in some browsers):

```bash
# Python
python3 -m http.server 8080

# Node (npx)
npx serve .

# VS Code
# Install "Live Server" extension, right-click index.html → Open with Live Server
```

---

## Extending

**Add a new chart:**
1. Create a `renderXyzChart(…)` function in `charts.js`
2. Call it from `renderAllCharts(…)` in the same file
3. Add a `<canvas id="chartXyz">` in `index.html`

**Add a new input field:**
1. Add the `<input>` / `<select>` in `index.html`
2. Read it in `getInputs()` in `inputs.js`
3. Use it in the relevant calc function in `calc.js`

**Change the colour scheme:**
Edit the CSS custom properties in `css/tokens.css` — they cascade to every component.

---

## Disclaimer

This tool is for **informational purposes only** and does not constitute financial advice. Always verify calculations with your lender and consult a qualified financial advisor before making mortgage decisions.
