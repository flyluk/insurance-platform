from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import UnderwritingCase
from app.schemas import CaseOut, DecisionIn, DomainEventIn
from insurance_shared.auth import make_auth_dependency
from insurance_shared.events import enqueue_event
from insurance_shared.metrics import record_event
from insurance_shared.parties import snapshot_incomplete, summary_from_snapshot
from insurance_shared.party_client import enrich_snapshot, fetch_parties

router = APIRouter(tags=["underwriting"])
auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm)
uw_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "underwriter", "admin")


def _party_cache_for_cases(cases: list[UnderwritingCase]) -> dict:
    need: set[str] = set()
    for case in cases:
        owner_id = case.party_id
        insured_id = case.insured_party_id or case.party_id
        if snapshot_incomplete(case.owner_snapshot):
            need.add(owner_id)
        if snapshot_incomplete(case.insured_snapshot):
            need.add(insured_id)
    return fetch_parties(settings.new_business_url, need)


def _case_out(case: UnderwritingCase, cache: dict | None = None) -> CaseOut:
    data = CaseOut.model_validate(case)
    insured_id = case.insured_party_id or case.party_id
    party_cache = cache if cache is not None else _party_cache_for_cases([case])
    owner_snap = enrich_snapshot(case.owner_snapshot, party_id=case.party_id, cache=party_cache)
    insured_snap = enrich_snapshot(case.insured_snapshot, party_id=insured_id, cache=party_cache)
    data.insured_party_id = insured_id
    data.owner = summary_from_snapshot(owner_snap, fallback_id=case.party_id)
    data.insured = summary_from_snapshot(insured_snap, fallback_id=insured_id)
    return data


def _emit_decision(db: Session, case: UnderwritingCase) -> None:
    payload = {
        "application_id": case.application_id,
        "case_id": case.id,
        "party_id": case.party_id,
        "owner_party_id": case.party_id,
        "insured_party_id": case.insured_party_id or case.party_id,
        "owner": case.owner_snapshot or {"id": case.party_id},
        "insured": case.insured_snapshot or {"id": case.insured_party_id or case.party_id},
        "product_code": case.product_code,
        "annual_premium": case.annual_premium,
        "risk_attributes": case.risk_attributes or {},
        "decision": case.final_decision,
        "reason": case.reason,
    }
    enqueue_event(
        db,
        event_type="UnderwritingDecided",
        aggregate_type="application",
        aggregate_id=case.application_id,
        payload=payload,
    )
    record_event("UnderwritingDecided", "produced", settings.service_name)


@router.post("/events")
def consume_event(body: DomainEventIn, db: Session = Depends(get_db)):
    from app.event_handlers import handle_domain_event

    handle_domain_event(body.model_dump())
    return {"status": "ok"}


@router.get("/api/uw/cases", response_model=list[CaseOut])
def list_cases(status: str | None = None, db: Session = Depends(get_db), _=Depends(auth)):
    q = db.query(UnderwritingCase).order_by(UnderwritingCase.created_at.desc())
    if status:
        q = q.filter(UnderwritingCase.status == status)
    cases = q.limit(200).all()
    cache = _party_cache_for_cases(cases)
    return [_case_out(c, cache) for c in cases]


@router.get("/api/uw/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db), _=Depends(auth)):
    case = db.get(UnderwritingCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return _case_out(case)


@router.get("/api/uw/queue", response_model=list[CaseOut])
def referral_queue(db: Session = Depends(get_db), _=Depends(uw_auth)):
    cases = (
        db.query(UnderwritingCase)
        .filter(UnderwritingCase.status == "REFERRED")
        .order_by(UnderwritingCase.created_at)
        .all()
    )
    cache = _party_cache_for_cases(cases)
    return [_case_out(c, cache) for c in cases]


@router.post("/api/uw/cases/{case_id}/decide", response_model=CaseOut)
def decide(case_id: str, body: DecisionIn, db: Session = Depends(get_db), _=Depends(uw_auth)):
    case = db.get(UnderwritingCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    if case.status not in ("REFERRED", "PENDING"):
        raise HTTPException(400, f"Case already decided: {case.status}")
    case.final_decision = body.decision
    case.reason = body.reason or case.reason
    case.status = "ACCEPTED" if body.decision == "ACCEPT" else ("DECLINED" if body.decision == "DECLINE" else "REFERRED")
    if body.decision == "REFER":
        raise HTTPException(400, "Use ACCEPT or DECLINE for final decision")
    db.flush()
    _emit_decision(db, case)
    db.commit()
    db.refresh(case)
    return _case_out(case)
