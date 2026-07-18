"""Thin Zephyr Scale Cloud REST client."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from zephyr import DEFAULT_BASE_URL


class ZephyrScaleError(RuntimeError):
    """Raised when a Zephyr Scale API call fails."""


class ZephyrScaleClient:
    def __init__(
        self,
        token: str | None = None,
        project_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.token = token or os.environ.get("ZEPHYR_SCALE_TOKEN", "")
        self.project_key = project_key or os.environ.get("ZEPHYR_PROJECT_KEY", "")
        self.base_url = (base_url or os.environ.get("ZEPHYR_SCALE_BASE_URL") or DEFAULT_BASE_URL).rstrip(
            "/"
        )
        if not self.token:
            raise ZephyrScaleError("ZEPHYR_SCALE_TOKEN is required")
        if not self.project_key:
            raise ZephyrScaleError("ZEPHYR_PROJECT_KEY is required")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ZephyrScaleClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            detail = resp.text
            try:
                detail = json.dumps(resp.json())
            except Exception:  # noqa: BLE001
                pass
            raise ZephyrScaleError(f"{method} {path} -> {resp.status_code}: {detail}")
        if resp.status_code == 204 or not resp.content:
            return None
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return resp.json()
        return resp.text

    def get_test_case(self, key: str) -> dict[str, Any] | None:
        try:
            return self._request("GET", f"/testcases/{key}")
        except ZephyrScaleError as exc:
            if "404" in str(exc):
                return None
            raise

    def create_test_case(
        self,
        *,
        name: str,
        objective: str | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "projectKey": self.project_key,
            "name": name,
        }
        if objective:
            body["objective"] = objective
        if labels:
            body["labels"] = labels
        return self._request("POST", "/testcases", json=body)

    def update_test_case(
        self,
        key: str,
        *,
        name: str | None = None,
        objective: str | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        existing = self.get_test_case(key)
        if not existing:
            raise ZephyrScaleError(f"Test case {key} not found")
        body: dict[str, Any] = {
            "id": existing["id"],
            "key": existing.get("key", key),
            "name": name if name is not None else existing.get("name", key),
            "project": existing["project"],
        }
        for field in ("objective", "precondition", "estimatedTime", "component", "priority", "status", "folder"):
            if field in existing and existing[field] is not None:
                body[field] = existing[field]
        if objective is not None:
            body["objective"] = objective
        if labels is not None:
            body["labels"] = labels
        elif existing.get("labels") is not None:
            body["labels"] = existing["labels"]
        return self._request("PUT", f"/testcases/{key}", json=body)

    def link_test_case_to_issue(self, test_case_key: str, issue_id: int) -> Any:
        return self._request(
            "POST",
            f"/testcases/{test_case_key}/links/issues",
            json={"issueId": issue_id},
        )

    def upload_junit(
        self,
        junit_path: Path,
        *,
        auto_create_test_cases: bool = True,
        test_cycle: dict[str, Any] | None = None,
    ) -> Any:
        path = Path(junit_path)
        if not path.is_file():
            raise ZephyrScaleError(f"JUnit file not found: {path}")
        params = {
            "projectKey": self.project_key,
            "autoCreateTestCases": str(auto_create_test_cases).lower(),
        }
        files = {"file": (path.name, path.read_bytes(), "application/xml")}
        data: dict[str, str] = {}
        if test_cycle:
            data["testCycle"] = json.dumps(test_cycle)
        resp = self._client.post(
            "/automations/executions/junit",
            params=params,
            files=files,
            data=data or None,
        )
        if resp.status_code >= 400:
            detail = resp.text
            try:
                detail = json.dumps(resp.json())
            except Exception:  # noqa: BLE001
                pass
            raise ZephyrScaleError(
                f"POST /automations/executions/junit -> {resp.status_code}: {detail}"
            )
        if not resp.content:
            return {"status": "ok"}
        try:
            return resp.json()
        except Exception:  # noqa: BLE001
            return {"status": "ok", "raw": resp.text}
