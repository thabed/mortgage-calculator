"""
main.py
Orchestrator: scrape → calculate → compare → email → cache.

Usage:
    python main.py              # normal weekly run
    python main.py --dry-run    # scrape + build report but don't send email
    python main.py --test-email # send a test email using cached/dummy data
"""

import asyncio
import json
import sys
from pathlib import Path

from scrapers import ALL_SCRAPERS
from scrapers.base import browser_context
from report import build_report
from email_sender import send_report

CONFIG_PATH = Path(__file__).parent / "config.json"
CACHE_PATH = Path(__file__).parent / "rates_cache.json"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_cache() -> list[dict]:
    if not CACHE_PATH.exists():
        return []
    with open(CACHE_PATH) as f:
        return json.load(f)


def save_cache(offers: list[dict]) -> None:
    with open(CACHE_PATH, "w") as f:
        json.dump(offers, f, indent=2, ensure_ascii=False)


async def run_scrapers() -> list[dict]:
    all_offers = []
    async with browser_context() as browser:
        for scraper in ALL_SCRAPERS:
            name = scraper.__module__.split(".")[-1]
            print(f"[scraper] running {name}…")
            try:
                offers = await scraper(browser)
                print(f"[scraper] {name}: {len(offers)} offer(s) found")
                all_offers.extend(offers)
            except Exception as e:
                print(f"[scraper] {name}: ERROR — {e}")
    return all_offers


async def main() -> None:
    dry_run = "--dry-run" in sys.argv
    test_email = "--test-email" in sys.argv

    config = load_config()
    prev_offers = load_cache()

    if test_email:
        offers = prev_offers or []
        print("[main] test-email mode: using cached offers")
    else:
        offers = await run_scrapers()

    if not offers:
        print("[main] WARNING: no offers scraped — check scrapers or network.")
        if not test_email:
            return

    html = build_report(config, offers, prev_offers)

    if dry_run:
        out_path = Path(__file__).parent / "report_preview.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"[main] dry-run: report saved to {out_path}")
        return

    send_report(config, html)

    if not test_email:
        save_cache(offers)
        print(f"[main] cache updated with {len(offers)} offer(s)")


if __name__ == "__main__":
    asyncio.run(main())
