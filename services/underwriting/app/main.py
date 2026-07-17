from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.event_handlers import HANDLED_TYPES, handle_domain_event
from app.models import UnderwritingCase  # noqa: F401
from app.routers import uw
from insurance_shared.events import OutboxBase
from insurance_shared.metrics import PrometheusMiddleware, metrics_response
from insurance_shared.runtime import event_runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    OutboxBase.metadata.create_all(bind=engine)
    async with event_runtime(
        SessionLocal,
        poll_seconds=settings.outbox_poll_seconds,
        enable_outbox=True,
        consumer_group=settings.service_name,
        handled_types=HANDLED_TYPES,
        handler=handle_domain_event,
    ):
        yield


app = FastAPI(title="Underwriting Service", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(PrometheusMiddleware, service_name=settings.service_name)
app.include_router(uw.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


@app.get("/metrics")
def metrics():
    return metrics_response()
