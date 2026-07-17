from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Application
from app.schemas import ApplicationOut, DomainEventIn
from insurance_shared.events import already_processed, mark_processed
from insurance_shared.metrics import record_event

router = APIRouter(tags=["events"])


@router.post("/events")
def consume_event(body: DomainEventIn, db: Session = Depends(get_db)):
    if already_processed(db, body.event_id):
        return {"status": "duplicate"}

    if body.event_type == "UnderwritingDecided":
        app_id = body.payload.get("application_id") or body.aggregate_id
        app = db.get(Application, app_id)
        if not app:
            raise HTTPException(404, "Application not found")
        decision = body.payload.get("decision")
        app.uw_decision = decision
        app.uw_reason = body.payload.get("reason")
        if decision == "ACCEPT":
            app.status = "ACCEPTED"
        elif decision == "DECLINE":
            app.status = "DECLINED"
        elif decision == "REFER":
            app.status = "REFERRED"
        else:
            app.status = "IN_UW"
        record_event("UnderwritingDecided", "consumed", settings.service_name)

    elif body.event_type == "PolicyBound":
        app_id = body.payload.get("application_id")
        if app_id:
            app = db.get(Application, app_id)
            if app:
                app.status = "BOUND"
                app.policy_id = body.payload.get("policy_id")
                record_event("PolicyBound", "consumed", settings.service_name)

    mark_processed(db, body.event_id, body.event_type)
    db.commit()
    return {"status": "ok"}


@router.get("/internal/applications/{application_id}", response_model=ApplicationOut)
def internal_get_application(application_id: str, db: Session = Depends(get_db)):
    app = db.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    return app
