import pytest
from helpers import login

pytestmark = [pytest.mark.api, pytest.mark.story("KAN-1")]


def test_health(api_client):
    """Gateway health endpoint is reachable."""
    resp = api_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "gateway"


def test_login_agent(api_client):
    """Agent can log in and receive a JWT."""
    data = login(api_client, "agent")
    assert data["role"] == "agent"
    assert data["email"] == "agent@insurance.local"
    assert data["access_token"]


def test_login_invalid(api_client):
    """Invalid credentials are rejected."""
    resp = api_client.post(
        "/api/auth/login",
        json={"email": "agent@insurance.local", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_auth_me(api_client, agent_headers):
    """Authenticated /me returns the agent profile."""
    resp = api_client.get("/api/auth/me", headers=agent_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "agent@insurance.local"
    assert body["role"] == "agent"
