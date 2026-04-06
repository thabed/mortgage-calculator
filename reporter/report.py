"""
report.py
Builds the HTML weekly email from scraped offers and calculation results.
"""

import json
from datetime import date
from pathlib import Path
from calc import (
    effective_rate,
    monthly_payment,
    total_interest_estimate,
    amortization_schedule,
    break_even_analysis,
)

SCHEDULE_PATH = Path(__file__).parent / "schedule.json"


def _load_schedule() -> list[dict] | None:
    """Load bank-provided schedule from schedule.json if it exists."""
    if SCHEDULE_PATH.exists():
        with open(SCHEDULE_PATH) as f:
            return json.load(f)
    return None


def fmt_isk(amount: float) -> str:
    return f"{int(amount):,} kr".replace(",", ".")


def fmt_pct(rate: float) -> str:
    return f"{rate * 100:.2f}%"


def _loan_type_label(t: str) -> str:
    return {"index": "Verðtryggð", "fixed": "Föst", "variable": "Breytileg"}.get(t, t)


def build_report(config: dict, offers: list[dict], prev_offers: list[dict]) -> str:
    """
    Build a full HTML email string.

    config      — contents of config.json
    offers      — this week's scraped LoanOffer dicts, each enriched with break_even_analysis
    prev_offers — last week's cached offers (may be empty)
    """

    today = date.today().strftime("%d. %B %Y")
    inflation = config.get("inflation", 0.0)
    eff_current = effective_rate(config["annual_rate"], config["loan_type"], inflation)
    mp_current = monthly_payment(config["principal"], eff_current, config["total_term"])

    # Use bank-provided schedule if available, otherwise compute
    bank_schedule = _load_schedule()
    if bank_schedule:
        total_interest = sum(r["interest"] + r.get("indexation", 0) for r in bank_schedule)
        schedule = bank_schedule  # already has month, payment, interest, principal_paid, balance
    else:
        total_interest = total_interest_estimate(config["principal"], eff_current, config["years_left"])
        schedule = amortization_schedule(
            config["principal"],
            config["annual_rate"],
            config["years_left"],
            config["loan_type"],
            inflation,
        )

    # Enrich offers with calc results and sort by net_at_term_end desc
    enriched = []
    for offer in offers:
        analysis = break_even_analysis(config, offer)
        enriched.append({**offer, **analysis})
    enriched.sort(key=lambda x: x["net_at_term_end"], reverse=True)

    # Rate change detection
    prev_map = {(o["institution"], o["loan_type"]): o["annual_rate"] for o in prev_offers}
    changes = []
    for o in enriched:
        key = (o["institution"], o["loan_type"])
        if key in prev_map:
            delta = o["annual_rate"] - prev_map[key]
            if abs(delta) >= 0.0001:
                direction = "▲" if delta > 0 else "▼"
                changes.append(
                    f"{o['institution']} {_loan_type_label(o['loan_type'])}: "
                    f"{direction} {abs(delta) * 100:.2f}pp → {fmt_pct(o['annual_rate'])}"
                )

    best = enriched[0] if enriched else None

    # --- HTML ---
    html = f"""<!DOCTYPE html>
<html lang="is">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; color: #222; }}
  .wrapper {{ max-width: 700px; margin: 24px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,.1); }}
  .header {{ background: #1a3a5c; color: #fff; padding: 24px 32px; }}
  .header h1 {{ margin: 0; font-size: 22px; }}
  .header p {{ margin: 6px 0 0; opacity: .8; font-size: 14px; }}
  .section {{ padding: 24px 32px; border-bottom: 1px solid #eee; }}
  .section:last-child {{ border-bottom: none; }}
  h2 {{ font-size: 16px; color: #1a3a5c; margin: 0 0 12px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #f0f4f8; text-align: left; padding: 8px 10px; font-weight: 600; color: #555; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #f0f0f0; }}
  tr:last-child td {{ border-bottom: none; }}
  .best-row {{ background: #f0fff4; font-weight: 600; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; }}
  .badge-index {{ background: #dbeafe; color: #1e40af; }}
  .badge-fixed {{ background: #dcfce7; color: #166534; }}
  .badge-variable {{ background: #fef9c3; color: #854d0e; }}
  .highlight-box {{ background: #f0fff4; border-left: 4px solid #22c55e; padding: 14px 18px; border-radius: 4px; }}
  .change-up {{ color: #dc2626; }}
  .change-down {{ color: #16a34a; }}
  .meta {{ font-size: 12px; color: #888; margin-top: 4px; }}
  .amort-table td, .amort-table th {{ padding: 5px 8px; font-size: 12px; }}
</style>
</head>
<body>
<div class="wrapper">

  <div class="header">
    <h1>Húsnæðislán — Vikuleg skýrsla</h1>
    <p>{today}</p>
  </div>

  <!-- CURRENT LOAN SUMMARY -->
  <div class="section">
    <h2>Núverandi lán</h2>
    <table>
      <tr><th>Höfuðstóll</th><td>{fmt_isk(config['principal'])}</td></tr>
      <tr><th>Nafnvextir</th><td>{fmt_pct(config['annual_rate'])}</td></tr>
      <tr><th>Gerð láns</th><td>{_loan_type_label(config['loan_type'])}</td></tr>
      <tr><th>Verðlag / inflation</th><td>{fmt_pct(inflation)}</td></tr>
      <tr><th>Virkir vextir</th><td>{fmt_pct(eff_current)}</td></tr>
      <tr><th>Mánaðarleg greiðsla</th><td>{fmt_isk(mp_current)}</td></tr>
      <tr><th>Ár eftir af lánstíma</th><td>{config['years_left']} ár</td></tr>
      <tr><th>Áætlaðar vaxtagreiðslur eftir</th><td>{fmt_isk(total_interest)}</td></tr>
    </table>
  </div>

  <!-- AMORTIZATION SCHEDULE (first 24 months) -->
  <div class="section">
    <h2>Greiðsluáætlun — næstu 24 mánuðir</h2>
    <table class="amort-table">
      <tr>
        <th>Gjalddagi</th><th>Greiðsla</th><th>Vextir</th><th>Afborgun</th><th>Eftirstöðvar</th>
      </tr>
      {"".join(
          f"<tr><td>{row.get('date', row['month'])}</td><td>{fmt_isk(row['payment'])}</td>"
          f"<td>{fmt_isk(row['interest'])}</td><td>{fmt_isk(row['principal_paid'])}</td>"
          f"<td>{fmt_isk(row['balance'])}</td></tr>"
          for row in schedule[:24]
      )}
    </table>
  </div>
"""

    # BEST RECOMMENDATION
    if best and best["net_at_term_end"] > 0:
        be = best["break_even_month"]
        be_str = f"{be} mánuðir" if be is not None else "N/A"
        html += f"""
  <div class="section">
    <h2>Besta tilboð</h2>
    <div class="highlight-box">
      <strong>{best['institution']} — {best['name']}</strong><br>
      {fmt_pct(best['annual_rate'])} &nbsp;·&nbsp; {_loan_type_label(best['loan_type'])}<br>
      Mánaðarlegar sparnaður: <strong>{fmt_isk(best['monthly_saving'])}</strong><br>
      Break-even: <strong>{be_str}</strong><br>
      Nettó sparnaður við lok lánstíma: <strong>{fmt_isk(best['net_at_term_end'])}</strong>
    </div>
  </div>
"""
    elif enriched:
        html += """
  <div class="section">
    <h2>Besta tilboð</h2>
    <p>Ekkert tilboð skilar jákvæðum nettó sparnaði miðað við núverandi lán.</p>
  </div>
"""

    # FULL RANKED TABLE
    html += """
  <div class="section">
    <h2>Öll tilboð — raðað eftir nettó sparnaði</h2>
    <table>
      <tr>
        <th>Stofnun</th><th>Lán</th><th>Gerð</th><th>Vextir</th>
        <th>Mán. greiðsla</th><th>Mán. sparnaður</th><th>Break-even</th><th>Nettó</th>
      </tr>
"""
    for i, o in enumerate(enriched):
        row_class = "best-row" if i == 0 and o["net_at_term_end"] > 0 else ""
        be = o["break_even_month"]
        be_str = f"{be}m" if be is not None else "—"
        eff_new = effective_rate(o["annual_rate"], o["loan_type"], inflation)
        mp_new = monthly_payment(config["principal"], eff_new, config["total_term"])
        badge_class = f"badge-{o['loan_type']}"
        html += (
            f'<tr class="{row_class}">'
            f"<td>{o['institution']}</td>"
            f"<td style='font-size:11px'>{o['name'][:40]}</td>"
            f"<td><span class='badge {badge_class}'>{_loan_type_label(o['loan_type'])}</span></td>"
            f"<td>{fmt_pct(o['annual_rate'])}</td>"
            f"<td>{fmt_isk(mp_new)}</td>"
            f"<td>{'+ ' if o['monthly_saving'] >= 0 else ''}{fmt_isk(o['monthly_saving'])}</td>"
            f"<td>{be_str}</td>"
            f"<td>{fmt_isk(o['net_at_term_end'])}</td>"
            f"</tr>\n"
        )
    html += "    </table>\n  </div>\n"

    # RATE CHANGES
    if changes:
        html += "  <div class='section'>\n    <h2>Vextir breyttust síðan í síðustu viku</h2>\n    <ul>\n"
        for c in changes:
            cls = "change-up" if "▲" in c else "change-down"
            html += f"      <li class='{cls}'>{c}</li>\n"
        html += "    </ul>\n  </div>\n"
    else:
        html += "  <div class='section'>\n    <h2>Vextir breyttust síðan í síðustu viku</h2>\n    <p>Engar breytingar fundust.</p>\n  </div>\n"

    html += """
  <div class="section">
    <p class="meta">Þessi skýrsla er eingöngu til upplýsingar og telst ekki fjárráðgjöf.
    Staðfestið alltaf útreikninga hjá lánadrottni og leitið ráða hjá fjármálaráðgjafa.</p>
  </div>

</div>
</body>
</html>"""

    return html
