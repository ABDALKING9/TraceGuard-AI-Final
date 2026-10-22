"""Pytest bootstrap for the TraceGuard AI backend test-suite.

The test-suite must never touch the demonstration database in ``data/``.  A
throw-away SQLite file is created per test session and injected through
``TRACEGUARD_DATABASE_URL`` *before* ``backend.app.db.database`` is imported.
"""

import os
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.mkdtemp(prefix="traceguard-tests-")) / "traceguard-test.db"
os.environ["TRACEGUARD_DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ.setdefault("TRACEGUARD_SECRET_KEY", "traceguard-test-suite-signing-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.db.database import Base, engine  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.seed import seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    """Create the schema once for the whole session and load the seed corpus."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed()
    yield


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def token(client):
    """A valid bearer token for the demonstration operator."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@traceguard.local", "password": "Demo@123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
