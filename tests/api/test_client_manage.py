"""List, search, and update clients via New Business party APIs."""

from __future__ import annotations

import pytest
from helpers import unique_email, party_create_payload

pytestmark = [pytest.mark.api]


@pytest.mark.story("KAN-2")
def test_list_search_and_update_client(api_client, agent_headers):
    created = api_client.post(
        "/api/nb/parties",
        headers=agent_headers,
        json=party_create_payload("Manage Client Test", email=unique_email("manage")),
    )
    assert created.status_code == 200, created.text
    party = created.json()

    listed = api_client.get("/api/nb/parties", headers=agent_headers)
    assert listed.status_code == 200
    assert any(p["id"] == party["id"] for p in listed.json())

    search = api_client.get(
        "/api/nb/clients/search",
        headers=agent_headers,
        params={"name": "Manage Client"},
    )
    assert search.status_code == 200
    assert any(p["id"] == party["id"] for p in search.json())

    updated = api_client.put(
        f"/api/nb/parties/{party['id']}",
        headers=agent_headers,
        json={
            "full_name": "Manage Client Updated",
            "email": party["email"],
            "phone": "+1-555-0199",
            "date_of_birth": "1988-07-04",
            "address": "99 Updated Ave, Austin, TX 78701",
            "id_number": party["id_number"],
            "gender": "male",
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["full_name"] == "Manage Client Updated"
    assert body["phone"] == "+1-555-0199"
    assert body["address"].startswith("99 Updated")
    assert body["gender"] == "male"
