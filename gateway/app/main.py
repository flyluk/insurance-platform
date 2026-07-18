from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import User
from insurance_shared.auth import create_access_token, decode_token
from insurance_shared.metrics import PrometheusMiddleware, metrics_response
from jose import JWTError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

SEED_USERS = [
    ("admin@insurance.local", "admin123", "Platform Admin", "admin"),
    ("agent@insurance.local", "agent123", "Demo Agent", "agent"),
    ("uw@insurance.local", "uw123456", "Demo Underwriter", "underwriter"),
    ("claims@insurance.local", "claims123", "Demo Claims", "claims"),
    ("finance@insurance.local", "finance123", "Demo Finance", "finance"),
    ("product@insurance.local", "product123", "Product Manager", "product"),
]

ROUTE_MAP = [
    ("/api/nb", "new_business_url"),
    ("/api/uw", "underwriting_url"),
    ("/api/policies", "policy_admin_url"),
    ("/api/claims", "claims_url"),
    ("/api/finance", "finance_url"),
    ("/api/products", "product_engine_url"),
]


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str
    full_name: str


def seed_users() -> None:
    db = SessionLocal()
    try:
        for email, password, name, role in SEED_USERS:
            if db.query(User).filter(User.email == email).first():
                continue
            db.add(
                User(
                    email=email,
                    full_name=name,
                    hashed_password=pwd_context.hash(password),
                    role=role,
                )
            )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_users()
    app.state.http = httpx.AsyncClient(timeout=30.0)
    yield
    await app.state.http.aclose()


app = FastAPI(title="Insurance API Gateway", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(PrometheusMiddleware, service_name=settings.service_name)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


@app.get("/metrics")
def metrics():
    return metrics_response()


@app.post("/api/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not pwd_context.verify(body.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "User inactive")
    token = create_access_token(
        subject=user.id,
        email=user.email,
        role=user.role,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
    )
    return TokenOut(
        access_token=token,
        role=user.role,
        email=user.email,
        full_name=user.full_name,
    )


@app.get("/api/auth/me")
def me(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(credentials.credentials, settings.jwt_secret, settings.jwt_algorithm)
    except JWTError as exc:
        raise HTTPException(401, "Invalid token") from exc
    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role"),
    }


def _target_for(path: str) -> str | None:
    for prefix, attr in ROUTE_MAP:
        if path.startswith(prefix):
            return getattr(settings, attr)
    return None


@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(full_path: str, request: Request):
    path = f"/api/{full_path}"
    if path.startswith("/api/auth"):
        raise HTTPException(404, "Not found")
    base = _target_for(path)
    if not base:
        raise HTTPException(404, f"No upstream for {path}")

    url = f"{base}{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    body = await request.body()
    client: httpx.AsyncClient = request.app.state.http
    upstream = await client.request(request.method, url, content=body, headers=headers)
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )
