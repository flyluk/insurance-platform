import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import UnderwritingCase  # noqa: F401
from app.routers import uw
from insurance_shared.events import OutboxBase, outbox_poller
from insurance_shared.metrics import PrometheusMiddleware, metrics_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    OutboxBase.metadata.create_all(bind=engine)
    task = asyncio.create_task(outbox_poller(SessionLocal, settings.outbox_poll_seconds))
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


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
