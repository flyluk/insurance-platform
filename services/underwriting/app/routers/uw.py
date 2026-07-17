from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import UnderwritingCase
from app.schemas import CaseOut, DecisionIn, DomainEventIn
from app.rules import evaluate
from insurance_shared.auth import make_auth_dependency
from insurance_shared.events import already_processed, enqueue_event, mark_processed
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
        destination_url=settings.new_business_events_url,
    )
    if case.final_decision == "ACCEPT":
        enqueue_event(
            db,
            event_type="UnderwritingDecided",
            aggregate_type="application",
            aggregate_id=case.application_id,
            payload=payload,
            destination_url=settings.policy_admin_events_url,
        )
    record_event("UnderwritingDecided", "produced", settings.service_name)


@router.post("/events")
def consume_event(body: DomainEventIn, db: Session = Depends(get_db)):
    if already_processed(db, body.event_id):
        return {"status": "duplicate"}

    if body.event_type == "ApplicationSubmitted":
        existing = (
            db.query(UnderwritingCase)
            .filter(UnderwritingCase.application_id == body.payload["application_id"])
            .first()
        )
        if existing:
            mark_processed(db, body.event_id, body.event_type)
            db.commit()
            return {"status": "exists"}

        decision, reason = evaluate(
            body.payload["product_code"],
            body.payload.get("risk_attributes") or {},
            float(body.payload["annual_premium"]),
        )
        case = UnderwritingCase(
            application_id=body.payload["application_id"],
            party_id=body.payload["party_id"],
            product_code=body.payload["product_code"],
            annual_premium=float(body.payload["annual_premium"]),
            risk_attributes=body.payload.get("risk_attributes") or {},
            auto_decision=decision,
            reason=reason,
        )
        if decision == "REFER":
            case.status = "REFERRED"
            case.final_decision = None
        else:
            case.status = "ACCEPTED" if decision == "ACCEPT" else "DECLINED"
            case.final_decision = decision
        db.add(case)
        db.flush()
        if case.final_decision:
            _emit_decision(db, case)
        record_event("ApplicationSubmitted", "consumed", settings.service_name)

    mark_processed(db, body.event_id, body.event_type)
    db.commit()
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
