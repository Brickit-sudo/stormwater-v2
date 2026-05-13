from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.integration_status import IntegrationsStatusResponse
from app.services import integrations_service


router = APIRouter(prefix="/v1/integrations", tags=["integrations"])
SessionDep = Annotated[Session, Depends(get_db)]


@router.get("/status", response_model=IntegrationsStatusResponse)
def get_integrations_status(
    db: SessionDep,
    organization_id: Annotated[
        uuid.UUID | None,
        Query(description="Optional organization scope for provider connection status."),
    ] = None,
) -> IntegrationsStatusResponse:
    return integrations_service.get_integrations_status(db=db, organization_id=organization_id)
