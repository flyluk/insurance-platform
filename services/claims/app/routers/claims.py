import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Claim
from app.schemas import ClaimCreate, ClaimOut, ReserveUpdate, SettleIn
from insurance_shared.auth import make_auth_dependency
from insurance_shared.events import enqueue_event
from insurance_shared.metrics import record_event

router = APIRouter(prefix="/api/claims", tags=["claims"])
auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm)
claims_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "claims", "admin")
open_auth = make_auth_dependency(
    settings.jwt_secret, settings.jwt_algorithm, "claims", "admin", "policyholder"
)


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


@router.post("", response_model=ClaimOut)
def open_claim(
    body: ClaimCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: dict = Depends(open_auth),
):
    party_id = body.party_id
    product_code = body.product_code
    if _is_policyholder(user):
        party_id = _require_party(user)
        policy = _fetch_policy(body.policy_id, request.headers.get("authorization"))
        if policy.get("party_id") != party_id:
            raise HTTPException(403, "Cannot open a claim on another party's policy")
        if policy.get("status") != "ACTIVE":
            raise HTTPException(400, "Policy must be ACTIVE to open a claim")
        product_code = policy.get("product_code") or product_code

    claim = Claim(
        claim_number=f"CLM-{uuid.uuid4().hex[:8].upper()}",
        policy_id=body.policy_id,
        party_id=party_id,
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
    return claim


@router.get("", response_model=list[ClaimOut])
def list_claims(db: Session = Depends(get_db), user: dict = Depends(auth)):
    q = db.query(Claim)
    if _is_policyholder(user):
        q = q.filter(Claim.party_id == _require_party(user))
    return q.order_by(Claim.created_at.desc()).limit(200).all()


@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(claim_id: str, db: Session = Depends(get_db), user: dict = Depends(auth)):
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    if _is_policyholder(user) and claim.party_id != _require_party(user):
        raise HTTPException(404, "Claim not found")
    return claim


@router.post("/{claim_id}/reserve", response_model=ClaimOut)
def set_reserve(claim_id: str, body: ReserveUpdate, db: Session = Depends(get_db), _=Depends(claims_auth)):
    claim = db.get(Claim, claim_id)
    if not claim or claim.status in ("SETTLED", "DENIED"):
        raise HTTPException(400, "Claim not reservable")
    claim.reserve_amount = body.reserve_amount
    claim.status = "RESERVED"
    db.commit()
    db.refresh(claim)
    return claim


@router.post("/{claim_id}/investigate", response_model=ClaimOut)
def investigate(claim_id: str, db: Session = Depends(get_db), _=Depends(claims_auth)):
    claim = db.get(Claim, claim_id)
    if not claim or claim.status in ("SETTLED", "DENIED"):
        raise HTTPException(400, "Invalid claim state")
    claim.status = "INVESTIGATING"
    db.commit()
    db.refresh(claim)
    return claim


@router.post("/{claim_id}/settle", response_model=ClaimOut)
def settle(claim_id: str, body: SettleIn, db: Session = Depends(get_db), _=Depends(claims_auth)):
    claim = db.get(Claim, claim_id)
    if not claim or claim.status in ("SETTLED", "DENIED"):
        raise HTTPException(400, "Claim not settleable")
    claim.settlement_amount = body.settlement_amount
    claim.status = "SETTLED"
    db.flush()
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
            "product_code": claim.product_code,
            "amount": body.settlement_amount,
        },
    )
    record_event("ClaimPaymentRequested", "produced", settings.service_name)
    db.commit()
    db.refresh(claim)
    return claim


@router.post("/{claim_id}/deny", response_model=ClaimOut)
def deny(claim_id: str, db: Session = Depends(get_db), _=Depends(claims_auth)):
    claim = db.get(Claim, claim_id)
    if not claim or claim.status in ("SETTLED", "DENIED"):
        raise HTTPException(400, "Claim not deniable")
    claim.status = "DENIED"
    db.commit()
    db.refresh(claim)
    return claim
