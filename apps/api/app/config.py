from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Stormwater V2 API", validation_alias="APP_NAME")
    environment: str = Field(default="local", validation_alias="ENVIRONMENT")
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    cors_origins: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )
    microsoft_tenant_id: str | None = Field(default=None, validation_alias="MICROSOFT_TENANT_ID")
    microsoft_client_id: str | None = Field(default=None, validation_alias="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: str | None = Field(default=None, validation_alias="MICROSOFT_CLIENT_SECRET")
    microsoft_redirect_uri: str | None = Field(default=None, validation_alias="MICROSOFT_REDIRECT_URI")
    microsoft_graph_base_url: str = Field(
        default="https://graph.microsoft.com/v1.0",
        validation_alias="MICROSOFT_GRAPH_BASE_URL",
    )
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", validation_alias="OPENAI_MODEL")
    ai_features_enabled: bool | None = Field(default=None, validation_alias="AI_FEATURES_ENABLED")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_cors_origins() -> list[str]:
    settings = get_settings()
    return [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
