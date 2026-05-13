from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1)


class AuthOrganization(BaseModel):
    id: uuid.UUID
    name: str
    role: str


class AuthUser(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    default_organization_id: uuid.UUID | None
    default_role: str | None
    organizations: list[AuthOrganization]


class AuthStatusResponse(BaseModel):
    auth_enabled: bool
    authenticated: bool
    user: AuthUser | None


class LoginResponse(AuthStatusResponse):
    authenticated: bool = True


class LogoutResponse(BaseModel):
    auth_enabled: bool
    authenticated: bool = False
