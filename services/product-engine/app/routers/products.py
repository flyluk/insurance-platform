from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.defaults import RISK_SCHEMAS, UW_RULES
from app.models import Plan, PlanRider, RateVersion, Rider
from app.pricing import evaluate_uw_rules, resolve_plan_amount, resolve_rider_amount
from app.schemas import (
    EvaluateUwIn,
    EvaluateUwOut,
    LineSummary,
    PlanCreate,
    PlanOut,
    PlanRidersUpdate,
    PlanUpdate,
    QuoteResolveIn,
    QuoteResolveOut,
    RateVersionCreate,
    RateVersionOut,
    RiderCreate,
    RiderOut,
    RiderUpdate,
)
from insurance_shared.auth import decode_token, make_auth_dependency

router = APIRouter(prefix="/api/products", tags=["product-engine"])
product_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "product", "admin")
_bearer = HTTPBearer(auto_error=False)

LINES = ("AUTO", "HOME", "LIFE")
READ_ROLES = {"agent", "underwriter", "product", "admin", "claims", "finance"}


def _optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    if credentials is None:
        return None
    try:
        return decode_token(credentials.credentials, settings.jwt_secret, settings.jwt_algorithm)
    except JWTError:
        return None


def _require_reader(user: dict | None) -> dict:
    if user is None:
        raise HTTPException(401, "Not authenticated")
    if user.get("role") not in READ_ROLES:
        raise HTTPException(403, "Insufficient role")
    return user


def _rider_out(db: Session, rider: Rider, as_of: date | None = None) -> RiderOut:
    amount, _ = resolve_rider_amount(db, rider, as_of)
    data = RiderOut.model_validate(rider)
    data.effective_premium = amount
    return data


def _plan_out(db: Session, plan: Plan, as_of: date | None = None) -> PlanOut:
    riders = [pr.rider for pr in plan.plan_riders if pr.rider is not None]
    riders.sort(key=lambda r: (r.sort_order, r.name))
    amount, _ = resolve_plan_amount(db, plan, as_of)
    return PlanOut(
        id=plan.id,
        product_code=plan.product_code,
        code=plan.code,
        name=plan.name,
        description=plan.description,
        base_premium=plan.base_premium,
        status=plan.status,
        sort_order=plan.sort_order,
        risk_schema=plan.risk_schema or [],
        uw_rules=plan.uw_rules or {"decline": [], "refer": []},
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        riders=[_rider_out(db, r, as_of) for r in riders],
        effective_premium=amount,
    )


def _load_plan(db: Session, plan_id: str) -> Plan:
    plan = (
        db.query(Plan)
        .options(joinedload(Plan.plan_riders).joinedload(PlanRider.rider))
        .filter(Plan.id == plan_id)
        .first()
    )
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan


@router.get("/lines", response_model=list[LineSummary])
def list_lines(db: Session = Depends(get_db), user: dict | None = Depends(_optional_user)):
    _require_reader(user)
    out: list[LineSummary] = []
    for code in LINES:
        plans = db.query(Plan).filter(Plan.product_code == code).all()
        riders = db.query(Rider).filter(Rider.product_code == code).count()
        out.append(
            LineSummary(
                product_code=code,  # type: ignore[arg-type]
                plan_count=len(plans),
                rider_count=riders,
                published_plans=sum(1 for p in plans if p.status == "PUBLISHED"),
            )
        )
    return out


@router.get("/plans", response_model=list[PlanOut])
def list_plans(
    product_code: str | None = None,
    status: str | None = Query(default=None),
    as_of: date | None = None,
    db: Session = Depends(get_db),
    user: dict | None = Depends(_optional_user),
):
    if not status or status.upper() != "PUBLISHED":
        _require_reader(user)
    q = db.query(Plan).options(joinedload(Plan.plan_riders).joinedload(PlanRider.rider))
    if product_code:
        q = q.filter(Plan.product_code == product_code.upper())
    if status:
        q = q.filter(Plan.status == status.upper())
    plans = q.order_by(Plan.product_code, Plan.sort_order, Plan.name).all()
    seen: set[str] = set()
    unique: list[Plan] = []
    for p in plans:
        if p.id in seen:
            continue
        seen.add(p.id)
        unique.append(p)
    return [_plan_out(db, p, as_of) for p in unique]


