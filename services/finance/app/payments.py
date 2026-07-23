"""Simulated card / ACH payment processor for demo self-serve collections."""

from __future__ import annotations

import re
import uuid

from fastapi import HTTPException

from app.schemas import PaymentCreate

# Test card ending in these digits is always declined (demo fraud / insufficient funds).
DECLINED_CARD_SUFFIX = "0000"


def process_payment(body: PaymentCreate, *, require_instrument: bool) -> tuple[str, str | None]:
    """Validate instrument and return (processor_reference, masked_account).

    Staff can record CASH/CARD/ACH without instrument details.
    Policyholders must supply CARD or ACH instrument fields.
    """
    method = body.method.upper()
    if method == "CASH":
        return f"sim_cash_{uuid.uuid4().hex[:10]}", None
    if method == "CARD":
        if not require_instrument and not body.card_number:
            return f"sim_card_{uuid.uuid4().hex[:10]}", "staff-recorded"
        return _process_card(body)
    if method == "ACH":
        if not require_instrument and not body.account_number:
            return f"sim_ach_{uuid.uuid4().hex[:10]}", "staff-recorded"
        return _process_ach(body)
    raise HTTPException(400, f"Unsupported payment method: {body.method}")


def debit_account_for(method: str) -> str:
    method = method.upper()
    if method == "CARD":
        return "CARD_CLEARING"
    if method == "ACH":
        return "BANK"
    return "CASH"


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _process_card(body: PaymentCreate) -> tuple[str, str]:
    number = _digits_only(body.card_number or "")
    cvv = _digits_only(body.card_cvv or "")
    if len(number) < 13 or len(number) > 19:
        raise HTTPException(400, "Invalid card number")
    if body.card_exp_month is None or body.card_exp_year is None:
        raise HTTPException(400, "Card expiry required")
    if len(cvv) < 3 or len(cvv) > 4:
        raise HTTPException(400, "Invalid card CVV")
    if number.endswith(DECLINED_CARD_SUFFIX):
        raise HTTPException(402, "Card declined by simulated processor")
    last4 = number[-4:]
    return f"sim_card_{uuid.uuid4().hex[:10]}", f"•••• {last4}"


def _process_ach(body: PaymentCreate) -> tuple[str, str]:
    account = _digits_only(body.account_number or "")
    routing = _digits_only(body.routing_number or "")
    if not (body.account_name or "").strip():
        raise HTTPException(400, "Account name required for ACH")
    if len(account) < 4 or len(account) > 17:
        raise HTTPException(400, "Invalid bank account number")
    if len(routing) != 9:
        raise HTTPException(400, "Routing number must be 9 digits")
    if routing == "000000000":
        raise HTTPException(402, "ACH rejected by simulated processor")
    return f"sim_ach_{uuid.uuid4().hex[:10]}", f"•••• {account[-4:]}"
