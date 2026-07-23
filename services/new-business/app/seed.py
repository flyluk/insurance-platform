"""Seed the demo policyholder party linked to gateway identity."""

from sqlalchemy.orm import Session

from app.models import Party
from insurance_shared.demo import DEMO_PARTY_ID


def seed_demo_party(db: Session) -> None:
    if db.get(Party, DEMO_PARTY_ID):
        return
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
    db.commit()
