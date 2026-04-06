"""
Almenni Lífsverk scraper.
Target: http://almenni-lifsverk.is/ (homepage)

Rates live in a JS variable in the page source:
    var php_vars = { ..., "vextir": { "Vextir_Overdtr": "8.85",
                                      "Vextir_Verdtr_Fastir": "4.4",
                                      "Vextir_Verdtr_Breytilegir": "3.5" }, ... }
"""

import re
import json
from playwright.async_api import Browser
from .base import new_page

URL = "http://almenni-lifsverk.is/"

RATE_KEYS = {
    "Vextir_Overdtr":            ("Óverðtryggð föst (36 mán.)", "fixed"),
    "Vextir_Verdtr_Fastir":      ("Verðtryggð föst",            "index"),
    "Vextir_Verdtr_Breytilegir": ("Verðtryggð breytileg",       "index"),
}


async def scrape(browser: Browser) -> list[dict]:
    page = await new_page(browser)
    offers = []
    try:
        await page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        content = await page.content()
        offers = _extract_php_vars(content)
        if not offers:
            print("[almenni] php_vars not found, falling back to text scan")
            offers = await _text_fallback(page)
    except Exception as e:
        print(f"[almenni] scrape failed: {e}")
    finally:
        await page.context.close()
    return offers


def _extract_php_vars(html: str) -> list[dict]:
    pattern = re.compile(r'var\s+php_vars\s*=\s*(\{.*?\})\s*;', re.DOTALL)
    m = pattern.search(html)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
        vextir = data.get("vextir", {})
        offers = []
        for key, (name, loan_type) in RATE_KEYS.items():
            val = vextir.get(key)
            if val is None:
                continue
            rate = float(str(val).replace(",", ".")) / 100
            if 0.001 <= rate <= 0.30:
                offers.append({
                    "institution": "Almenni Lífsverk",
                    "name": name,
                    "loan_type": loan_type,
                    "annual_rate": rate,
                    "notes": "Members only",
                })
        return offers
    except Exception as e:
        print(f"[almenni] failed to parse php_vars: {e}")
        return []


async def _text_fallback(page) -> list[dict]:
    """Scan page text for percentage values near loan-related keywords."""
    offers = []
    elements = await page.query_selector_all("td, li, p, span, div")
    seen = set()
    for el in elements:
        try:
            text = (await el.inner_text()).strip()
        except Exception:
            continue
        if not text or text in seen or len(text) > 200:
            continue
        seen.add(text)
        match = re.search(r"(\d+[,.]?\d*)\s*%", text)
        if not match:
            continue
        rate = float(match.group(1).replace(",", ".")) / 100
        if not (0.001 <= rate <= 0.30):
            continue
        loan_type = "index" if any(k in text.lower() for k in ["verðtrygg", "index"]) else "variable"
        offers.append({
            "institution": "Almenni Lífsverk",
            "name": text[:80],
            "loan_type": loan_type,
            "annual_rate": rate,
            "notes": "Members only",
        })
    return _deduplicate(offers)


def _deduplicate(offers):
    seen, result = set(), []
    for o in offers:
        key = (round(o["annual_rate"], 4), o["loan_type"])
        if key not in seen:
            seen.add(key)
            result.append(o)
    return result
