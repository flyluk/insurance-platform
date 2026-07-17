from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import UnderwritingCase
from app.schemas import CaseOut, DecisionIn, DomainEventIn
from insurance_shared.auth import make_auth_dependency
from insurance_shared.events import enqueue_event
from insurance_shared.metrics import record_event

router = APIRouter(tags=["underwriting"])
auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm)
uw_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "underwriter", "admin")


def _emit_decision(db: Session, case: UnderwritingCase) -> None:
    payload = {
        "application_id": case.application_id,
        "case_id": case.id,
        "party_id": case.party_id,
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
    return q.limit(200).all()


@router.get("/api/uw/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db), _=Depends(auth)):
    case = db.get(UnderwritingCase, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


@router.get("/api/uw/queue", response_model=list[CaseOut])
def referral_queue(db: Session = Depends(get_db), _=Depends(uw_auth)):
    return (
        db.query(UnderwritingCase)
        .filter(UnderwritingCase.status == "REFERRED")
        .order_by(UnderwritingCase.created_at)
        .all()
    )


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
    return case
