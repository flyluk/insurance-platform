from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Application, Party, Quote
from app.rating import rate_quote
from app.schemas import ApplicationOut, PartyCreate, PartyOut, QuoteCreate, QuoteOut
from insurance_shared.auth import make_auth_dependency
from insurance_shared.events import enqueue_event
from insurance_shared.metrics import record_event

router = APIRouter(prefix="/api/nb", tags=["new-business"])
auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm)
agent_auth = make_auth_dependency(settings.jwt_secret, settings.jwt_algorithm, "agent", "admin")


@router.post("/parties", response_model=PartyOut)
def create_party(body: PartyCreate, db: Session = Depends(get_db), _=Depends(agent_auth)):
    party = Party(**body.model_dump())
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


@router.get("/parties", response_model=list[PartyOut])
def list_parties(db: Session = Depends(get_db), _=Depends(auth)):
    return db.query(Party).order_by(Party.created_at.desc()).limit(200).all()


@router.get("/parties/{party_id}", response_model=PartyOut)
def get_party(party_id: str, db: Session = Depends(get_db), _=Depends(auth)):
    party = db.get(Party, party_id)
    if not party:
        raise HTTPException(404, "Party not found")
    return party


@router.post("/quotes", response_model=QuoteOut)
def create_quote(body: QuoteCreate, db: Session = Depends(get_db), _=Depends(agent_auth)):
    if not db.get(Party, body.party_id):
        raise HTTPException(404, "Party not found")
    quote = Quote(
        party_id=body.party_id,
        product_code=body.product_code,
        risk_attributes=body.risk_attributes,
        status="DRAFT",
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


@router.get("/quotes", response_model=list[QuoteOut])
def list_quotes(db: Session = Depends(get_db), _=Depends(auth)):
    return db.query(Quote).order_by(Quote.created_at.desc()).limit(200).all()


@router.get("/quotes/{quote_id}", response_model=QuoteOut)
def get_quote(quote_id: str, db: Session = Depends(get_db), _=Depends(auth)):
    quote = db.get(Quote, quote_id)
    if not quote:
        raise HTTPException(404, "Quote not found")
    return quote


@router.post("/quotes/{quote_id}/rate", response_model=QuoteOut)
def rate(quote_id: str, db: Session = Depends(get_db), _=Depends(agent_auth)):
    quote = db.get(Quote, quote_id)
    if not quote:
        raise HTTPException(404, "Quote not found")
    quote.annual_premium = rate_quote(quote.product_code, quote.risk_attributes or {})
    quote.status = "RATED"
    db.commit()
    db.refresh(quote)
    return quote


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

    app = Application(
        quote_id=quote.id,
        party_id=quote.party_id,
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
        "product_code": quote.product_code,
        "annual_premium": quote.annual_premium,
        "risk_attributes": quote.risk_attributes or {},
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
    return app


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db), _=Depends(auth)):
    return db.query(Application).order_by(Application.created_at.desc()).limit(200).all()


@router.get("/applications/{application_id}", response_model=ApplicationOut)
def get_application(application_id: str, db: Session = Depends(get_db), _=Depends(auth)):
    app = db.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    return app
