import time
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.db.models.base import EventsBase


class TestDatabaseConnection:
    """Test database connection and basic operations."""

    @pytest.mark.asyncio
    @pytest.mark.db
    async def test_database_connection(
        self, test_db_session: AsyncSession
    ) -> None:
        """Test that database connection works."""
        result = await test_db_session.execute(text("SELECT 1 as test_value"))
        row = result.fetchone()
        assert row is not None, "No row returned from test_value query"
        assert (
            row.test_value == 1
        ), f"Expected test_value 1, got {row.test_value}"

    @pytest.mark.asyncio
    @pytest.mark.db
    async def test_database_transaction_rollback(
        self, test_db_session: AsyncSession
    ) -> None:
        """Test that database transactions can be rolled back."""
        async with test_db_session.begin():
            result = await test_db_session.execute(
                text("SELECT 1 as test_value")
            )
            row = result.fetchone()
            assert row is not None, "No row returned from test_value query"
            assert (
                row.test_value == 1
            ), f"Expected test_value 1, got {row.test_value}"
        await test_db_session.rollback()

    @pytest.mark.asyncio
    @pytest.mark.db
    async def test_database_commit(self, test_db_session: AsyncSession):
        """Test that database commits work."""
        await test_db_session.commit()

    @pytest.mark.asyncio
    @pytest.mark.db
    async def test_metadata_tables_created(
        self, test_db_session: AsyncSession
    ) -> None:
        """Test that all tables from metadata are created."""
        if test_db_session.bind.dialect.name != "postgresql":
            pytest.skip("Table check only for PostgreSQL")

        expected_tables = set(EventsBase.metadata.tables.keys())
        result = await test_db_session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        )
        actual_tables = {row.table_name for row in result.fetchall()}
        missing_tables = expected_tables - actual_tables
        assert expected_tables.issubset(
            actual_tables
        ), f"Missing tables: {missing_tables}"


class TestDatabaseTransactions:
    """Test database transaction handling."""

    @pytest.mark.asyncio
    @pytest.mark.db
    async def test_transaction_isolation(
        self, test_db_transaction: AsyncSession
    ) -> None:
        """Test that transactions are properly isolated."""
        result = await test_db_transaction.execute(
            text("SELECT 1 as isolated_test")
        )
        row = result.fetchone()
        assert row is not None, "No row returned from isolated_test query"
        assert (
            row.isolated_test == 1
        ), f"Expected isolated_test 1, got {row.isolated_test}"

    @pytest.mark.asyncio
    @pytest.mark.db
    async def test_concurrent_sessions(
        self, test_session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Test that multiple sessions can work concurrently."""
        async with test_session_factory() as session1:
            async with test_session_factory() as session2:
                result1 = await session1.execute(
                    text("SELECT 1 as session1_test")
                )
                result2 = await session2.execute(
                    text("SELECT 2 as session2_test")
                )
                row1 = result1.fetchone()
                row2 = result2.fetchone()
                assert (
                    row1 is not None
                ), "No row returned from session1_test query"
                assert (
                    row2 is not None
                ), "No row returned from session2_test query"
                assert (
                    row1.session1_test == 1
                ), f"Expected session1_test 1, got {row1.session1_test}"
                assert (
                    row2.session2_test == 2
                ), f"Expected session2_test 2, got {row2.session2_test}"


class TestDatabaseFixtures:
    """Test database fixture cleanup functionality."""

    @pytest.mark.asyncio
    @pytest.mark.db
    async def test_clean_db_fixture(
        self, clean_db: Any, test_db_session: AsyncSession
    ) -> None:
        """Test that the clean_db fixture works properly."""
        result = await test_db_session.execute(text("SELECT 1 as clean_test"))
        row = result.fetchone()
        assert row is not None, "No row returned from clean_test query"
        assert (
            row.clean_test == 1
        ), f"Expected clean_test 1, got {row.clean_test}"


class TestDatabasePerformance:
    """Test database performance characteristics."""

    @pytest.mark.asyncio
    @pytest.mark.db
    @pytest.mark.slow
    async def test_query_performance(
        self, test_db_session: AsyncSession, benchmark_settings: dict
    ) -> None:
        """Test that basic queries perform within acceptable limits."""
        start_time = time.time()
        result = await test_db_session.execute(text("SELECT 1 as perf_test"))
        end_time = time.time()
        query_time = end_time - start_time

        max_time = benchmark_settings["max_db_query_time"]
        assert (
            query_time < max_time
        ), f"Query took {query_time:.3f}s, max allowed: {max_time}s"

        row = result.fetchone()
        assert row is not None, "No row returned from perf_test query"
        assert row.perf_test == 1, f"Expected perf_test 1, got {row.perf_test}"
