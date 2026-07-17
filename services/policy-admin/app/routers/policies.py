import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Endorsement, Policy
from app.schemas import DomainEventIn, EndorsementCreate, EndorsementOut, PolicyOut
from insurance_shared.auth import make_auth_dependency
from insurance_shared.events import already_processed, enqueue_event, mark_processed
from insurance_shared.metrics import record_event

router = APIRouter(tags=["policy-admin"])
auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm)
agent_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "agent", "admin")


def _policy_number(product_code: str) -> str:
    return f"{product_code}-{uuid.uuid4().hex[:8].upper()}"


def _emit_bound(db: Session, policy: Policy) -> None:
    payload = {
        "policy_id": policy.id,
        "policy_number": policy.policy_number,
        "application_id": policy.application_id,
        "party_id": policy.party_id,
        "product_code": policy.product_code,
        "annual_premium": policy.annual_premium,
        "effective_date": policy.effective_date.isoformat(),
        "expiry_date": policy.expiry_date.isoformat(),
    }
    enqueue_event(
        db,
        event_type="PolicyBound",
        aggregate_type="policy",
        aggregate_id=policy.id,
        payload=payload,
        destination_url=settings.new_business_events_url,
    )
    enqueue_event(
        db,
        event_type="PremiumDue",
        aggregate_type="policy",
        aggregate_id=policy.id,
        payload={**payload, "amount": policy.annual_premium, "invoice_type": "PREMIUM"},
        destination_url=settings.finance_events_url,
    )
    record_event("PolicyBound", "produced", settings.service_name)
    record_event("PremiumDue", "produced", settings.service_name)


@router.post("/events")
def consume_event(body: DomainEventIn, db: Session = Depends(get_db)):
    if already_processed(db, body.event_id):
        return {"status": "duplicate"}

    if body.event_type == "UnderwritingDecided" and body.payload.get("decision") == "ACCEPT":
        app_id = body.payload["application_id"]
        existing = db.query(Policy).filter(Policy.application_id == app_id).first()
        if not existing:
            now = datetime.now(timezone.utc)
            policy = Policy(
                policy_number=_policy_number(body.payload["product_code"]),
                application_id=app_id,
                party_id=body.payload["party_id"],
                product_code=body.payload["product_code"],
                status="ACTIVE",
                annual_premium=float(body.payload["annual_premium"]),
                risk_attributes=body.payload.get("risk_attributes") or {},
                effective_date=now,
                expiry_date=now + timedelta(days=365),
            )
            db.add(policy)
            db.flush()
            _emit_bound(db, policy)
            record_event("UnderwritingDecided", "consumed", settings.service_name)

    mark_processed(db, body.event_id, body.event_type)
    db.commit()
    return {"status": "ok"}


@router.get("/api/policies", response_model=list[PolicyOut])
def list_policies(db: Session = Depends(get_db), _=Depends(auth)):
    return db.query(Policy).order_by(Policy.created_at.desc()).limit(200).all()


@router.get("/api/policies/{policy_id}", response_model=PolicyOut)
def get_policy(policy_id: str, db: Session = Depends(get_db), _=Depends(auth)):
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(404, "Policy not found")
    return policy


@router.post("/api/policies/{policy_id}/endorse", response_model=PolicyOut)
def endorse(policy_id: str, body: EndorsementCreate, db: Session = Depends(get_db), _=Depends(agent_auth)):
    policy = db.get(Policy, policy_id)
    if not policy or policy.status != "ACTIVE":
        raise HTTPException(400, "Active policy required")
    end = Endorsement(
        policy_id=policy.id,
        endorsement_type=body.endorsement_type,
        description=body.description,
        premium_delta=body.premium_delta,
    )
    db.add(end)
    db.flush()
    policy.annual_premium = round(policy.annual_premium + body.premium_delta, 2)
    if body.risk_attributes:
        merged = dict(policy.risk_attributes or {})
        merged.update(body.risk_attributes)
        policy.risk_attributes = merged
    if body.premium_delta:
        enqueue_event(
            db,
            event_type="PremiumDue",
            aggregate_type="policy",
            aggregate_id=policy.id,
            payload={
                "policy_id": policy.id,
                "policy_number": policy.policy_number,
                "party_id": policy.party_id,
                "product_code": policy.product_code,
                "amount": body.premium_delta,
                "invoice_type": "ENDORSEMENT",
                "endorsement_id": end.id,
            },
            destination_url=settings.finance_events_url,
        )
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/api/policies/{policy_id}/renew", response_model=PolicyOut)
def renew(policy_id: str, db: Session = Depends(get_db), _=Depends(agent_auth)):
    policy = db.get(Policy, policy_id)
    if not policy or policy.status != "ACTIVE":
        raise HTTPException(400, "Active policy required")
    policy.effective_date = policy.expiry_date
    policy.expiry_date = policy.expiry_date + timedelta(days=365)
    enqueue_event(
        db,
        event_type="PremiumDue",
        aggregate_type="policy",
        aggregate_id=policy.id,
        payload={
            "policy_id": policy.id,
            "policy_number": policy.policy_number,
            "party_id": policy.party_id,
            "product_code": policy.product_code,
            "amount": policy.annual_premium,
            "invoice_type": "RENEWAL",
            "effective_date": policy.effective_date.isoformat(),
            "expiry_date": policy.expiry_date.isoformat(),
        },
        destination_url=settings.finance_events_url,
    )
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/api/policies/{policy_id}/cancel", response_model=PolicyOut)
def cancel(policy_id: str, db: Session = Depends(get_db), _=Depends(agent_auth)):
    policy = db.get(Policy, policy_id)
    if not policy or policy.status != "ACTIVE":
        raise HTTPException(400, "Active policy required")
    policy.status = "CANCELLED"
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/api/policies/{policy_id}/endorsements", response_model=list[EndorsementOut])
def list_endorsements(policy_id: str, db: Session = Depends(get_db), _=Depends(auth)):
    return (
        db.query(Endorsement)
        .filter(Endorsement.policy_id == policy_id)
        .order_by(Endorsement.created_at.desc())
        .all()
    )
