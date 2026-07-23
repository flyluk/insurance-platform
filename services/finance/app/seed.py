"""Seed a demo open invoice for the policyholder portal."""

import uuid

from sqlalchemy.orm import Session

from app.models import Invoice, JournalEntry, JournalLine
from insurance_shared.demo import DEMO_INVOICE_ID, DEMO_PARTY_ID, DEMO_POLICY_ID

DEMO_OWNER_SNAP = {
    "id": DEMO_PARTY_ID,
    "full_name": "Alex Rivera",
    "email": "policyholder@insurance.local",
    "phone": "+1-555-0100",
    "date_of_birth": "1990-04-12",
    "address": "1200 Meridian Ave, Austin, TX 78701",
    "id_number": "DRV-DEMO-1001",
    "gender": "unspecified",
}


def seed_demo_invoice(db: Session) -> None:
    open_inv = (
        db.query(Invoice)
        .filter(Invoice.party_id == DEMO_PARTY_ID, Invoice.status == "OPEN")
        .first()
    )
    if open_inv:
        if not open_inv.owner_snapshot:
            open_inv.owner_snapshot = DEMO_OWNER_SNAP
            db.commit()
        return

    invoice_id = DEMO_INVOICE_ID if not db.get(Invoice, DEMO_INVOICE_ID) else str(uuid.uuid4())
    inv = Invoice(
        id=invoice_id,
        invoice_number=f"INV-DEMO-{uuid.uuid4().hex[:4].upper()}",
        policy_id=DEMO_POLICY_ID,
        party_id=DEMO_PARTY_ID,
        owner_snapshot=DEMO_OWNER_SNAP,
        invoice_type="PREMIUM",
        amount=864.0,
        status="OPEN",
        description="Annual premium — Auto Basic (demo policy)",
    )
    db.add(inv)
    db.flush()
    entry = JournalEntry(
        reference_type="invoice",
        reference_id=inv.id,
        memo=f"Premium due {inv.invoice_number}",
    )
    db.add(entry)
    db.flush()
    db.add(JournalLine(entry_id=entry.id, account="AR_PREMIUM", debit=inv.amount, credit=0.0))
    db.add(JournalLine(entry_id=entry.id, account="PREMIUM_REVENUE", debit=0.0, credit=inv.amount))
    db.commit()
