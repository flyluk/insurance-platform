import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Endorsement, Policy
from app.rating_client import RatingError, rate_policy_premium
from app.schemas import (
    CancelPreviewOut,
    DomainEventIn,
    EndorsePreviewIn,
    EndorsePreviewOut,
    EndorsementCreate,
    EndorsementOut,
    PolicyOut,
)
from insurance_shared.auth import make_auth_dependency
from insurance_shared.events import enqueue_event
from insurance_shared.metrics import record_event
from insurance_shared.proration import (
    prorate_delta,
    remaining_days,
    remaining_fraction,
    term_days,
    unearned_premium,
)
from insurance_shared.parties import snapshot_incomplete, summary_from_snapshot
from insurance_shared.party_client import enrich_snapshot, fetch_parties

router = APIRouter(tags=["policy-admin"])
auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm)
agent_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "agent", "admin")
admin_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "admin")


def _is_policyholder(user: dict) -> bool:
    return user.get("role") == "policyholder"


def _require_party(user: dict) -> str:
    party_id = user.get("party_id")
    if not party_id:
        raise HTTPException(403, "Policyholder account is not linked to a party")
    return party_id


def _party_cache_for_policies(policies: list[Policy]) -> dict:
    need: set[str] = set()
    for policy in policies:
        owner_id = policy.owner_party_id or policy.party_id
        insured_id = policy.insured_party_id or policy.party_id
        if snapshot_incomplete(policy.owner_snapshot):
            need.add(owner_id)
        if snapshot_incomplete(policy.insured_snapshot):
            need.add(insured_id)
    return fetch_parties(settings.new_business_url, need)


def _policy_out(policy: Policy, cache: dict | None = None) -> PolicyOut:
    owner_id = policy.owner_party_id or policy.party_id
    insured_id = policy.insured_party_id or policy.party_id
    party_cache = cache if cache is not None else _party_cache_for_policies([policy])
    owner_snap = enrich_snapshot(policy.owner_snapshot, party_id=owner_id, cache=party_cache)
    insured_snap = enrich_snapshot(policy.insured_snapshot, party_id=insured_id, cache=party_cache)
    data = PolicyOut.model_validate(policy)
    data.owner_party_id = owner_id
    data.insured_party_id = insured_id
    data.owner = summary_from_snapshot(owner_snap, fallback_id=owner_id)
    data.insured = summary_from_snapshot(insured_snap, fallback_id=insured_id)
    return data



def _emit_bound(db: Session, policy: Policy) -> None:
    payload = {
        "policy_id": policy.id,
        "policy_number": policy.policy_number,
        "application_id": policy.application_id,
        "party_id": policy.party_id,
        "owner_party_id": policy.owner_party_id or policy.party_id,
        "insured_party_id": policy.insured_party_id or policy.party_id,
        "owner": policy.owner_snapshot or {"id": policy.party_id},
        "insured": policy.insured_snapshot or {"id": policy.insured_party_id or policy.party_id},
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
    )
    enqueue_event(
        db,
        event_type="PremiumDue",
        aggregate_type="policy",
        aggregate_id=policy.id,
        payload={**payload, "amount": policy.annual_premium, "invoice_type": "PREMIUM"},
    )
    record_event("PolicyBound", "produced", settings.service_name)
    record_event("PremiumDue", "produced", settings.service_name)


def _emit_premium_or_credit(
    db: Session,
    policy: Policy,
    *,
    amount: float,
    invoice_type: str,
    extra: dict | None = None,
) -> None:
    if abs(amount) < 0.01:
        return
    payload = {
        "policy_id": policy.id,
        "policy_number": policy.policy_number,
        "party_id": policy.party_id,
        "owner_party_id": policy.owner_party_id or policy.party_id,
        "insured_party_id": policy.insured_party_id or policy.party_id,
        "owner": policy.owner_snapshot or {"id": policy.party_id},
        "insured": policy.insured_snapshot or {"id": policy.insured_party_id or policy.party_id},
        "product_code": policy.product_code,
        "amount": abs(round(amount, 2)),
        "invoice_type": invoice_type,
        **(extra or {}),
    }
    if amount > 0:
        enqueue_event(
            db,
            event_type="PremiumDue",
            aggregate_type="policy",
            aggregate_id=policy.id,
            payload=payload,
        )
        record_event("PremiumDue", "produced", settings.service_name)
    else:
        enqueue_event(
            db,
            event_type="PremiumCredit",
            aggregate_type="policy",
            aggregate_id=policy.id,
            payload=payload,
        )
        record_event("PremiumCredit", "produced", settings.service_name)


def _compute_endorse(
    policy: Policy,
    body: EndorsementCreate | EndorsePreviewIn,
) -> tuple[dict, float, float, float]:
    merged = dict(policy.risk_attributes or {})
    if body.risk_attributes:
        merged.update(body.risk_attributes)
        # Preserve nested product_selection unless explicitly replaced
        if "product_selection" not in (body.risk_attributes or {}) and policy.risk_attributes:
            if "product_selection" in (policy.risk_attributes or {}):
                merged["product_selection"] = policy.risk_attributes["product_selection"]

    if body.re_rate:
        try:
            new_annual = rate_policy_premium(policy.product_code, merged)
        except RatingError as exc:
            raise HTTPException(400, str(exc)) from exc
        annual_delta = round(new_annual - policy.annual_premium, 2)
    else:
        annual_delta = round(float(body.premium_delta), 2)
        new_annual = round(policy.annual_premium + annual_delta, 2)

    billed = prorate_delta(annual_delta, policy.effective_date, policy.expiry_date)
    return merged, new_annual, annual_delta, billed


