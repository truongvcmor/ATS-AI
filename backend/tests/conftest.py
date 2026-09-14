import os
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://ats:ats@localhost:5433/ats_test")
# The whole suite shares one process/IP against the login rate limiter (many
# fixtures log in fresh per test) — raise the ceiling so tests never trip it.
os.environ.setdefault("LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "100000")

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.config import settings
from app.main import app
from app.models import *  # noqa: F401,F403 register all tables on Base.metadata


def _admin_database_url() -> str:
    return settings.DATABASE_URL.rsplit("/", 1)[0] + "/postgres"


def _ensure_test_database() -> None:
    admin_engine = create_engine(_admin_database_url(), isolation_level="AUTOCOMMIT")
    db_name = settings.DATABASE_URL.rsplit("/", 1)[1]
    with admin_engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    _ensure_test_database()
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables():
    engine = create_engine(settings.DATABASE_URL)
    table_names = [t.name for t in reversed(Base.metadata.sorted_tables)]
    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"))
        conn.commit()
    engine.dispose()

    # system_settings was just wiped — reset the in-process AI config cache
    # (app.core.runtime_config) back to plain env defaults so no test can
    # leak a DB-backed provider override into the next one. TestClient(app)
    # also does this via the startup event, but tests that call factories
    # directly (without a `client`) need it done explicitly here too.
    from app.core.runtime_config import apply_db_overrides

    apply_db_overrides(None)
    yield


@pytest.fixture()
def db_session():
    engine = create_engine(settings.DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def recruiter_token(client):
    email = f"recruiter-{uuid.uuid4().hex[:8]}@ats.com"
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test Recruiter", "role": "RECRUITER"},
    )
    resp = client.post("/api/auth/login", data={"username": email, "password": "password123"})
    return resp.json()["access_token"]


@pytest.fixture()
def auth_headers(recruiter_token):
    return {"Authorization": f"Bearer {recruiter_token}"}
