from __future__ import annotations

import httpx
import pytest

from helpers import API_BASE_URL, UI_BASE_URL, login


@pytest.fixture(scope="session")
def api_base() -> str:
    return API_BASE_URL


@pytest.fixture(scope="session")
def ui_base() -> str:
    return UI_BASE_URL


@pytest.fixture(scope="session")
def api_client(api_base: str) -> httpx.Client:
    with httpx.Client(base_url=api_base, timeout=30.0) as client:
        health = client.get("/health")
        health.raise_for_status()
        yield client


@pytest.fixture
def agent_headers(api_client: httpx.Client) -> dict[str, str]:
    token = login(api_client, "agent")["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def underwriter_headers(api_client: httpx.Client) -> dict[str, str]:
    token = login(api_client, "underwriter")["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def claims_headers(api_client: httpx.Client) -> dict[str, str]:
    token = login(api_client, "claims")["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def finance_headers(api_client: httpx.Client) -> dict[str, str]:
    token = login(api_client, "finance")["access_token"]
    return {"Authorization": f"Bearer {token}"}
