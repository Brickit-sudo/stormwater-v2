from app.main import app
from app.routers.health import health_check


def test_app_imports_cleanly() -> None:
    assert app.title == "Stormwater V2 API"


def test_health_endpoint_is_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/health" in paths


def test_crm_endpoints_are_registered() -> None:
    paths = {route.path for route in app.routes}
    assert "/v1/clients" in paths
    assert "/v1/clients/{client_id}/sites" in paths
    assert "/v1/clients/{client_id}/jobs" in paths
    assert "/v1/sites" in paths
    assert "/v1/sites/{site_id}/jobs" in paths
    assert "/v1/jobs" in paths


def test_health_handler_response() -> None:
    assert health_check() == {
        "status": "ok",
        "service": "stormwater-v2-api",
    }
