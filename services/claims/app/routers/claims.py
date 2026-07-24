import uuid

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Claim, ClaimDocument
from app.schemas import ClaimCreate, ClaimDocumentOut, ClaimOut, ReserveUpdate, SettleIn
from insurance_shared.auth import make_auth_dependency
from insurance_shared.events import enqueue_event
from insurance_shared.metrics import record_event
from insurance_shared.parties import snapshot_incomplete, summary_from_snapshot
from insurance_shared.party_client import enrich_snapshot, fetch_parties

router = APIRouter(prefix="/api/claims", tags=["claims"])
auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm)
claims_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "claims", "admin")
open_auth = make_auth_dependency(
    settings.jwt_secret, settings.jwt_algorithm, "claims", "admin", "policyholder"
)
doc_write_auth = make_auth_dependency(
    settings.jwt_secret, settings.jwt_algorithm, "claims", "admin", "policyholder"
)

ALLOWED_CATEGORIES = {"PHOTO", "POLICE_REPORT", "MEDICAL", "INVOICE", "OTHER"}
APPROVAL_THRESHOLD = 10_000.0
CLOSED_STATUSES = ("SETTLED", "DENIED")


def _is_policyholder(user: dict) -> bool:
    return user.get("role") == "policyholder"


def _require_party(user: dict) -> str:
    party_id = user.get("party_id")
    if not party_id:
        raise HTTPException(403, "Policyholder account is not linked to a party")
    return party_id


