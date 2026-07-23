import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import ClaimDisbursement, Invoice
from app.routers.finance import _post_journal
from insurance_shared.events import already_processed, mark_processed
from insurance_shared.metrics import record_event

HANDLED_TYPES = {"PremiumDue", "PremiumCredit", "PolicyCancelled", "ClaimPaymentRequested"}


def _void_open_invoices(db: Session, policy_id: str | None) -> int:
    if not policy_id:
        return 0
    open_rows = (
        db.query(Invoice)
        .filter(
            Invoice.policy_id == policy_id,
            Invoice.status == "OPEN",
            Invoice.invoice_type.in_(("PREMIUM", "ENDORSEMENT", "RENEWAL")),
        )
        .all()
    )
    for inv in open_rows:
        inv.status = "VOID"
    return len(open_rows)


def handle_domain_event(event: dict) -> None:
    db: Session = SessionLocal()
    try:
        event_id = event["event_id"]
        event_type = event["event_type"]
        payload = event.get("payload") or {}

        if already_processed(db, event_id):
            return

        if event_type == "PremiumDue":
            amount = abs(float(payload["amount"]))
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

        elif event_type == "PremiumCredit":
            amount = abs(float(payload["amount"]))
            inv_type = payload.get("invoice_type") or "CREDIT"
            inv = Invoice(
                invoice_number=f"CR-{uuid.uuid4().hex[:8].upper()}",
                policy_id=payload.get("policy_id"),
                party_id=payload["party_id"],
                invoice_type=inv_type,
                amount=amount,
                status="OPEN",
                description=(
                    f"Premium credit for policy {payload.get('policy_number')}"
                    + (f" ({inv_type})" if inv_type else "")
                ),
            )
            db.add(inv)
            db.flush()
            _post_journal(
                db,
                reference_type="credit",
                reference_id=inv.id,
                memo=f"Premium credit {inv.invoice_number}",
                debit_account="PREMIUM_REVENUE",
                credit_account="PREMIUM_PAYABLE",
                amount=amount,
            )
            record_event("PremiumCredit", "consumed", settings.service_name)

        elif event_type == "PolicyCancelled":
            voided = _void_open_invoices(db, payload.get("policy_id"))
            record_event("PolicyCancelled", "consumed", settings.service_name)
            if voided:
                # Keep a breadcrumb on the invoice descriptions when voided.
                pass

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
