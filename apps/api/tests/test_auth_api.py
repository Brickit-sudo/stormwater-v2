from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import auth
from app.config import get_settings
from app.models import Organization, OrganizationMembership, User
from scripts.seed_dev import DEMO_ORGANIZATION_ID, seed


@pytest.fixture()
def auth_enabled(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-not-used-outside-tests")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _create_user_with_membership(
    db_session: Session,
    organization_id: str,
    *,
    email: str = "admin@example.test",
    password: str = "correct-password",
    is_active: bool = True,
) -> User:
    organization_uuid = uuid.UUID(organization_id)
    user = User(
        email=email,
        full_name="Test Admin",
        password_hash=auth.hash_password(password),
        is_active=is_active,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        OrganizationMembership(
            organization_id=organization_uuid,
            user_id=user.id,
            role="admin",
        ),
    )
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_success_sets_cookie_and_returns_user_without_password(
    auth_enabled: None,
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
) -> None:
    user = _create_user_with_membership(db_session, organization_id)

    response = api_client.post(
        "/v1/auth/login",
        json={"email": user.email, "password": "correct-password"},
    )

    assert response.status_code == 200
    assert "stormwater_v2_session" in response.cookies
    body = response.json()
    assert body["auth_enabled"] is True
    assert body["authenticated"] is True
    assert body["user"]["email"] == user.email
    assert body["user"]["default_organization_id"] == organization_id
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


def test_login_failure_rejects_bad_password(
    auth_enabled: None,
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
) -> None:
    user = _create_user_with_membership(db_session, organization_id)

    response = api_client.post(
        "/v1/auth/login",
        json={"email": user.email, "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert "stormwater_v2_session" not in response.cookies


def test_me_requires_session_then_returns_current_user(
    auth_enabled: None,
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
) -> None:
    user = _create_user_with_membership(db_session, organization_id)

    missing = api_client.get("/v1/auth/me")
    assert missing.status_code == 401

    login = api_client.post(
        "/v1/auth/login",
        json={"email": user.email, "password": "correct-password"},
    )
    assert login.status_code == 200

    response = api_client.get("/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == user.email


def test_protected_route_rejects_missing_session_when_auth_enabled(
    auth_enabled: None,
    api_client: TestClient,
    organization_id: str,
) -> None:
    response = api_client.get("/v1/clients", params={"organization_id": organization_id})

    assert response.status_code == 401


def test_org_scope_requires_membership_when_auth_enabled(
    auth_enabled: None,
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
) -> None:
    user = _create_user_with_membership(db_session, organization_id)
    other_org = Organization(name="Other Organization")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)

    login = api_client.post(
        "/v1/auth/login",
        json={"email": user.email, "password": "correct-password"},
    )
    assert login.status_code == 200

    list_response = api_client.get("/v1/clients", params={"organization_id": str(other_org.id)})
    assert list_response.status_code == 403

    create_response = api_client.post(
        "/v1/clients",
        json={"organization_id": str(other_org.id), "name": "Wrong Org"},
    )
    assert create_response.status_code == 403


def test_auth_disabled_keeps_demo_org_query_mode(
    api_client: TestClient,
    organization_id: str,
) -> None:
    response = api_client.get("/v1/clients", params={"organization_id": organization_id})

    assert response.status_code == 200


def test_seed_creates_demo_admin_with_hashed_password(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-that-is-not-used-outside-tests")
    monkeypatch.setenv("DEMO_ADMIN_EMAIL", "seed-admin@example.test")
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "seed-admin-password")
    get_settings.cache_clear()

    try:
        seed(db_session)
    finally:
        get_settings.cache_clear()

    user = db_session.scalar(select(User).where(User.email == "seed-admin@example.test"))
    assert user is not None
    assert user.is_active is True
    assert user.password_hash is not None
    assert user.password_hash != "seed-admin-password"
    assert auth.verify_password("seed-admin-password", user.password_hash)

    membership = db_session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == DEMO_ORGANIZATION_ID,
        ),
    )
    assert membership is not None
    assert membership.role == "admin"
