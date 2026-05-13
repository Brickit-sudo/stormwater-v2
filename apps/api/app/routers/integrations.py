from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import auth
from app.db import get_db
from app.schemas.integration_status import IntegrationsStatusResponse
from app.services import integrations_service


router = APIRouter(prefix="/v1/integrations", tags=["integrations"])
SessionDep = Annotated[Session, Depends(get_db)]


@router.get("/status", response_model=IntegrationsStatusResponse)
def get_integrations_status(
    db: SessionDep,
    current_user: auth.CurrentUserDep,
    organization_id: auth.OptionalOrgQueryDep,
) -> IntegrationsStatusResponse:
    return integrations_service.get_integrations_status(db=db, organization_id=organization_id)
