import pytest
from helpers import create_auto_quote, wait_until

pytestmark = [pytest.mark.e2e, pytest.mark.story("KAN-2")]


def test_quote_to_policy_to_invoice(api_client, agent_headers):
    """AUTO quote with clean risk should auto-accept UW, bind policy, raise invoice."""
    _, quote = create_auto_quote(api_client, agent_headers)

    rated = api_client.post(f"/api/nb/quotes/{quote['id']}/rate", headers=agent_headers)
    rated.raise_for_status()
    assert rated.json()["status"] == "RATED"

    submitted = api_client.post(f"/api/nb/quotes/{quote['id']}/submit", headers=agent_headers)
    submitted.raise_for_status()
    application = submitted.json()
    app_id = application["id"]
    assert application["status"] == "SUBMITTED"

    def app_bound():
        apps = api_client.get("/api/nb/applications", headers=agent_headers)
        apps.raise_for_status()
        match = next((a for a in apps.json() if a["id"] == app_id), None)
        if match and match.get("status") == "BOUND" and match.get("policy_id"):
            return match
        return None

    bound = wait_until(app_bound, timeout=45, desc=f"application {app_id} BOUND")
    assert bound["uw_decision"] == "ACCEPT"
    policy_id = bound["policy_id"]

    policy = api_client.get(f"/api/policies/{policy_id}", headers=agent_headers)
    policy.raise_for_status()
    assert policy.json()["status"] == "ACTIVE"
    assert policy.json()["application_id"] == app_id

    def invoice_for_policy():
        inv = api_client.get("/api/finance/invoices", headers=agent_headers)
        inv.raise_for_status()
        return next((i for i in inv.json() if i.get("policy_id") == policy_id), None)

    invoice = wait_until(invoice_for_policy, timeout=30, desc=f"invoice for policy {policy_id}")
    assert invoice["status"] == "OPEN"
    assert invoice["amount"] > 0
