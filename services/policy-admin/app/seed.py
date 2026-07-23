"""Seed a demo active policy for the policyholder portal (owner + insured)."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Policy
from insurance_shared.demo import (
    DEMO_APPLICATION_ID,
    DEMO_INSURED_PARTY_ID,
    DEMO_PARTY_ID,
    DEMO_POLICY_ID,
)


def seed_demo_policy(db: Session) -> None:
    existing = db.get(Policy, DEMO_POLICY_ID)
    owner_snap = {
        "id": DEMO_PARTY_ID,
        "full_name": "Alex Rivera",
        "email": "policyholder@insurance.local",
        "phone": "+1-555-0100",
        "date_of_birth": "1990-04-12",
        "address": "1200 Meridian Ave, Austin, TX 78701",
        "id_number": "DRV-DEMO-1001",
        "gender": "unspecified",
    }
    insured_snap = {
        "id": DEMO_INSURED_PARTY_ID,
        "full_name": "Jordan Lee",
        "email": "jordan.lee@example.com",
        "phone": "+1-555-0142",
        "date_of_birth": "1994-08-03",
        "address": "88 Cedar Lane, Austin, TX 78702",
        "id_number": "DRV-DEMO-2042",
        "gender": "unspecified",
    }
    if existing:
        # Backfill owner/insured on existing demo rows
        existing.owner_party_id = existing.owner_party_id or DEMO_PARTY_ID
        existing.insured_party_id = existing.insured_party_id or DEMO_INSURED_PARTY_ID
        if not existing.owner_snapshot:
            existing.owner_snapshot = owner_snap
        if not existing.insured_snapshot:
            existing.insured_snapshot = insured_snap
        db.commit()
        return

    now = datetime.now(timezone.utc)
    db.add(
        Policy(
            id=DEMO_POLICY_ID,
            policy_number="AUTO-DEMO0001",
            application_id=DEMO_APPLICATION_ID,
            party_id=DEMO_PARTY_ID,
            owner_party_id=DEMO_PARTY_ID,
            insured_party_id=DEMO_INSURED_PARTY_ID,
            owner_snapshot=owner_snap,
            insured_snapshot=insured_snap,
            product_code="AUTO",
            status="ACTIVE",
            annual_premium=864.0,
            risk_attributes={
                "vehicle_year": 2022,
                "drivers": 1,
                "prior_claims": 0,
                "driver_age": 34,
            },
            effective_date=now,
            expiry_date=now + timedelta(days=365),
        )
    )
    db.commit()
