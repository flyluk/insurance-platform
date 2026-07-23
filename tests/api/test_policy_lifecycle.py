"""Policy lifecycle: pro-rata cancel, endorse re-rate, ACTIVE claim gate."""

from __future__ import annotations

import pytest
from helpers import create_auto_quote, wait_until

pytestmark = [pytest.mark.api, pytest.mark.story("KAN-8")]


@pytest.fixture
def admin_headers(api_client):
    from helpers import login

    token = login(api_client, "admin")["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _bind_policy(api_client, agent_headers) -> dict:
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


def test_cancel_preview_and_pro_rata_credit(api_client, agent_headers, finance_headers):
    policy = _bind_policy(api_client, agent_headers)

    def premium_invoice():
        rows = api_client.get("/api/finance/invoices", headers=finance_headers).json()
        return next(
            (
                i
                for i in rows
                if i.get("policy_id") == policy["id"]
                and i.get("invoice_type") == "PREMIUM"
                and i.get("status") == "OPEN"
            ),
            None,
        )

    wait_until(premium_invoice, timeout=30, desc="bind premium invoice")

    preview = api_client.get(f"/api/policies/{policy['id']}/cancel-preview", headers=agent_headers)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["unearned_premium"] > 0
    assert 0 < body["remaining_fraction"] <= 1

    cancelled = api_client.post(f"/api/policies/{policy['id']}/cancel", headers=agent_headers)
    assert cancelled.status_code == 200, cancelled.text
    data = cancelled.json()
    assert data["status"] == "CANCELLED"
    assert data["cancellation_refund"] == body["unearned_premium"]
    assert data["cancelled_at"]

    def credit_invoice():
        rows = api_client.get("/api/finance/invoices", headers=finance_headers).json()
        return next(
            (
                i
                for i in rows
                if i.get("policy_id") == policy["id"]
                and i.get("invoice_type") == "CANCELLATION"
                and i.get("status") == "OPEN"
            ),
            None,
        )

    credit = wait_until(credit_invoice, timeout=30, desc="cancellation credit invoice")
    assert abs(credit["amount"] - body["unearned_premium"]) < 0.02

    def premiums_voided():
        invoices = api_client.get("/api/finance/invoices", headers=finance_headers).json()
        open_premium = [
            i
            for i in invoices
            if i.get("policy_id") == policy["id"]
            and i.get("invoice_type") in ("PREMIUM", "ENDORSEMENT", "RENEWAL")
            and i.get("status") == "OPEN"
        ]
        return open_premium == []

    assert wait_until(premiums_voided, timeout=30, desc="open premiums voided")


def test_endorse_rerate_creates_prorated_bill(api_client, agent_headers, admin_headers, finance_headers):
    policy = _bind_policy(api_client, agent_headers)
    risk = dict(policy.get("risk_attributes") or {})
    # Increase prior claims to drive a higher AUTO risk factor
    risk["prior_claims"] = int(risk.get("prior_claims") or 0) + 2

    preview = api_client.post(
        f"/api/policies/{policy['id']}/endorse-preview",
        headers=admin_headers,
        json={"risk_attributes": risk, "re_rate": True},
    )
    assert preview.status_code == 200, preview.text
    p = preview.json()
    assert p["annual_delta"] > 0
    assert p["billed_amount"] > 0
    assert p["billed_amount"] <= p["annual_delta"] + 0.01

    endorsed = api_client.post(
        f"/api/policies/{policy['id']}/endorse",
        headers=admin_headers,
        json={
            "endorsement_type": "DRIVER_CHANGE",
            "description": "Added prior claims",
            "re_rate": True,
            "risk_attributes": risk,
        },
    )
    assert endorsed.status_code == 200, endorsed.text
    assert abs(endorsed.json()["annual_premium"] - p["new_annual"]) < 0.02

    ends = api_client.get(f"/api/policies/{policy['id']}/endorsements", headers=admin_headers).json()
    assert ends
    assert abs(ends[0]["billed_amount"] - p["billed_amount"]) < 0.02

    def endorsement_invoice():
        rows = api_client.get("/api/finance/invoices", headers=finance_headers).json()
        return next(
            (
                i
                for i in rows
                if i.get("policy_id") == policy["id"]
                and i.get("invoice_type") == "ENDORSEMENT"
                and i.get("status") == "OPEN"
            ),
            None,
        )

    inv = wait_until(endorsement_invoice, timeout=30, desc="endorsement invoice")
    assert abs(inv["amount"] - p["billed_amount"]) < 0.02


def test_staff_cannot_open_claim_on_cancelled_policy(api_client, agent_headers, claims_headers):
    policy = _bind_policy(api_client, agent_headers)
    api_client.post(f"/api/policies/{policy['id']}/cancel", headers=agent_headers).raise_for_status()

    resp = api_client.post(
        "/api/claims",
        headers=claims_headers,
        json={
            "policy_id": policy["id"],
            "party_id": policy["party_id"],
            "product_code": policy["product_code"],
            "description": "Should be rejected",
            "loss_date": "2026-07-22",
            "reserve_amount": 0,
        },
    )
    assert resp.status_code == 400
    assert "ACTIVE" in resp.text
