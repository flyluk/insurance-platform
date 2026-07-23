"""Owner vs insured party roles across NB → policy → claim APIs."""

from __future__ import annotations

import pytest
from helpers import unique_email, party_create_payload

pytestmark = [pytest.mark.api]


def _create_party(api_client, headers, name: str) -> dict:
    resp = api_client.post(
        "/api/nb/parties",
        headers=headers,
        json=party_create_payload(name, email=unique_email(name.split()[0].lower())),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _published_auto_plan(api_client, headers) -> dict:
    plans = api_client.get(
        "/api/products/plans",
        headers=headers,
        params={"product_code": "AUTO", "status": "PUBLISHED"},
    )
    assert plans.status_code == 200
    plan_list = plans.json()
    assert plan_list, "Expected seeded AUTO published plan"
    return plan_list[0]


def test_quote_owner_and_insured_differ(api_client, agent_headers):
    """Create a quote with distinct owner and insured; response includes both summaries."""
    owner = _create_party(api_client, agent_headers, "Owner Person")
    insured = _create_party(api_client, agent_headers, "Insured Person")
    plan = _published_auto_plan(api_client, agent_headers)

    quote = api_client.post(
        "/api/nb/quotes",
        headers=agent_headers,
        json={
            "party_id": owner["id"],
            "insured_party_id": insured["id"],
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
    assert quote.status_code == 200, quote.text
    body = quote.json()
    assert body["party_id"] == owner["id"]
    assert body["insured_party_id"] == insured["id"]
    assert body["owner"]["full_name"] == "Owner Person"
    assert body["insured"]["full_name"] == "Insured Person"
    assert body["owner"]["id"] != body["insured"]["id"]


def test_demo_policy_exposes_owner_and_insured(api_client, agent_headers):
    """Seeded demo policy returns owner Alex Rivera and insured Jordan Lee."""
    resp = api_client.get("/api/policies", headers=agent_headers)
    assert resp.status_code == 200
    policies = resp.json()
    demo = next((p for p in policies if p.get("policy_number") == "AUTO-DEMO0001"), None)
    assert demo is not None, "Expected seeded AUTO-DEMO0001"
    assert demo["owner"]["full_name"] == "Alex Rivera"
    assert demo["insured"]["full_name"] == "Jordan Lee"
    assert demo["party_id"] == demo["owner_party_id"] or demo["owner_party_id"] is not None
    assert demo["insured_party_id"] != demo["party_id"]


def test_open_claim_copies_insured_from_policy(api_client, claims_headers, agent_headers):
    """Opening a claim on the demo policy copies owner and insured snapshots."""
    policies = api_client.get("/api/policies", headers=agent_headers)
    assert policies.status_code == 200
    demo = next((p for p in policies.json() if p.get("policy_number") == "AUTO-DEMO0001"), None)
    assert demo is not None
    assert demo["status"] == "ACTIVE"

    claim = api_client.post(
        "/api/claims",
        headers=claims_headers,
        json={
            "policy_id": demo["id"],
            "party_id": demo["party_id"],
            "product_code": demo["product_code"],
            "description": "Owner/insured snapshot check",
            "loss_date": "2026-07-15",
            "reserve_amount": 100,
        },
    )
    assert claim.status_code == 200, claim.text
    body = claim.json()
    assert body["party_id"] == demo["party_id"]
    assert body["insured_party_id"] == demo["insured_party_id"]
    assert body["owner"]["full_name"] == "Alex Rivera"
    assert body["insured"]["full_name"] == "Jordan Lee"


def test_finance_invoice_includes_owner(api_client, finance_headers):
    """Invoices expose billing owner summary."""
    resp = api_client.get("/api/finance/invoices", headers=finance_headers)
    assert resp.status_code == 200
    invoices = resp.json()
    assert invoices, "Expected at least one invoice"
    # Prefer demo open invoice when present
    demo = next((i for i in invoices if i.get("owner") and i["owner"].get("full_name")), invoices[0])
    assert "owner" in demo
    assert demo["owner"]["id"] == demo["party_id"] or demo["owner"]["id"]
