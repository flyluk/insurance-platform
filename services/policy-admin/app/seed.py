"""Seed demo policies across product lines for staff and portal testing."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Policy
from insurance_shared.demo import (
    ALEX_RIVERA,
    DEMO_APPLICATION_ID,
    DEMO_APPLICATION_NUMBER,
    DEMO_AUTO2_APPLICATION_ID,
    DEMO_AUTO2_APPLICATION_NUMBER,
    DEMO_AUTO2_POLICY_ID,
    DEMO_CANCELLED_APPLICATION_ID,
    DEMO_CANCELLED_APPLICATION_NUMBER,
    DEMO_CANCELLED_POLICY_ID,
    DEMO_HOME_APPLICATION_ID,
    DEMO_HOME_APPLICATION_NUMBER,
    DEMO_HOME_POLICY_ID,
    DEMO_INSURED_PARTY_ID,
    DEMO_LIFE_APPLICATION_ID,
    DEMO_LIFE_APPLICATION_NUMBER,
    DEMO_LIFE_POLICY_ID,
    DEMO_PARTY_CASEY_ID,
    DEMO_PARTY_ID,
    DEMO_PARTY_RILEY_ID,
    DEMO_PARTY_SAM_ID,
    DEMO_POLICY_ID,
    JORDAN_LEE,
    RILEY_QUINN,
    SAM_CHEN,
    CASEY_RIVERA,
)


def seed_demo_policy(db: Session) -> None:
    now = datetime.now(timezone.utc)
    policies = [
        {
            "id": DEMO_POLICY_ID,
            "policy_number": "AUTO-DEMO0001",
            "application_id": DEMO_APPLICATION_ID,
            "application_number": DEMO_APPLICATION_NUMBER,
            "party_id": DEMO_PARTY_ID,
            "owner_party_id": DEMO_PARTY_ID,
            "insured_party_id": DEMO_INSURED_PARTY_ID,
            "owner_snapshot": ALEX_RIVERA,
            "insured_snapshot": JORDAN_LEE,
            "product_code": "AUTO",
            "status": "ACTIVE",
            "annual_premium": 864.0,
            "risk_attributes": {
                "vehicle_year": 2022,
                "drivers": 1,
                "prior_claims": 0,
                "driver_age": 34,
            },
            "effective_date": now - timedelta(days=60),
            "expiry_date": now + timedelta(days=305),
        },
        {
            "id": DEMO_HOME_POLICY_ID,
            "policy_number": "HOME-DEMO0001",
            "application_id": DEMO_HOME_APPLICATION_ID,
            "application_number": DEMO_HOME_APPLICATION_NUMBER,
            "party_id": DEMO_PARTY_SAM_ID,
            "owner_party_id": DEMO_PARTY_SAM_ID,
            "insured_party_id": DEMO_PARTY_SAM_ID,
            "owner_snapshot": SAM_CHEN,
            "insured_snapshot": SAM_CHEN,
            "product_code": "HOME",
            "status": "ACTIVE",
            "annual_premium": 1248.0,
            "risk_attributes": {
                "dwelling_value": 375000,
                "year_built": 2012,
                "construction": "brick",
            },
            "effective_date": now - timedelta(days=120),
            "expiry_date": now + timedelta(days=245),
        },
        {
            "id": DEMO_AUTO2_POLICY_ID,
            "policy_number": "AUTO-DEMO0002",
            "application_id": DEMO_AUTO2_APPLICATION_ID,
            "application_number": DEMO_AUTO2_APPLICATION_NUMBER,
            "party_id": DEMO_PARTY_RILEY_ID,
            "owner_party_id": DEMO_PARTY_RILEY_ID,
            "insured_party_id": DEMO_PARTY_RILEY_ID,
            "owner_snapshot": RILEY_QUINN,
            "insured_snapshot": RILEY_QUINN,
            "product_code": "AUTO",
            "status": "ACTIVE",
            "annual_premium": 912.0,
            "risk_attributes": {
                "vehicle_year": 2020,
                "drivers": 1,
                "prior_claims": 0,
                "driver_age": 37,
            },
            "effective_date": now - timedelta(days=30),
            "expiry_date": now + timedelta(days=335),
        },
        {
            "id": DEMO_LIFE_POLICY_ID,
            "policy_number": "LIFE-DEMO0001",
            "application_id": DEMO_LIFE_APPLICATION_ID,
            "application_number": DEMO_LIFE_APPLICATION_NUMBER,
            "party_id": DEMO_PARTY_SAM_ID,
            "owner_party_id": DEMO_PARTY_SAM_ID,
            "insured_party_id": DEMO_PARTY_SAM_ID,
            "owner_snapshot": SAM_CHEN,
            "insured_snapshot": SAM_CHEN,
            "product_code": "LIFE",
            "status": "ACTIVE",
            "annual_premium": 620.0,
            "risk_attributes": {"face_amount": 250000, "smoker": False, "age": 40},
            "effective_date": now - timedelta(days=200),
            "expiry_date": now + timedelta(days=165),
        },
        {
            "id": DEMO_CANCELLED_POLICY_ID,
            "policy_number": "AUTO-DEMO-CX01",
            "application_id": DEMO_CANCELLED_APPLICATION_ID,
            "application_number": DEMO_CANCELLED_APPLICATION_NUMBER,
            "party_id": DEMO_PARTY_CASEY_ID,
            "owner_party_id": DEMO_PARTY_CASEY_ID,
            "insured_party_id": DEMO_PARTY_CASEY_ID,
            "owner_snapshot": CASEY_RIVERA,
            "insured_snapshot": CASEY_RIVERA,
            "product_code": "AUTO",
            "status": "CANCELLED",
            "annual_premium": 1100.0,
            "risk_attributes": {
                "vehicle_year": 2016,
                "drivers": 1,
                "prior_claims": 2,
                "driver_age": 34,
            },
            "effective_date": now - timedelta(days=200),
            "expiry_date": now + timedelta(days=165),
            "cancelled_at": now - timedelta(days=14),
            "cancellation_refund": 220.0,
        },
    ]

    for row in policies:
        existing = db.get(Policy, row["id"])
        if existing:
            existing.owner_party_id = existing.owner_party_id or row["owner_party_id"]
            existing.insured_party_id = existing.insured_party_id or row["insured_party_id"]
            if not existing.owner_snapshot:
                existing.owner_snapshot = row["owner_snapshot"]
            if not existing.insured_snapshot:
                existing.insured_snapshot = row["insured_snapshot"]
            if not existing.application_number:
                existing.application_number = row["application_number"]
            continue
        db.add(Policy(**row))
    db.commit()
