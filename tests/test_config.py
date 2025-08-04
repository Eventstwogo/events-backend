import json
import os
from functools import lru_cache
from typing import List, Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

os.environ.pop("ENVIRONMENT", None)  # Prevent override
load_dotenv(dotenv_path=".env.test", override=True)


class AppTestSettings(BaseSettings):
    """Test-specific settings that override the main application settings."""

    # === General ===
    APP_NAME: str = "FastAPI Test Application"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["testing"] = "testing"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:3000"
    DESCRIPTION: str = (
        "Events2Go application for managing events and users, built with FastAPI."
    )

    # === Database (isolated test DB) ===
    DB_DRIVER: str = "asyncpg"
    DB_SCHEME: str = "postgresql"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5433
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "events2go_testdb"

    @property
    def database_url(self) -> str:
        return (
            f"{self.DB_SCHEME}+{self.DB_DRIVER}://"
            f"{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # === CORS ===
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        """
        Parses ALLOWED_ORIGINS from either:
        - A JSON list (e.g., '["http://localhost", "http://localhost:3000"]')
        - Or a plain comma-separated string (e.g., 'http://localhost,http://localhost:3000')
        """
        try:
            parsed = json.loads(self.ALLOWED_ORIGINS)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    # === Media ===
    MEDIA_ROOT: str = "test_media/"
    MEDIA_BASE_URL: str = "http://localhost:8000/test_media/"
    DEFAULT_MEDIA_URL: str = "config/logo/abcd1234.png"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_MEDIA_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    ]
    CATEGORY_IMAGE_PATH: str = "categories/{slug_name}/"
    SUBCATEGORY_IMAGE_PATH: str = "subcategories/{category_id}/{slug_name}/"
    CONFIG_LOGO_PATH: str = "config/logo/"
    PROFILE_PICTURE_UPLOAD_PATH: str = (
        "users/profile_pictures/{username}_avatar.{file_extension}"
    )

    # === Email ===
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_USER: str = "your-email@gmail.com"
    SMTP_PASSWORD: str = "your-smtp-password"
    EMAIL_FROM: str = "your-email@gmail.com"
    EMAIL_FROM_NAME: str = "Events2Go API"
    EMAIL_TEMPLATES_DIR: str = "templates"

    # === JWT ===
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600
    REFRESH_TOKEN_EXPIRE_DAYS_IN_SECONDS: int = 604800
    JWT_KEYS_DIR: str = "keys/test"

    # === DigitalOcean Spaces (for mocking in test) ===
    SPACES_REGION_NAME: str = "nyc3"
    SPACES_ENDPOINT_URL: str = "https://nyc3.digitaloceanspaces.com"
    SPACES_BUCKET_NAME: str = "events2go-test"
    SPACES_ACCESS_KEY: str = "test-access-key"
    SPACES_SECRET_KEY: str = "test-secret-key"

    @property
    def spaces_public_url(self) -> str:
        return f"https://{self.SPACES_BUCKET_NAME}.digitaloceanspaces.com"

    # === Meta (loads .env.test automatically) ===
    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        extra="allow",
    )


# === Singleton accessor for tests (optional) ===
@lru_cache()
def get_test_settings() -> AppTestSettings:
    settings = AppTestSettings()
    # Optional: Create media root dir if needed
    import os

    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    return settings
