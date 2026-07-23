"""Claim document upload, list, download, and role scoping."""

from __future__ import annotations

import io

import pytest
from helpers import login

pytestmark = [pytest.mark.api, pytest.mark.story("KAN-7")]


def _open_claim(api_client, headers: dict[str, str], *, party_id: str | None = None) -> dict:
    """Open a claim on the seeded demo AUTO policy (or first ACTIVE policy)."""
    policies = api_client.get("/api/policies", headers=headers).json()
    active = next((p for p in policies if p["status"] == "ACTIVE"), None)
    assert active, "Expected an active policy for document tests"
    body = {
        "policy_id": active["id"],
        "party_id": party_id or active["party_id"],
        "product_code": active["product_code"],
        "description": "Document evidence test claim",
        "loss_date": "2026-07-21",
        "reserve_amount": 0,
    }
    resp = api_client.post("/api/claims", headers=headers, json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_upload_list_download_delete_document(api_client, claims_headers):
    claim = _open_claim(api_client, claims_headers)
    assert claim.get("document_count", 0) == 0

    content = b"%PDF-1.4 demo police report"
    files = {"file": ("scene-photo.pdf", io.BytesIO(content), "application/pdf")}
    data = {"category": "POLICE_REPORT"}
    upload = api_client.post(
        f"/api/claims/{claim['id']}/documents",
        headers=claims_headers,
        files=files,
        data=data,
    )
    assert upload.status_code == 201, upload.text
    doc = upload.json()
    assert doc["filename"] == "scene-photo.pdf"
    assert doc["category"] == "POLICE_REPORT"
    assert doc["size_bytes"] == len(content)
    assert doc["content_type"] == "application/pdf"

    listed = api_client.get(f"/api/claims/{claim['id']}/documents", headers=claims_headers)
    assert listed.status_code == 200
    assert any(d["id"] == doc["id"] for d in listed.json())

    refreshed = api_client.get(f"/api/claims/{claim['id']}", headers=claims_headers).json()
    assert refreshed["document_count"] == 1

    download = api_client.get(
        f"/api/claims/{claim['id']}/documents/{doc['id']}",
        headers=claims_headers,
    )
    assert download.status_code == 200
    assert download.content == content
    assert "attachment" in download.headers.get("content-disposition", "").lower()

    deleted = api_client.delete(
        f"/api/claims/{claim['id']}/documents/{doc['id']}",
        headers=claims_headers,
    )
    assert deleted.status_code == 204
    empty = api_client.get(f"/api/claims/{claim['id']}/documents", headers=claims_headers).json()
    assert empty == []


def test_policyholder_can_upload_own_claim_document(api_client, policyholder_headers):
    party_id = login(api_client, "policyholder")["party_id"]
    claim = _open_claim(api_client, policyholder_headers, party_id=party_id)

    files = {"file": ("bumper.jpg", io.BytesIO(b"\xff\xd8\xff fakejpeg"), "image/jpeg")}
    data = {"category": "PHOTO"}
    upload = api_client.post(
        f"/api/claims/{claim['id']}/documents",
        headers=policyholder_headers,
        files=files,
        data=data,
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["category"] == "PHOTO"

    listed = api_client.get(
        f"/api/claims/{claim['id']}/documents", headers=policyholder_headers
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_reject_unsupported_type_and_oversize(api_client, claims_headers):
    claim = _open_claim(api_client, claims_headers)

    bad_type = api_client.post(
        f"/api/claims/{claim['id']}/documents",
        headers=claims_headers,
        files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
        data={"category": "OTHER"},
    )
    assert bad_type.status_code == 400

    huge = b"x" * (5 * 1024 * 1024 + 1)
    oversized = api_client.post(
        f"/api/claims/{claim['id']}/documents",
        headers=claims_headers,
        files={"file": ("huge.txt", io.BytesIO(huge), "text/plain")},
        data={"category": "OTHER"},
    )
    assert oversized.status_code == 413


def test_policyholder_cannot_delete_document(api_client, policyholder_headers, claims_headers):
    party_id = login(api_client, "policyholder")["party_id"]
    claim = _open_claim(api_client, policyholder_headers, party_id=party_id)
    upload = api_client.post(
        f"/api/claims/{claim['id']}/documents",
        headers=policyholder_headers,
        files={"file": ("note.txt", io.BytesIO(b"hello"), "text/plain")},
        data={"category": "OTHER"},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    denied = api_client.delete(
        f"/api/claims/{claim['id']}/documents/{doc_id}",
        headers=policyholder_headers,
    )
    assert denied.status_code == 403

    # Staff can still delete
    ok = api_client.delete(
        f"/api/claims/{claim['id']}/documents/{doc_id}",
        headers=claims_headers,
    )
    assert ok.status_code == 204
