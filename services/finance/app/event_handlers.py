import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import ClaimDisbursement, Invoice, JournalEntry, JournalLine
from app.routers.finance import _post_journal
from insurance_shared.events import already_processed, mark_processed
from insurance_shared.metrics import record_event

HANDLED_TYPES = {"PremiumDue", "ClaimPaymentRequested"}


def handle_domain_event(event: dict) -> None:
    db: Session = SessionLocal()
    try:
        event_id = event["event_id"]
        event_type = event["event_type"]
        payload = event.get("payload") or {}

        if already_processed(db, event_id):
            return

        if event_type == "PremiumDue":
            amount = float(payload["amount"])
            inv = Invoice(
                invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
                policy_id=payload.get("policy_id"),
                party_id=payload["party_id"],
                invoice_type=payload.get("invoice_type") or "PREMIUM",
                amount=amount,
                status="OPEN",
                description=f"Premium for policy {payload.get('policy_number')}",
            )
            db.add(inv)
            db.flush()
            _post_journal(
                db,
                reference_type="invoice",
                reference_id=inv.id,
                memo=f"Premium receivable {inv.invoice_number}",
                debit_account="AR_PREMIUM",
                credit_account="PREMIUM_REVENUE",
                amount=amount,
            )
            record_event("PremiumDue", "consumed", settings.service_name)

        elif event_type == "ClaimPaymentRequested":
            claim_id = payload["claim_id"]
            existing = db.query(ClaimDisbursement).filter(ClaimDisbursement.claim_id == claim_id).first()
            if not existing:
                amount = float(payload["amount"])
                disb = ClaimDisbursement(
                    claim_id=claim_id,
                    claim_number=payload["claim_number"],
                    policy_id=payload["policy_id"],
                    party_id=payload["party_id"],
                    amount=amount,
                    status="PAID",
                )
                db.add(disb)
                db.flush()
                _post_journal(
                    db,
                    reference_type="claim_payment",
                    reference_id=disb.id,
                    memo=f"Claim payment {payload['claim_number']}",
                    debit_account="CLAIMS_EXPENSE",
                    credit_account="CASH",
                    amount=amount,
                )
                record_event("ClaimPaymentRequested", "consumed", settings.service_name)

        mark_processed(db, event_id, event_type)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
