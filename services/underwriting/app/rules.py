"""Underwriting rules — prefer product-engine thresholds, fallback carefully."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from insurance_shared.auth import create_access_token


def _local_fallback(product_code: str, risk: dict[str, Any], annual_premium: float) -> tuple[str, str]:
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


def _service_headers() -> dict[str, str]:
    token = create_access_token(
        subject="service-underwriting",
        email="underwriting@internal",
        role="underwriter",
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=30,
    )
    return {"Authorization": f"Bearer {token}"}


def evaluate(
    product_code: str,
    risk: dict[str, Any],
    annual_premium: float,
    *,
    plan_id: str | None = None,
) -> tuple[str, str]:
    """Return (decision, reason) where decision in ACCEPT|REFER|DECLINE.

    When a plan_id is present, catalog rules must be used. If product-engine is
    unreachable or returns an unusable body, REFER for manual review instead of
    applying line-default local rules that ignore the plan (including auto-bind).
    """
    url = f"{settings.product_engine_url.rstrip('/')}/api/products/evaluate-uw"
    try:
        resp = httpx.post(
            url,
            headers=_service_headers(),
            json={
                "plan_id": plan_id,
                "product_code": product_code,
                "risk_attributes": risk,
                "annual_premium": annual_premium,
            },
            timeout=10.0,
        )
        if resp.status_code < 400:
            try:
                body = resp.json()
            except ValueError:
                body = None
            if isinstance(body, dict):
                decision = body.get("decision")
                reason = body.get("reason")
                if isinstance(decision, str) and isinstance(reason, str):
                    return decision, reason
    except httpx.HTTPError:
        pass

    if plan_id:
        return "REFER", "Product catalog unavailable — manual underwriting required"
    return _local_fallback(product_code, risk, annual_premium)
