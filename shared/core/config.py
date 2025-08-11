import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Literal, Tuple, Type

from dotenv import load_dotenv
from pydantic import SecretBytes
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from shared.core import ENVIRONMENT
from shared.core.secrets import fetch_vault_secrets_sync
from shared.keys.key_manager import KeyManager

# Development override (uncomment if needed for local development)
# os.environ.pop("ENVIRONMENT", None)
# load_dotenv(dotenv_path=".env.local", override=True)


class VaultSettingsSource(PydanticBaseSettingsSource):
    """
    Custom Pydantic settings source that loads values from Vault.
    Skips DB-related secrets in non-production environments.
    """

    def __init__(self, settings_cls: Type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        self._vault_data = None

    def _get_vault_data(self) -> Dict[str, Any]:
        """Lazy load Vault data to avoid multiple calls."""
        if self._vault_data is None:
            self._vault_data = fetch_vault_secrets_sync()
        return self._vault_data

    def get_field_value(
        self, field: Any, field_name: str
    ) -> Tuple[Any, str, bool]:
        """
        Get a single field value from Vault.
        Skips DB secrets in non-production.
        """
        vault_data = self._get_vault_data()

        vault_key_mapping = {
            "POSTGRES_USER": "DATABASE",
            "POSTGRES_HOST": "DB_HOST",
            "POSTGRES_PASSWORD": "DB_PASSWORD",
            "POSTGRES_PORT": "DB_PORT",
            "POSTGRES_DB": "SOURCE_DB_NAME",
            "EMAIL_FROM": "SENDER_EMAIL",
            "SMTP_PASSWORD": "SENDER_PASSWORD",
            "SMTP_USER": "SMTP_LOGIN",
            "SMTP_PORT": "SMTP_PORT",
            "SMTP_HOST": "SMTP_SERVER",
            "SPACES_ACCESS_KEY_ID": "SPACES_ACCESS_KEY",
            "SPACES_BUCKET_NAME": "SPACES_BUCKET_NAME",
            "SPACES_REGION_NAME": "SPACES_REGION_NAME",
            "SPACES_SECRET_ACCESS_KEY": "SPACES_SECRET_KEY",
            "FERNET_KEY": "FERNET_KEY",
        }

        # Skip DB secrets in non-production
        db_fields = {
            "POSTGRES_USER",
            "POSTGRES_HOST",
            "POSTGRES_PASSWORD",
            "POSTGRES_PORT",
            "POSTGRES_DB",
        }
        if ENVIRONMENT != "production" and field_name in db_fields:
            return None, field_name, False

        vault_key = vault_key_mapping.get(field_name)
        if vault_key and vault_key in vault_data:
            return vault_data[vault_key], field_name, False

        return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        """
        Return a dict of settings from Vault.
        Skips DB-related secrets in non-production.
        """
        vault_data = self._get_vault_data()

        if ENVIRONMENT != "production":
            return {
                "EMAIL_FROM": vault_data.get("SENDER_EMAIL"),
                "SMTP_PASSWORD": vault_data.get("SENDER_PASSWORD"),
                "SMTP_USER": vault_data.get("SMTP_LOGIN"),
                "SMTP_PORT": vault_data.get("SMTP_PORT"),
                "SMTP_HOST": vault_data.get("SMTP_SERVER"),
                "SPACES_ACCESS_KEY_ID": vault_data.get("SPACES_ACCESS_KEY"),
                "SPACES_BUCKET_NAME": vault_data.get("SPACES_BUCKET_NAME"),
                "SPACES_REGION_NAME": vault_data.get("SPACES_REGION_NAME"),
                "SPACES_SECRET_ACCESS_KEY": vault_data.get("SPACES_SECRET_KEY"),
                "FERNET_KEY": vault_data.get("FERNET_KEY"),
            }

        # Production: return all secrets
        return {
            "POSTGRES_USER": vault_data.get("DATABASE"),
            "POSTGRES_HOST": vault_data.get("DB_HOST"),
            "POSTGRES_PASSWORD": vault_data.get("DB_PASSWORD"),
            "POSTGRES_PORT": vault_data.get("DB_PORT"),
            "POSTGRES_DB": vault_data.get("SOURCE_DB_NAME"),
            "EMAIL_FROM": vault_data.get("SENDER_EMAIL"),
            "SMTP_PASSWORD": vault_data.get("SENDER_PASSWORD"),
            "SMTP_USER": vault_data.get("SMTP_LOGIN"),
            "SMTP_PORT": vault_data.get("SMTP_PORT"),
            "SMTP_HOST": vault_data.get("SMTP_SERVER"),
            "SPACES_ACCESS_KEY_ID": vault_data.get("SPACES_ACCESS_KEY"),
            "SPACES_BUCKET_NAME": vault_data.get("SPACES_BUCKET_NAME"),
            "SPACES_REGION_NAME": vault_data.get("SPACES_REGION_NAME"),
            "SPACES_SECRET_ACCESS_KEY": vault_data.get("SPACES_SECRET_KEY"),
            "FERNET_KEY": vault_data.get("FERNET_KEY"),
        }


class Settings(BaseSettings):
    """
    Application-wide configuration settings.
    Loaded from environment variables or .env files.
    """

    # === General ===
    APP_NAME: str = "Events2Go App API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["local", "testing", "production", "staging"] = "local"
    APP_HOST: str = "0.0.0.0"  # nosec B104
    APP_PORT: int = 8000
    LOG_LEVEL: str = "info"
    ADMIN_FRONTEND_URL: str = "http://localhost:3001"
    ORGANIZER_FRONTEND_URL: str = "http://localhost:3002"
    USERS_APPLICATION_FRONTEND_URL: str = "http://localhost:3000"
    API_BACKEND_URL: str = "http://localhost:8000"
    DESCRIPTION: str = (
        "Events2Go application for managing events and users, built with FastAPI."
    )

    # === Database ===
    POSTGRES_DRIVER: str = "asyncpg"
    POSTGRES_SCHEME: str = "postgresql"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "events2go"

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

    # === DigitalOcean Spaces ===
    SPACES_REGION_NAME: str = "syd1"
    SPACES_ENDPOINT_URL: str = (
        f"https://{SPACES_REGION_NAME}.digitaloceanspaces.com"
    )
    SPACES_BUCKET_NAME: str = "events2go"
    SPACES_ACCESS_KEY_ID: str = "spaces-access-key-id"
    SPACES_SECRET_ACCESS_KEY: str = "spaces-secret-access-key"

    # === CORS ===
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:3000"

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

    # === JWT ===
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600
    REFRESH_TOKEN_EXPIRE_DAYS_IN_SECONDS: int = 604800
    JWT_KEYS_DIR: str = "shared/keys"
    JWT_ISSUER: str = "e2g-api"
    JWT_AUDIENCE: str = "e2g-clients"

    # === AES256 Encryption ===
    FERNET_KEY: str = "fernet-key"

    # === Pydantic config ===
    model_config = SettingsConfigDict(
        env_file=f".env.{ENVIRONMENT}",
        env_file_encoding="utf-8",
        extra="allow",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            VaultSettingsSource(settings_cls),
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @property
    def spaces_public_url(self) -> str:
        return (
            f"{self.SPACES_ENDPOINT_URL.rstrip('/')}/{self.SPACES_BUCKET_NAME}"
        )

    @property
    def database_url(self) -> str:
        return (
            f"{self.POSTGRES_SCHEME}+{self.POSTGRES_DRIVER}://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # @property
    # def database_url(self) -> str:
    #     return "postgresql+asyncpg://postgres:postgres@localhost:5432/events2go"

    @property
    def cors_origins(self) -> List[str]:
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


# === Singleton accessor (ensures one instance only) ===
@lru_cache()
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
