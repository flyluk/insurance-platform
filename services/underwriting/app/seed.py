"""Seed underwriting queue cases for staff UW tab testing."""

from sqlalchemy.orm import Session

from app.models import UnderwritingCase
from insurance_shared.demo import (
    AVERY_KIM,
    DEMO_PARTY_AVERY_ID,
    DEMO_PARTY_MORGAN_ID,
    DEMO_REFER_APPLICATION_ID,
    DEMO_REFER_APPLICATION_NUMBER,
    DEMO_UW_APPLICATION_ID,
    DEMO_UW_APPLICATION_NUMBER,
    DEMO_UW_CASE_PENDING_ID,
    DEMO_UW_CASE_REFERRED_ID,
    MORGAN_BLAKE,
)


def seed_demo_uw_cases(db: Session) -> None:
    cases = [
        UnderwritingCase(
            id=DEMO_UW_CASE_PENDING_ID,
            application_id=DEMO_UW_APPLICATION_ID,
            application_number=DEMO_UW_APPLICATION_NUMBER,
            party_id=DEMO_PARTY_MORGAN_ID,
            insured_party_id=DEMO_PARTY_MORGAN_ID,
            owner_snapshot=MORGAN_BLAKE,
            insured_snapshot=MORGAN_BLAKE,
            product_code="AUTO",
            annual_premium=980.0,
            risk_attributes={"vehicle_year": 2021, "drivers": 2, "prior_claims": 1, "driver_age": 33},
            status="PENDING",
            auto_decision=None,
            final_decision=None,
            reason="Awaiting underwriter review (demo)",
        ),
        UnderwritingCase(
            id=DEMO_UW_CASE_REFERRED_ID,
            application_id=DEMO_REFER_APPLICATION_ID,
            application_number=DEMO_REFER_APPLICATION_NUMBER,
            party_id=DEMO_PARTY_AVERY_ID,
            insured_party_id=DEMO_PARTY_AVERY_ID,
            owner_snapshot=AVERY_KIM,
            insured_snapshot=AVERY_KIM,
            product_code="HOME",
            annual_premium=2100.0,
            risk_attributes={"dwelling_value": 890000, "year_built": 1995, "construction": "frame"},
            status="REFERRED",
            auto_decision="REFER",
            final_decision=None,
            reason="High dwelling value — manual review (demo)",
        ),
    ]
    for case in cases:
        if not db.get(UnderwritingCase, case.id):
            db.add(case)
    db.commit()