@router.get("/plans/{plan_id}", response_model=PlanOut)
def get_plan(
    plan_id: str,
    as_of: date | None = None,
    db: Session = Depends(get_db),
    user: dict | None = Depends(_optional_user),
):
    plan = _load_plan(db, plan_id)
    if plan.status != "PUBLISHED":
        _require_reader(user)
    return _plan_out(db, plan, as_of)


@router.post("/plans", response_model=PlanOut)
def create_plan(body: PlanCreate, db: Session = Depends(get_db), _=Depends(product_auth)):
    existing = (
        db.query(Plan)
        .filter(Plan.product_code == body.product_code, Plan.code == body.code)
        .first()
    )
    if existing:
        raise HTTPException(400, "Plan code already exists for this line")
    data = body.model_dump()
    schema = data.pop("risk_schema") or RISK_SCHEMAS.get(body.product_code, [])
    rules = data.pop("uw_rules")
    if rules is None:
        rules = UW_RULES.get(body.product_code, {"decline": [], "refer": []})
    plan = Plan(**data, status="DRAFT", risk_schema=schema, uw_rules=rules)
    db.add(plan)
    db.flush()
    db.add(
        RateVersion(
            plan_id=plan.id,
            version_code="v1",
            amount=plan.base_premium,
            effective_from=date.today(),
            status="DRAFT",
        )
    )
    db.commit()
    return _plan_out(db, _load_plan(db, plan.id))


