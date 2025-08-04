import logging
from logging import Logger

from shared.core.secrets import fetch_secrets_from_vault

# Configure logging
logging.basicConfig(level=logging.INFO)
logger: Logger = logging.getLogger(__name__)

import json
import os
from functools import lru_cache
from typing import List, Literal

from dotenv import load_dotenv
from pydantic import SecretBytes
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.keys.key_manager import KeyManager

# os.environ.pop("ENVIRONMENT", None)  # Prevent override
# load_dotenv(dotenv_path=".env.local", override=True)


class Settings(BaseSettings):
    """
    Application-wide configuration settings.
    Loaded from environment variables or .env files.
    """

    # === General ===
    APP_NAME: str = "Events2Go App API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    APP_HOST: str = "0.0.0.0"  # nosec B104
    APP_PORT: int = 8000
    LOG_LEVEL: str = "info"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:3000"
    DESCRIPTION: str = (
        "Events2Go application for managing events and users, built with FastAPI."
    )

    # === Database ===
    DB_DRIVER: str = "asyncpg"
    DB_SCHEME: str = "postgresql"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "events2go"

    @property
    def database_url(self) -> str:
        """Builds the SQLAlchemy-compatible database URL."""
        return (
            f"{self.DB_SCHEME}+{self.DB_DRIVER}://"
            f"{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # === Vault Configuration ===
    VAULT_URL: str = os.getenv("VAULT_URL", "http://localhost:8200")
    VAULT_TOKEN: str = os.getenv("VAULT_TOKEN", "")
    VAULT_SECRET_PATH: str = os.getenv(
        "VAULT_SECRET_PATH", "v1/kv/data/secrets"
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
    MEDIA_ROOT: str = "media/"
    MEDIA_BASE_URL: str = "http://localhost:8000/media/"
    DEFAULT_MEDIA_URL: str = "config/logo/abcd1234.png"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_MEDIA_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
        "image/avif",
        "image/jxl",
    ]

    CATEGORY_IMAGE_PATH: str = "categories/{slug_name}/"
    SUBCATEGORY_IMAGE_PATH: str = "subcategories/{category_id}/{slug_name}/"
    CONFIG_LOGO_PATH: str = "config/logo/"
    PROFILE_PICTURE_UPLOAD_PATH: str = (
        "users/profile_pictures/{username}_avatar"
    )
    EVENT_CARD_IMAGE_UPLOAD_PATH: str = "events/{event_id}/card_image"
    EVENT_BANNER_IMAGE_UPLOAD_PATH: str = "events/{event_id}/banner_image"
    EVENT_EXTRA_IMAGES_UPLOAD_PATH: str = "events/{event_id}/extra_images"

    # === Email ===
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_USER: str = "your-email@gmail.com"
    SMTP_PASSWORD: str = "your-smtp-password"
    EMAIL_FROM: str = "your-email@gmail.com"
    EMAIL_FROM_NAME: str = "Events2Go API"
    EMAIL_TEMPLATES_DIR: str = "shared/templates"
    SUPPORT_EMAIL: str = "support@events2go.com"

    # === JWT ===
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600
    REFRESH_TOKEN_EXPIRE_DAYS_IN_SECONDS: int = 604800
    JWT_KEYS_DIR: str = "shared/keys"
    JWT_ISSUER: str = "e2g-api"
    JWT_AUDIENCE: str = "e2g-clients"

    # === AES256 Encryption ===
    FERNET_KEY: str = "75ncwG_cPEC45F60cDCKTzfM_eVO1bYTz3ieIOWv3mQ="

    # === DigitalOcean Spaces ===
    SPACES_REGION_NAME: str = "nyc3"
    SPACES_ENDPOINT_URL: str = "https://nyc3.digitaloceanspaces.com"
    SPACES_BUCKET_NAME: str = "events2go"
    SPACES_ACCESS_KEY: str = "spaces-access-key-id"
    SPACES_SECRET_KEY: str = "spaces-secret-access-key"

    @property
    def spaces_public_url(self) -> str:
        """Returns public URL to access the DigitalOcean Spaces bucket."""
        return f"https://{self.SPACES_BUCKET_NAME}.digitaloceanspaces.com"

    # === Meta Configuration for Pydantic ===
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="allow",
    )

    async def load_vault_secrets(self):
        global vault_url, vault_token, secret_path
        vault_url = self.VAULT_URL
        vault_token = self.VAULT_TOKEN
        secret_path = self.VAULT_SECRET_PATH
        logger.info(f"Fetching secrets from Vault: {vault_url}/{secret_path}")
        secrets = await fetch_secrets_from_vault()
        logger.info(f"Raw secrets from Vault: {secrets}")
        self.DB_NAME = secrets.get("DB_NAME", self.DB_NAME)
        self.DB_HOST = secrets.get("DB_HOST", self.DB_HOST)
        self.DB_PASSWORD = secrets.get("DB_PASSWORD", self.DB_PASSWORD)
        self.DB_PORT = int(secrets.get("DB_PORT", self.DB_PORT))
        self.DB_USER = secrets.get("DB_USER", self.DB_USER)
        if not self.DB_USER:
            self.DB_USER = secrets.get("DB_USER", self.DB_USER)
        if not all(
            [self.DB_USER, self.DB_PASSWORD, self.DB_HOST, self.DB_NAME]
        ):
            raise ValueError(
                f"Missing database credentials after Vault fetch: user={self.DB_USER}, host={self.DB_HOST}, port={self.DB_PORT}, db={self.DB_NAME}, secrets={secrets}"
            )
        self.SMTP_PORT = int(secrets.get("SMTP_PORT", self.SMTP_PORT))
        self.SMTP_HOST = secrets.get("SMTP_HOST", self.SMTP_HOST)
        self.SMTP_USER = secrets.get("SMTP_USER", self.SMTP_USER)
        self.SMTP_PASSWORD = secrets.get("SMTP_PASSWORD", self.SMTP_PASSWORD)
        self.EMAIL_FROM = secrets.get("EMAIL_FROM", self.EMAIL_FROM)
        self.SPACES_REGION_NAME = secrets.get(
            "SPACES_REGION_NAME", self.SPACES_REGION_NAME
        )
        self.SPACES_BUCKET_NAME = secrets.get(
            "SPACES_BUCKET_NAME", self.SPACES_BUCKET_NAME
        )
        self.SPACES_ACCESS_KEY = secrets.get(
            "SPACES_ACCESS_KEY", self.SPACES_ACCESS_KEY
        )
        self.SPACES_SECRET_KEY = secrets.get(
            "SPACES_SECRET_KEY", self.SPACES_SECRET_KEY
        )
        logger.info(
            f"Updated database settings: user={self.DB_USER}, host={self.DB_HOST}, port={self.DB_PORT}, db={self.DB_NAME}"
        )


# === Singleton accessor (ensures one instance only) ===
# @lru_cache()
def get_settings() -> Settings:
    settings_instance = Settings()  # Renamed to avoid redefinition warning

    # Automatically create media directory if it doesn't exist
    os.makedirs(settings_instance.MEDIA_ROOT, exist_ok=True)

    return settings_instance


# === Load settings ===
settings: Settings = get_settings()

# === KeyManager initialization for JWT ===
key_manager = KeyManager(
    key_dir=settings.JWT_KEYS_DIR,
    key_refresh_days=settings.REFRESH_TOKEN_EXPIRE_DAYS_IN_SECONDS,
)

PRIVATE_KEY = SecretBytes(key_manager.get_private_key())
PUBLIC_KEY = SecretBytes(key_manager.get_public_key())
JWT_KEY_ID = key_manager.get_key_id()
