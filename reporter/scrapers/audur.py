"""
Auður scraper (Kvika subsidiary).
Target: https://audur.is/husnaedislan

Rate appears in static HTML text as e.g. "8,9% breytilegir vextir" and also in
an embedded `mortgagePage` JSON object. Loan is non-indexed variable rate.
Rate composition: base rate + margin (1.4% first 3 years, 1.9% thereafter).
"""

import re
import json
from playwright.async_api import Browser
from .base import new_page

URL = "https://audur.is/husnaedislan"


async def scrape(browser: Browser) -> list[dict]:
    page = await new_page(browser)
    offers = []
    try:
        await page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        content = await page.content()

        # Try embedded JSON first
        offers = _extract_mortgage_page_json(content)
        if offers:
            return offers

        # Fallback: find "X,X% breytilegir vextir" / "X,X% vextir" in page text
        matches = re.findall(r"(\d+[,.]?\d*)\s*%\s*(?:breytileg[ira]*\s*)?vext[ira]+", content, re.IGNORECASE)
        seen = set()
        for m in matches:
            rate = float(m.replace(",", ".")) / 100
            if 0.001 <= rate <= 0.30 and rate not in seen:
                seen.add(rate)
                offers.append({
                    "institution": "Auður",
                    "name": "Húsnæðislán — breytileg vextir, óverðtryggt",
                    "loan_type": "variable",
                    "annual_rate": rate,
                    "notes": "",
                })

    except Exception as e:
        print(f"[audur] scrape failed: {e}")
    finally:
        await page.context.close()
    return offers


def _extract_mortgage_page_json(html: str) -> list[dict]:
    """Parse the mortgagePage embedded JSON object for rate data."""
    pattern = re.compile(r'mortgagePage\s*[:=]\s*(\{.*?\})\s*[,;]', re.DOTALL)
    m = pattern.search(html)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
        offers = []
        # Walk description arrays for rate values
        for block in data.get("body", []):
            primary = block.get("primary", {})
            for item in primary.get("description", []):
                text = str(item)
                rate_match = re.search(r"(\d+[,.]?\d*)\s*%", text)
                if rate_match:
                    rate = float(rate_match.group(1).replace(",", ".")) / 100
                    if 0.001 <= rate <= 0.30:
                        offers.append({
                            "institution": "Auður",
                            "name": "Húsnæðislán — breytileg vextir, óverðtryggt",
                            "loan_type": "variable",
                            "annual_rate": rate,
                            "notes": "",
                        })
        return _deduplicate(offers)
    except Exception:
        return []


def _deduplicate(offers):
    seen, result = set(), []
    for o in offers:
        key = round(o["annual_rate"], 4)
        if key not in seen:
            seen.add(key)
            result.append(o)
    return result
