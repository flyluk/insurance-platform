import pytest
from helpers import create_auto_quote, party_create_payload, unique_email

pytestmark = [pytest.mark.api, pytest.mark.story("KAN-2")]


def test_create_and_list_parties(api_client, agent_headers):
    """Create a party and see it in the parties list."""
    email = unique_email("party")
    create = api_client.post(
        "/api/nb/parties",
        headers=agent_headers,
        json=party_create_payload("API Test Party", email=email),
    )
    assert create.status_code == 200
    party = create.json()
    assert party["id"]
    assert party["email"] == email

    listing = api_client.get("/api/nb/parties", headers=agent_headers)
    assert listing.status_code == 200
    ids = {p["id"] for p in listing.json()}
    assert party["id"] in ids


def test_create_party_requires_all_fields(api_client, agent_headers):
    """Create client rejects payloads missing email or other required fields."""
    incomplete = api_client.post(
        "/api/nb/parties",
        headers=agent_headers,
        json={"full_name": f"Incomplete {unique_email('inc').split('@')[0]}"},
    )
    assert incomplete.status_code == 422

    email_only = api_client.post(
        "/api/nb/parties",
        headers=agent_headers,
        json={
            "full_name": "Almost Complete",
            "email": unique_email("almost"),
        },
    )
    assert email_only.status_code == 422


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


def test_search_parties_by_name(api_client, agent_headers):
    """Client search requires name and returns exact/partial matches."""
    email = unique_email("search")
    unique_name = f"Searchable Client {email.split('@')[0]}"
    created = api_client.post(
        "/api/nb/parties",
        headers=agent_headers,
        json=party_create_payload(unique_name, email=email, address="1 Main St"),
    )
    assert created.status_code == 200
    party_id = created.json()["id"]

    for path in ("/api/nb/clients/search", "/api/nb/parties/search"):
        hits = api_client.get(path, headers=agent_headers, params={"name": "Searchable Client"})
        assert hits.status_code == 200, path
        ids = {p["id"] for p in hits.json()}
        assert party_id in ids

        # token from unique email fragment may not be in name — use last name token instead
        partial = api_client.get(path, headers=agent_headers, params={"name": unique_name.split()[-1]})
        assert partial.status_code == 200
        assert party_id in {p["id"] for p in partial.json()}

        exact = api_client.get(path, headers=agent_headers, params={"name": unique_name})
        assert exact.status_code == 200
        assert exact.json()[0]["id"] == party_id
        assert exact.json()[0]["full_name"] == unique_name

    missing = api_client.get(
        "/api/nb/clients/search",
        headers=agent_headers,
        params={"name": "DefinitelyNoSuchClientXYZ"},
    )
    assert missing.status_code == 200
    assert missing.json() == []

    bad = api_client.get(
        "/api/nb/clients/search",
        headers=agent_headers,
        params={"name": ""},
    )
    assert bad.status_code == 400
