"""Admin user list and update APIs."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.api]


@pytest.mark.story("KAN-1")
def test_admin_list_and_update_user(api_client, admin_headers, agent_headers):
    listed = api_client.get("/api/users", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    users = listed.json()
    assert isinstance(users, list)
    assert len(users) >= 1

    forbidden = api_client.get("/api/users", headers=agent_headers)
    assert forbidden.status_code == 403

    agent = next((u for u in users if u["email"] == "agent@insurance.local"), users[0])
    original_name = agent["full_name"]

    updated = api_client.put(
        f"/api/users/{agent['id']}",
        headers=admin_headers,
        json={
            "email": agent["email"],
            "full_name": "Demo Agent Updated",
            "role": agent["role"],
            "party_id": agent.get("party_id"),
            "is_active": True,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["full_name"] == "Demo Agent Updated"

    restore = api_client.put(
        f"/api/users/{agent['id']}",
        headers=admin_headers,
        json={
            "email": agent["email"],
            "full_name": original_name,
            "role": agent["role"],
            "party_id": agent.get("party_id"),
            "is_active": True,
        },
    )
    assert restore.status_code == 200, restore.text
