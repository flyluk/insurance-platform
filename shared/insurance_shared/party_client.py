"""Fetch party snapshots from new-business (cluster-internal)."""

from __future__ import annotations

from typing import Any

import httpx

from insurance_shared.parties import snapshot_incomplete


def fetch_parties(
    new_business_url: str,
    party_ids: set[str] | list[str],
    *,
    timeout: float = 5.0,
) -> dict[str, dict[str, Any]]:
    """Return party_id -> snapshot for requested IDs. Missing IDs are omitted."""
    ids = sorted({str(i) for i in party_ids if i})
    if not ids or not new_business_url:
        return {}
    base = new_business_url.rstrip("/")
    try:
        resp = httpx.get(
            f"{base}/api/nb/internal/parties",
            params={"ids": ",".join(ids)},
            timeout=timeout,
        )
    except httpx.HTTPError:
        return {}
    if resp.status_code >= 400:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in resp.json() or []:
        snap = {
            "id": str(row.get("id") or ""),
            "full_name": row.get("full_name") or "",
            "email": row.get("email") or "",
            "phone": row.get("phone"),
            "date_of_birth": row.get("date_of_birth"),
            "address": row.get("address"),
            "id_number": row.get("id_number"),
            "gender": row.get("gender"),
        }
        if snap["id"]:
            out[snap["id"]] = snap
    return out


def enrich_snapshot(
    snapshot: dict[str, Any] | None,
    *,
    party_id: str | None,
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Fill incomplete snapshot from cache; always keep party_id."""
    pid = str((snapshot or {}).get("id") or party_id or "")
    base = dict(snapshot or {})
    if pid and not base.get("id"):
        base["id"] = pid
    if not snapshot_incomplete(base):
        return base
    enrich = cache.get(pid) or {}
    for key, value in enrich.items():
        if value is None or value == "":
            continue
        if not base.get(key):
            base[key] = value
    return base
