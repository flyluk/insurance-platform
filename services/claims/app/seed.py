"""Seed demo claims including a large settlement awaiting approval."""

from sqlalchemy.orm import Session

from app.models import Claim
from insurance_shared.demo import (
    ALEX_RIVERA,
    DEMO_AUTO2_POLICY_ID,
    DEMO_CLAIM_OPEN_ID,
    DEMO_CLAIM_PENDING_APPROVAL_ID,
    DEMO_CLAIM_RESERVED_ID,
    DEMO_INSURED_PARTY_ID,
    DEMO_PARTY_ID,
    DEMO_PARTY_RILEY_ID,
    DEMO_POLICY_ID,
    JORDAN_LEE,
    RILEY_QUINN,
)


def seed_demo_claims(db: Session) -> None:
    claims = [
        Claim(
            id=DEMO_CLAIM_OPEN_ID,
            claim_number="CLM-DEMO0001",
            policy_id=DEMO_POLICY_ID,
            party_id=DEMO_PARTY_ID,
            insured_party_id=DEMO_INSURED_PARTY_ID,
            owner_snapshot=ALEX_RIVERA,
            insured_snapshot=JORDAN_LEE,
            product_code="AUTO",
            status="OPEN",
            description="Front bumper damage after parking-lot collision (demo).",
            loss_date="2026-06-15",
            reserve_amount=2500.0,
            settlement_amount=None,
        ),
        Claim(
            id=DEMO_CLAIM_RESERVED_ID,
            claim_number="CLM-DEMO0002",
            policy_id=DEMO_POLICY_ID,
            party_id=DEMO_PARTY_ID,
            insured_party_id=DEMO_INSURED_PARTY_ID,
            owner_snapshot=ALEX_RIVERA,
            insured_snapshot=JORDAN_LEE,
            product_code="AUTO",
            status="RESERVED",
            description="Windshield crack — glass reserve set (demo).",
            loss_date="2026-05-02",
            reserve_amount=800.0,
            settlement_amount=None,
        ),
        Claim(
            id=DEMO_CLAIM_PENDING_APPROVAL_ID,
            claim_number="CLM-DEMO-HI01",
            policy_id=DEMO_AUTO2_POLICY_ID,
            party_id=DEMO_PARTY_RILEY_ID,
            insured_party_id=DEMO_PARTY_RILEY_ID,
            owner_snapshot=RILEY_QUINN,
            insured_snapshot=RILEY_QUINN,
            product_code="AUTO",
            status="PENDING_APPROVAL",
            description="Total loss estimate after highway collision — settlement over $10,000 awaits approval.",
            loss_date="2026-07-01",
            reserve_amount=18000.0,
            settlement_amount=15500.0,
        ),
    ]
    for claim in claims:
        if not db.get(Claim, claim.id):
            db.add(claim)
    db.commit()
