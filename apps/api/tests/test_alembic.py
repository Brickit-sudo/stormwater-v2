from pathlib import Path

from alembic.config import Config

from app.db import Base
import app.models


API_DIR = Path(__file__).resolve().parents[1]


def test_alembic_config_loads() -> None:
    config = Config(str(API_DIR / "alembic.ini"))
    assert config.get_main_option("script_location") == "alembic"


def test_alembic_env_targets_model_metadata() -> None:
    env_py = API_DIR / "alembic" / "env.py"
    assert env_py.exists()
    assert "target_metadata = Base.metadata" in env_py.read_text(encoding="utf-8")
    assert Base.metadata.tables["organizations"].name == "organizations"
    assert app.models
