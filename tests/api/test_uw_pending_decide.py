"""PENDING underwriting cases can be accepted or declined by underwriters."""

from __future__ import annotations

import pytest
from helpers import wait_until

pytestmark = [pytest.mark.api]


@pytest.mark.story("KAN-3")
def test_decide_pending_case(api_client, underwriter_headers):
    """Seeded or listed PENDING case can be accepted from the review queue."""
    queue = api_client.get("/api/uw/queue", headers=underwriter_headers)
    assert queue.status_code == 200
    pending = next((c for c in queue.json() if c["status"] == "PENDING"), None)
    if pending is None:
        pytest.skip("No PENDING underwriting case in environment")

    decided = api_client.post(
        f"/api/uw/cases/{pending['id']}/decide",
        headers=underwriter_headers,
        json={"decision": "ACCEPT", "reason": "Manual accept of pending case"},
    )
    assert decided.status_code == 200, decided.text
    body = decided.json()
    assert body["status"] == "ACCEPTED"
    assert body["final_decision"] == "ACCEPT"

    def left_queue():
        q = api_client.get("/api/uw/queue", headers=underwriter_headers)
        q.raise_for_status()
        return None if any(c["id"] == pending["id"] for c in q.json()) else True

    wait_until(left_queue, timeout=10, desc="pending case removed from review queue")
