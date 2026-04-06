"""
Landsbankinn scraper.
Target: https://www.landsbankinn.is/vextir-og-verdskra

Landsbankinn publishes rates as PDF documents. This scraper:
  1. Loads the rates page and finds the link to the current "Vaxtatafla" PDF
  2. Downloads the PDF and extracts text with pdfplumber
  3. Parses housing loan (húsnæðislán) rows for rate values

Requires: pdfplumber  (pip install pdfplumber)
"""

import io
import re
import urllib.request
from playwright.async_api import Browser
from .base import new_page, is_housing_loan

RATES_PAGE = "https://www.landsbankinn.is/vextir-og-verdskra"

HOUSING_KEYWORDS = re.compile(r"húsnæð|íbúð|fasteigna|veðlán", re.I)
# Section headers that signal end of housing loan section
SECTION_END = re.compile(
    r"^(\d+\.\s*)?(bíla|tækja|skuldabréf|skammtíma|dráttarvext|yfirdrátt|kreditkort"
    r"|sparireikn|veltureikn|erlend\s*mynt|innlán)",
    re.I,
)


async def scrape(browser: Browser) -> list[dict]:
    page = await new_page(browser)
    offers = []
    try:
        await page.goto(RATES_PAGE, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(1_500)

        # Find the href of the first PDF link that looks like a rate table
        pdf_url = await _find_pdf_url(page)
        if not pdf_url:
            print("[landsbankinn] no PDF link found on rates page")
            return []

        print(f"[landsbankinn] downloading PDF: {pdf_url}")
        offers = _parse_pdf(pdf_url)

    except Exception as e:
        print(f"[landsbankinn] scrape failed: {e}")
    finally:
        await page.context.close()
    return offers


async def _find_pdf_url(page) -> str | None:
    """Return the URL of the current vaxtatafla PDF (not historical trend PDFs)."""
    links = await page.query_selector_all("a[href$='.pdf']")
    for link in links:
        href = await link.get_attribute("href")
        if not href:
            continue
        # Skip the two historical trend documents
        if "throun" in href or "þróun" in href.lower():
            continue
        if href.startswith("/"):
            href = "https://www.landsbankinn.is" + href
        return href
    return None


def _parse_pdf(url: str) -> list[dict]:
    """Download and extract housing loan rates from the PDF."""
    try:
        import pdfplumber
    except ImportError:
        print("[landsbankinn] pdfplumber not installed — run: pip install pdfplumber")
        return []

    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            pdf_bytes = resp.read()

        offers = []
        seen = set()

        # Only trigger housing section from explicit numbered loan section header,
        # NOT from deposit products that happen to mention "verðtryggð" etc.
        HOUSING_SECTION_START = re.compile(r"^\d+\.\s*Íbúðalán", re.I)

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_obj in pdf.pages:
                text = page_obj.extract_text() or ""
                lines = text.splitlines()

                in_housing_section = False
                current_loan_type = "fixed"

                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        continue

                    # Start housing section only on the explicit numbered header
                    if HOUSING_SECTION_START.match(stripped):
                        in_housing_section = True
                        continue

                    # End housing section on the next numbered section header
                    if SECTION_END.match(stripped):
                        in_housing_section = False
                        continue

                    if not in_housing_section:
                        continue

                    # Skip discontinued products
                    if "ekki í boði" in stripped.lower():
                        continue

                    # For lines with ↑ (heildarvextir marker), only read rates
                    # that follow the LAST ↑ — everything before is base/margin components
                    rate_source = stripped.split("↑")[-1] if "↑" in stripped else stripped

                    # Extract rates in realistic mortgage range (3%–20%)
                    line_rates = [
                        float(m.replace(",", ".")) / 100
                        for m in re.findall(r"(\d+[,.]?\d*)\s*%", rate_source)
                        if 0.03 <= float(m.replace(",", ".")) / 100 <= 0.20
                    ]
                    if not line_rates:
                        # Sub-header line — update type context
                        current_loan_type = _infer_type(stripped)
                        continue

                    # Rate row — determine its type
                    line_type = _infer_type(stripped)
                    if line_type == "fixed" and "breyti" not in stripped.lower():
                        line_type = current_loan_type

                    # Build name: keep LTV% info but strip rate numbers,
                    # footnote superscripts (digits glued directly to a letter), and ↑
                    name = re.sub(r"\b(\d+[,.]?\d*)\s*%(?!\s*veðsetn)", "", stripped)
                    name = re.sub(r"(?<=[a-zA-ZþæöðáéíóúýÞÆÖÐÁÉÍÓÚÝ])\d{1,2}\b", "", name)
                    name = re.sub(r"\s*↑\s*", " ", name)
                    name = re.sub(r"\s{2,}", " ", name).strip().strip(",").strip()
                    if not name:
                        name = stripped

                    for rate in line_rates:
                        key = (round(rate, 4), line_type)
                        if key in seen:
                            continue
                        seen.add(key)
                        offers.append({
                            "institution": "Landsbankinn",
                            "name": name[:80],
                            "loan_type": line_type,
                            "annual_rate": rate,
                            "notes": "",
                        })

        return offers

    except Exception as e:
        print(f"[landsbankinn] PDF parse error: {e}")
        return []


def _infer_type(text: str) -> str:
    t = text.lower()
    if "verðtrygg" in t:
        return "index"
    if "óverðtrygg" in t and "breytileg" in t:
        return "variable"
    if "óverðtrygg" in t:
        return "fixed"
    if "breytileg" in t:
        return "variable"
    return "fixed"
