from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

security = HTTPBearer(auto_error=False)

ROLES = ("agent", "underwriter", "claims", "finance", "admin")


def create_access_token(
    *,
    subject: str,
    email: str,
    role: str,
    secret: str,
    algorithm: str = "HS256",
    expire_minutes: int = 60,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {
        "sub": subject,
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, secret: str, algorithm: str = "HS256") -> dict:
    return jwt.decode(token, secret, algorithms=[algorithm])


def require_roles(*allowed: str) -> Callable:
    allowed_set = set(allowed)

    def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> dict:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Secret injected via closure by services using make_auth_dependency
        raise HTTPException(status_code=500, detail="Auth not configured")

    dependency.allowed = allowed_set  # type: ignore[attr-defined]
    return dependency


def make_auth_dependency(secret: str, algorithm: str = "HS256", *allowed_roles: str):
    allowed = set(allowed_roles) if allowed_roles else None

    def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> dict:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            payload = decode_token(credentials.credentials, secret, algorithm)
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        role = payload.get("role")
        if allowed and role not in allowed and role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return payload

    return dependency
