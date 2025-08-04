from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI

from rbac_service.services.init_roles_permissions import init_roles_permissions
from shared.core.config import JWT_KEY_ID, PRIVATE_KEY, PUBLIC_KEY, settings
from shared.core.logging_config import get_logger
from shared.core.secrets import fetch_secrets_from_vault
from shared.db.sessions.database import (
    configure_session_factory,
    init_db,
    shutdown_db,
)

logger = get_logger(__name__)

PRIVATE_KEY = PRIVATE_KEY
PUBLIC_KEY = PUBLIC_KEY
JWT_KEY_ID = JWT_KEY_ID


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[Any, None]:
    """Handle startup and shutdown events for the FastAPI application."""
    logger.info("Starting up FastAPI application...")

    engine = None
    session_factory = None

    try:
        # 1️⃣ Fetch secrets from Vault and apply to settings
        secrets = await fetch_secrets_from_vault()

        settings.DB_NAME = secrets.get("DB_NAME", settings.DB_NAME)
        settings.DB_HOST = secrets.get("DB_HOST", settings.DB_HOST)
        settings.DB_PASSWORD = secrets.get("DB_PASSWORD", settings.DB_PASSWORD)
        settings.DB_PORT = int(secrets.get("DB_PORT", settings.DB_PORT))
        settings.DB_USER = secrets.get("DB_USER", settings.DB_USER)

        logger.info("🔐 Vault secrets fetched successfully")
        logger.info(
            f"✅ Database config loaded from Vault: "
            f"user={settings.DB_USER}, host={settings.DB_HOST}, port={settings.DB_PORT}, db={settings.DB_NAME}"
        )
        logger.info(f"🔗 Final DATABASE_URL: {settings.database_url}")

        # 2️⃣ Create engine and session factory
        session_factory = configure_session_factory(settings.database_url)

        # 3️⃣ Initialize DB schema
        await init_db(settings.database_url)
        logger.info("Database initialized successfully")

        # 4️⃣ Seed default roles/permissions
        async with session_factory() as session:
            await init_roles_permissions(session)
            logger.info("Default roles and permissions initialized")

    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

    yield

    logger.info("Shutting down FastAPI application...")
    try:
        if engine and session_factory:
            await shutdown_db(engine, session_factory)
            logger.info("Database shutdown successfully")
    except Exception as e:
        logger.error(f"Shutdown failed: {str(e)}")
        raise
