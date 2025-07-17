"""
Test cases for main subcategories endpoints (/api/v1/subcategories/)
Tests for subcategories.py endpoints:
- GET / - Get all subcategories with filtering
- GET /analytics - Subcategory analytics
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import insert, select

from db.models import Category, SubCategory


def uuid_str():
    """Generate a UUID string for testing."""
    return str(uuid.uuid4())


class TestGetSubcategories:
    """Test cases for getting subcategories."""

    @pytest.mark.asyncio
    async def test_get_all_subcategories(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching all subcategories without filter."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT001",
                category_name="ELECTRONICS",
                category_slug="electronics",
                category_status=False,  # Active
            )
        )

        # Create subcategories
        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB001",
                        "subcategory_name": "SMARTPHONES",
                        "subcategory_slug": "smartphones",
                        "subcategory_status": False,  # Active
                        "category_id": "CAT001",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB002",
                        "subcategory_name": "LAPTOPS",
                        "subcategory_slug": "laptops",
                        "subcategory_status": True,  # Inactive
                        "category_id": "CAT001",
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/")
        body = res.json()

        assert res.status_code == 200
        assert len(body["data"]) == 2
        assert body["message"] == "Subcategories fetched successfully"

        # Check subcategory names are title case
        subcategory_names = [sub["subcategory_name"] for sub in body["data"]]
        assert "Smartphones" in subcategory_names
        assert "Laptops" in subcategory_names

    @pytest.mark.asyncio
    async def test_get_active_subcategories_only(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching only active subcategories."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT002",
                category_name="BOOKS",
                category_slug="books",
                category_status=False,
            )
        )

        # Create subcategories
        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB003",
                        "subcategory_name": "FICTION",
                        "subcategory_slug": "fiction",
                        "subcategory_status": False,  # Active
                        "category_id": "CAT002",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB004",
                        "subcategory_name": "NON_FICTION",
                        "subcategory_slug": "non-fiction",
                        "subcategory_status": True,  # Inactive
                        "category_id": "CAT002",
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get(
            "/api/v1/subcategories/?status_filter=false"
        )
        body = res.json()

        assert res.status_code == 200
        assert len(body["data"]) == 1
        assert body["data"][0]["subcategory_status"] is False  # Active
        assert body["data"][0]["subcategory_name"] == "Fiction"

    @pytest.mark.asyncio
    async def test_get_inactive_subcategories_only(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching only inactive subcategories."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT003",
                category_name="SPORTS",
                category_slug="sports",
                category_status=False,
            )
        )

        # Create subcategories
        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB005",
                        "subcategory_name": "FOOTBALL",
                        "subcategory_slug": "football",
                        "subcategory_status": False,  # Active
                        "category_id": "CAT003",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB006",
                        "subcategory_name": "BASKETBALL",
                        "subcategory_slug": "basketball",
                        "subcategory_status": True,  # Inactive
                        "category_id": "CAT003",
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/?status_filter=true")
        body = res.json()

        assert res.status_code == 200
        assert len(body["data"]) == 1
        assert body["data"][0]["subcategory_status"] is True  # Inactive
        assert body["data"][0]["subcategory_name"] == "Basketball"

    @pytest.mark.asyncio
    async def test_get_subcategories_empty(
        self, test_client: AsyncClient, clean_db
    ):
        """Test fetching subcategories when none exist."""
        res = await test_client.get("/api/v1/subcategories/")
        body = res.json()

        assert res.status_code == 200
        assert body["data"] == []

    @pytest.mark.asyncio
    async def test_get_subcategories_with_featured_flag(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching subcategories with featured flag."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT004",
                category_name="GAMING",
                category_slug="gaming",
                category_status=False,
            )
        )

        # Create subcategories with different featured flags
        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB007",
                        "subcategory_name": "CONSOLES",
                        "subcategory_slug": "consoles",
                        "subcategory_status": False,
                        "featured_subcategory": True,  # Featured
                        "category_id": "CAT004",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB008",
                        "subcategory_name": "PC_GAMES",
                        "subcategory_slug": "pc-games",
                        "subcategory_status": False,
                        "featured_subcategory": False,  # Not featured
                        "category_id": "CAT004",
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/")
        body = res.json()

        assert res.status_code == 200
        assert len(body["data"]) == 2

        # Find the featured subcategory
        featured_sub = None
        non_featured_sub = None
        for sub in body["data"]:
            if sub["subcategory_name"] == "Consoles":
                featured_sub = sub
            elif (
                sub["subcategory_name"] == "Pc_Games"
            ):  # Title case of "PC_GAMES"
                non_featured_sub = sub

        assert featured_sub is not None, "Featured subcategory not found"
        assert (
            non_featured_sub is not None
        ), "Non-featured subcategory not found"

        assert featured_sub["featured_subcategory"] is True
        assert non_featured_sub["featured_subcategory"] is False

    @pytest.mark.asyncio
    async def test_get_subcategories_with_menu_visibility(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching subcategories with menu visibility flags."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT005",
                category_name="MOVIES",
                category_slug="movies",
                category_status=False,
            )
        )

        # Create subcategories with different menu visibility
        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB009",
                        "subcategory_name": "ACTION",
                        "subcategory_slug": "action",
                        "subcategory_status": False,
                        "show_in_menu": True,  # Show in menu
                        "category_id": "CAT005",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB010",
                        "subcategory_name": "COMEDY",
                        "subcategory_slug": "comedy",
                        "subcategory_status": False,
                        "show_in_menu": False,  # Hidden from menu
                        "category_id": "CAT005",
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/")
        body = res.json()

        assert res.status_code == 200
        assert len(body["data"]) == 2

        # Find subcategories by name
        action_sub = None
        comedy_sub = None
        for sub in body["data"]:
            if sub["subcategory_name"] == "Action":
                action_sub = sub
            elif sub["subcategory_name"] == "Comedy":
                comedy_sub = sub

        assert action_sub is not None, "Action subcategory not found"
        assert comedy_sub is not None, "Comedy subcategory not found"

        assert action_sub["show_in_menu"] is True
        assert comedy_sub["show_in_menu"] is False


class TestSubcategoryAnalytics:
    """Test cases for subcategory analytics."""

    @pytest.mark.asyncio
    async def test_subcategory_analytics_empty(
        self, test_client: AsyncClient, clean_db
    ):
        """Test analytics when no subcategories exist."""
        res = await test_client.get("/api/v1/subcategories/analytics")
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Subcategory analytics fetched successfully"
        assert body["data"]["total_subcategories"] == 0
        assert body["data"]["active_subcategories"] == 0
        assert body["data"]["inactive_subcategories"] == 0
        assert body["data"]["featured_subcategories"] == 0
        assert body["data"]["shown_in_menu"] == 0
        assert body["data"]["hidden_from_menu"] == 0

    @pytest.mark.asyncio
    async def test_subcategory_analytics_with_data(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test analytics with various subcategory configurations."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT006",
                category_name="TECHNOLOGY",
                category_slug="technology",
                category_status=False,
            )
        )

        # Create subcategories with different configurations
        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB011",
                        "subcategory_name": "AI",
                        "subcategory_slug": "ai",
                        "subcategory_status": False,  # Active
                        "featured_subcategory": True,  # Featured
                        "show_in_menu": True,  # Show in menu
                        "category_id": "CAT006",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB012",
                        "subcategory_name": "BLOCKCHAIN",
                        "subcategory_slug": "blockchain",
                        "subcategory_status": False,  # Active
                        "featured_subcategory": False,  # Not featured
                        "show_in_menu": False,  # Hidden from menu
                        "category_id": "CAT006",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB013",
                        "subcategory_name": "LEGACY_TECH",
                        "subcategory_slug": "legacy-tech",
                        "subcategory_status": True,  # Inactive
                        "featured_subcategory": False,  # Not featured
                        "show_in_menu": False,  # Hidden from menu
                        "category_id": "CAT006",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB014",
                        "subcategory_name": "ROBOTICS",
                        "subcategory_slug": "robotics",
                        "subcategory_status": False,  # Active
                        "featured_subcategory": True,  # Featured
                        "show_in_menu": True,  # Show in menu
                        "category_id": "CAT006",
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/analytics")
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Subcategory analytics fetched successfully"

        # Verify analytics data
        # Note: In the analytics endpoint, the status logic is reversed:
        # - active_subcategories counts where subcategory_status=True (which means inactive in business logic)
        # - inactive_subcategories counts where subcategory_status=False (which means active in business logic)
        data = body["data"]
        assert data["total_subcategories"] == 4
        assert data["active_subcategories"] == 1  # LEGACY_TECH (status=True)
        assert (
            data["inactive_subcategories"] == 3
        )  # AI, BLOCKCHAIN, ROBOTICS (status=False)
        assert data["featured_subcategories"] == 2  # AI, ROBOTICS
        assert data["shown_in_menu"] == 2  # AI, ROBOTICS
        assert data["hidden_from_menu"] == 2  # BLOCKCHAIN, LEGACY_TECH

    @pytest.mark.asyncio
    async def test_subcategory_analytics_mixed_statuses(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test analytics with mixed active/inactive subcategories."""
        # Create parent categories
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "CAT007",
                        "category_name": "FOOD",
                        "category_slug": "food",
                        "category_status": False,
                    },
                    {
                        "category_id": "CAT008",
                        "category_name": "DRINKS",
                        "category_slug": "drinks",
                        "category_status": False,
                    },
                ]
            )
        )

        # Create subcategories across different categories
        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB015",
                        "subcategory_name": "PIZZA",
                        "subcategory_slug": "pizza",
                        "subcategory_status": False,  # Active
                        "featured_subcategory": True,
                        "show_in_menu": True,
                        "category_id": "CAT007",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB016",
                        "subcategory_name": "SUSHI",
                        "subcategory_slug": "sushi",
                        "subcategory_status": True,  # Inactive
                        "featured_subcategory": False,
                        "show_in_menu": False,
                        "category_id": "CAT007",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB017",
                        "subcategory_name": "COFFEE",
                        "subcategory_slug": "coffee",
                        "subcategory_status": False,  # Active
                        "featured_subcategory": False,
                        "show_in_menu": True,
                        "category_id": "CAT008",
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/analytics")
        body = res.json()

        assert res.status_code == 200

        data = body["data"]
        assert data["total_subcategories"] == 3
        assert data["active_subcategories"] == 1  # SUSHI (status=True)
        assert (
            data["inactive_subcategories"] == 2
        )  # PIZZA, COFFEE (status=False)
        assert data["featured_subcategories"] == 1  # PIZZA
        assert data["shown_in_menu"] == 2  # PIZZA, COFFEE
        assert data["hidden_from_menu"] == 1  # SUSHI
