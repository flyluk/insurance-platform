"""Resolve Jira issue keys to numeric IDs for Zephyr Scale issue links."""

from __future__ import annotations

import os
from typing import Any

import httpx


class JiraError(RuntimeError):
    pass


def resolve_jira_api_base(
    base_url: str | None = None,
    api_token: str | None = None,
    cloud_id: str | None = None,
) -> str:
    """Return the REST base URL for the configured token type.

    Classic site API tokens use ``https://<site>.atlassian.net``.
    Scoped tokens (``ATATT…``) must use
    ``https://api.atlassian.com/ex/jira/<cloudId>``.
    """
    site = (base_url or os.environ.get("JIRA_BASE_URL", "")).rstrip("/")
    token = api_token if api_token is not None else os.environ.get("JIRA_API_TOKEN", "")
    cloud = cloud_id or os.environ.get("JIRA_CLOUD_ID") or os.environ.get("ATLASSIAN_CLOUD_ID") or ""
    cloud = cloud.strip()

    scoped = token.startswith("ATATT") or bool(cloud)
    if scoped:
        if not cloud:
            raise JiraError(
                "Scoped Jira API tokens require JIRA_CLOUD_ID "
                "(https://api.atlassian.com/ex/jira/<cloudId>). "
                "Find cloudId via Atlassian admin or MCP getAccessibleAtlassianResources."
            )
        return f"https://api.atlassian.com/ex/jira/{cloud}"
    if not site:
        raise JiraError("JIRA_BASE_URL is required for classic Jira API tokens")
    return site


class JiraClient:
    def __init__(
        self,
        base_url: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
        cloud_id: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.email = email or os.environ.get("JIRA_EMAIL", "")
        self.api_token = api_token or os.environ.get("JIRA_API_TOKEN", "")
        if not self.email or not self.api_token:
            raise JiraError(
                "JIRA_EMAIL and JIRA_API_TOKEN are required for story linking"
            )
        self.base_url = resolve_jira_api_base(
            base_url=base_url,
            api_token=self.api_token,
            cloud_id=cloud_id,
        )
        self._client = httpx.Client(
            base_url=self.base_url,
            auth=(self.email, self.api_token),
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        self._cache: dict[str, int] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> JiraClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def issue_id(self, issue_key: str) -> int:
        if issue_key in self._cache:
            return self._cache[issue_key]
        resp = self._client.get(f"/rest/api/3/issue/{issue_key}", params={"fields": "id"})
        if resp.status_code >= 400:
            raise JiraError(f"GET issue {issue_key} -> {resp.status_code}: {resp.text}")
        data: dict[str, Any] = resp.json()
        issue_id = int(data["id"])
        self._cache[issue_key] = issue_id
        return issue_id
