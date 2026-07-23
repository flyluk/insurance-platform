"""Resolve plan/rider base rates from product-engine and apply risk factors."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from insurance_shared.rating import rate_quote


class RatingError(Exception):
    pass


def _product_selection(risk: dict[str, Any]) -> tuple[str | None, list[str]]:
    selection = risk.get("product_selection") if isinstance(risk.get("product_selection"), dict) else {}
    plan_id = selection.get("plan_id")
    rider_ids = selection.get("rider_ids") or []
    if not isinstance(rider_ids, list):
        rider_ids = []
    return plan_id, [str(r) for r in rider_ids]


def resolve_base_pricing(plan_id: str, rider_ids: list[str]) -> dict[str, Any]:
    url = f"{settings.product_engine_url.rstrip('/')}/api/products/resolve-quote"
    try:
        resp = httpx.post(url, json={"plan_id": plan_id, "rider_ids": rider_ids}, timeout=10.0)
    except httpx.HTTPError as exc:
        raise RatingError(f"Product engine unreachable: {exc}") from exc
    if resp.status_code >= 400:
        detail = resp.text
        try:
            detail = resp.json().get("detail", detail)
        except Exception:  # noqa: BLE001
            pass
        raise RatingError(str(detail))
    return resp.json()


def rate_policy_premium(product_code: str, risk: dict[str, Any]) -> float:
    """Compute full annual premium from risk attrs + published plan/rider rates."""
    plan_id, rider_ids = _product_selection(risk)
    base_premium = None
    rider_premiums: list[float] | None = None
    if plan_id:
        pricing = resolve_base_pricing(plan_id, rider_ids)
        base_premium = float(pricing.get("plan_amount") or 0)
        rider_premiums = [float(r.get("amount") or 0) for r in pricing.get("riders") or []]
    return rate_quote(
        product_code,
        risk,
        base_premium=base_premium,
        rider_premiums=rider_premiums,
    )
