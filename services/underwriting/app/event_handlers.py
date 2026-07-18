from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import UnderwritingCase
from app.routers.uw import _emit_decision
from app.rules import evaluate
from insurance_shared.events import already_processed, mark_processed
from insurance_shared.metrics import record_event

HANDLED_TYPES = {"ApplicationSubmitted"}


def handle_domain_event(event: dict) -> None:
    db: Session = SessionLocal()
    try:
        event_id = event["event_id"]
        event_type = event["event_type"]
        payload = event.get("payload") or {}

        if already_processed(db, event_id):
            return

        if event_type == "ApplicationSubmitted":
            existing = (
                db.query(UnderwritingCase)
                .filter(UnderwritingCase.application_id == payload["application_id"])
                .first()
            )
            if existing:
                mark_processed(db, event_id, event_type)
                db.commit()
                return

            risk_attrs = payload.get("risk_attributes") or {}
            selection = risk_attrs.get("product_selection") or {}
            plan_id = payload.get("plan_id") or selection.get("plan_id")
            decision, reason = evaluate(
                payload["product_code"],
                risk_attrs,
                float(payload["annual_premium"]),
                plan_id=plan_id,
            )
            case = UnderwritingCase(
                application_id=payload["application_id"],
                party_id=payload["party_id"],
                product_code=payload["product_code"],
                annual_premium=float(payload["annual_premium"]),
                risk_attributes=payload.get("risk_attributes") or {},
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

        mark_processed(db, event_id, event_type)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
