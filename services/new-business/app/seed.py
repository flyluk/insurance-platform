"""Seed demo owner + insured parties linked to the policyholder portal."""

from sqlalchemy.orm import Session

from app.models import Party
from insurance_shared.demo import DEMO_INSURED_PARTY_ID, DEMO_PARTY_ID


def seed_demo_party(db: Session) -> None:
    if not db.get(Party, DEMO_PARTY_ID):
        db.add(
            Party(
                id=DEMO_PARTY_ID,
                full_name="Alex Rivera",
                email="policyholder@insurance.local",
                phone="+1-555-0100",
                date_of_birth="1990-04-12",
                address="1200 Meridian Ave, Austin, TX 78701",
                id_number="DRV-DEMO-1001",
                gender="unspecified",
            )
        )
    if not db.get(Party, DEMO_INSURED_PARTY_ID):
        db.add(
            Party(
                id=DEMO_INSURED_PARTY_ID,
                full_name="Jordan Lee",
                email="jordan.lee@example.com",
                phone="+1-555-0142",
                date_of_birth="1994-08-03",
                address="88 Cedar Lane, Austin, TX 78702",
                id_number="DRV-DEMO-2042",
                gender="unspecified",
            )
        )
    db.commit()
