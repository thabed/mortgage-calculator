"""
Íslandsbanki scraper.
Uses the public JSON API directly — no browser needed.

Endpoint: https://www.islandsbanki.is/publicapi/interestrateTable/loans?lang=is

Mortgage categories in the response:
  irt.mortgageNonIndexed — Óverðtryggð húsnæðislán
  irt.mortgageIndexed    — Verðtryggð húsnæðislán
"""

import json
import re
import urllib.request
from playwright.async_api import Browser  # kept for signature compatibility

API_URL = "https://www.islandsbanki.is/publicapi/interestrateTable/loans?lang=is"
MORTGAGE_CATEGORIES = {"irt.mortgageNonIndexed", "irt.mortgageIndexed"}


async def scrape(browser: Browser) -> list[dict]:
    """browser arg is unused — API is fetched directly."""
    try:
        req = urllib.request.Request(
            API_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Referer": "https://www.islandsbanki.is/",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())

        offers = []
        seen = set()
        for category in data.get("categories", []):
            cat_key = category["title"]["title"]
            if cat_key not in MORTGAGE_CATEGORIES:
                continue
            loan_type = "index" if "Indexed" in cat_key else "variable"

            for item in category.get("items", []):
                item_name = item["name"].strip()
                # Only include individual (einstaklingar) products
                target = item.get("targetType", "")
                if target and target not in ("individual", ""):
                    continue

                for cfg in item.get("configurations", []):
                    if not cfg.get("showOnInterestsPage", True):
                        continue
                    pct = cfg["interest"].get("percentage")
                    itype = cfg["interest"].get("type", "")
                    if pct is None:
                        continue
                    rate = float(pct) / 100
                    if not (0.001 <= rate <= 0.30):
                        continue

                    cfg_name = cfg.get("name", "").strip()
                    full_name = f"{item_name} — {cfg_name}" if cfg_name else item_name

                    # Map API type to our loan_type
                    if cat_key == "irt.mortgageIndexed":
                        effective_type = "index"   # verðtryggð
                    elif itype == "fixed":
                        effective_type = "fixed"   # óverðtryggð, fixed interest
                    else:
                        effective_type = "variable"  # óverðtryggð, variable interest

                    key = (round(rate, 4), effective_type)
                    if key in seen:
                        continue
                    seen.add(key)
                    offers.append({
                        "institution": "Íslandsbanki",
                        "name": full_name[:80],
                        "loan_type": effective_type,
                        "annual_rate": rate,
                        "notes": "",
                    })

        return offers

    except Exception as e:
        print(f"[islandsbanki] scrape failed: {e}")
        return []
