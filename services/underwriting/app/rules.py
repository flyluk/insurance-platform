"""Declarative underwriting rules for AUTO / HOME / LIFE."""

from typing import Any


def evaluate(product_code: str, risk: dict[str, Any], annual_premium: float) -> tuple[str, str]:
    """Return (decision, reason) where decision in ACCEPT|REFER|DECLINE."""
    if product_code == "AUTO":
        prior = int(risk.get("prior_claims") or 0)
        age = int(risk.get("driver_age") or risk.get("insured_age") or 35)
        if prior >= 3:
            return "DECLINE", "Too many prior claims"
        if prior >= 1 or age < 25 or annual_premium > 2500:
            return "REFER", "Elevated auto risk requires manual review"
        return "ACCEPT", "Auto rules passed"

    if product_code == "HOME":
        value = float(risk.get("property_value") or 0)
        flood = bool(risk.get("flood_zone"))
        year_built = int(risk.get("year_built") or 2000)
        if flood and value > 500000:
            return "DECLINE", "High-value flood zone exposure"
        if value > 750000 or year_built < 1950:
            return "REFER", "Property risk outside auto-bind limits"
        return "ACCEPT", "Home rules passed"

    if product_code == "LIFE":
        age = int(risk.get("insured_age") or 35)
        sum_insured = float(risk.get("sum_insured") or 0)
        smoker = bool(risk.get("smoker"))
        if age > 70 or sum_insured > 2_000_000:
            return "DECLINE", "Age or sum insured exceeds life limits"
        if age > 55 or sum_insured > 750_000 or smoker:
            return "REFER", "Life risk requires medical underwriting"
        return "ACCEPT", "Life rules passed"

    return "REFER", "Unknown product — manual review"
