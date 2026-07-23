from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ClaimDisbursement, Invoice, JournalEntry, JournalLine, Payment
from app.payments import debit_account_for, process_payment
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
from insurance_shared.parties import summary_from_snapshot

router = APIRouter(tags=["finance"])
auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm)
# Staff finance + policyholders (ownership checked in handler)
pay_auth = make_auth_dependency(
    settings.jwt_secret, settings.jwt_algorithm, "finance", "admin", "policyholder"
)
staff_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "finance", "admin")


def _party_id(user: dict) -> str | None:
    return user.get("party_id")


def _is_policyholder(user: dict) -> bool:
    return user.get("role") == "policyholder"


def _invoice_out(inv: Invoice) -> InvoiceOut:
    data = InvoiceOut.model_validate(inv)
    data.owner = summary_from_snapshot(inv.owner_snapshot, fallback_id=inv.party_id)
    return data


def _disbursement_out(d: ClaimDisbursement) -> DisbursementOut:
    data = DisbursementOut.model_validate(d)
    data.owner = summary_from_snapshot(d.owner_snapshot, fallback_id=d.party_id)
    return data


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
def consume_event(body: DomainEventIn):
    """HTTP ingress for domain events — same handler as the Kafka consumer."""
    from app.event_handlers import handle_domain_event

    handle_domain_event(body.model_dump())
    return {"status": "ok"}


@router.get("/api/finance/invoices", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db), user: dict = Depends(auth)):
    q = db.query(Invoice)
    if _is_policyholder(user):
        party_id = _party_id(user)
        if not party_id:
            raise HTTPException(403, "Policyholder account is not linked to a party")
        q = q.filter(Invoice.party_id == party_id)
    return [_invoice_out(inv) for inv in q.order_by(Invoice.created_at.desc()).limit(200).all()]


@router.get("/api/finance/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: str, db: Session = Depends(get_db), user: dict = Depends(auth)):
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if _is_policyholder(user) and inv.party_id != _party_id(user):
        raise HTTPException(404, "Invoice not found")
    return _invoice_out(inv)


@router.post("/api/finance/invoices/{invoice_id}/pay", response_model=PaymentOut)
def pay_invoice(
    invoice_id: str,
    body: PaymentCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(pay_auth),
):
    inv = db.get(Invoice, invoice_id)
    if not inv or inv.status != "OPEN":
        raise HTTPException(400, "Invoice not payable")
    if _is_policyholder(user):
        if inv.party_id != _party_id(user):
            raise HTTPException(403, "Cannot pay another party's invoice")
        if body.method == "CASH":
            raise HTTPException(400, "Policyholders must pay by CARD or ACH")
    if abs(body.amount - inv.amount) > 0.01:
        raise HTTPException(400, "Payment amount must match invoice")

    reference, masked = process_payment(body, require_instrument=_is_policyholder(user))
    payment = Payment(
        invoice_id=inv.id,
        amount=body.amount,
        method=body.method.upper(),
        reference=reference,
        masked_account=masked,
    )
    db.add(payment)
    db.flush()
    inv.status = "PAID"
    inv.paid_at = datetime.now(timezone.utc)
    is_credit = inv.invoice_type in ("CREDIT", "CANCELLATION") or inv.invoice_number.startswith("CR-")
    if is_credit:
        # Refund / credit settlement: clear premium payable
        _post_journal(
            db,
            reference_type="refund",
            reference_id=payment.id,
            memo=f"Premium refund {inv.invoice_number} via {payment.method}",
            debit_account="PREMIUM_PAYABLE",
            credit_account=debit_account_for(payment.method),
            amount=body.amount,
        )
    else:
        _post_journal(
            db,
            reference_type="payment",
            reference_id=payment.id,
            memo=f"Premium collection {inv.invoice_number} via {payment.method}",
            debit_account=debit_account_for(payment.method),
            credit_account="AR_PREMIUM",
            amount=body.amount,
        )
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/api/finance/disbursements", response_model=list[DisbursementOut])
def list_disbursements(db: Session = Depends(get_db), user: dict = Depends(auth)):
    if _is_policyholder(user):
        raise HTTPException(403, "Insufficient role")
    rows = db.query(ClaimDisbursement).order_by(ClaimDisbursement.created_at.desc()).limit(200).all()
    return [_disbursement_out(d) for d in rows]


@router.get("/api/finance/ledger", response_model=list[JournalEntryOut])
def list_ledger(db: Session = Depends(get_db), user: dict = Depends(staff_auth)):
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
