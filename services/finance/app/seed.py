"""Seed demo invoices (open + paid) for finance and policyholder testing."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Invoice, JournalEntry, JournalLine, Payment
from insurance_shared.demo import (
    ALEX_RIVERA,
    DEMO_AUTO2_INVOICE_ID,
    DEMO_AUTO2_POLICY_ID,
    DEMO_HOME_INVOICE_ID,
    DEMO_HOME_POLICY_ID,
    DEMO_INVOICE_ID,
    DEMO_PAID_INVOICE_ID,
    DEMO_PARTY_ID,
    DEMO_PARTY_RILEY_ID,
    DEMO_PARTY_SAM_ID,
    DEMO_POLICY_ID,
    RILEY_QUINN,
    SAM_CHEN,
)


def _add_invoice_journal(db: Session, inv: Invoice, memo: str) -> None:
    entry = JournalEntry(reference_type="invoice", reference_id=inv.id, memo=memo)
    db.add(entry)
    db.flush()
    db.add(JournalLine(entry_id=entry.id, account="AR_PREMIUM", debit=inv.amount, credit=0.0))
    db.add(JournalLine(entry_id=entry.id, account="PREMIUM_REVENUE", debit=0.0, credit=inv.amount))


def seed_demo_invoice(db: Session) -> None:
    now = datetime.now(timezone.utc)
    specs = [
        {
            "id": DEMO_INVOICE_ID,
            "invoice_number": "INV-DEMO-AUTO1",
            "policy_id": DEMO_POLICY_ID,
            "party_id": DEMO_PARTY_ID,
            "owner_snapshot": ALEX_RIVERA,
            "invoice_type": "PREMIUM",
            "amount": 864.0,
            "status": "OPEN",
            "description": "Annual premium — Auto Basic (demo policy)",
            "paid": False,
        },
        {
            "id": DEMO_HOME_INVOICE_ID,
            "invoice_number": "INV-DEMO-HOME1",
            "policy_id": DEMO_HOME_POLICY_ID,
            "party_id": DEMO_PARTY_SAM_ID,
            "owner_snapshot": SAM_CHEN,
            "invoice_type": "PREMIUM",
            "amount": 1248.0,
            "status": "OPEN",
            "description": "Annual premium — Home Basic (demo)",
            "paid": False,
        },
        {
            "id": DEMO_AUTO2_INVOICE_ID,
            "invoice_number": "INV-DEMO-AUTO2",
            "policy_id": DEMO_AUTO2_POLICY_ID,
            "party_id": DEMO_PARTY_RILEY_ID,
            "owner_snapshot": RILEY_QUINN,
            "invoice_type": "PREMIUM",
            "amount": 912.0,
            "status": "OPEN",
            "description": "Annual premium — Auto Basic (Riley Quinn)",
            "paid": False,
        },
        {
            "id": DEMO_PAID_INVOICE_ID,
            "invoice_number": "INV-DEMO-PAID1",
            "policy_id": DEMO_HOME_POLICY_ID,
            "party_id": DEMO_PARTY_SAM_ID,
            "owner_snapshot": SAM_CHEN,
            "invoice_type": "PREMIUM",
            "amount": 312.0,
            "status": "PAID",
            "description": "Prior-term installment — Home Basic (paid demo)",
            "paid": True,
            "paid_at": now,
        },
    ]

    for spec in specs:
        existing = db.get(Invoice, spec["id"])
        if existing:
            if not existing.owner_snapshot:
                existing.owner_snapshot = spec["owner_snapshot"]
            continue

        # Keep one open invoice for the policyholder party even if id differs
        if spec["id"] == DEMO_INVOICE_ID:
            open_inv = (
                db.query(Invoice)
                .filter(Invoice.party_id == DEMO_PARTY_ID, Invoice.status == "OPEN")
                .first()
            )
            if open_inv:
                if not open_inv.owner_snapshot:
                    open_inv.owner_snapshot = ALEX_RIVERA
                continue

        inv = Invoice(
            id=spec["id"],
            invoice_number=spec["invoice_number"],
            policy_id=spec["policy_id"],
            party_id=spec["party_id"],
            owner_snapshot=spec["owner_snapshot"],
            invoice_type=spec["invoice_type"],
            amount=spec["amount"],
            status=spec["status"],
            description=spec["description"],
            paid_at=spec.get("paid_at"),
        )
        db.add(inv)
        db.flush()
        _add_invoice_journal(db, inv, f"Premium due {inv.invoice_number}")
        if spec["paid"]:
            db.add(
                Payment(
                    invoice_id=inv.id,
                    amount=inv.amount,
                    method="CARD",
                    reference="DEMO-PAY-001",
                    masked_account="****4242",
                )
            )
            entry = JournalEntry(
                reference_type="payment",
                reference_id=inv.id,
                memo=f"Payment received {inv.invoice_number}",
            )
            db.add(entry)
            db.flush()
            db.add(JournalLine(entry_id=entry.id, account="CASH", debit=inv.amount, credit=0.0))
            db.add(JournalLine(entry_id=entry.id, account="AR_PREMIUM", debit=0.0, credit=inv.amount))

    db.commit()
