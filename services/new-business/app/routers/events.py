from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.event_handlers import handle_domain_event
from app.models import Application
from app.schemas import ApplicationOut, DomainEventIn

router = APIRouter(tags=["events"])


@router.post("/events")
def consume_event(body: DomainEventIn, db: Session = Depends(get_db)):
    handle_domain_event(body.model_dump())
    return {"status": "ok"}


@router.get("/internal/applications/{application_id}", response_model=ApplicationOut)
def internal_get_application(application_id: str, db: Session = Depends(get_db)):
    app = db.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    return app
