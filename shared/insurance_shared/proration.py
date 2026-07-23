"""Term remaining / unearned premium helpers for mid-term lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone


def _as_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def term_days(effective: datetime, expiry: datetime) -> int:
    effective = _as_aware(effective)
    expiry = _as_aware(expiry)
    days = (expiry - effective).days
    return max(days, 1)


def remaining_days(effective: datetime, expiry: datetime, as_of: datetime | None = None) -> int:
    as_of = _as_aware(as_of or datetime.now(timezone.utc))
    expiry = _as_aware(expiry)
    effective = _as_aware(effective)
    if as_of <= effective:
        return term_days(effective, expiry)
    if as_of >= expiry:
        return 0
    return max((expiry - as_of).days, 0)


def remaining_fraction(effective: datetime, expiry: datetime, as_of: datetime | None = None) -> float:
    total = term_days(effective, expiry)
    rem = remaining_days(effective, expiry, as_of)
    return round(rem / total, 6)


def unearned_premium(annual_premium: float, effective: datetime, expiry: datetime, as_of: datetime | None = None) -> float:
    return round(float(annual_premium) * remaining_fraction(effective, expiry, as_of), 2)


def prorate_delta(annual_delta: float, effective: datetime, expiry: datetime, as_of: datetime | None = None) -> float:
    """Billable mid-term amount for an annual premium change."""
    return round(float(annual_delta) * remaining_fraction(effective, expiry, as_of), 2)
