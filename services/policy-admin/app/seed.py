"""Seed a demo active policy for the policyholder portal."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Policy
from insurance_shared.demo import DEMO_APPLICATION_ID, DEMO_PARTY_ID, DEMO_POLICY_ID


def seed_demo_policy(db: Session) -> None:
    if db.get(Policy, DEMO_POLICY_ID):
        return
    now = datetime.now(timezone.utc)
    db.add(
        Policy(
            id=DEMO_POLICY_ID,
            policy_number="AUTO-DEMO0001",
            application_id=DEMO_APPLICATION_ID,
            party_id=DEMO_PARTY_ID,
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
