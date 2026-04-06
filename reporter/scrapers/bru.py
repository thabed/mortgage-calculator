"""
Brú lífeyrissjóður scraper.
Target: https://www.lifbru.is/is/lan/um-lan/vaxtatafla

The page has two tables:

1. Current rates — 2-column: "Tegund láns" | "Vextir í gildi frá DD.MM.YYYY"
   Rows contain e.g.:
     Verðtryggðir fastir vextir        | 4,4%
     Verðtryggðir breytilegir vextir*  | 4,1%
     Óverðtryggðir fastir vextir*      | 7,2%

2. Historical table — multi-column with date | indexed-fixed | indexed-variable | ...
   First data row = most recent rates (same as table 1).

We parse table 1 (simpler structure).
"""

import re
from playwright.async_api import Browser
from .base import new_page

URL = "https://www.lifbru.is/is/lan/um-lan/vaxtatafla"

TYPE_MAP = [
    # óverðtrygg must come before verðtrygg (it's a substring of the latter)
    (re.compile(r"óver\w*trygg.*fast|fast.*óver\w*trygg",     re.I), "Óverðtryggð föst",      "fixed"),
    (re.compile(r"óver\w*trygg.*breyti|breyti.*óver\w*trygg", re.I), "Óverðtryggð breytileg", "variable"),
    (re.compile(r"ver\w*trygg.*fast|fast.*ver\w*trygg",        re.I), "Verðtryggð föst",       "index"),
    (re.compile(r"ver\w*trygg.*breyti|breyti.*ver\w*trygg",    re.I), "Verðtryggð breytileg",  "index"),
]


async def scrape(browser: Browser) -> list[dict]:
    page = await new_page(browser)
    offers = []
    try:
        resp = await page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        if resp and resp.status >= 400:
            print(f"[bru] HTTP {resp.status}")
            return []

        await page.wait_for_timeout(1_000)

        # Parse only the first table on the page — that's the current-rates
        # 2-column table: "Tegund láns" | "Vextir í gildi frá DD.MM.YYYY"
        # The second table is historical and must be ignored.
        tables = await page.query_selector_all("table")
        target_table = tables[0] if tables else None

        if target_table:
            rows = await target_table.query_selector_all("tr")
            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) < 2:
                    continue  # skip header rows (<th> only)
                name_text = (await cells[0].inner_text()).strip()
                rate_text = (await cells[1].inner_text()).strip()

                # Skip rows where the first cell looks like a date (historical table bleed)
                if re.match(r"\d{2}\.\d{2}\.\d{4}", name_text):
                    continue

                match = re.search(r"(\d+[,.]?\d*)\s*%", rate_text)
                if not match:
                    continue
                rate = float(match.group(1).replace(",", ".")) / 100
                if not (0.001 <= rate <= 0.30):
                    continue

                loan_type, canonical_name = _classify(name_text)
                offers.append({
                    "institution": "Brú lífeyrissjóður",
                    "name": canonical_name,
                    "loan_type": loan_type,
                    "annual_rate": rate,
                    "notes": "Members only",
                })

        # If first table failed, fall back to the historical table's first data row
        if not offers:
            offers = await _historical_fallback(page)

    except Exception as e:
        print(f"[bru] scrape failed: {e}")
    finally:
        await page.context.close()
    return offers


async def _historical_fallback(page) -> list[dict]:
    """
    Parse the multi-column historical table.
    Header row: Gildistími | Verðtryggðir fastir | Verðtryggðir breytilegir | ...
    First data row: most recent rates.
    """
    offers = []
    tables = await page.query_selector_all("table")
    for table in tables:
        header_row = await table.query_selector("tr")
        if not header_row:
            continue
        headers = [
            (await th.inner_text()).strip()
            for th in await header_row.query_selector_all("th, td")
        ]
        if not any("vextir" in h.lower() or "verðtrygg" in h.lower() for h in headers):
            continue

        # First data row after header
        data_rows = await table.query_selector_all("tr")
        for row in data_rows[1:2]:  # only first data row = most recent
            cells = await row.query_selector_all("td")
            for i, header in enumerate(headers[1:], start=1):
                if i >= len(cells):
                    break
                rate_text = (await cells[i].inner_text()).strip()
                match = re.search(r"(\d+[,.]?\d*)\s*%", rate_text)
                if not match:
                    continue
                rate = float(match.group(1).replace(",", ".")) / 100
                if not (0.001 <= rate <= 0.30):
                    continue
                loan_type, name = _classify(header)
                offers.append({
                    "institution": "Brú lífeyrissjóður",
                    "name": name,
                    "loan_type": loan_type,
                    "annual_rate": rate,
                    "notes": "Members only",
                })
        if offers:
            break
    return offers


def _classify(text: str) -> tuple[str, str]:
    for pattern, name, loan_type in TYPE_MAP:
        if pattern.search(text):
            return loan_type, name
    return "fixed", text[:60]
