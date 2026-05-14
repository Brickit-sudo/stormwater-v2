from scripts import smoke_crm_api
from scripts.seed_dev import DEMO_ORGANIZATION_ID


def test_smoke_script_defaults_match_seed_constants() -> None:
    assert smoke_crm_api.DEFAULT_API_BASE_URL == "http://127.0.0.1:8000"
    assert smoke_crm_api.DEFAULT_ORGANIZATION_ID == str(DEMO_ORGANIZATION_ID)
    assert smoke_crm_api.EXPECTED_COUNTS == {
        "clients": 3,
        "sites": 5,
        "map_sites": 5,
        "jobs": 8,
        "reminders": 4,
        "open_reminders": 3,
        "files": 9,
        "email_messages": 5,
        "ai_drafts": 3,
        "email_import_batches": 1,
        "bmp_systems": 4,
        "observations": 4,
        "record_notes": 3,
        "knowledge_items": 4,
        "documents": 3,
        "product_ideas": 21,
        "product_decisions": 8,
    }
