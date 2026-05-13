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
    token_encryption_key: str | None = Field(default=None, validation_alias="TOKEN_ENCRYPTION_KEY")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", validation_alias="OPENAI_MODEL")
    ai_features_enabled: bool | None = Field(default=None, validation_alias="AI_FEATURES_ENABLED")
    google_client_id: str | None = Field(default=None, validation_alias="GOOGLE_CLIENT_ID")
    google_api_key: str | None = Field(default=None, validation_alias="GOOGLE_API_KEY")
    auth_enabled: bool = Field(default=False, validation_alias="AUTH_ENABLED")
    jwt_secret_key: str | None = Field(default=None, validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_expires_minutes: int = Field(default=720, validation_alias="JWT_EXPIRES_MINUTES")
    auth_cookie_name: str = Field(
        default="stormwater_v2_session",
        validation_alias="AUTH_COOKIE_NAME",
    )
    auth_cookie_secure: bool = Field(default=False, validation_alias="AUTH_COOKIE_SECURE")
    auth_cookie_samesite: str = Field(default="lax", validation_alias="AUTH_COOKIE_SAMESITE")
    demo_admin_email: str = Field(
        default="admin@stormwater.local",
        validation_alias="DEMO_ADMIN_EMAIL",
    )
    demo_admin_password: str | None = Field(default=None, validation_alias="DEMO_ADMIN_PASSWORD")

    @property
    def google_drive_picker_enabled(self) -> bool:
        return bool(
            self.google_client_id
            and self.google_client_id.strip()
            and self.google_api_key
            and self.google_api_key.strip()
        )

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
