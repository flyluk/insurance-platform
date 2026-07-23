"""Multi-product rating using plan/rider premiums and risk factors."""

from typing import Any


def risk_factor(product_code: str, risk: dict[str, Any]) -> float:
    if product_code == "AUTO":
        year = int(risk.get("vehicle_year") or 2020)
        age_factor = max(0.8, 1.2 - (2026 - year) * 0.02)
        drivers = int(risk.get("drivers") or 1)
        claims = int(risk.get("prior_claims") or 0)
        return age_factor * (1 + 0.15 * (drivers - 1)) * (1 + 0.25 * claims)
    if product_code == "HOME":
        value = float(risk.get("property_value") or 250000)
        year_built = int(risk.get("year_built") or 1990)
        age = max(0, 2026 - year_built)
        return (value / 250000) * (1 + age * 0.005)
    if product_code == "LIFE":
        age = int(risk.get("insured_age") or 35)
        sum_insured = float(risk.get("sum_insured") or 250000)
        smoker = 1.4 if risk.get("smoker") else 1.0
        return (sum_insured / 250000) * (1 + max(0, age - 30) * 0.03) * smoker
    return 1.0


def rate_quote(
    product_code: str,
    risk: dict[str, Any],
    *,
    base_premium: float | None = None,
    rider_premiums: list[float] | None = None,
) -> float:
    base = float(
        base_premium
        if base_premium is not None
        else {"AUTO": 800.0, "HOME": 1200.0, "LIFE": 600.0}.get(product_code, 1000.0)
    )
    riders = sum(float(x) for x in (rider_premiums or []))
    return round((base + riders) * risk_factor(product_code, risk), 2)
