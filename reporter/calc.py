"""
calc.py
Python port of the core financial logic from js/calc.js.
All rate inputs are decimals (e.g. 0.0875 for 8.75%).
"""

import math


def effective_rate(nominal_rate: float, loan_type: str, inflation: float) -> float:
    """Effective annual rate. For index-linked loans, inflation is added."""
    return nominal_rate + inflation if loan_type == "index" else nominal_rate


def monthly_payment(principal: float, annual_rate: float, total_years: float) -> float:
    """Monthly annuity payment."""
    if annual_rate <= 0:
        return principal / (total_years * 12)
    r = annual_rate / 12
    n = total_years * 12
    return principal * r * math.pow(1 + r, n) / (math.pow(1 + r, n) - 1)


def total_interest_estimate(principal: float, eff_rate: float, total_years: float) -> float:
    mp = monthly_payment(principal, eff_rate, total_years)
    return mp * total_years * 12 - principal


def remaining_balance(
    principal: float, annual_rate: float, total_years: float, months_elapsed: int
) -> float:
    """Outstanding principal after months_elapsed payments on a standard annuity."""
    if months_elapsed <= 0:
        return principal
    if annual_rate <= 0:
        n = round(total_years * 12)
        return max(0.0, principal * (1 - months_elapsed / n))
    r = annual_rate / 12
    n = round(total_years * 12)
    mp = principal * r * math.pow(1 + r, n) / (math.pow(1 + r, n) - 1)
    return max(
        0.0,
        principal * math.pow(1 + r, months_elapsed)
        - mp * (math.pow(1 + r, months_elapsed) - 1) / r,
    )


def remaining_balance_indexed(
    principal: float,
    real_rate: float,
    inflation: float,
    total_years: float,
    months_elapsed: int,
) -> float:
    """Outstanding nominal principal for an index-linked loan."""
    if months_elapsed <= 0:
        return principal
    real_remaining = remaining_balance(principal, real_rate, total_years, months_elapsed)
    return real_remaining * math.pow(1 + inflation, months_elapsed / 12)


def amortization_schedule(
    principal: float, annual_rate: float, total_years: int, loan_type: str, inflation: float
) -> list[dict]:
    """
    Full month-by-month amortization schedule.
    Returns a list of dicts with keys:
        month, payment, interest, principal_paid, balance
    For index-linked loans, balance grows in nominal terms in early years.
    """
    eff = effective_rate(annual_rate, loan_type, inflation)
    payment = monthly_payment(principal, eff, total_years)
    schedule = []
    balance = principal
    monthly_inf = (1 + inflation) ** (1 / 12) - 1 if loan_type == "index" else 0.0
    monthly_rate = annual_rate / 12

    for m in range(1, total_years * 12 + 1):
        if loan_type == "index":
            # Index the balance first, then apply interest and payment
            balance *= 1 + monthly_inf
            interest = balance * monthly_rate
        else:
            interest = balance * monthly_rate

        principal_paid = payment - interest
        balance = max(0.0, balance - principal_paid)
        schedule.append({
            "month": m,
            "payment": round(payment),
            "interest": round(interest),
            "principal_paid": round(principal_paid),
            "balance": round(balance),
        })

    return schedule


def break_even_analysis(config: dict, offer: dict) -> dict:
    """
    Compute the net savings and break-even month if switching from the
    current loan (config) to offer today.

    Returns:
        {
            "monthly_saving":   float,   # positive = cheaper on new loan
            "break_even_month": int|None,
            "net_at_term_end":  float,
            "switch_cost":      float,
        }
    """
    principal = config["principal"]
    years_left = config["years_left"]
    total_term = config["total_term"]
    inflation_current = config.get("inflation", 0.0)
    penalty_rate = config.get("penalty_rate", 0.0)
    setup_fee = config.get("setup_fee", 0.0)

    eff_current = effective_rate(config["annual_rate"], config["loan_type"], inflation_current)
    eff_new = effective_rate(offer["annual_rate"], offer["loan_type"], inflation_current)

    mp_current = monthly_payment(principal, eff_current, total_term)
    mp_new = monthly_payment(principal, eff_new, total_term)
    monthly_saving = mp_current - mp_new

    switch_cost = principal * penalty_rate * years_left + setup_fee
    total_months = round(years_left * 12)

    best_net = -math.inf
    break_even_month = None

    for m in range(total_months + 1):
        if config["loan_type"] == "index":
            p_m = remaining_balance_indexed(
                principal, config["annual_rate"], inflation_current, total_term, m
            )
        else:
            p_m = remaining_balance(principal, eff_current, total_term, m)

        penalty = p_m * penalty_rate * max(years_left - m / 12, 0)
        cost = penalty + setup_fee
        rem_years = max(total_term - m / 12, 1 / 12)
        m_saving = monthly_payment(p_m, eff_current, rem_years) - monthly_payment(p_m, eff_new, rem_years)
        savings = m_saving * (total_months - m)
        net = savings - cost

        if net > best_net:
            best_net = net

        if net > 0 and break_even_month is None:
            break_even_month = m

    return {
        "monthly_saving": round(monthly_saving),
        "break_even_month": break_even_month,
        "net_at_term_end": round(best_net),
        "switch_cost": round(switch_cost),
    }
