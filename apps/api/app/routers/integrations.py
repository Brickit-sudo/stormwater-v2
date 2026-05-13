from __future__ import annotations

from fastapi import APIRouter

from app.schemas.integration_status import IntegrationsStatusResponse
from app.services import integrations_service


router = APIRouter(prefix="/v1/integrations", tags=["integrations"])


@router.get("/status", response_model=IntegrationsStatusResponse)
def get_integrations_status() -> IntegrationsStatusResponse:
    return integrations_service.get_integrations_status()
