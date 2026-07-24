"""Seed demo parties, quotes, and applications for staff / portal testing."""

from sqlalchemy.orm import Session

from app.models import Application, Party, Quote
from insurance_shared.demo import (
    DEMO_APPLICATION_ID,
    DEMO_APPLICATION_NUMBER,
    DEMO_AUTO2_APPLICATION_ID,
    DEMO_AUTO2_APPLICATION_NUMBER,
    DEMO_CANCELLED_APPLICATION_ID,
    DEMO_CANCELLED_APPLICATION_NUMBER,
    DEMO_DRAFT_QUOTE_ID,
    DEMO_HOME_APPLICATION_ID,
    DEMO_HOME_APPLICATION_NUMBER,
    DEMO_HOME_POLICY_ID,
    DEMO_LIFE_APPLICATION_ID,
    DEMO_LIFE_APPLICATION_NUMBER,
    DEMO_LIFE_POLICY_ID,
    DEMO_PARTIES,
    DEMO_PARTY_ID,
    DEMO_PARTY_AVERY_ID,
    DEMO_PARTY_CASEY_ID,
    DEMO_PARTY_MORGAN_ID,
    DEMO_PARTY_RILEY_ID,
    DEMO_PARTY_SAM_ID,
    DEMO_POLICY_ID,
    DEMO_RATED_QUOTE_ID,
    DEMO_REFER_APPLICATION_ID,
    DEMO_REFER_APPLICATION_NUMBER,
    DEMO_REFER_QUOTE_ID,
    DEMO_UW_APPLICATION_ID,
    DEMO_UW_APPLICATION_NUMBER,
    DEMO_UW_QUOTE_ID,
    DEMO_AUTO2_POLICY_ID,
    DEMO_CANCELLED_POLICY_ID,
    DEMO_INSURED_PARTY_ID,
)


def seed_demo_party(db: Session) -> None:
    for snap in DEMO_PARTIES:
        if db.get(Party, snap["id"]):
            continue
        db.add(
            Party(
                id=snap["id"],
                full_name=snap["full_name"],
                email=snap["email"],
                phone=snap.get("phone"),
                date_of_birth=snap.get("date_of_birth"),
                address=snap.get("address"),
                id_number=snap.get("id_number"),
                gender=snap.get("gender") or "unspecified",
            )
        )
    db.commit()
    seed_demo_quotes_and_applications(db)


