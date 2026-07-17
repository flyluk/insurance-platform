import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ClaimDisbursement, Invoice, JournalEntry, JournalLine, Payment
from app.schemas import (
    DisbursementOut,
    DomainEventIn,
    InvoiceOut,
    JournalEntryOut,
    JournalLineOut,
    PaymentCreate,
    PaymentOut,
)
from insurance_shared.auth import make_auth_dependency
from insurance_shared.events import already_processed, mark_processed
from insurance_shared.metrics import record_event

router = APIRouter(tags=["finance"])
auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm)
finance_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "finance", "admin")


def _post_journal(
    db: Session,
    *,
    reference_type: str,
    reference_id: str,
    memo: str,
    debit_account: str,
    credit_account: str,
    amount: float,
) -> JournalEntry:
    entry = JournalEntry(reference_type=reference_type, reference_id=reference_id, memo=memo)
    db.add(entry)
    db.flush()
    db.add(JournalLine(entry_id=entry.id, account=debit_account, debit=amount, credit=0.0))
    db.add(JournalLine(entry_id=entry.id, account=credit_account, debit=0.0, credit=amount))
    return entry


@router.post("/events")
def consume_event(body: DomainEventIn, db: Session = Depends(get_db)):
    if already_processed(db, body.event_id):
        return {"status": "duplicate"}

    if body.event_type == "PremiumDue":
        amount = float(body.payload["amount"])
        inv = Invoice(
            invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
            policy_id=body.payload.get("policy_id"),
            party_id=body.payload["party_id"],
            invoice_type=body.payload.get("invoice_type") or "PREMIUM",
            amount=amount,
            status="OPEN",
            description=f"Premium for policy {body.payload.get('policy_number')}",
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

    elif body.event_type == "ClaimPaymentRequested":
        claim_id = body.payload["claim_id"]
        existing = db.query(ClaimDisbursement).filter(ClaimDisbursement.claim_id == claim_id).first()
        if not existing:
            amount = float(body.payload["amount"])
            disb = ClaimDisbursement(
                claim_id=claim_id,
                claim_number=body.payload["claim_number"],
                policy_id=body.payload["policy_id"],
                party_id=body.payload["party_id"],
                amount=amount,
                status="PAID",
            )
            db.add(disb)
            db.flush()
            _post_journal(
                db,
                reference_type="claim_payment",
                reference_id=disb.id,
                memo=f"Claim payment {body.payload['claim_number']}",
                debit_account="CLAIMS_EXPENSE",
                credit_account="CASH",
                amount=amount,
            )
            record_event("ClaimPaymentRequested", "consumed", settings.service_name)

    mark_processed(db, body.event_id, body.event_type)
    db.commit()
    return {"status": "ok"}


@router.get("/api/finance/invoices", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db), _=Depends(auth)):
    return db.query(Invoice).order_by(Invoice.created_at.desc()).limit(200).all()


@router.get("/api/finance/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: str, db: Session = Depends(get_db), _=Depends(auth)):
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return inv


@router.post("/api/finance/invoices/{invoice_id}/pay", response_model=PaymentOut)
def pay_invoice(invoice_id: str, body: PaymentCreate, db: Session = Depends(get_db), _=Depends(finance_auth)):
    inv = db.get(Invoice, invoice_id)
    if not inv or inv.status != "OPEN":
        raise HTTPException(400, "Invoice not payable")
    if abs(body.amount - inv.amount) > 0.01:
        raise HTTPException(400, "Payment amount must match invoice")
    payment = Payment(invoice_id=inv.id, amount=body.amount, method=body.method)
    db.add(payment)
    db.flush()
    inv.status = "PAID"
    inv.paid_at = datetime.now(timezone.utc)
    _post_journal(
        db,
        reference_type="payment",
        reference_id=payment.id,
        memo=f"Premium collection {inv.invoice_number}",
        debit_account="CASH",
        credit_account="AR_PREMIUM",
        amount=body.amount,
    )
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/api/finance/disbursements", response_model=list[DisbursementOut])
def list_disbursements(db: Session = Depends(get_db), _=Depends(auth)):
    return db.query(ClaimDisbursement).order_by(ClaimDisbursement.created_at.desc()).limit(200).all()


@router.get("/api/finance/ledger", response_model=list[JournalEntryOut])
def list_ledger(db: Session = Depends(get_db), _=Depends(auth)):
    entries = db.query(JournalEntry).order_by(JournalEntry.created_at.desc()).limit(100).all()
    result = []
    for e in entries:
        lines = db.query(JournalLine).filter(JournalLine.entry_id == e.id).all()
        result.append(
            JournalEntryOut(
                id=e.id,
                reference_type=e.reference_type,
                reference_id=e.reference_id,
                memo=e.memo,
                created_at=e.created_at,
                lines=[JournalLineOut.model_validate(l) for l in lines],
            )
        )
    return result