def _fetch_policy(policy_id: str, authorization: str | None) -> dict:
    headers = {"Authorization": authorization} if authorization else {}
    try:
        resp = httpx.get(
            f"{settings.policy_admin_url}/api/policies/{policy_id}",
            headers=headers,
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Unable to verify policy") from exc
    if resp.status_code == 404:
        raise HTTPException(404, "Policy not found")
    if resp.status_code >= 400:
        raise HTTPException(502, "Unable to verify policy")
    return resp.json()


def _get_claim_for_user(db: Session, claim_id: str, user: dict) -> Claim:
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    if _is_policyholder(user) and claim.party_id != _require_party(user):
        raise HTTPException(404, "Claim not found")
    return claim


def _document_counts(db: Session, claim_ids: list[str]) -> dict[str, int]:
    if not claim_ids:
        return {}
    rows = (
        db.query(ClaimDocument.claim_id, func.count(ClaimDocument.id))
        .filter(ClaimDocument.claim_id.in_(claim_ids))
        .group_by(ClaimDocument.claim_id)
        .all()
    )
    return {claim_id: count for claim_id, count in rows}


def _party_cache_for_claims(claims: list[Claim]) -> dict:
    need: set[str] = set()
    for claim in claims:
        owner_id = claim.party_id
        insured_id = claim.insured_party_id or claim.party_id
        if snapshot_incomplete(claim.owner_snapshot):
            need.add(owner_id)
        if snapshot_incomplete(claim.insured_snapshot):
            need.add(insured_id)
    return fetch_parties(settings.new_business_url, need)


def _claim_out(claim: Claim, document_count: int = 0, cache: dict | None = None) -> ClaimOut:
    owner_id = claim.party_id
    insured_id = claim.insured_party_id or claim.party_id
    party_cache = cache if cache is not None else _party_cache_for_claims([claim])
    owner_snap = enrich_snapshot(claim.owner_snapshot, party_id=owner_id, cache=party_cache)
    insured_snap = enrich_snapshot(claim.insured_snapshot, party_id=insured_id, cache=party_cache)
    return ClaimOut(
        id=claim.id,
        claim_number=claim.claim_number,
        policy_id=claim.policy_id,
        party_id=claim.party_id,
        insured_party_id=insured_id,
        product_code=claim.product_code,
        status=claim.status,
        description=claim.description,
        loss_date=claim.loss_date,
        reserve_amount=claim.reserve_amount,
        settlement_amount=claim.settlement_amount,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        document_count=document_count,
        owner=summary_from_snapshot(owner_snap, fallback_id=owner_id),
        insured=summary_from_snapshot(insured_snap, fallback_id=insured_id),
    )


def _allowed_content_types() -> set[str]:
    return {t.strip().lower() for t in settings.allowed_document_types.split(",") if t.strip()}


@router.post("", response_model=ClaimOut)
def open_claim(
    body: ClaimCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(open_auth),
):
    auth_header = request.headers.get("authorization")
    policy = _fetch_policy(body.policy_id, auth_header)
    if policy.get("status") != "ACTIVE":
        raise HTTPException(400, "Policy must be ACTIVE to open a claim")

    party_id = policy.get("owner_party_id") or policy.get("party_id") or body.party_id
    insured_party_id = policy.get("insured_party_id") or party_id
    product_code = policy.get("product_code") or body.product_code
    owner_snap = policy.get("owner") or {"id": party_id}
    insured_snap = policy.get("insured") or {"id": insured_party_id}
    if _is_policyholder(user):
        linked = _require_party(user)
        if policy.get("party_id") != linked and policy.get("owner_party_id") != linked:
            raise HTTPException(403, "Cannot open a claim on another party's policy")
        party_id = linked

    claim = Claim(
        claim_number=f"CLM-{uuid.uuid4().hex[:8].upper()}",
        policy_id=body.policy_id,
        party_id=party_id,
        insured_party_id=insured_party_id,
        owner_snapshot=owner_snap if isinstance(owner_snap, dict) else {"id": party_id},
        insured_snapshot=insured_snap if isinstance(insured_snap, dict) else {"id": insured_party_id},
        product_code=product_code,
        description=body.description,
        loss_date=body.loss_date,
        reserve_amount=body.reserve_amount,
        status="INVESTIGATING" if body.reserve_amount else "OPEN",
    )
    if body.reserve_amount:
        claim.status = "RESERVED"
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return _claim_out(claim, 0)


@router.get("", response_model=list[ClaimOut])
def list_claims(db: Session = Depends(get_db), user: dict = Depends(auth)):
    q = db.query(Claim)
    if _is_policyholder(user):
        q = q.filter(Claim.party_id == _require_party(user))
    claims = q.order_by(Claim.created_at.desc()).limit(200).all()
    counts = _document_counts(db, [c.id for c in claims])
    cache = _party_cache_for_claims(claims)
    return [_claim_out(c, counts.get(c.id, 0), cache) for c in claims]


@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(claim_id: str, db: Session = Depends(get_db), user: dict = Depends(auth)):
    claim = _get_claim_for_user(db, claim_id, user)
    counts = _document_counts(db, [claim.id])
    return _claim_out(claim, counts.get(claim.id, 0))


@router.post("/{claim_id}/documents", response_model=ClaimDocumentOut, status_code=201)
async def upload_document(
    claim_id: str,
    file: UploadFile = File(...),
    category: str = Form("OTHER"),
    db: Session = Depends(get_db),
    user: dict = Depends(doc_write_auth),
):
    claim = _get_claim_for_user(db, claim_id, user)
    if claim.status in CLOSED_STATUSES and _is_policyholder(user):
        raise HTTPException(400, "Cannot add documents to a closed claim")

    cat = (category or "OTHER").upper()
    if cat not in ALLOWED_CATEGORIES:
        raise HTTPException(400, f"Invalid category. Allowed: {sorted(ALLOWED_CATEGORIES)}")

    content_type = (file.content_type or "application/octet-stream").lower()
    if content_type not in _allowed_content_types():
        raise HTTPException(
            400,
            f"Unsupported file type '{content_type}'. Allowed: {sorted(_allowed_content_types())}",
        )

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > settings.max_document_bytes:
        raise HTTPException(
            413,
            f"File exceeds maximum size of {settings.max_document_bytes} bytes",
        )

    filename = (file.filename or "upload.bin").strip()[:255] or "upload.bin"
    doc = ClaimDocument(
        claim_id=claim.id,
        filename=filename,
        content_type=content_type,
        category=cat,
        size_bytes=len(data),
        uploaded_by=user.get("email"),
        uploaded_by_role=user.get("role"),
        content=data,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return ClaimDocumentOut.model_validate(doc)


@router.get("/{claim_id}/documents", response_model=list[ClaimDocumentOut])
def list_documents(claim_id: str, db: Session = Depends(get_db), user: dict = Depends(auth)):
    _get_claim_for_user(db, claim_id, user)
    docs = (
        db.query(ClaimDocument)
        .filter(ClaimDocument.claim_id == claim_id)
        .order_by(ClaimDocument.created_at.desc())
        .all()
    )
    return [ClaimDocumentOut.model_validate(d) for d in docs]


@router.get("/{claim_id}/documents/{document_id}")
def download_document(
    claim_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(auth),
):
    _get_claim_for_user(db, claim_id, user)
    doc = db.get(ClaimDocument, document_id)
    if not doc or doc.claim_id != claim_id:
        raise HTTPException(404, "Document not found")
    return Response(
        content=doc.content,
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.filename}"',
            "Content-Length": str(doc.size_bytes),
        },
    )


@router.delete("/{claim_id}/documents/{document_id}", status_code=204)
def delete_document(
    claim_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(claims_auth),
):
    _get_claim_for_user(db, claim_id, user)
    doc = db.get(ClaimDocument, document_id)
    if not doc or doc.claim_id != claim_id:
        raise HTTPException(404, "Document not found")
    db.delete(doc)
    db.commit()
    return Response(status_code=204)


