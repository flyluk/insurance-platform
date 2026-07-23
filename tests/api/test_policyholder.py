"""Policyholder self-serve: scoped policies/invoices, CARD/ACH pay, FNOL."""

from __future__ import annotations

import os
import uuid

import httpx
import pytest
from helpers import login

pytestmark = [pytest.mark.api, pytest.mark.story("KAN-6")]

FINANCE_URL = os.getenv("FINANCE_URL", "http://localhost:8005").rstrip("/")


def _party_id(api_client) -> str:
    return login(api_client, "policyholder")["party_id"]


def _ensure_open_invoice(api_client, headers: dict[str, str]) -> dict:
    invoices = api_client.get("/api/finance/invoices", headers=headers)
    invoices.raise_for_status()
    open_inv = next((i for i in invoices.json() if i["status"] == "OPEN"), None)
    if open_inv:
        return open_inv

    party_id = _party_id(api_client)
    policies = api_client.get("/api/policies", headers=headers).json()
    assert policies, "Expected seeded demo policy"
    policy = policies[0]
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "PremiumDue",
        "aggregate_type": "policy",
        "aggregate_id": policy["id"],
        "payload": {
            "policy_id": policy["id"],
            "policy_number": policy["policy_number"],
            "party_id": party_id,
            "product_code": policy["product_code"],
            "amount": 125.5,
            "invoice_type": "PREMIUM",
        },
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(f"{FINANCE_URL}/events", json=event)
        resp.raise_for_status()

    invoices = api_client.get("/api/finance/invoices", headers=headers)
    invoices.raise_for_status()
    open_inv = next((i for i in invoices.json() if i["status"] == "OPEN"), None)
    assert open_inv, "Failed to create open invoice for policyholder tests"
    return open_inv


def test_login_policyholder(api_client):
    data = login(api_client, "policyholder")
    assert data["role"] == "policyholder"
    assert data["email"] == "policyholder@insurance.local"
    assert data["party_id"]
    assert data["access_token"]


def test_policyholder_sees_own_policy(api_client, policyholder_headers):
    resp = api_client.get("/api/policies", headers=policyholder_headers)
    assert resp.status_code == 200
    policies = resp.json()
    assert policies, "Expected seeded demo policy"
    party_id = _party_id(api_client)
    assert all(p["party_id"] == party_id for p in policies)


def test_policyholder_card_declined(api_client, policyholder_headers):
    open_inv = _ensure_open_invoice(api_client, policyholder_headers)
    pay = api_client.post(
        f"/api/finance/invoices/{open_inv['id']}/pay",
        headers=policyholder_headers,
        json={
            "amount": open_inv["amount"],
            "method": "CARD",
            "card_number": "4000000000000000",
            "card_exp_month": 12,
            "card_exp_year": 2030,
            "card_cvv": "123",
        },
    )
    assert pay.status_code == 402


def test_policyholder_pay_card(api_client, policyholder_headers):
    open_inv = _ensure_open_invoice(api_client, policyholder_headers)
    pay = api_client.post(
        f"/api/finance/invoices/{open_inv['id']}/pay",
        headers=policyholder_headers,
        json={
            "amount": open_inv["amount"],
            "method": "CARD",
            "card_number": "4242424242424242",
            "card_exp_month": 12,
            "card_exp_year": 2030,
            "card_cvv": "123",
        },
    )
    assert pay.status_code == 200, pay.text
    body = pay.json()
    assert body["method"] == "CARD"
    assert body["masked_account"]
    assert body["reference"]

    refreshed = api_client.get(
        f"/api/finance/invoices/{open_inv['id']}", headers=policyholder_headers
    )
    assert refreshed.json()["status"] == "PAID"


def test_policyholder_fnol(api_client, policyholder_headers):
    policies = api_client.get("/api/policies", headers=policyholder_headers).json()
    active = next((p for p in policies if p["status"] == "ACTIVE"), None)
    assert active

    party_id = _party_id(api_client)
    resp = api_client.post(
        "/api/claims",
        headers=policyholder_headers,
        json={
            "policy_id": active["id"],
            "party_id": party_id,
            "product_code": active["product_code"],
            "description": "Demo windshield crack from road debris",
            "loss_date": "2026-07-20",
            "reserve_amount": 0,
        },
    )
    assert resp.status_code == 200, resp.text
    claim = resp.json()
    assert claim["party_id"] == party_id
    assert claim["policy_id"] == active["id"]
    assert claim["status"] == "OPEN"

    listed = api_client.get("/api/claims", headers=policyholder_headers)
    assert listed.status_code == 200
    assert any(c["id"] == claim["id"] for c in listed.json())


def test_policyholder_cannot_access_ledger(api_client, policyholder_headers):
    resp = api_client.get("/api/finance/ledger", headers=policyholder_headers)
    assert resp.status_code == 403
