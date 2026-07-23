"""Party role helpers and snapshot shape shared across services."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PartySummary(BaseModel):
    id: str
    full_name: str = ""
    email: str = ""
    phone: str | None = None
    date_of_birth: str | None = None
    address: str | None = None
    id_number: str | None = None
    gender: str | None = None

    model_config = {"from_attributes": True}


def party_snapshot(party: Any | None, *, party_id: str | None = None) -> dict[str, Any]:
    """Build a JSON-serializable party snapshot from an ORM/party-like object."""
    if party is None:
        return {"id": party_id or "", "full_name": "", "email": ""}
    return {
        "id": getattr(party, "id", None) or party_id or "",
        "full_name": getattr(party, "full_name", "") or "",
        "email": getattr(party, "email", "") or "",
        "phone": getattr(party, "phone", None),
        "date_of_birth": getattr(party, "date_of_birth", None),
        "address": getattr(party, "address", None),
        "id_number": getattr(party, "id_number", None),
        "gender": getattr(party, "gender", None),
    }


def summary_from_snapshot(data: dict[str, Any] | None, *, fallback_id: str | None = None) -> PartySummary:
    data = data or {}
    return PartySummary(
        id=str(data.get("id") or fallback_id or ""),
        full_name=str(data.get("full_name") or ""),
        email=str(data.get("email") or ""),
        phone=data.get("phone"),
        date_of_birth=data.get("date_of_birth"),
        address=data.get("address"),
        id_number=data.get("id_number"),
        gender=data.get("gender"),
    )


def snapshot_incomplete(data: dict[str, Any] | None) -> bool:
    """True when a stored snapshot is missing display fields (name / DOB / address)."""
    data = data or {}
    if not data.get("id") and not (data.get("full_name") or "").strip():
        return True
    return not (data.get("full_name") or "").strip()


def merge_snapshot(base: dict[str, Any] | None, enrich: dict[str, Any] | None) -> dict[str, Any]:
    """Prefer non-empty fields from enrich over base."""
    out = dict(base or {})
    for key, value in (enrich or {}).items():
        if value is None or value == "":
            continue
        if not out.get(key):
            out[key] = value
    return out
