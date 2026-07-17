import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Policy
from app.routers.policies import _emit_bound
from insurance_shared.events import already_processed, mark_processed
from insurance_shared.metrics import record_event

HANDLED_TYPES = {"UnderwritingDecided"}


def _policy_number(product_code: str) -> str:
    return f"{product_code}-{uuid.uuid4().hex[:8].upper()}"


def handle_domain_event(event: dict) -> None:
    db: Session = SessionLocal()
    try:
        event_id = event["event_id"]
        event_type = event["event_type"]
        payload = event.get("payload") or {}

        if already_processed(db, event_id):
            return

        if event_type == "UnderwritingDecided" and payload.get("decision") == "ACCEPT":
            app_id = payload["application_id"]
            existing = db.query(Policy).filter(Policy.application_id == app_id).first()
            if not existing:
                now = datetime.now(timezone.utc)
                policy = Policy(
                    policy_number=_policy_number(payload["product_code"]),
                    application_id=app_id,
                    party_id=payload["party_id"],
                    product_code=payload["product_code"],
                    status="ACTIVE",
                    annual_premium=float(payload["annual_premium"]),
                    risk_attributes=payload.get("risk_attributes") or {},
                    effective_date=now,
                    expiry_date=now + timedelta(days=365),
                )
                db.add(policy)
                db.flush()
                _emit_bound(db, policy)
                record_event("UnderwritingDecided", "consumed", settings.service_name)

        mark_processed(db, event_id, event_type)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
