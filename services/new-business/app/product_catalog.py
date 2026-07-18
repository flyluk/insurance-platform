"""Fetch published plans/riders and resolve effective rates from product-engine."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from insurance_shared.auth import create_access_token


class ProductCatalogError(Exception):
    pass


def _service_headers() -> dict[str, str]:
    token = create_access_token(
        subject="service-new-business",
        email="new-business@internal",
        role="agent",
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=30,
    )
    return {"Authorization": f"Bearer {token}"}


def fetch_plan(plan_id: str) -> dict[str, Any]:
    url = f"{settings.product_engine_url.rstrip('/')}/api/products/plans/{plan_id}"
    try:
        resp = httpx.get(url, headers=_service_headers(), timeout=10.0)
    except httpx.HTTPError as exc:
        raise ProductCatalogError(f"Product engine unreachable: {exc}") from exc
    if resp.status_code == 404:
        raise ProductCatalogError("Plan not found")
    if resp.status_code >= 400:
        raise ProductCatalogError(f"Product engine error: {resp.status_code} {resp.text}")
    return resp.json()


def resolve_quote_pricing(plan_id: str, rider_ids: list[str]) -> dict[str, Any]:
    url = f"{settings.product_engine_url.rstrip('/')}/api/products/resolve-quote"
    try:
        resp = httpx.post(
            url,
            headers=_service_headers(),
            json={"plan_id": plan_id, "rider_ids": rider_ids},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise ProductCatalogError(f"Product engine unreachable: {exc}") from exc
    if resp.status_code >= 400:
        detail = resp.text
        if resp.headers.get("content-type", "").startswith("application/json"):
            try:
                detail = resp.json().get("detail", detail)
            except ValueError:
                pass
        raise ProductCatalogError(detail)
    return resp.json()


def validate_quote_selection(
    *,
    product_code: str,
    plan_id: str,
    rider_ids: list[str],
) -> dict[str, Any]:
    plan = fetch_plan(plan_id)
    if plan.get("product_code") != product_code:
        raise ProductCatalogError("Plan does not match product line")
    if plan.get("status") != "PUBLISHED":
        raise ProductCatalogError("Plan is not published")
    pricing = resolve_quote_pricing(plan_id, rider_ids)
    allowed = {r["id"]: r for r in plan.get("riders") or []}
    selected_riders: list[dict[str, Any]] = []
    for rid in dict.fromkeys(rider_ids):
        rider = allowed.get(rid)
        if not rider:
            raise ProductCatalogError("Rider is not allowed on this plan")
        if rider.get("status") != "PUBLISHED":
            raise ProductCatalogError(f"Rider {rider.get('code')} is not published")
        selected_riders.append(rider)
    return {"plan": plan, "riders": selected_riders, "pricing": pricing}