def _emit_claim_payment(db: Session, claim: Claim, amount: float) -> None:
    enqueue_event(
        db,
        event_type="ClaimPaymentRequested",
        aggregate_type="claim",
        aggregate_id=claim.id,
        payload={
            "claim_id": claim.id,
            "claim_number": claim.claim_number,
            "policy_id": claim.policy_id,
            "party_id": claim.party_id,
            "insured_party_id": claim.insured_party_id or claim.party_id,
            "owner": claim.owner_snapshot or {"id": claim.party_id},
            "insured": claim.insured_snapshot
            or {"id": claim.insured_party_id or claim.party_id},
            "product_code": claim.product_code,
            "amount": amount,
        },
    )
    record_event("ClaimPaymentRequested", "produced", settings.service_name)


def _finalize_settlement(db: Session, claim: Claim, amount: float) -> ClaimOut:
    claim.settlement_amount = amount
    claim.status = "SETTLED"
    db.flush()
    _emit_claim_payment(db, claim, amount)
    db.commit()
    db.refresh(claim)
    counts = _document_counts(db, [claim.id])
    return _claim_out(claim, counts.get(claim.id, 0))


@router.post("/{claim_id}/reserve", response_model=ClaimOut)
def set_reserve(claim_id: str, body: ReserveUpdate, db: Session = Depends(get_db), _=Depends(claims_auth)):
    claim = db.get(Claim, claim_id)
    if not claim or claim.status in CLOSED_STATUSES or claim.status == "PENDING_APPROVAL":
        raise HTTPException(400, "Claim not reservable")
    claim.reserve_amount = body.reserve_amount
    claim.status = "RESERVED"
    db.commit()
    db.refresh(claim)
    counts = _document_counts(db, [claim.id])
    return _claim_out(claim, counts.get(claim.id, 0))


@router.post("/{claim_id}/investigate", response_model=ClaimOut)
def investigate(claim_id: str, db: Session = Depends(get_db), _=Depends(claims_auth)):
    claim = db.get(Claim, claim_id)
    if not claim or claim.status in CLOSED_STATUSES or claim.status == "PENDING_APPROVAL":
        raise HTTPException(400, "Invalid claim state")
    claim.status = "INVESTIGATING"
    db.commit()
    db.refresh(claim)
    counts = _document_counts(db, [claim.id])
    return _claim_out(claim, counts.get(claim.id, 0))


@router.post("/{claim_id}/settle", response_model=ClaimOut)
def settle(claim_id: str, body: SettleIn, db: Session = Depends(get_db), _=Depends(claims_auth)):
    claim = db.get(Claim, claim_id)
    if not claim or claim.status in CLOSED_STATUSES:
        raise HTTPException(400, "Claim not settleable")
    if claim.status == "PENDING_APPROVAL":
        raise HTTPException(400, "Claim is already awaiting approval")

    amount = float(body.settlement_amount)
    if amount > APPROVAL_THRESHOLD:
        # Large settlements require an explicit approval step before payment.
        claim.settlement_amount = amount
        claim.status = "PENDING_APPROVAL"
        db.commit()
        db.refresh(claim)
        counts = _document_counts(db, [claim.id])
        return _claim_out(claim, counts.get(claim.id, 0))

    return _finalize_settlement(db, claim, amount)


@router.post("/{claim_id}/approve", response_model=ClaimOut)
def approve_settlement(claim_id: str, db: Session = Depends(get_db), _=Depends(claims_auth)):
    """Approve a large settlement (> $10,000) and release payment."""
    claim = db.get(Claim, claim_id)
    if not claim or claim.status != "PENDING_APPROVAL":
        raise HTTPException(400, "Claim is not awaiting approval")
    amount = float(claim.settlement_amount or 0)
    if amount <= APPROVAL_THRESHOLD:
        raise HTTPException(400, "Claim does not require approval")
    return _finalize_settlement(db, claim, amount)


@router.post("/{claim_id}/reject-approval", response_model=ClaimOut)
def reject_settlement_approval(
    claim_id: str, db: Session = Depends(get_db), _=Depends(claims_auth)
):
    """Reject a pending large settlement and return the claim to reservable state."""
    claim = db.get(Claim, claim_id)
    if not claim or claim.status != "PENDING_APPROVAL":
        raise HTTPException(400, "Claim is not awaiting approval")
    claim.settlement_amount = None
    claim.status = "RESERVED" if claim.reserve_amount else "INVESTIGATING"
    db.commit()
    db.refresh(claim)
    counts = _document_counts(db, [claim.id])
    return _claim_out(claim, counts.get(claim.id, 0))


@router.post("/{claim_id}/deny", response_model=ClaimOut)
def deny(claim_id: str, db: Session = Depends(get_db), _=Depends(claims_auth)):
    claim = db.get(Claim, claim_id)
    if not claim or claim.status in CLOSED_STATUSES:
        raise HTTPException(400, "Claim not deniable")
    claim.status = "DENIED"
    claim.settlement_amount = None
    db.commit()
    db.refresh(claim)
    counts = _document_counts(db, [claim.id])
    return _claim_out(claim, counts.get(claim.id, 0))
