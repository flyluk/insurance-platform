from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.event_handlers import HANDLED_TYPES, handle_domain_event
from app.models import Endorsement, Policy  # noqa: F401
from app.routers import policies
from insurance_shared.events import OutboxBase
from insurance_shared.metrics import PrometheusMiddleware, metrics_response
from insurance_shared.runtime import event_runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    OutboxBase.metadata.create_all(bind=engine)
    _ensure_lifecycle_columns()
    db = SessionLocal()
    try:
        from app.seed import seed_demo_policy

        seed_demo_policy(db)
    finally:
        db.close()
    async with event_runtime(
        SessionLocal,
        poll_seconds=settings.outbox_poll_seconds,
        enable_outbox=True,
        consumer_group=settings.service_name,
        handled_types=HANDLED_TYPES,
        handler=handle_domain_event,
    ):
        yield


def _ensure_lifecycle_columns() -> None:
    from sqlalchemy import text

    statements = [
        "ALTER TABLE policies ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ",
        "ALTER TABLE policies ADD COLUMN IF NOT EXISTS cancellation_refund DOUBLE PRECISION",
        "ALTER TABLE endorsements ADD COLUMN IF NOT EXISTS billed_amount DOUBLE PRECISION DEFAULT 0",
        "ALTER TABLE policies ADD COLUMN IF NOT EXISTS owner_party_id VARCHAR(36)",
        "ALTER TABLE policies ADD COLUMN IF NOT EXISTS insured_party_id VARCHAR(36)",
        "ALTER TABLE policies ADD COLUMN IF NOT EXISTS owner_snapshot JSONB DEFAULT '{}'::jsonb",
        "ALTER TABLE policies ADD COLUMN IF NOT EXISTS insured_snapshot JSONB DEFAULT '{}'::jsonb",
        "ALTER TABLE policies ADD COLUMN IF NOT EXISTS application_number VARCHAR(64)",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        conn.execute(
            text(
                """
                UPDATE policies
                SET application_number = 'APP-' || product_code || '-' ||
                    UPPER(SUBSTRING(REPLACE(application_id, '-', '') FROM 1 FOR 6))
                WHERE application_number IS NULL OR application_number = ''
                """
            )
        )


app = FastAPI(title="Policy Admin Service", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(PrometheusMiddleware, service_name=settings.service_name)
app.include_router(policies.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


@app.get("/metrics")
def metrics():
    return metrics_response()
