import pytest

pytestmark = pytest.mark.api


@pytest.mark.story("KAN-3")
def test_list_uw_cases(api_client, underwriter_headers):
    """Underwriter can list UW cases."""
    resp = api_client.get("/api/uw/cases", headers=underwriter_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.story("KAN-3")
def test_list_uw_queue(api_client, underwriter_headers):
    """Underwriter can list the review queue (pending + referred)."""
    resp = api_client.get("/api/uw/queue", headers=underwriter_headers)
    assert resp.status_code == 200
    cases = resp.json()
    assert isinstance(cases, list)
    assert all(c["status"] in ("PENDING", "REFERRED") for c in cases)


@pytest.mark.story("KAN-3")
def test_list_policies(api_client, agent_headers):
    """Agent can list policies and fetch detail when present."""
    resp = api_client.get("/api/policies", headers=agent_headers)
    assert resp.status_code == 200
    policies = resp.json()
    assert isinstance(policies, list)
    if policies:
        detail = api_client.get(f"/api/policies/{policies[0]['id']}", headers=agent_headers)
        assert detail.status_code == 200
        body = detail.json()
        assert body["policy_number"]
        assert "risk_attributes" in body


@pytest.mark.story("KAN-4")
def test_list_claims(api_client, claims_headers):
    """Claims user can list claims."""
    resp = api_client.get("/api/claims", headers=claims_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.story("KAN-4")
def test_list_finance(api_client, finance_headers):
    """Finance user can list invoices and ledger entries."""
    invoices = api_client.get("/api/finance/invoices", headers=finance_headers)
    assert invoices.status_code == 200
    assert isinstance(invoices.json(), list)

    ledger = api_client.get("/api/finance/ledger", headers=finance_headers)
    assert ledger.status_code == 200
    assert isinstance(ledger.json(), list)
