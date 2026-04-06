"""
Arion Bank scraper.
Target: https://www.arionbanki.is/einstaklingar/lan/ibudalan/

Strategy:
  1. Intercept JSON API responses while the page loads (captures rate data if served via API)
  2. DOM fallback: collect the innerText of every element that contains BOTH a
     housing-loan keyword AND a percentage in the same text block
"""

import re
import json
from playwright.async_api import Browser
from .base import new_page, is_housing_loan

URL = "https://www.arionbanki.is/einstaklingar/lan/ibudalan/"
RATE_RE = re.compile(r"(\d+[,.]?\d*)\s*%")


async def scrape(browser: Browser) -> list[dict]:
    page = await new_page(browser)
    intercepted: list[dict] = []

    async def handle_response(response):
        try:
            ct = response.headers.get("content-type", "")
            if "json" not in ct:
                return
            body = await response.json()
            _extract_from_json(body, intercepted)
        except Exception:
            pass

    page.on("response", handle_response)

    offers = []
    try:
        await page.goto(URL, wait_until="networkidle", timeout=45_000)
        await page.wait_for_timeout(3_000)

        if intercepted:
            return _deduplicate(intercepted)

        # Collect innerText of every element — filter to those containing BOTH
        # a housing keyword and a percentage sign in the same block
        blocks = await page.evaluate("""() => {
            const results = [];
            const all = document.querySelectorAll('*');
            const seen = new Set();
            for (const el of all) {
                const full = (el.innerText || '').replace(/\\s+/g, ' ').trim();
                if (full.length < 5 || full.length > 500) continue;
                if (seen.has(full)) continue;
                seen.add(full);
                results.push(full);
            }
            return results;
        }""")

        seen_rates = set()
        for text in blocks:
            if not is_housing_loan(text):
                continue
            m = RATE_RE.search(text)
            if not m:
                continue
            rate = float(m.group(1).replace(",", ".")) / 100
            if not (0.02 <= rate <= 0.20) or rate in seen_rates:
                continue
            seen_rates.add(rate)
            offers.append({
                "institution": "Arion",
                "name": text[:80],
                "loan_type": _infer_type(text),
                "annual_rate": rate,
                "notes": "",
            })

    except Exception as e:
        print(f"[arion] scrape failed: {e}")
    finally:
        await page.context.close()
    return _deduplicate(offers)


def _extract_from_json(data, offers: list, depth: int = 0) -> None:
    if depth > 8:
        return
    if isinstance(data, dict):
        name = str(data.get("name") or data.get("title") or data.get("label") or "")
        if is_housing_loan(name):
            for k in ("rate", "interest", "vextir", "interestRate", "annualRate", "percentage"):
                val = data.get(k)
                if val is None:
                    continue
                try:
                    rate = float(val)
                    if rate > 1:
                        rate /= 100
                    if 0.02 <= rate <= 0.20:
                        offers.append({
                            "institution": "Arion",
                            "name": name[:80],
                            "loan_type": _infer_type(name),
                            "annual_rate": rate,
                            "notes": "",
                        })
                        break
                except (TypeError, ValueError):
                    pass
        for v in data.values():
            _extract_from_json(v, offers, depth + 1)
    elif isinstance(data, list):
        for item in data:
            _extract_from_json(item, offers, depth + 1)


def _infer_type(text: str) -> str:
    t = text.lower()
    # Check óverðtrygg before verðtrygg — it's a substring of the latter
    if "óverðtryggt" in t or "óverðtryggð" in t:
        return "variable" if "breytileg" in t else "fixed"
    if "verðtrygg" in t:
        return "index"
    if "breytileg" in t:
        return "variable"
    return "fixed"


def _deduplicate(offers):
    seen, result = set(), []
    for o in offers:
        key = (round(o["annual_rate"], 4), o["loan_type"])
        if key not in seen:
            seen.add(key)
            result.append(o)
    return result
