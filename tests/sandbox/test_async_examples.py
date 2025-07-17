"""
Comprehensive async test examples demonstrating all testing features.
This file serves as a reference for writing async tests.
"""

import asyncio
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.db.models import Category, Role
from tests.utils.db_helpers import AsyncDatabaseTestHelper


@pytest.mark.usefixtures("test_db_session", "test_client")
class TestAsyncExamples:
    """Reference async test patterns for database and API."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_basic_async_db_operation(
        self, test_db_session: AsyncSession
    ) -> None:
        """Basic async test example."""
        db_helper = AsyncDatabaseTestHelper(test_db_session)
        role = await db_helper.create_role(
            role_name="Basic Async Role", role_status=True
        )
        assert role.role_id is not None
        assert role.role_name == "Basic Async Role"
        assert role.role_status is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_async_api_interaction(
        self, test_client: AsyncClient
    ) -> None:
        """Correct async test for root and health routes."""

        # Request root endpoint
        root_res = await test_client.get("/")
        assert root_res.status_code == 200
        root_json = root_res.json()

        assert root_json["message"] == "Welcome to Events2go API Services"
        assert "version" in root_json
        assert "docs_url" in root_json
        assert "redoc_url" in root_json

        # Request health endpoint
        health_res = await test_client.get("/health")
        assert health_res.status_code == 200
        health_json = health_res.json()

        assert health_json["status"] == "healthy"
        assert "message" in health_json

    @pytest.mark.asyncio
    @pytest.mark.db
    async def test_concurrent_database_operations(
        self, test_session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Example of concurrent async database operations."""

        async def create_role_with_index(index: int) -> Role:
            async with test_session_factory() as session:
                db_helper = AsyncDatabaseTestHelper(session)
                return await db_helper.create_role(
                    role_name=f"Concurrent Role {index}", role_status=True
                )

        coros = [create_role_with_index(i) for i in range(5)]
        roles = await asyncio.gather(*coros)
        assert len(roles) == 5

    @pytest.mark.asyncio
    @pytest.mark.db
    async def test_concurrent_category_operations(
        self, test_session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Example of concurrent async category operations."""

        async def create_category(index: int) -> Category:
            async with test_session_factory() as session:
                db_helper = AsyncDatabaseTestHelper(session)
                return await db_helper.create_category(
                    category_name=f"Concurrent Category {index}",
                    category_status=True,
                )

        coros = [create_category(i) for i in range(3)]
        categories = await asyncio.gather(*coros)
        assert len(categories) == 3

    @pytest.mark.asyncio
    @pytest.mark.db
    async def test_concurrent_test_entities(
        self, test_session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Example of concurrent async test entities."""

        async def create_test_entities(index: int) -> Any:
            async with test_session_factory() as session:
                db_helper = AsyncDatabaseTestHelper(session)
                return await db_helper.create_role(
                    role_name=f"Concurrent Test Entity {index}",
                    role_status=True,
                )

        coros = [create_test_entities(i) for i in range(5)]
        batches = await asyncio.gather(*coros)
        assert len(batches) == 5
