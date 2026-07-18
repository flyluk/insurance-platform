from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8090").rstrip("/")
UI_BASE_URL = os.getenv("UI_BASE_URL", "http://localhost:8088").rstrip("/")

USERS = {
    "agent": ("agent@insurance.local", "agent123"),
    "underwriter": ("uw@insurance.local", "uw123456"),
    "claims": ("claims@insurance.local", "claims123"),
    "finance": ("finance@insurance.local", "finance123"),
    "admin": ("admin@insurance.local", "admin123"),
}


def login(client: httpx.Client, role: str = "agent") -> dict[str, Any]:
    email, password = USERS[role]
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    data = resp.json()
    assert "access_token" in data
    return data


def unique_email(prefix: str = "test") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


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
        json={
            "full_name": "Test Party",
            "email": unique_email("party"),
        },
    )
    party.raise_for_status()
    party_data = party.json()

    quote = client.post(
        "/api/nb/quotes",
        headers=headers,
        json={
            "party_id": party_data["id"],
            "product_code": "AUTO",
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
