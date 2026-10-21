import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.ingest import ingest_catalog, ingest_entries  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database():
    """Requires a reachable PostgreSQL with pgvector (DATABASE_URL in backend/.env)."""
    init_db()
    with SessionLocal() as db:
        ingest_catalog(db)
        ingest_entries(db)
    yield


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
