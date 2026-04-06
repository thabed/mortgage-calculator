"""
import_csv.py
Parse the bank's CSV payment schedule and populate config.json + schedule.json.

Usage:
    python import_csv.py /path/to/greidsluaetlun.csv

The script:
  - Derives principal, current rate, loan type, and term from the CSV
  - Writes the full schedule to schedule.json (used by report.py)
  - Updates the financial fields in config.json (email/penalty fields are preserved)

Icelandic number format: period = thousands separator, comma = decimal point.
E.g. "45.049.264" → 45049264,  "8,75%" → 0.0875
"""

import csv
import json
import sys
from pathlib import Path
from datetime import datetime, date

CONFIG_PATH = Path(__file__).parent / "config.json"
SCHEDULE_PATH = Path(__file__).parent / "schedule.json"


def parse_isk(value: str) -> float:
    """Convert Icelandic-formatted number string to float. '45.049.264' → 45049264.0"""
    return float(value.strip().replace(".", "").replace(",", "."))


def parse_rate(value: str) -> float:
    """Convert '8,75%' → 0.0875"""
    return float(value.strip().strip('"').replace("%", "").replace(",", ".")) / 100


def parse_date(value: str) -> date:
    """Convert 'DD.MM.YYYY' → date"""
    return datetime.strptime(value.strip(), "%d.%m.%Y").date()


def load_csv(path: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "date":            parse_date(row["Gjalddagi"]),
                "principal_paid":  parse_isk(row["Afborgun"]),
                "indexation":      parse_isk(row["Verðbætur"]),
                "interest":        parse_isk(row["Vextir"]),
                "rate":            parse_rate(row["%"]),
                "fees":            parse_isk(row["Kostnaður"]),
                "total_payment":   parse_isk(row["Samtals"]),
                "balance":         parse_isk(row["Heildar eftirstöðvar"]),
            })
    return rows


def derive_config(rows: list[dict]) -> dict:
    first = rows[0]
    last  = rows[-1]

    # Principal = balance after first payment + principal repaid in first payment
    principal = first["balance"] + first["principal_paid"]

    # Current rate = rate on the first row
    current_rate = first["rate"]

    # Loan type: indexed if any indexation > 0, otherwise variable/fixed
    has_indexation = any(r["indexation"] > 0 for r in rows)
    loan_type = "index" if has_indexation else "variable"

    # Years remaining = number of payments / 12
    total_months = len(rows)
    years_left = round(total_months / 12, 2)

    # First payment date (to compute months from today)
    today = date.today()
    first_payment_date = first["date"]
    months_until_first = max(
        0,
        (first_payment_date.year - today.year) * 12 + (first_payment_date.month - today.month),
    )

    return {
        "principal":    round(principal),
        "annual_rate":  current_rate,
        "loan_type":    loan_type,
        "inflation":    0.0,
        "years_left":   years_left,
        "total_term":   years_left,
        "months_until_first_payment": months_until_first,
    }


def build_schedule(rows: list[dict]) -> list[dict]:
    return [
        {
            "month":          i + 1,
            "date":           r["date"].strftime("%Y-%m-%d"),
            "rate":           r["rate"],
            "payment":        round(r["total_payment"]),
            "interest":       round(r["interest"]),
            "indexation":     round(r["indexation"]),
            "principal_paid": round(r["principal_paid"]),
            "balance":        round(r["balance"]),
        }
        for i, r in enumerate(rows)
    ]


def update_config(derived: dict) -> None:
    existing = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            existing = json.load(f)

    # Merge: CSV-derived fields override, personal fields (email, penalty) are preserved
    financial_keys = {"principal", "annual_rate", "loan_type", "inflation",
                      "years_left", "total_term", "months_until_first_payment"}
    updated = {**existing, **{k: v for k, v in derived.items() if k in financial_keys}}

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python import_csv.py /path/to/greidsluaetlun.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    print(f"Reading {csv_path}…")
    rows = load_csv(csv_path)
    print(f"  {len(rows)} payment rows found")

    derived = derive_config(rows)
    schedule = build_schedule(rows)

    # Print summary
    print(f"\nDerived loan details:")
    print(f"  Principal:    {derived['principal']:,} ISK")
    print(f"  Current rate: {derived['annual_rate'] * 100:.2f}%")
    print(f"  Loan type:    {derived['loan_type']}")
    print(f"  Years left:   {derived['years_left']}")
    print(f"  Payments:     {len(rows)} months ({rows[0]['date']} → {rows[-1]['date']})")

    # Detect rate changes
    seen_rates = []
    for r in rows:
        if not seen_rates or r["rate"] != seen_rates[-1][0]:
            seen_rates.append((r["rate"], r["date"]))
    if len(seen_rates) > 1:
        print(f"\n  Rate schedule:")
        for rate, start_date in seen_rates:
            print(f"    {rate * 100:.2f}%  from {start_date}")

    update_config(derived)
    print(f"\nconfig.json updated.")

    with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2, ensure_ascii=False)
    print(f"schedule.json written ({len(schedule)} rows).")


if __name__ == "__main__":
    main()
