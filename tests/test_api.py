"""API regression tests for auth and per-user data isolation."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

_DB_FILE = tempfile.NamedTemporaryFile(prefix="careeros-test-", suffix=".db", delete=False)
_DB_FILE.close()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_FILE.name
os.environ["SECRET_KEY"] = "test-secret-key-for-tests-only-and-over-32-bytes"

from fastapi.testclient import TestClient  # noqa: E402
from modules.database import Base, engine  # noqa: E402
from api import app  # noqa: E402

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def register(client: TestClient, name: str, email: str) -> dict:
    response = client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": "a-strong-test-password"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def token_for(client: TestClient, email: str) -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "a-strong-test-password"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_health_and_docs(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/openapi.json").status_code == 200


def test_password_is_hashed_and_login_returns_expiring_token(client: TestClient) -> None:
    user = register(client, "Ada", "ada@example.com")
    assert "password_hash" not in user
    token = token_for(client, "ada@example.com")
    assert token
    from modules.database import SessionLocal
    from modules.models import User

    with SessionLocal() as db:
        saved = db.get(User, user["id"])
        assert saved is not None
        assert saved.password_hash
        assert saved.password_hash != "a-strong-test-password"


def test_private_endpoints_reject_missing_or_invalid_tokens(client: TestClient) -> None:
    assert client.get("/applications").status_code == 401
    assert client.get("/career-timeline").status_code == 401
    assert client.get("/career-dna").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_users_cannot_read_each_others_records(client: TestClient) -> None:
    register(client, "Ada", "ada@example.com")
    register(client, "Grace", "grace@example.com")
    ada = token_for(client, "ada@example.com")
    grace = token_for(client, "grace@example.com")

    created = client.post(
        "/applications",
        headers={"Authorization": f"Bearer {ada}"},
        json={"company": "Example Inc", "job_title": "Analyst", "status": "Applied"},
    )
    assert created.status_code == 201, created.text

    ada_apps = client.get("/applications", headers={"Authorization": f"Bearer {ada}"})
    grace_apps = client.get("/applications", headers={"Authorization": f"Bearer {grace}"})
    assert len(ada_apps.json()) == 1
    assert grace_apps.json() == []

    event = client.post(
        "/career-timeline",
        headers={"Authorization": f"Bearer {ada}"},
        json={"type": "education", "title": "Degree", "date": "2026-05-01"},
    )
    assert event.status_code == 201, event.text
    assert client.get("/career-timeline", headers={"Authorization": f"Bearer {grace}"}).json() == []


def test_duplicate_email_and_weak_password_are_rejected(client: TestClient) -> None:
    register(client, "Ada", "ada@example.com")
    duplicate = client.post(
        "/auth/register",
        json={"name": "Other Ada", "email": "ADA@example.com", "password": "a-strong-test-password"},
    )
    assert duplicate.status_code == 409
    weak = client.post(
        "/auth/register",
        json={"name": "New User", "email": "new@example.com", "password": "short"},
    )
    assert weak.status_code == 422



def test_login_rejects_wrong_password(client: TestClient) -> None:
    register(client, "Security Check", "security-check@example.com")
    response = client.post(
        "/auth/login",
        json={"email": "security-check@example.com", "password": "not-the-correct-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_access_token_has_expiration_claim(client: TestClient) -> None:
    import jwt
    from datetime import datetime, timezone

    register(client, "Expiry Check", "expiry-check@example.com")
    token = token_for(client, "expiry-check@example.com")
    claims = jwt.decode(
        token,
        os.environ["SECRET_KEY"],
        algorithms=["HS256"],
        options={"verify_exp": False},
    )
    assert "exp" in claims
    assert "iat" in claims
    assert claims["exp"] > datetime.now(timezone.utc).timestamp()
