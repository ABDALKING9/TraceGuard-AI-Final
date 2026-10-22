"""Local demonstration authentication for the TraceGuard AI backend.

The project ships with a single demonstration operator account and short-lived
signed bearer tokens (HS256).  Tokens can be revoked server side, and every
application API endpoint requires a valid token except the explicitly public
endpoints (``/health``, ``/api/v1/auth/login`` and ``/api/v1/meta``).
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Header, HTTPException, status

from .config import (
    DEMO_EMAIL,
    SECRET_KEY,
    TOKEN_ALGORITHM,
    TOKEN_TTL_MINUTES,
    verify_password,
)

# jti values of revoked tokens.  In-memory on purpose: this is a local,
# single-process demonstration server that is restarted between sessions.
_REVOKED_TOKENS: set[str] = set()


def authenticate(email: str, password: str) -> bool:
    """Validate the demonstration credentials."""
    if not email or not password:
        return False
    if email.strip().lower() != DEMO_EMAIL.strip().lower():
        return False
    return verify_password(password)


def create_access_token(subject: str) -> tuple[str, datetime, int]:
    """Create a signed bearer token.  Returns (token, expires_at, ttl_minutes)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=TOKEN_TTL_MINUTES)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": uuid.uuid4().hex,
        "typ": "demo-session",
        "iss": "traceguard-ai-local",
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=TOKEN_ALGORITHM)
    if isinstance(token, bytes):  # PyJWT < 2 compatibility
        token = token.decode("utf-8")
    return token, expires_at, TOKEN_TTL_MINUTES


def decode_access_token(token: str) -> dict:
    """Decode and validate a token.  Raises HTTPException(401) when invalid."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[TOKEN_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise credentials_error from None
    except jwt.InvalidTokenError:
        raise credentials_error from None
    if payload.get("jti") in _REVOKED_TOKENS:
        raise credentials_error
    return payload


def revoke_access_token(token: str) -> bool:
    """Revoke a token server side.  Returns True when the token was valid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[TOKEN_ALGORITHM])
    except jwt.InvalidTokenError:
        return False
    jti = payload.get("jti")
    if not jti:
        return False
    _REVOKED_TOKENS.add(jti)
    return True


def is_revoked(jti: str) -> bool:
    return jti in _REVOKED_TOKENS


def require_session(authorization: str | None = Header(default=None)) -> dict:
    """FastAPI dependency that enforces a valid bearer token."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a bearer token from /api/v1/auth/login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a bearer token from /api/v1/auth/login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(token)
