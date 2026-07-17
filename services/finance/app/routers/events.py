from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.event_handlers import handle_domain_event
from app.schemas import DomainEventIn

router = APIRouter(tags=["events"])


@router.post("/events")
def consume_event(body: DomainEventIn, db: Session = Depends(get_db)):
    handle_domain_event(body.model_dump())
    return {"status": "ok"}
