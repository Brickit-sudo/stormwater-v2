from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Query, Request, Response, status
from jwt import InvalidTokenError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import OrganizationMembership, User


SessionDep = Annotated[Session, Depends(get_db)]


def auth_is_enabled(settings: Settings | None = None) -> bool:
    return (settings or get_settings()).auth_enabled


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _require_jwt_secret(settings: Settings) -> str:
    secret = settings.jwt_secret_key.strip() if settings.jwt_secret_key else ""
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET_KEY is required when AUTH_ENABLED=true.",
        )
    return secret


def create_access_token(user: User, settings: Settings | None = None) -> str:
    current = settings or get_settings()
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=current.jwt_expires_minutes)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, _require_jwt_secret(current), algorithm=current.jwt_algorithm)


def set_auth_cookie(response: Response, token: str, settings: Settings | None = None) -> None:
    current = settings or get_settings()
    response.set_cookie(
        key=current.auth_cookie_name,
        value=token,
        max_age=current.jwt_expires_minutes * 60,
        httponly=True,
        secure=current.auth_cookie_secure,
        samesite=current.auth_cookie_samesite,
    )


def clear_auth_cookie(response: Response, settings: Settings | None = None) -> None:
    current = settings or get_settings()
    response.delete_cookie(
        key=current.auth_cookie_name,
        httponly=True,
        secure=current.auth_cookie_secure,
        samesite=current.auth_cookie_samesite,
    )


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized = email.strip().lower()
    if not normalized:
        return None
    return db.scalar(select(User).where(func.lower(User.email) == normalized))


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or user.archived_at is not None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(request: Request, db: SessionDep) -> User | None:
    settings = get_settings()
    if not settings.auth_enabled:
        request.state.current_user = None
        return None

    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    try:
        payload = jwt.decode(
            token,
            _require_jwt_secret(settings),
            algorithms=[settings.jwt_algorithm],
        )
        user_id = uuid.UUID(str(payload["sub"]))
    except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        ) from error

    user = db.get(User, user_id)
    if user is None or user.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive.",
        )

    request.state.current_user = user
    return user


CurrentUserDep = Annotated[User | None, Depends(get_current_user)]


def get_user_memberships(db: Session, user: User) -> list[OrganizationMembership]:
    return list(
        db.scalars(
            select(OrganizationMembership)
            .where(OrganizationMembership.user_id == user.id)
            .order_by(OrganizationMembership.created_at.asc()),
        ).all(),
    )


def get_default_membership(db: Session, user: User) -> OrganizationMembership | None:
    memberships = get_user_memberships(db, user)
    return memberships[0] if memberships else None


def require_organization_access(
    db: Session,
    current_user: User | None,
    organization_id: uuid.UUID,
) -> OrganizationMembership | None:
    if not auth_is_enabled():
        return None
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.organization_id == organization_id,
        ),
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this organization.",
        )
    return membership


def get_query_organization_id(
    db: SessionDep,
    current_user: CurrentUserDep,
    organization_id: Annotated[
        uuid.UUID,
        Query(description="Organization scope. Enforced from auth membership when auth is enabled."),
    ],
) -> uuid.UUID:
    require_organization_access(db, current_user, organization_id)
    return organization_id


def get_optional_query_organization_id(
    db: SessionDep,
    current_user: CurrentUserDep,
    organization_id: Annotated[
        uuid.UUID | None,
        Query(description="Optional organization scope. Enforced from auth membership when auth is enabled."),
    ] = None,
) -> uuid.UUID | None:
    if organization_id is not None:
        require_organization_access(db, current_user, organization_id)
    return organization_id


OrgQueryDep = Annotated[uuid.UUID, Depends(get_query_organization_id)]
OptionalOrgQueryDep = Annotated[uuid.UUID | None, Depends(get_optional_query_organization_id)]
