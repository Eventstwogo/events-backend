"""
Test configuration and fixtures for the FastAPI application.

This module provides:
- Database fixtures for testing with SQLite in-memory database
- FastAPI test client setup
- Common test utilities and fixtures
- Proper async support for all fixtures
"""

# Standard library
import asyncio
import io
import os
from typing import Any, AsyncGenerator, Generator
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import UploadFile

# Third-party packages
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Local application imports
from shared.core import config
from shared.db.models import Config, EventsBase, Role
from shared.db.sessions.database import get_db
from main import create_app
from tests.test_config import AppTestSettings, get_test_settings
from user_service.utils.auth import hash_password

test_password = os.getenv("DEFAULT_TEST_PASSWORD", "password123")


@pytest.fixture(scope="session", autouse=True)
def override_global_settings():
    """Force override the global settings at the
    beginning of the test session."""
    config.get_settings.cache_clear()
    config.settings = get_test_settings()


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a test database engine with asyncpg for PostgreSQL."""
    test_settings = get_test_settings()
    print(
        f"\n[Pytest] Connecting to test database at: "
        f"{test_settings.database_url}\n"
    )
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        pool_size=2,  # Smaller pool for tests
        max_overflow=5,
        pool_timeout=30,
        pool_pre_ping=True,
        pool_recycle=1800,
        isolation_level="READ COMMITTED",
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(EventsBase.metadata.create_all)

    yield engine

    # Clean up
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session_factory(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create a test session factory."""
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture(scope="function")
async def test_db_session(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with proper cleanup."""
    async with test_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def test_app(test_db_session: AsyncSession) -> AsyncGenerator[Any, None]:
    """Create a test FastAPI application with mocked dependencies."""
    # Create test settings
    test_settings = get_test_settings()

    # Mock the settings
    with (
        patch("shared.core.config.get_settings", return_value=test_settings),
        patch("shared.core.config.settings", test_settings),
        patch("shared.db.sessions.database.settings", test_settings),
    ):

        app = create_app()

        # Override the database dependency
        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield test_db_session

        app.dependency_overrides[get_db] = override_get_db

        yield app

        # Clean up
        app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_client(test_app: Any) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with proper async support."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", timeout=30.0
    ) as client:
        yield client


@pytest.fixture
def test_settings() -> AppTestSettings:
    """Provide test settings."""
    return get_test_settings()


# Database transaction fixtures for more complex testing scenarios
@pytest_asyncio.fixture(scope="function")
async def test_db_transaction(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session within a transaction that gets rolled back.
    Useful for tests that need to test database operations but shouldn't
    persist changes.
    """
    async with test_session_factory() as session:
        transaction = await session.begin()
        try:
            yield session
        finally:
            await transaction.rollback()
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def isolated_db_session(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Create an isolated database session for tests that need complete isolation.
    """
    async with test_session_factory() as session:
        # Start a savepoint
        savepoint = await session.begin_nested()
        try:
            yield session
        finally:
            await savepoint.rollback()
            await session.close()


# Utility fixtures
@pytest.fixture
def mock_user_data() -> dict[str, Any]:
    """Provide mock user data for testing."""
    return {
        "user_id": "USR123",
        "role_id": "ROL001",
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "is_active": True,
    }


@pytest.fixture
def mock_role_data() -> dict[str, Any]:
    """Provide mock role data for testing."""
    return {
        "role_id": "ROL001",
        "role_name": "Test Role",
        "role_status": True,
    }


@pytest.fixture
def mock_permission_data() -> dict[str, Any]:
    """Provide mock permission data for testing."""
    return {
        "permission_id": "PRM001",
        "permission_name": "Test Permission",
        "permission_status": True,
    }


@pytest.fixture
def mock_category_data() -> dict[str, Any]:
    """Provide mock category data for testing."""
    return {
        "category_id": "CAT123",
        "category_name": "Test Category",
        "category_description": "A test category",
        "category_slug": "test-category",
        "category_status": True,
        "featured_category": True,
        "show_in_menu": True,
    }


@pytest.fixture
def mock_subcategory_data() -> dict[str, Any]:
    """Provide mock subcategory data for testing."""
    return {
        "subcategory_id": "SUB123",
        "category_id": "CAT123",
        "subcategory_name": "Test Subcategory",
        "subcategory_description": "A test subcategory",
        "subcategory_slug": "test-subcategory",
        "subcategory_status": True,
    }


# Authentication fixtures
@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Provide authentication headers for testing."""
    return {
        "Authorization": "Bearer test_token",
        "Content-Type": "application/json",
    }


@pytest.fixture
def admin_auth_headers() -> dict[str, str]:
    """Provide admin authentication headers for testing."""
    return {
        "Authorization": "Bearer admin_test_token",
        "Content-Type": "application/json",
        "X-User-Role": "admin",
    }


# Database cleanup utilities
@pytest_asyncio.fixture(scope="function")
async def clean_db(test_db_session: AsyncSession) -> AsyncGenerator[None, None]:
    """Clean the database before and after tests."""
    # Clean before test
    for table in reversed(EventsBase.metadata.sorted_tables):
        await test_db_session.execute(table.delete())
    await test_db_session.commit()

    yield

    # Clean after test - handle stale data errors
    try:
        # Expunge all objects to avoid stale data issues
        test_db_session.expunge_all()
        # Rollback any pending transactions
        await test_db_session.rollback()
        # Now clean the tables
        for table in reversed(EventsBase.metadata.sorted_tables):
            await test_db_session.execute(table.delete())
        await test_db_session.commit()
    except Exception:
        # If cleanup fails, rollback and try again
        await test_db_session.rollback()
        try:
            for table in reversed(EventsBase.metadata.sorted_tables):
                await test_db_session.execute(table.delete())
            await test_db_session.commit()
        except Exception:
            # If still failing, just rollback
            await test_db_session.rollback()


# Performance testing fixtures
@pytest.fixture
def benchmark_settings() -> dict[str, float]:
    """Settings for performance benchmarking."""
    return {
        "max_response_time": 2.0,  # seconds
        "max_db_query_time": 1.0,  # seconds
    }


# Async context managers for testing
@pytest_asyncio.fixture
async def async_context() -> AsyncGenerator[dict[str, Any], None]:
    """Provide an async context for testing async operations."""
    context: dict[str, Any] = {}
    yield context
    # Cleanup any async resources if needed


# Mock external services
@pytest.fixture
def mock_email_service() -> Any:
    """Mock email service for testing."""

    class MockEmailService:
        def __init__(self):
            self.sent_emails = []

        async def send_email(self, to: str, subject: str, body: str) -> bool:
            self.sent_emails.append(
                {"to": to, "subject": subject, "body": body}
            )
            return True

    return MockEmailService()


# Test data factories
@pytest.fixture
def test_data_factory() -> Any:
    """Factory for creating test data."""

    class TestDataFactory:
        @staticmethod
        def create_user_data(**overrides: Any) -> dict[str, Any]:
            data = {
                "user_id": "USR001",
                "role_id": "ROL001",
                "username": "testuser",
                "email": "test@example.com",
                "password_hash": "hashed_password",
                "is_active": True,
            }
            data.update(overrides)
            return data

        @staticmethod
        def create_category_data(**overrides: Any) -> dict[str, Any]:
            data = {
                "category_id": "CAT001",
                "category_name": "Test Category",
                "category_slug": "test-category",
                "category_status": True,
            }
            data.update(overrides)
            return data

    return TestDataFactory()


# Async test utilities
@pytest.fixture
def async_test_utils() -> Any:
    """Utilities for async testing."""

    class AsyncTestUtils:
        @staticmethod
        async def wait_for_condition(
            condition_func: Any, timeout: float = 5.0, interval: float = 0.1
        ) -> bool:
            """Wait for a condition to become true."""
            import time

            start_time = time.time()
            while time.time() - start_time < timeout:
                if await condition_func():
                    return True
                await asyncio.sleep(interval)
            return False

        @staticmethod
        async def run_with_timeout(coro: Any, timeout: float = 10.0) -> Any:
            """Run a coroutine with a timeout."""
            return await asyncio.wait_for(coro, timeout=timeout)

    return AsyncTestUtils()


# Cleanup fixture to run at the end of each test
@pytest_asyncio.fixture(autouse=True)
async def cleanup_after_test() -> AsyncGenerator[None, None]:
    """Cleanup fixture that runs after each test."""
    yield
    # Perform any necessary cleanup
    # This runs after each test automatically due to autouse=True
    await asyncio.sleep(0)  # Allow any pending tasks to complete


@pytest.fixture
async def seed_config(test_db_session):
    # Check if a config with id=1 already exists
    result = await test_db_session.execute(select(Config).where(Config.id == 1))
    existing_config = result.scalar_one_or_none()

    if not existing_config:
        config = Config(
            id=1,
            default_password=test_password,
            default_password_hash=hash_password(test_password),
            global_180_day_flag=True,
        )
        test_db_session.add(config)
        await test_db_session.commit()
        return config
    return existing_config


@pytest.fixture
async def seed_roles(test_db_session):
    async def _create_role(role_name: str = "SUPERADMIN"):
        # Check if role already exists
        stmt = select(Role).where(Role.role_name == role_name.upper())
        result = await test_db_session.execute(stmt)
        existing_role = result.scalar_one_or_none()

        if existing_role:
            return existing_role

        role = Role(
            role_id="az3v2k",  # or use a random ID generator if needed
            role_name=role_name.upper(),
            role_status=False,  # assume default
        )
        test_db_session.add(role)
        await test_db_session.commit()
        return role

    return _create_role


def generate_test_image(filename="avatar.jpg", content_type="image/jpeg"):
    return UploadFile(
        filename=filename,
        file=io.BytesIO(b"fake-image-content"),
    )
