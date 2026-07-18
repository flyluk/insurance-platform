"""Resolve effective-dated premiums and evaluate UW rule sets."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import Plan, RateVersion, Rider


def _active_versions(q, as_of: date):
    return (
        q.filter(RateVersion.status == "PUBLISHED")
        .filter(RateVersion.effective_from <= as_of)
        .filter((RateVersion.effective_to.is_(None)) | (RateVersion.effective_to >= as_of))
        .order_by(RateVersion.effective_from.desc())
    )


def retire_overlapping_published_rates(db: Session, new_ver: RateVersion) -> None:
    """End-date or supersede prior PUBLISHED rates that overlap the newly published version."""
    q = db.query(RateVersion).filter(
        RateVersion.id != new_ver.id,
        RateVersion.status == "PUBLISHED",
    )
    if new_ver.plan_id:
        q = q.filter(RateVersion.plan_id == new_ver.plan_id)
    elif new_ver.rider_id:
        q = q.filter(RateVersion.rider_id == new_ver.rider_id)
    else:
        return

    start = new_ver.effective_from
    new_end = new_ver.effective_to
    for old in q.all():
        old_end = old.effective_to
        overlaps = (old_end is None or old_end >= start) and (
            new_end is None or new_end >= old.effective_from
        )
        if not overlaps:
            continue
        if old.effective_from < start:
            old.effective_to = start - timedelta(days=1)
        else:
            # Same or later start date — retire so only one published rate applies.
            old.status = "SUPERSEDED"


def resolve_plan_amount(db: Session, plan: Plan, as_of: date | None = None) -> tuple[float, RateVersion | None]:
    as_of = as_of or date.today()
    q = db.query(RateVersion).filter(RateVersion.plan_id == plan.id)
    ver = _active_versions(q, as_of).first()
    if ver:
        return float(ver.amount), ver
    return float(plan.base_premium), None


def resolve_rider_amount(db: Session, rider: Rider, as_of: date | None = None) -> tuple[float, RateVersion | None]:
    as_of = as_of or date.today()
    q = db.query(RateVersion).filter(RateVersion.rider_id == rider.id)
    ver = _active_versions(q, as_of).first()
    if ver:
        return float(ver.amount), ver
    return float(rider.premium), None


def _cmp(left: Any, op: str, right: Any) -> bool:
    # Missing risk fields never satisfy a condition (do not raise on None >= n).
    if left is None:
        return False
    try:
        if isinstance(right, bool) or isinstance(left, bool):
            left_b = bool(left) if not isinstance(left, bool) else left
            # JSON may send true/false; risk may send "yes"
            if isinstance(left, str):
                left_b = left.lower() in {"1", "true", "yes", "y"}
            right_b = bool(right)
            left, right = left_b, right_b
        else:
            left = float(left) if not isinstance(left, (int, float, str)) or str(left).replace(".", "", 1).isdigit() else left
            if isinstance(right, (int, float)) and not isinstance(left, bool):
                left = float(left)
                right = float(right)
    except (TypeError, ValueError):
        return False

    try:
        if op == "eq":
            return left == right
        if op == "ne":
            return left != right
        if op == "gt":
            return left > right
        if op == "gte":
            return left >= right
        if op == "lt":
            return left < right
        if op == "lte":
            return left <= right
    except TypeError:
        return False
    return False


def _rule_matches(rule: dict[str, Any], context: dict[str, Any]) -> bool:
    conditions = rule.get("all") or []
    if not conditions:
        return False
    for cond in conditions:
        field = cond.get("field")
        op = cond.get("op", "eq")
        value = cond.get("value")
        if not _cmp(context.get(field), op, value):
            return False
    return True


def evaluate_uw_rules(
    uw_rules: dict[str, Any] | None,
    risk: dict[str, Any],
    annual_premium: float,
    *,
    product_code: str = "",
) -> tuple[str, str]:
    """Return (decision, reason). Falls back to ACCEPT if no rules."""
    rules = uw_rules or {}
    context = dict(risk or {})
    context["annual_premium"] = annual_premium
    context["product_code"] = product_code

    for rule in rules.get("decline") or []:
        if _rule_matches(rule, context):
            return "DECLINE", rule.get("reason") or "Declined by product rules"
    for rule in rules.get("refer") or []:
        if _rule_matches(rule, context):
            return "REFER", rule.get("reason") or "Referred by product rules"
    return "ACCEPT", "Product rules passed"
