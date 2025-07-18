"""
Legacy test cases for subcategory endpoints.
These tests are kept for backward compatibility.
For comprehensive testing, see:
- test_subcategories_main.py
- test_subcategories_by_id.py
- test_subcategories_by_slug.py
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import insert

from shared.db.models import Category, SubCategory


def uuid_str():
    """Generate a UUID string for testing."""
    return str(uuid.uuid4())


class TestLegacySubcategoryEndpoints:
    """Legacy test cases for subcategory endpoints."""

    @pytest.mark.asyncio
    async def test_get_subcategory_by_id_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test getting subcategory by ID - legacy test."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT200",
                category_name="Gaming",
                category_slug="gaming",
                category_status=False,
            )
        )

        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB200",
                subcategory_name="Consoles",
                subcategory_slug="consoles",
                subcategory_status=False,
                category_id="CAT200",
            )
        )

        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/SUB200")
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Subcategory fetched successfully"
        assert body["data"]["subcategory_id"] == "SUB200"
        assert body["data"]["parent_category"]["category_id"] == "CAT200"

    @pytest.mark.asyncio
    async def test_get_subcategory_by_id_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test getting non-existent subcategory by ID - legacy test."""
        res = await test_client.get("/api/v1/subcategories/INVALID_SUB_ID")
        body = res.json()

        assert res.status_code == 404
        # Handle both possible response structures
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, dict):
            error_message = error_message.get("message", "")
        assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_get_subcategory_by_slug_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test getting subcategory by slug - legacy test."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT300",
                category_name="Media",
                category_slug="media",
                category_status=True,
            )
        )

        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB300",
                subcategory_name="Streaming",
                subcategory_slug="streaming",
                subcategory_status=True,
                category_id="CAT300",
            )
        )

        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/slug/streaming")
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["subcategory_slug"] == "streaming"
        assert body["data"]["parent_category"]["category_id"] == "CAT300"

    @pytest.mark.asyncio
    async def test_get_subcategory_by_slug_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test getting non-existent subcategory by slug - legacy test."""
        res = await test_client.get("/api/v1/subcategories/slug/nonexistent")
        body = res.json()

        assert res.status_code == 404
        # Handle both possible response structures
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, dict):
            error_message = error_message.get("message", "")
        assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_get_all_subcategories(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test getting all subcategories - legacy test."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT400",
                category_name="Apps",
                category_slug="apps",
                category_status=True,
            )
        )

        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB400A",
                        "subcategory_name": "Productivity",
                        "subcategory_slug": "productivity",
                        "subcategory_status": True,
                        "category_id": "CAT400",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB400B",
                        "subcategory_name": "Entertainment",
                        "subcategory_slug": "entertainment",
                        "subcategory_status": False,
                        "category_id": "CAT400",
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/")
        body = res.json()

        assert res.status_code == 200
        assert len(body["data"]) == 2

    @pytest.mark.asyncio
    async def test_get_active_subcategories_only(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test getting only active subcategories - legacy test."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT500",
                category_name="Tools",
                category_slug="tools",
                category_status=True,
            )
        )

        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB500A",
                        "subcategory_name": "Utilities",
                        "subcategory_slug": "utilities",
                        "subcategory_status": True,
                        "category_id": "CAT500",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB500B",
                        "subcategory_name": "Legacy",
                        "subcategory_slug": "legacy",
                        "subcategory_status": False,
                        "category_id": "CAT500",
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/?status_filter=true")
        body = res.json()

        assert res.status_code == 200
        assert all(sub["subcategory_status"] for sub in body["data"])
        assert len(body["data"]) == 1

    @pytest.mark.asyncio
    async def test_get_inactive_subcategories_only(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test getting only inactive subcategories - legacy test."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT600",
                category_name="Archives",
                category_slug="archives",
                category_status=True,
            )
        )

        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB600A",
                        "subcategory_name": "Old Docs",
                        "subcategory_slug": "old-docs",
                        "subcategory_status": False,
                        "category_id": "CAT600",
                    }
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get(
            "/api/v1/subcategories/?status_filter=false"
        )
        body = res.json()

        assert res.status_code == 200
        assert all(not sub["subcategory_status"] for sub in body["data"])
        assert len(body["data"]) == 1

    @pytest.mark.asyncio
    async def test_get_all_subcategories_empty(
        self, test_client: AsyncClient, clean_db
    ):
        """Test getting subcategories when none exist - legacy test."""
        res = await test_client.get("/api/v1/subcategories/")
        body = res.json()

        assert res.status_code == 200
        assert body["data"] == []