def seed_demo_quotes_and_applications(db: Session) -> None:
    quotes = [
        Quote(
            id=DEMO_DRAFT_QUOTE_ID,
            party_id=DEMO_PARTY_CASEY_ID,
            insured_party_id=DEMO_PARTY_CASEY_ID,
            product_code="AUTO",
            status="DRAFT",
            risk_attributes={"vehicle_year": 2019, "drivers": 1, "prior_claims": 0, "driver_age": 33},
            annual_premium=None,
        ),
        Quote(
            id=DEMO_RATED_QUOTE_ID,
            party_id=DEMO_PARTY_CASEY_ID,
            insured_party_id=DEMO_PARTY_CASEY_ID,
            product_code="HOME",
            status="RATED",
            risk_attributes={"dwelling_value": 420000, "year_built": 2008, "construction": "frame"},
            annual_premium=1320.0,
        ),
        Quote(
            id=DEMO_UW_QUOTE_ID,
            party_id=DEMO_PARTY_MORGAN_ID,
            insured_party_id=DEMO_PARTY_MORGAN_ID,
            product_code="AUTO",
            status="SUBMITTED",
            risk_attributes={"vehicle_year": 2021, "drivers": 2, "prior_claims": 1, "driver_age": 33},
            annual_premium=980.0,
        ),
        Quote(
            id=DEMO_REFER_QUOTE_ID,
            party_id=DEMO_PARTY_AVERY_ID,
            insured_party_id=DEMO_PARTY_AVERY_ID,
            product_code="HOME",
            status="SUBMITTED",
            risk_attributes={"dwelling_value": 890000, "year_built": 1995, "construction": "frame"},
            annual_premium=2100.0,
        ),
    ]
    for q in quotes:
        if not db.get(Quote, q.id):
            db.add(q)

    applications = [
        Application(
            id=DEMO_APPLICATION_ID,
            application_number=DEMO_APPLICATION_NUMBER,
            quote_id=DEMO_APPLICATION_ID,  # placeholder unique; quote not required for bound seed
            party_id=DEMO_PARTY_ID,
            insured_party_id=DEMO_INSURED_PARTY_ID,
            product_code="AUTO",
            status="BOUND",
            risk_attributes={"vehicle_year": 2022, "drivers": 1, "prior_claims": 0, "driver_age": 34},
            annual_premium=864.0,
            uw_decision="ACCEPTED",
            uw_reason="Seeded demo bind",
            policy_id=DEMO_POLICY_ID,
            policy_number="AUTO-DEMO0001",
        ),
        Application(
            id=DEMO_HOME_APPLICATION_ID,
            application_number=DEMO_HOME_APPLICATION_NUMBER,
            quote_id=DEMO_HOME_APPLICATION_ID,
            party_id=DEMO_PARTY_SAM_ID,
            insured_party_id=DEMO_PARTY_SAM_ID,
            product_code="HOME",
            status="BOUND",
            risk_attributes={"dwelling_value": 375000, "year_built": 2012, "construction": "brick"},
            annual_premium=1248.0,
            uw_decision="ACCEPTED",
            uw_reason="Seeded demo bind",
            policy_id=DEMO_HOME_POLICY_ID,
            policy_number="HOME-DEMO0001",
        ),
        Application(
            id=DEMO_AUTO2_APPLICATION_ID,
            application_number=DEMO_AUTO2_APPLICATION_NUMBER,
            quote_id=DEMO_AUTO2_APPLICATION_ID,
            party_id=DEMO_PARTY_RILEY_ID,
            insured_party_id=DEMO_PARTY_RILEY_ID,
            product_code="AUTO",
            status="BOUND",
            risk_attributes={"vehicle_year": 2020, "drivers": 1, "prior_claims": 0, "driver_age": 37},
            annual_premium=912.0,
            uw_decision="ACCEPTED",
            uw_reason="Seeded demo bind",
            policy_id=DEMO_AUTO2_POLICY_ID,
            policy_number="AUTO-DEMO0002",
        ),
        Application(
            id=DEMO_LIFE_APPLICATION_ID,
            application_number=DEMO_LIFE_APPLICATION_NUMBER,
            quote_id=DEMO_LIFE_APPLICATION_ID,
            party_id=DEMO_PARTY_SAM_ID,
            insured_party_id=DEMO_PARTY_SAM_ID,
            product_code="LIFE",
            status="BOUND",
            risk_attributes={"face_amount": 250000, "smoker": False, "age": 40},
            annual_premium=620.0,
            uw_decision="ACCEPTED",
            uw_reason="Seeded demo bind",
            policy_id=DEMO_LIFE_POLICY_ID,
            policy_number="LIFE-DEMO0001",
        ),
        Application(
            id=DEMO_CANCELLED_APPLICATION_ID,
            application_number=DEMO_CANCELLED_APPLICATION_NUMBER,
            quote_id=DEMO_CANCELLED_APPLICATION_ID,
            party_id=DEMO_PARTY_CASEY_ID,
            insured_party_id=DEMO_PARTY_CASEY_ID,
            product_code="AUTO",
            status="BOUND",
            risk_attributes={"vehicle_year": 2016, "drivers": 1, "prior_claims": 2, "driver_age": 34},
            annual_premium=1100.0,
            uw_decision="ACCEPTED",
            uw_reason="Seeded cancelled-policy bind",
            policy_id=DEMO_CANCELLED_POLICY_ID,
            policy_number="AUTO-DEMO-CX01",
        ),
        Application(
            id=DEMO_UW_APPLICATION_ID,
            application_number=DEMO_UW_APPLICATION_NUMBER,
            quote_id=DEMO_UW_QUOTE_ID,
            party_id=DEMO_PARTY_MORGAN_ID,
            insured_party_id=DEMO_PARTY_MORGAN_ID,
            product_code="AUTO",
            status="IN_UW",
            risk_attributes={"vehicle_year": 2021, "drivers": 2, "prior_claims": 1, "driver_age": 33},
            annual_premium=980.0,
        ),
        Application(
            id=DEMO_REFER_APPLICATION_ID,
            application_number=DEMO_REFER_APPLICATION_NUMBER,
            quote_id=DEMO_REFER_QUOTE_ID,
            party_id=DEMO_PARTY_AVERY_ID,
            insured_party_id=DEMO_PARTY_AVERY_ID,
            product_code="HOME",
            status="REFERRED",
            risk_attributes={"dwelling_value": 890000, "year_built": 1995, "construction": "frame"},
            annual_premium=2100.0,
            uw_decision="REFERRED",
            uw_reason="High dwelling value — manual review",
        ),
    ]
    for app in applications:
        if not db.get(Application, app.id):
            # Avoid unique quote_id collisions if a prior row reused the id
            existing_quote = db.query(Application).filter(Application.quote_id == app.quote_id).first()
            if existing_quote and existing_quote.id != app.id:
                continue
            db.add(app)
    db.commit()
