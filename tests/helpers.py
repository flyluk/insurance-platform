from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8090").rstrip("/")
UI_BASE_URL = os.getenv("UI_BASE_URL", "http://localhost:8088").rstrip("/")
PRODUCT_UI_BASE_URL = os.getenv("PRODUCT_UI_BASE_URL", "http://localhost:8089").rstrip("/")

USERS = {
    "agent": ("agent@insurance.local", "agent123"),
    "underwriter": ("uw@insurance.local", "uw123456"),
    "claims": ("claims@insurance.local", "claims123"),
    "finance": ("finance@insurance.local", "finance123"),
    "product": ("product@insurance.local", "product123"),
    "admin": ("admin@insurance.local", "admin123"),
    "policyholder": ("policyholder@insurance.local", "holder123"),
}

HOLDER_UI_BASE_URL = os.getenv("HOLDER_UI_BASE_URL", "http://localhost:8091").rstrip("/")


def login(client: httpx.Client, role: str = "agent") -> dict[str, Any]:
    email, password = USERS[role]
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    data = resp.json()
    assert "access_token" in data
    return data


def unique_email(prefix: str = "test") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


def party_create_payload(full_name: str, *, email: str | None = None, **overrides: Any) -> dict[str, Any]:
    """Full required payload for POST /api/nb/parties."""
    payload = {
        "full_name": full_name,
        "email": email or unique_email("party"),
        "phone": "+1 555 0100",
        "date_of_birth": "1990-01-15",
        "address": "1 Main St",
        "id_number": f"ID-{uuid.uuid4().hex[:8].upper()}",
        "gender": "female",
    }
    payload.update(overrides)
    return payload


def wait_until(predicate, *, timeout: float = 30.0, interval: float = 1.0, desc: str = "condition"):
    deadline = time.time() + timeout
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
        time.sleep(interval)
    msg = f"Timed out waiting for {desc}"
    if last_exc:
        msg = f"{msg}: {last_exc}"
    raise TimeoutError(msg)


def create_auto_quote(client: httpx.Client, headers: dict[str, str]) -> tuple[dict, dict]:
    party = client.post(
        "/api/nb/parties",
        headers=headers,
        json=party_create_payload("Test Party"),
    )
    party.raise_for_status()
    party_data = party.json()

    plans = client.get(
        "/api/products/plans",
        headers=headers,
        params={"product_code": "AUTO", "status": "PUBLISHED"},
    )
    plans.raise_for_status()
    plan_list = plans.json()
    assert plan_list, "Expected seeded AUTO published plan"
    plan = plan_list[0]

    quote = client.post(
        "/api/nb/quotes",
        headers=headers,
        json={
            "party_id": party_data["id"],
            "product_code": "AUTO",
            "plan_id": plan["id"],
            "rider_ids": [],
            "risk_attributes": {
                "vehicle_year": 2022,
                "drivers": 1,
                "prior_claims": 0,
                "driver_age": 34,
            },
        },
    )
    quote.raise_for_status()
    return party_data, quote.json()
