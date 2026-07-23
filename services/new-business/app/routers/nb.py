from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Application, Party, Quote
from app.product_catalog import ProductCatalogError, validate_quote_selection
from app.rating import rate_quote
from app.schemas import ApplicationOut, PartyCreate, PartyOut, QuoteCreate, QuoteOut
from insurance_shared.auth import make_auth_dependency
from insurance_shared.events import enqueue_event
from insurance_shared.metrics import record_event
from insurance_shared.parties import party_snapshot, summary_from_snapshot

router = APIRouter(prefix="/api/nb", tags=["new-business"])
auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm)
agent_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "agent", "admin")


def _quote_out(db: Session, quote: Quote) -> QuoteOut:
    owner = db.get(Party, quote.party_id)
    insured_id = quote.insured_party_id or quote.party_id
    insured = db.get(Party, insured_id)
    data = QuoteOut.model_validate(quote)
    data.insured_party_id = insured_id
    data.owner = summary_from_snapshot(party_snapshot(owner, party_id=quote.party_id))
    data.insured = summary_from_snapshot(party_snapshot(insured, party_id=insured_id))
    return data


def _app_out(db: Session, app: Application) -> ApplicationOut:
    owner = db.get(Party, app.party_id)
    insured_id = app.insured_party_id or app.party_id
    insured = db.get(Party, insured_id)
    data = ApplicationOut.model_validate(app)
    data.insured_party_id = insured_id
    data.owner = summary_from_snapshot(party_snapshot(owner, party_id=app.party_id))
    data.insured = summary_from_snapshot(party_snapshot(insured, party_id=insured_id))
    return data


def _policyholder_can_view_party(db: Session, user_party_id: str, target_party_id: str) -> bool:
    if user_party_id == target_party_id:
        return True
    # Allow viewing an insured who appears on the owner's quotes/applications
    linked = (
        db.query(Quote.id)
        .filter(Quote.party_id == user_party_id, Quote.insured_party_id == target_party_id)
        .first()
        or db.query(Application.id)
        .filter(Application.party_id == user_party_id, Application.insured_party_id == target_party_id)
        .first()
    )
    return linked is not None


@router.post("/parties", response_model=PartyOut)
def create_party(body: PartyCreate, db: Session = Depends(get_db), _=Depends(agent_auth)):
    party = Party(**body.model_dump())
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


@router.get("/parties", response_model=list[PartyOut])
def list_parties(db: Session = Depends(get_db), user: dict = Depends(auth)):
    if user.get("role") == "policyholder":
        party_id = user.get("party_id")
        if not party_id:
            raise HTTPException(403, "Policyholder account is not linked to a party")
        # Owner + any insureds on their quotes/apps
        ids = {party_id}
        for row in db.query(Quote.insured_party_id).filter(Quote.party_id == party_id).all():
            if row[0]:
                ids.add(row[0])
        for row in db.query(Application.insured_party_id).filter(Application.party_id == party_id).all():
            if row[0]:
                ids.add(row[0])
        return db.query(Party).filter(Party.id.in_(ids)).order_by(Party.full_name).all()
    return db.query(Party).order_by(Party.created_at.desc()).limit(200).all()


@router.get("/parties/{party_id}", response_model=PartyOut)
def get_party(party_id: str, db: Session = Depends(get_db), user: dict = Depends(auth)):
    if user.get("role") == "policyholder":
        own = user.get("party_id")
        if not own or not _policyholder_can_view_party(db, own, party_id):
            raise HTTPException(404, "Party not found")
    party = db.get(Party, party_id)
    if not party:
        raise HTTPException(404, "Party not found")
    return party


@router.get("/internal/parties", response_model=list[PartyOut])
def internal_parties(ids: str = "", db: Session = Depends(get_db)):
    """Cluster-internal bulk party lookup used to enrich owner/insured snapshots."""
    id_list = [x.strip() for x in ids.split(",") if x.strip()]
    if not id_list:
        return []
    return db.query(Party).filter(Party.id.in_(id_list)).all()