@router.post("/events")
def consume_event(body: DomainEventIn, db: Session = Depends(get_db)):
    from app.event_handlers import handle_domain_event

    handle_domain_event(body.model_dump())
    return {"status": "ok"}


@router.get("/api/policies", response_model=list[PolicyOut])
def list_policies(db: Session = Depends(get_db), user: dict = Depends(auth)):
    q = db.query(Policy)
    if _is_policyholder(user):
        q = q.filter(Policy.party_id == _require_party(user))
    policies = q.order_by(Policy.created_at.desc()).limit(200).all()
    cache = _party_cache_for_policies(policies)
    return [_policy_out(p, cache) for p in policies]


@router.get("/api/policies/{policy_id}", response_model=PolicyOut)
def get_policy(policy_id: str, db: Session = Depends(get_db), user: dict = Depends(auth)):
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(404, "Policy not found")
    if _is_policyholder(user) and policy.party_id != _require_party(user):
        raise HTTPException(404, "Policy not found")
    return _policy_out(policy)


@router.get("/api/policies/{policy_id}/cancel-preview", response_model=CancelPreviewOut)
def cancel_preview(policy_id: str, db: Session = Depends(get_db), _=Depends(agent_auth)):
    policy = db.get(Policy, policy_id)
    if not policy or policy.status != "ACTIVE":
        raise HTTPException(400, "Active policy required")
    now = datetime.now(timezone.utc)
    return CancelPreviewOut(
        policy_id=policy.id,
        annual_premium=policy.annual_premium,
        term_days=term_days(policy.effective_date, policy.expiry_date),
        remaining_days=remaining_days(policy.effective_date, policy.expiry_date, now),
        remaining_fraction=remaining_fraction(policy.effective_date, policy.expiry_date, now),
        unearned_premium=unearned_premium(
            policy.annual_premium, policy.effective_date, policy.expiry_date, now
        ),
    )


@router.post("/api/policies/{policy_id}/endorse-preview", response_model=EndorsePreviewOut)
def endorse_preview(
    policy_id: str,
    body: EndorsePreviewIn,
    db: Session = Depends(get_db),
    _=Depends(admin_auth),
):
    policy = db.get(Policy, policy_id)
    if not policy or policy.status != "ACTIVE":
        raise HTTPException(400, "Active policy required")
    _, new_annual, annual_delta, billed = _compute_endorse(policy, body)
    return EndorsePreviewOut(
        policy_id=policy.id,
        current_annual=policy.annual_premium,
        new_annual=new_annual,
        annual_delta=annual_delta,
        remaining_fraction=remaining_fraction(policy.effective_date, policy.expiry_date),
        billed_amount=billed,
    )


@router.post("/api/policies/{policy_id}/endorse", response_model=PolicyOut)
def endorse(policy_id: str, body: EndorsementCreate, db: Session = Depends(get_db), _=Depends(admin_auth)):
    policy = db.get(Policy, policy_id)
    if not policy or policy.status != "ACTIVE":
        raise HTTPException(400, "Active policy required")

    merged, new_annual, annual_delta, billed = _compute_endorse(policy, body)
    end = Endorsement(
        policy_id=policy.id,
        endorsement_type=body.endorsement_type,
        description=body.description,
        premium_delta=annual_delta,
        billed_amount=billed,
    )
    db.add(end)
    db.flush()
    policy.annual_premium = new_annual
    policy.risk_attributes = merged
    if abs(billed) >= 0.01:
        _emit_premium_or_credit(
            db,
            policy,
            amount=billed,
            invoice_type="ENDORSEMENT",
            extra={"endorsement_id": end.id, "annual_delta": annual_delta},
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
    )
    record_event("PremiumDue", "produced", settings.service_name)
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/api/policies/{policy_id}/cancel", response_model=PolicyOut)
def cancel(policy_id: str, db: Session = Depends(get_db), _=Depends(agent_auth)):
    policy = db.get(Policy, policy_id)
    if not policy or policy.status != "ACTIVE":
        raise HTTPException(400, "Active policy required")
    now = datetime.now(timezone.utc)
    refund = unearned_premium(policy.annual_premium, policy.effective_date, policy.expiry_date, now)
    policy.status = "CANCELLED"
    policy.cancelled_at = now
    policy.cancellation_refund = refund
    payload = {
        "policy_id": policy.id,
        "policy_number": policy.policy_number,
        "party_id": policy.party_id,
        "product_code": policy.product_code,
        "cancelled_at": now.isoformat(),
        "unearned_premium": refund,
        "remaining_fraction": remaining_fraction(policy.effective_date, policy.expiry_date, now),
        "annual_premium": policy.annual_premium,
    }
    enqueue_event(
        db,
        event_type="PolicyCancelled",
        aggregate_type="policy",
        aggregate_id=policy.id,
        payload=payload,
    )
    record_event("PolicyCancelled", "produced", settings.service_name)
    if refund >= 0.01:
        _emit_premium_or_credit(
            db,
            policy,
            amount=-refund,
            invoice_type="CANCELLATION",
            extra={"cancelled_at": now.isoformat()},
        )
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/api/policies/{policy_id}/endorsements", response_model=list[EndorsementOut])
def list_endorsements(policy_id: str, db: Session = Depends(get_db), user: dict = Depends(auth)):
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(404, "Policy not found")
    if _is_policyholder(user) and policy.party_id != _require_party(user):
        raise HTTPException(404, "Policy not found")
    return (
        db.query(Endorsement)
        .filter(Endorsement.policy_id == policy_id)
        .order_by(Endorsement.created_at.desc())
        .all()
    )
