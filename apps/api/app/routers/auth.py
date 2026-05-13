from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import auth
from app.config import get_settings
from app.db import get_db
from app.models import OrganizationMembership, User
from app.schemas.auth import (
    AuthOrganization,
    AuthStatusResponse,
    AuthUser,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
)


router = APIRouter(prefix="/v1/auth", tags=["auth"])
SessionDep = Annotated[Session, Depends(get_db)]


def _serialize_user(db: Session, user: User) -> AuthUser:
    memberships = auth.get_user_memberships(db, user)
    default_membership = memberships[0] if memberships else None
    return AuthUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        default_organization_id=(
            default_membership.organization_id if default_membership is not None else None
        ),
        default_role=default_membership.role if default_membership is not None else None,
        organizations=[
            AuthOrganization(
                id=membership.organization_id,
                name=membership.organization.name,
                role=membership.role,
            )
            for membership in memberships
        ],
    )


def _require_membership(membership: OrganizationMembership | None) -> OrganizationMembership:
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to an organization.",
        )
    return membership


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: SessionDep) -> LoginResponse:
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication is disabled for this environment.",
        )

    user = auth.authenticate_user(db, email=payload.email, password=payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    _require_membership(auth.get_default_membership(db, user))
    token = auth.create_access_token(user, settings)
    auth.set_auth_cookie(response, token, settings)
    return LoginResponse(
        auth_enabled=True,
        authenticated=True,
        user=_serialize_user(db, user),
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(response: Response) -> LogoutResponse:
    settings = get_settings()
    auth.clear_auth_cookie(response, settings)
    return LogoutResponse(auth_enabled=settings.auth_enabled)


@router.get("/me", response_model=AuthStatusResponse)
def get_me(db: SessionDep, current_user: auth.CurrentUserDep) -> AuthStatusResponse:
    settings = get_settings()
    if not settings.auth_enabled:
        return AuthStatusResponse(auth_enabled=False, authenticated=False, user=None)
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return AuthStatusResponse(
        auth_enabled=True,
        authenticated=True,
        user=_serialize_user(db, current_user),
    )