@router.post("/quotes", response_model=QuoteOut)
def create_quote(body: QuoteCreate, db: Session = Depends(get_db), _=Depends(agent_auth)):
    if not db.get(Party, body.party_id):
        raise HTTPException(404, "Owner party not found")
    insured_id = body.insured_party_id or body.party_id
    if not db.get(Party, insured_id):
        raise HTTPException(404, "Insured party not found")
    try:
        selection = validate_quote_selection(
            product_code=body.product_code,
            plan_id=body.plan_id,
            rider_ids=body.rider_ids,
        )
    except ProductCatalogError as exc:
        raise HTTPException(400, str(exc)) from exc

    plan = selection["plan"]
    riders = selection["riders"]
    risk = dict(body.risk_attributes or {})
    risk["product_selection"] = {
        "plan_id": plan["id"],
        "plan_code": plan["code"],
        "rider_ids": [r["id"] for r in riders],
        "rider_codes": [r["code"] for r in riders],
    }
    quote = Quote(
        party_id=body.party_id,
        insured_party_id=insured_id,
        product_code=body.product_code,
        plan_id=body.plan_id,
        rider_ids=body.rider_ids,
        risk_attributes=risk,
        status="DRAFT",
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return _quote_out(db, quote)


@router.get("/quotes", response_model=list[QuoteOut])
def list_quotes(db: Session = Depends(get_db), _=Depends(auth)):
    quotes = db.query(Quote).order_by(Quote.created_at.desc()).limit(200).all()
    return [_quote_out(db, q) for q in quotes]


@router.get("/quotes/{quote_id}", response_model=QuoteOut)
def get_quote(quote_id: str, db: Session = Depends(get_db), _=Depends(auth)):
    quote = db.get(Quote, quote_id)
    if not quote:
        raise HTTPException(404, "Quote not found")
    return _quote_out(db, quote)


@router.post("/quotes/{quote_id}/rate", response_model=QuoteOut)
def rate(quote_id: str, db: Session = Depends(get_db), _=Depends(agent_auth)):
    quote = db.get(Quote, quote_id)
    if not quote:
        raise HTTPException(404, "Quote not found")
    base = None
    rider_premiums: list[float] = []
    if quote.plan_id:
        try:
            selection = validate_quote_selection(
                product_code=quote.product_code,
                plan_id=quote.plan_id,
                rider_ids=list(quote.rider_ids or []),
            )
        except ProductCatalogError as exc:
            raise HTTPException(400, str(exc)) from exc
        pricing = selection["pricing"]
        base = float(pricing["plan_amount"])
        rider_premiums = [float(r["amount"]) for r in pricing["riders"]]
    quote.annual_premium = rate_quote(
        quote.product_code,
        quote.risk_attributes or {},
        base_premium=base,
        rider_premiums=rider_premiums,
    )
    quote.status = "RATED"
    db.commit()
    db.refresh(quote)
    return _quote_out(db, quote)


@router.post("/quotes/{quote_id}/submit", response_model=ApplicationOut)
def submit_application(quote_id: str, db: Session = Depends(get_db), _=Depends(agent_auth)):
    quote = db.get(Quote, quote_id)
    if not quote:
        raise HTTPException(404, "Quote not found")
    if quote.status != "RATED" or quote.annual_premium is None:
        raise HTTPException(400, "Quote must be rated before submit")
    existing = db.query(Application).filter(Application.quote_id == quote_id).first()
    if existing:
        raise HTTPException(400, "Application already exists for quote")

    insured_id = quote.insured_party_id or quote.party_id
    owner = db.get(Party, quote.party_id)
    insured = db.get(Party, insured_id)
    app = Application(
        quote_id=quote.id,
        party_id=quote.party_id,
        insured_party_id=insured_id,
        product_code=quote.product_code,
        status="SUBMITTED",
        risk_attributes=quote.risk_attributes or {},
        annual_premium=quote.annual_premium,
    )
    db.add(app)
    quote.status = "SUBMITTED"
    db.flush()

    payload = {
        "application_id": app.id,
        "quote_id": quote.id,
        "party_id": quote.party_id,
        "owner_party_id": quote.party_id,
        "insured_party_id": insured_id,
        "owner": party_snapshot(owner, party_id=quote.party_id),
        "insured": party_snapshot(insured, party_id=insured_id),
        "product_code": quote.product_code,
        "annual_premium": quote.annual_premium,
        "risk_attributes": quote.risk_attributes or {},
        "plan_id": quote.plan_id,
        "rider_ids": quote.rider_ids or [],
    }
    enqueue_event(
        db,
        event_type="ApplicationSubmitted",
        aggregate_type="application",
        aggregate_id=app.id,
        payload=payload,
    )
    record_event("ApplicationSubmitted", "produced", settings.service_name)
    db.commit()
    db.refresh(app)
    return _app_out(db, app)


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db), _=Depends(auth)):
    apps = db.query(Application).order_by(Application.created_at.desc()).limit(200).all()
    return [_app_out(db, a) for a in apps]


@router.get("/applications/{application_id}", response_model=ApplicationOut)
def get_application(application_id: str, db: Session = Depends(get_db), _=Depends(auth)):
    app = db.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    return _app_out(db, app)
