from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.defaults import RISK_SCHEMAS, UW_RULES
from app.models import Plan, PlanRider, RateVersion, Rider  # noqa: F401
from app.routers import products
from app.seed import seed_catalog
from insurance_shared.metrics import PrometheusMiddleware, metrics_response


def _ensure_columns() -> None:
    statements = [
        "ALTER TABLE plans ADD COLUMN IF NOT EXISTS risk_schema JSONB DEFAULT '[]'::jsonb",
        "ALTER TABLE plans ADD COLUMN IF NOT EXISTS uw_rules JSONB DEFAULT '{\"decline\":[],\"refer\":[]}'::jsonb",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def _backfill_plan_metadata(db) -> None:
    today = date.today()
    for plan in db.query(Plan).all():
        changed = False
        # Only backfill when risk_schema is NULL. An empty list is a valid
        # Product Studio configuration and must not be overwritten on restart.
        if plan.risk_schema is None:
            plan.risk_schema = RISK_SCHEMAS.get(plan.product_code, [])
            changed = True
        # Only backfill when uw_rules is missing entirely. Empty
        # {"decline":[],"refer":[]} is a valid auto-bind configuration and must
        # not be overwritten with product defaults on every startup.
        if plan.uw_rules is None:
            plan.uw_rules = UW_RULES.get(plan.product_code, {"decline": [], "refer": []})
            changed = True
        if changed:
            db.add(plan)
        has_rate = (
            db.query(RateVersion)
            .filter(RateVersion.plan_id == plan.id, RateVersion.status == "PUBLISHED")
            .first()
        )
        if plan.status == "PUBLISHED" and not has_rate:
            db.add(
                RateVersion(
                    plan_id=plan.id,
                    version_code="v1",
                    amount=plan.base_premium,
                    effective_from=today,
                    status="PUBLISHED",
                )
            )
    for rider in db.query(Rider).all():
        if rider.status != "PUBLISHED":
            continue
        has_rate = (
            db.query(RateVersion)
            .filter(RateVersion.rider_id == rider.id, RateVersion.status == "PUBLISHED")
            .first()
        )
        if not has_rate:
            db.add(
                RateVersion(
                    rider_id=rider.id,
                    version_code="v1",
                    amount=rider.premium,
                    effective_from=today,
                    status="PUBLISHED",
                )
            )
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    db = SessionLocal()
    try:
        seed_catalog(db)
        _backfill_plan_metadata(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Product Engine", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PrometheusMiddleware, service_name=settings.service_name)
app.include_router(products.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


@app.get("/metrics")
def metrics():
    return metrics_response()