@router.patch("/plans/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: str, body: PlanUpdate, db: Session = Depends(get_db), _=Depends(product_auth)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    payload = body.model_dump(exclude_unset=True)
    if "risk_schema" in payload and payload["risk_schema"] is not None:
        payload["risk_schema"] = [f if isinstance(f, dict) else f for f in payload["risk_schema"]]
    if "uw_rules" in payload and payload["uw_rules"] is not None:
        payload["uw_rules"] = payload["uw_rules"]
    for key, value in payload.items():
        setattr(plan, key, value)
    if "base_premium" in payload and payload["base_premium"] is not None:
        plan.base_premium = payload["base_premium"]
    db.commit()
    return _plan_out(db, _load_plan(db, plan_id))


@router.post("/plans/{plan_id}/publish", response_model=PlanOut)
def publish_plan(plan_id: str, db: Session = Depends(get_db), _=Depends(product_auth)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    plan.status = "PUBLISHED"
    # Ensure at least one published rate version
    published = (
        db.query(RateVersion)
        .filter(RateVersion.plan_id == plan_id, RateVersion.status == "PUBLISHED")
        .count()
    )
    if published == 0:
        db.add(
            RateVersion(
                plan_id=plan.id,
                version_code="v1",
                amount=plan.base_premium,
                effective_from=date.today(),
                status="PUBLISHED",
            )
        )
    db.commit()
    return _plan_out(db, _load_plan(db, plan_id))


@router.post("/plans/{plan_id}/unpublish", response_model=PlanOut)
def unpublish_plan(plan_id: str, db: Session = Depends(get_db), _=Depends(product_auth)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    plan.status = "DRAFT"
    db.commit()
    return _plan_out(db, _load_plan(db, plan_id))


@router.put("/plans/{plan_id}/riders", response_model=PlanOut)
def set_plan_riders(
    plan_id: str, body: PlanRidersUpdate, db: Session = Depends(get_db), _=Depends(product_auth)
):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    riders = db.query(Rider).filter(Rider.id.in_(body.rider_ids)).all() if body.rider_ids else []
    if len(riders) != len(set(body.rider_ids)):
        raise HTTPException(400, "One or more riders not found")
    for rider in riders:
        if rider.product_code != plan.product_code:
            raise HTTPException(400, f"Rider {rider.code} is not for line {plan.product_code}")
    db.query(PlanRider).filter(PlanRider.plan_id == plan_id).delete()
    for rider in riders:
        db.add(PlanRider(plan_id=plan_id, rider_id=rider.id))
    db.commit()
    return _plan_out(db, _load_plan(db, plan_id))


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: str, db: Session = Depends(get_db), _=Depends(product_auth)):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    db.delete(plan)
    db.commit()
    return {"ok": True}


@router.get("/riders", response_model=list[RiderOut])
def list_riders(
    product_code: str | None = None,
    status: str | None = Query(default=None),
    as_of: date | None = None,
    db: Session = Depends(get_db),
    user: dict | None = Depends(_optional_user),
):
    if not status or status.upper() != "PUBLISHED":
        _require_reader(user)
    q = db.query(Rider)
    if product_code:
        q = q.filter(Rider.product_code == product_code.upper())
    if status:
        q = q.filter(Rider.status == status.upper())
    riders = q.order_by(Rider.product_code, Rider.sort_order, Rider.name).all()
    return [_rider_out(db, r, as_of) for r in riders]


@router.get("/riders/{rider_id}", response_model=RiderOut)
def get_rider(
    rider_id: str,
    as_of: date | None = None,
    db: Session = Depends(get_db),
    user: dict | None = Depends(_optional_user),
):
    rider = db.get(Rider, rider_id)
    if not rider:
        raise HTTPException(404, "Rider not found")
    if rider.status != "PUBLISHED":
        _require_reader(user)
    return _rider_out(db, rider, as_of)


@router.post("/riders", response_model=RiderOut)
def create_rider(body: RiderCreate, db: Session = Depends(get_db), _=Depends(product_auth)):
    existing = (
        db.query(Rider)
        .filter(Rider.product_code == body.product_code, Rider.code == body.code)
        .first()
    )
    if existing:
        raise HTTPException(400, "Rider code already exists for this line")
    rider = Rider(**body.model_dump(), status="DRAFT")
    db.add(rider)
    db.flush()
    db.add(
        RateVersion(
            rider_id=rider.id,
            version_code="v1",
            amount=rider.premium,
            effective_from=date.today(),
            status="DRAFT",
        )
    )
    db.commit()
    db.refresh(rider)
    return _rider_out(db, rider)


@router.patch("/riders/{rider_id}", response_model=RiderOut)
def update_rider(rider_id: str, body: RiderUpdate, db: Session = Depends(get_db), _=Depends(product_auth)):
    rider = db.get(Rider, rider_id)
    if not rider:
        raise HTTPException(404, "Rider not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(rider, key, value)
    db.commit()
    db.refresh(rider)
    return _rider_out(db, rider)


@router.post("/riders/{rider_id}/publish", response_model=RiderOut)
def publish_rider(rider_id: str, db: Session = Depends(get_db), _=Depends(product_auth)):
    rider = db.get(Rider, rider_id)
    if not rider:
        raise HTTPException(404, "Rider not found")
    rider.status = "PUBLISHED"
    if (
        db.query(RateVersion)
        .filter(RateVersion.rider_id == rider_id, RateVersion.status == "PUBLISHED")
        .count()
        == 0
    ):
        db.add(
            RateVersion(
                rider_id=rider.id,
                version_code="v1",
                amount=rider.premium,
                effective_from=date.today(),
                status="PUBLISHED",
            )
        )
    db.commit()
    db.refresh(rider)
    return _rider_out(db, rider)


@router.post("/riders/{rider_id}/unpublish", response_model=RiderOut)
def unpublish_rider(rider_id: str, db: Session = Depends(get_db), _=Depends(product_auth)):
    rider = db.get(Rider, rider_id)
    if not rider:
        raise HTTPException(404, "Rider not found")
    rider.status = "DRAFT"
    db.commit()
    db.refresh(rider)
    return _rider_out(db, rider)


@router.delete("/riders/{rider_id}")
def delete_rider(rider_id: str, db: Session = Depends(get_db), _=Depends(product_auth)):
    rider = db.get(Rider, rider_id)
    if not rider:
        raise HTTPException(404, "Rider not found")
    db.delete(rider)
    db.commit()
    return {"ok": True}


# --- Rate versions ---


@router.get("/plans/{plan_id}/rates", response_model=list[RateVersionOut])
def list_plan_rates(plan_id: str, db: Session = Depends(get_db), user: dict | None = Depends(_optional_user)):
    _require_reader(user)
    if not db.get(Plan, plan_id):
        raise HTTPException(404, "Plan not found")
    return (
        db.query(RateVersion)
        .filter(RateVersion.plan_id == plan_id)
        .order_by(RateVersion.effective_from.desc())
        .all()
    )


@router.post("/plans/{plan_id}/rates", response_model=RateVersionOut)
def create_plan_rate(
    plan_id: str, body: RateVersionCreate, db: Session = Depends(get_db), _=Depends(product_auth)
):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    ver = RateVersion(plan_id=plan_id, status="DRAFT", **body.model_dump())
    db.add(ver)
    db.commit()
    db.refresh(ver)
    return ver


@router.post("/plans/{plan_id}/rates/{rate_id}/publish", response_model=RateVersionOut)
def publish_plan_rate(
    plan_id: str, rate_id: str, db: Session = Depends(get_db), _=Depends(product_auth)
):
    ver = db.get(RateVersion, rate_id)
    if not ver or ver.plan_id != plan_id:
        raise HTTPException(404, "Rate version not found")
    ver.status = "PUBLISHED"
    plan = db.get(Plan, plan_id)
    if plan:
        plan.base_premium = ver.amount
    db.commit()
    db.refresh(ver)
    return ver


@router.get("/riders/{rider_id}/rates", response_model=list[RateVersionOut])
def list_rider_rates(rider_id: str, db: Session = Depends(get_db), user: dict | None = Depends(_optional_user)):
    _require_reader(user)
    if not db.get(Rider, rider_id):
        raise HTTPException(404, "Rider not found")
    return (
        db.query(RateVersion)
        .filter(RateVersion.rider_id == rider_id)
        .order_by(RateVersion.effective_from.desc())
        .all()
    )


@router.post("/riders/{rider_id}/rates", response_model=RateVersionOut)
def create_rider_rate(
    rider_id: str, body: RateVersionCreate, db: Session = Depends(get_db), _=Depends(product_auth)
):
    rider = db.get(Rider, rider_id)
    if not rider:
        raise HTTPException(404, "Rider not found")
    ver = RateVersion(rider_id=rider_id, status="DRAFT", **body.model_dump())
    db.add(ver)
    db.commit()
    db.refresh(ver)
    return ver


@router.post("/riders/{rider_id}/rates/{rate_id}/publish", response_model=RateVersionOut)
def publish_rider_rate(
    rider_id: str, rate_id: str, db: Session = Depends(get_db), _=Depends(product_auth)
):
    ver = db.get(RateVersion, rate_id)
    if not ver or ver.rider_id != rider_id:
        raise HTTPException(404, "Rate version not found")
    ver.status = "PUBLISHED"
    rider = db.get(Rider, rider_id)
    if rider:
        rider.premium = ver.amount
    db.commit()
    db.refresh(ver)
    return ver


@router.post("/resolve-quote", response_model=QuoteResolveOut)
def resolve_quote(body: QuoteResolveIn, db: Session = Depends(get_db)):
    """Public for new-business service-to-service rating."""
    plan = _load_plan(db, body.plan_id)
    if plan.status != "PUBLISHED":
        raise HTTPException(400, "Plan is not published")
    as_of = body.as_of or date.today()
    plan_amount, plan_ver = resolve_plan_amount(db, plan, as_of)
    allowed = {pr.rider_id: pr.rider for pr in plan.plan_riders if pr.rider}
    rider_rows = []
    total = plan_amount
    for rid in body.rider_ids:
        rider = allowed.get(rid)
        if not rider:
            raise HTTPException(400, "Rider is not allowed on this plan")
        if rider.status != "PUBLISHED":
            raise HTTPException(400, f"Rider {rider.code} is not published")
        amount, rver = resolve_rider_amount(db, rider, as_of)
        total += amount
        rider_rows.append(
            {
                "rider_id": rider.id,
                "code": rider.code,
                "amount": amount,
                "rate_version_id": rver.id if rver else None,
            }
        )
    return QuoteResolveOut(
        plan_id=plan.id,
        plan_amount=plan_amount,
        plan_rate_version_id=plan_ver.id if plan_ver else None,
        riders=rider_rows,
        total_base=total,
    )


@router.post("/evaluate-uw", response_model=EvaluateUwOut)
def evaluate_uw(body: EvaluateUwIn, db: Session = Depends(get_db)):
    """Public for underwriting service-to-service decisions."""
    plan = None
    if body.plan_id:
        plan = _load_plan(db, body.plan_id)
        if plan.status != "PUBLISHED":
            raise HTTPException(400, "Plan is not published")
    rules = (plan.uw_rules if plan else None) or UW_RULES.get(
        (body.product_code or "").upper(), {"decline": [], "refer": []}
    )
    decision, reason = evaluate_uw_rules(
        rules,
        body.risk_attributes,
        body.annual_premium,
        product_code=(plan.product_code if plan else body.product_code) or "",
    )
    return EvaluateUwOut(decision=decision, reason=reason, plan_id=plan.id if plan else None)
