from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Application
from insurance_shared.events import already_processed, mark_processed
from insurance_shared.metrics import record_event

HANDLED_TYPES = {"UnderwritingDecided", "PolicyBound"}


def handle_domain_event(event: dict) -> None:
    db: Session = SessionLocal()
    try:
        event_id = event["event_id"]
        event_type = event["event_type"]
        payload = event.get("payload") or {}

        if already_processed(db, event_id):
            return

        if event_type == "UnderwritingDecided":
            app_id = payload.get("application_id") or event["aggregate_id"]
            app = db.get(Application, app_id)
            if not app:
                return
            decision = payload.get("decision")
            app.uw_decision = decision
            app.uw_reason = payload.get("reason")
            if decision == "ACCEPT":
                app.status = "ACCEPTED"
            elif decision == "DECLINE":
                app.status = "DECLINED"
            elif decision == "REFER":
                app.status = "REFERRED"
            else:
                app.status = "IN_UW"
            record_event("UnderwritingDecided", "consumed", settings.service_name)

        elif event_type == "PolicyBound":
            app_id = payload.get("application_id")
            if app_id:
                app = db.get(Application, app_id)
                if app:
                    app.status = "BOUND"
                    app.policy_id = payload.get("policy_id")
                    record_event("PolicyBound", "consumed", settings.service_name)

        mark_processed(db, event_id, event_type)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
