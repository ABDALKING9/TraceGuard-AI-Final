"""Local configuration for the TraceGuard AI demonstration server.

Every value can be overridden with an environment variable so the same code base
can be reproduced on another machine.  The defaults are *demonstration* values
only: they are not secrets and they are not suitable for a real deployment.
"""

import hashlib
import hmac
import os

# --- demo account -----------------------------------------------------------------
DEMO_EMAIL = os.getenv("TRACEGUARD_DEMO_EMAIL", "demo@traceguard.local")
DEMO_PASSWORD = os.getenv("TRACEGUARD_DEMO_PASSWORD", "Demo@123")

# --- session token ----------------------------------------------------------------
# Local demonstration signing key.  Override TRACEGUARD_SECRET_KEY outside of a
# throw-away demo environment.
SECRET_KEY = os.getenv(
    "TRACEGUARD_SECRET_KEY",
    "traceguard-local-demonstration-signing-key-not-a-production-secret",
)
TOKEN_TTL_MINUTES = int(os.getenv("TRACEGUARD_TOKEN_TTL_MINUTES", "480"))
TOKEN_ALGORITHM = "HS256"

# --- database ---------------------------------------------------------------------
# Empty means "use data/traceguard.db next to the project root".
DATABASE_URL = os.getenv("TRACEGUARD_DATABASE_URL", "")

# --- CORS -------------------------------------------------------------------------
# Explicit allow-list of the local frontend origins.  No wildcard is used.
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

_PASSWORD_SALT = "traceguard-demo-password-salt"


def hash_password(password: str) -> str:
    """Salted SHA-256 digest used for the local demonstration credential."""
    return hashlib.sha256((_PASSWORD_SALT + (password or "")).encode("utf-8")).hexdigest()


DEMO_PASSWORD_HASH = hash_password(DEMO_PASSWORD)


def verify_password(password: str) -> bool:
    return hmac.compare_digest(hash_password(password), DEMO_PASSWORD_HASH)


def using_default_secret() -> bool:
    return SECRET_KEY == "traceguard-local-demonstration-signing-key-not-a-production-secret"
