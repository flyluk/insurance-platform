import pytest
from helpers import create_auto_quote, wait_until

pytestmark = pytest.mark.e2e


def test_claim_settlement_creates_disbursement(api_client, agent_headers, claims_headers, finance_headers):
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
    policy = api_client.get(f"/api/policies/{bound['policy_id']}", headers=agent_headers).json()

    claim_resp = api_client.post(
        "/api/claims",
        headers=claims_headers,
        json={
            "policy_id": policy["id"],
            "party_id": policy["party_id"],
            "product_code": policy["product_code"],
            "description": "E2E collision claim",
            "loss_date": "2026-07-01",
            "reserve_amount": 1000,
        },
    )
    claim_resp.raise_for_status()
    claim = claim_resp.json()

    settle = api_client.post(
        f"/api/claims/{claim['id']}/settle",
        headers=claims_headers,
        json={"settlement_amount": 1500},
    )
    settle.raise_for_status()
    assert settle.json()["status"] == "SETTLED"

    def disbursement():
        rows = api_client.get("/api/finance/disbursements", headers=finance_headers).json()
        return next((d for d in rows if d.get("claim_id") == claim["id"]), None)

    disb = wait_until(disbursement, timeout=30, desc="claim disbursement")
    assert disb["amount"] == 1500
    assert disb["status"] == "PAID"
