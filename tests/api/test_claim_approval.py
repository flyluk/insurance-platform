"""Large claim settlements require approval before payment."""

from __future__ import annotations

import pytest
from helpers import create_auto_quote, wait_until

pytestmark = [pytest.mark.api, pytest.mark.story("KAN-4")]


def _bound_auto_policy(api_client, agent_headers) -> dict:
    _, quote = create_auto_quote(api_client, agent_headers)
    api_client.post(f"/api/nb/quotes/{quote['id']}/rate", headers=agent_headers).raise_for_status()
    app = api_client.post(f"/api/nb/quotes/{quote['id']}/submit", headers=agent_headers).json()

    def bound_app():
        apps = api_client.get("/api/nb/applications", headers=agent_headers).json()
        match = next((a for a in apps if a["id"] == app["id"]), None)
        if match and match.get("status") == "BOUND" and match.get("policy_id"):
            return match
        return None

    bound = wait_until(bound_app, timeout=45, desc="bound application")
    return api_client.get(f"/api/policies/{bound['policy_id']}", headers=agent_headers).json()


def _open_claim(api_client, claims_headers, policy: dict) -> dict:
    resp = api_client.post(
        "/api/claims",
        headers=claims_headers,
        json={
            "policy_id": policy["id"],
            "party_id": policy["party_id"],
            "product_code": policy["product_code"],
            "description": "Large loss claim",
            "loss_date": "2026-07-01",
            "reserve_amount": 5000,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_large_settlement_requires_approval(api_client, agent_headers, claims_headers, finance_headers):
    policy = _bound_auto_policy(api_client, agent_headers)
    claim = _open_claim(api_client, claims_headers, policy)

    pending = api_client.post(
        f"/api/claims/{claim['id']}/settle",
        headers=claims_headers,
        json={"settlement_amount": 12500},
    )
    assert pending.status_code == 200, pending.text
    body = pending.json()
    assert body["status"] == "PENDING_APPROVAL"
    assert body["settlement_amount"] == 12500

    # No disbursement until approved
    rows = api_client.get("/api/finance/disbursements", headers=finance_headers).json()
    assert not any(d.get("claim_id") == claim["id"] for d in rows)

    approved = api_client.post(f"/api/claims/{claim['id']}/approve", headers=claims_headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "SETTLED"

    def disbursement():
        rows = api_client.get("/api/finance/disbursements", headers=finance_headers).json()
        return next((d for d in rows if d.get("claim_id") == claim["id"]), None)

    disb = wait_until(disbursement, timeout=30, desc="approved claim disbursement")
    assert disb["amount"] == 12500
    assert disb["status"] == "PAID"


def test_reject_large_settlement_approval(api_client, agent_headers, claims_headers):
    policy = _bound_auto_policy(api_client, agent_headers)
    claim = _open_claim(api_client, claims_headers, policy)

    pending = api_client.post(
        f"/api/claims/{claim['id']}/settle",
        headers=claims_headers,
        json={"settlement_amount": 15000},
    )
    assert pending.status_code == 200
    assert pending.json()["status"] == "PENDING_APPROVAL"

    rejected = api_client.post(
        f"/api/claims/{claim['id']}/reject-approval",
        headers=claims_headers,
    )
    assert rejected.status_code == 200, rejected.text
    body = rejected.json()
    assert body["status"] == "RESERVED"
    assert body["settlement_amount"] is None


def test_small_settlement_skips_approval(api_client, agent_headers, claims_headers):
    policy = _bound_auto_policy(api_client, agent_headers)
    claim = _open_claim(api_client, claims_headers, policy)

    settled = api_client.post(
        f"/api/claims/{claim['id']}/settle",
        headers=claims_headers,
        json={"settlement_amount": 10000},
    )
    assert settled.status_code == 200, settled.text
    assert settled.json()["status"] == "SETTLED"
