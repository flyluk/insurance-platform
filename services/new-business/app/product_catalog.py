"""Fetch published plans/riders and resolve effective rates from product-engine."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class ProductCatalogError(Exception):
    pass


def fetch_plan(plan_id: str) -> dict[str, Any]:
    url = f"{settings.product_engine_url.rstrip('/')}/api/products/plans/{plan_id}"
    try:
        resp = httpx.get(url, timeout=10.0)
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
            json={"plan_id": plan_id, "rider_ids": rider_ids},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise ProductCatalogError(f"Product engine unreachable: {exc}") from exc
    if resp.status_code >= 400:
        raise ProductCatalogError(resp.json().get("detail") if resp.headers.get("content-type", "").startswith("application/json") else resp.text)
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
    for rid in rider_ids:
        rider = allowed.get(rid)
        if not rider:
            raise ProductCatalogError("Rider is not allowed on this plan")
        if rider.get("status") != "PUBLISHED":
            raise ProductCatalogError(f"Rider {rider.get('code')} is not published")
        selected_riders.append(rider)
    return {"plan": plan, "riders": selected_riders, "pricing": pricing}
