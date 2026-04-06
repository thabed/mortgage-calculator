# Húsnæðislán · Mortgage Switch Calculator

A client-side mortgage decision tool designed for the **Icelandic housing market**. Model single and double switch scenarios, compare fixed vs. variable vs. index-linked (verðtryggð) loans, and find your break-even date — all in ISK.

The project also includes a **weekly email reporter** that scrapes live rates from Icelandic banks and pension funds and sends a comparison report against your current mortgage every Sunday.

**Live demo:** `https://<your-username>.github.io/mortgage-calculator/`

---

## Features

### Calculator (browser)
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

### Weekly reporter (`reporter/`)
- Scrapes current mortgage rates from **Landsbankinn, Arion, Íslandsbanki, Auður, Almenni Lífsverk, Brú lífeyrissjóður** using a headless browser
- Computes break-even date and net savings for every available offer vs. your current loan
- Detects rate changes since last week
- Sends a styled HTML email via Gmail every Sunday
- Reads your actual bank-provided payment plan from a CSV export

---

## Project Structure

```
mortgage-calculator/
├── index.html              # Calculator entry point
├── css/
│   ├── tokens.css
│   ├── layout.css
│   └── components.css
├── js/
│   ├── main.js
│   ├── calc.js
│   ├── charts.js
│   ├── inputs.js
│   └── utils.js
└── reporter/               # Weekly email reporter
    ├── import_csv.py       # One-time setup: parse bank CSV → config.json + schedule.json
    ├── main.py             # Orchestrator: scrape → calculate → email → cache
    ├── calc.py             # Python port of calc.js financial logic
    ├── report.py           # HTML email builder
    ├── email_sender.py     # Gmail SMTP sender
    ├── requirements.txt
    ├── config.json         # Your loan details + Gmail credentials (not committed)
    ├── schedule.json       # Full payment schedule from CSV (not committed)
    ├── rates_cache.json    # Last week's scraped rates for diff (not committed)
    └── scrapers/
        ├── base.py
        ├── landsbankinn.py
        ├── arion.py
        ├── islandsbanki.py
        ├── audur.py
        ├── almenni.py
        └── bru.py
```

---

## Reporter — Setup

### 1. Install dependencies

```bash
cd reporter
pip3 install -r requirements.txt
playwright install chromium
```

### 2. Import your payment plan CSV

Export your greiðsluáætlun CSV from your bank and run:

```bash
python3 import_csv.py /path/to/greidsluaetlun.csv
```

This writes `config.json` (financial fields) and `schedule.json` (full payment schedule). Re-run whenever you receive an updated payment plan from your bank.

The script derives from the CSV:
- Principal, current rate, loan type, years remaining
- Full month-by-month schedule with actual dates and rate changes

### 3. Complete config.json

After importing, fill in the remaining fields that can't be read from the CSV:

```json
{
  "penalty_rate":       0.003,
  "setup_fee":          150000,
  "email_to":           "you@gmail.com",
  "email_from":         "you@gmail.com",
  "email_app_password": "xxxx xxxx xxxx xxxx"
}
```

| Field | Description |
|-------|-------------|
| `penalty_rate` | Early repayment penalty per remaining year (ask your bank; typically 0.001–0.005) |
| `setup_fee` | Estimated cost to set up a new loan in ISK (typically 100,000–200,000) |
| `email_app_password` | 16-character Gmail App Password — see below |

**Getting a Gmail App Password:**
1. Enable 2-Step Verification on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create a new app password (name it e.g. "mortgage-reporter")
4. Paste the 16-character password into `config.json`

### 4. Test before scheduling

```bash
# Build the report and save as HTML — no email sent
python3 main.py --dry-run
# Open reporter/report_preview.html in a browser to review

# Send a real test email using cached data
python3 main.py --test-email
```

### 5. Schedule for Sunday 9am (cron)

```bash
crontab -e
```

Add this line (adjust the path):

```
0 9 * * 0 cd /path/to/mortgage-calculator/reporter && python3 main.py >> ~/mortgage-reporter.log 2>&1
```

---

## Reporter — Report contents

Each weekly email includes:

1. **Current loan summary** — principal, rate, effective rate, monthly payment, total remaining interest
2. **Amortization schedule** — next 24 months with actual dates from your CSV
3. **Best available offer** — highlighted recommendation with monthly saving, break-even date, and net savings at term end
4. **Full ranked table** — all scraped offers sorted by net savings vs. your loan
5. **Rate changes** — any institutions that changed rates since last week

---

## Reporter — Scraper notes

All six institution pages are JavaScript-rendered, so the scrapers use Playwright (headless Chromium). If a scraper returns 0 results after a `--dry-run`, the most likely cause is a page structure change. To debug:

```bash
# Run a single scraper interactively
cd reporter
python3 - <<'EOF'
import asyncio
from scrapers.base import browser_context
from scrapers import landsbankinn  # swap for any scraper

async def main():
    async with browser_context() as browser:
        offers = await landsbankinn.scrape(browser)
        print(offers)

asyncio.run(main())
EOF
```

Then inspect the page source to find the updated selectors and edit the relevant file in `reporter/scrapers/`.

---

## Calculator — Module responsibilities

| Module | Responsibility |
|--------|---------------|
| `calc.js` | Pure functions — no DOM access. `calcSingleSwitch`, `calcDoubleSwitch`, `buildScenarios`, `effectiveRate`, `monthlyPayment`, `totalInterestEstimate` |
| `inputs.js` | Reads all form values, manages visibility of conditional fields, wires input listeners |
| `charts.js` | Creates/destroys Chart.js instances; `renderAllCharts` is the public API |
| `ui.js` | All DOM writes — sticky bar, cards, verdict, rate bars, comparison table, timeline |
| `utils.js` | Formatting utilities — `fmt`, `fmtShort`, `fmtAxis`, `clamp` |
| `main.js` | Imports everything, holds `activeTab` / `show2nd` state, calls `calculate()` |

---

## Calculator — How calculations work

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

> The static calculator has no build step. The `reporter/` directory is ignored by GitHub Pages.

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

**Add a new institution scraper:**
1. Create `reporter/scrapers/newbank.py` following the pattern of existing scrapers
2. Add it to the `ALL_SCRAPERS` list in `reporter/scrapers/__init__.py`

**Change the colour scheme:**
Edit the CSS custom properties in `css/tokens.css` — they cascade to every component.

---

## Disclaimer

This tool is for **informational purposes only** and does not constitute financial advice. Always verify calculations with your lender and consult a qualified financial advisor before making mortgage decisions.
