import pytest
from helpers import create_auto_quote, unique_email

pytestmark = [pytest.mark.api, pytest.mark.story("KAN-2")]


def test_create_and_list_parties(api_client, agent_headers):
    """Create a party and see it in the parties list."""
    email = unique_email("party")
    create = api_client.post(
        "/api/nb/parties",
        headers=agent_headers,
        json={"full_name": "API Test Party", "email": email},
    )
    assert create.status_code == 200
    party = create.json()
    assert party["id"]
    assert party["email"] == email

    listing = api_client.get("/api/nb/parties", headers=agent_headers)
    assert listing.status_code == 200
    ids = {p["id"] for p in listing.json()}
    assert party["id"] in ids


def test_create_rate_quote(api_client, agent_headers):
    """Create an AUTO quote and rate it to a positive premium."""
    _, quote = create_auto_quote(api_client, agent_headers)
    assert quote["status"] == "DRAFT"
    assert quote["product_code"] == "AUTO"

    rated = api_client.post(f"/api/nb/quotes/{quote['id']}/rate", headers=agent_headers)
    assert rated.status_code == 200
    body = rated.json()
    assert body["status"] == "RATED"
    assert body["annual_premium"] is not None
    assert body["annual_premium"] > 0


def test_list_applications(api_client, agent_headers):
    """List new-business applications."""
    resp = api_client.get("/api/nb/applications", headers=agent_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
