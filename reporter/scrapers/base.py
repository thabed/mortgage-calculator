"""
base.py
Shared Playwright browser context for all scrapers.
Each scraper receives a Playwright Page and returns a list of LoanOffer dicts:

    {
        "institution": str,
        "name":        str,   # e.g. "Fixed 5yr indexed"
        "loan_type":   str,   # "fixed" | "variable" | "index"
        "annual_rate": float, # decimal, e.g. 0.044
        "notes":       str,   # optional extra info
    }

Scrapers should return [] on any error and print a warning — a failed scraper
must never crash the whole run.
"""

import re
from playwright.async_api import async_playwright, Browser, Page
from typing import AsyncGenerator
from contextlib import asynccontextmanager

# Only keep offers whose name matches at least one of these housing-loan terms
HOUSING_FILTER = re.compile(
    r"húsnæðislán|verðtryggð|verðtryggt|óverðtryggð|óverðtryggt|íbúðalán",
    re.IGNORECASE,
)


def is_housing_loan(text: str) -> bool:
    return bool(HOUSING_FILTER.search(text))


@asynccontextmanager
async def browser_context() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            await browser.close()


async def new_page(browser: Browser) -> Page:
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="is-IS",
    )
    page = await context.new_page()
    return page
