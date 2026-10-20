from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Telegram
    api_id: int
    api_hash: str
    collector_session: str = ""
    bot_token: str
    admin_telegram_id: int

    # Database
    database_url: str
    database_url_local: str | None = None

    # Redis
    redis_url: str

    # MinIO
    minio_endpoint: str
    minio_endpoint_local: str = "localhost:9000"
    minio_root_user: str
    minio_root_password: str
    minio_bucket: str = "media"
    minio_public_url: str = "http://localhost:9000"
    minio_secure: bool = False

    # Web
    jwt_secret: str
    web_public_url: str
    bot_username: str

    # AI
    gemini_api_key: str = ""

    # Логика
    buffer_ttl_days: int = 3
    published_ttl_days: int = 1

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()