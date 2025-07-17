"""
Test cases for main categories endpoints (/api/v1/categories/)
Tests for categories.py endpoints:
- POST /create - Create category or subcategory
- GET / - Get all categories with filtering
- GET /analytics - Category analytics
- GET /total_categories_count - Total categories count
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import insert, select

from db.models import Category, SubCategory


def uuid_str():
    """Generate a UUID string for testing."""
    return str(uuid.uuid4())


class TestCreateCategory:
    """Test cases for creating categories."""

    @pytest.mark.asyncio
    async def test_create_category_success(
        self, test_client: AsyncClient, clean_db, test_db_session
    ):
        """Test successful creation of a new category."""
        data = {
            "name": "Electronics",
            "slug": "electronics",
            "description": "Electronic items and devices",
            "meta_title": "Electronics Store",
            "meta_description": "Top tech and electronics",
            "featured": "true",
            "show_in_menu": "true",
        }

        res = await test_client.post("/api/v1/categories/create", data=data)
        body = res.json()

        assert res.status_code == 201
        assert "category_id" in body["data"]
        assert body["message"] == "Category created successfully"

        # Verify in database
        stmt = select(Category).where(Category.category_slug == "electronics")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category is not None
        assert category.category_name == "ELECTRONICS"  # Converted to uppercase
        assert category.featured_category is True
        assert category.show_in_menu is True

    @pytest.mark.asyncio
    async def test_create_category_minimal_data(
        self, test_client: AsyncClient, clean_db, test_db_session
    ):
        """Test creating category with minimal required data."""
        data = {"name": "Books"}

        res = await test_client.post("/api/v1/categories/create", data=data)
        body = res.json()

        assert res.status_code == 201
        assert "category_id" in body["data"]

        # Verify in database
        stmt = select(Category).where(Category.category_name == "BOOKS")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category is not None
        assert category.category_slug == "books"  # Auto-generated from name

    @pytest.mark.asyncio
    async def test_create_subcategory_success(
        self, test_client: AsyncClient, clean_db, test_db_session
    ):
        """Test successful creation of a subcategory under existing category."""
        # First create parent category
        parent_category = Category(
            category_id="CAT001",
            category_name="ELECTRONICS",
            category_slug="electronics",
            category_status=False,  # Active
        )
        test_db_session.add(parent_category)
        await test_db_session.commit()

        data = {
            "category_id": "CAT001",  # Parent category ID
            "name": "Smartphones",
            "slug": "smartphones",
            "description": "Mobile phones and accessories",
        }

        res = await test_client.post("/api/v1/categories/create", data=data)
        body = res.json()

        assert res.status_code == 201
        assert "subcategory_id" in body["data"]
        assert body["message"] == "Subcategory created successfully"

        # Verify in database
        stmt = select(SubCategory).where(
            SubCategory.subcategory_slug == "smartphones"
        )
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory is not None
        assert subcategory.subcategory_name == "SMARTPHONES"
        assert subcategory.category_id == "CAT001"

    @pytest.mark.asyncio
    async def test_create_category_duplicate_name(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test creating category with duplicate name fails."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT001",
                category_name="ELECTRONICS",
                category_slug="electronics",
                category_status=False,
            )
        )
        await test_db_session.commit()

        data = {"name": "Electronics"}

        res = await test_client.post("/api/v1/categories/create", data=data)
        body = res.json()

        assert res.status_code == 400
        # Check both possible response structures
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            error_message = error_message.lower()
            assert "already exists" in error_message
        else:
            # Handle case where error_message might be a dict or other type
            assert "already exists" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_create_category_invalid_name(
        self, test_client: AsyncClient, clean_db
    ):
        """Test creating category with invalid name fails."""
        data = {"name": ""}  # Empty name

        res = await test_client.post("/api/v1/categories/create", data=data)

        assert res.status_code in [400, 422]  # Validation error

    @pytest.mark.asyncio
    async def test_create_subcategory_invalid_parent(
        self, test_client: AsyncClient, clean_db
    ):
        """Test creating subcategory with non-existent parent category fails."""
        data = {
            "category_id": "INVALID_CAT",
            "name": "Smartphones",
        }

        res = await test_client.post("/api/v1/categories/create", data=data)
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            error_message = error_message.lower()
            assert "not found" in error_message
        else:
            # Handle case where error_message might be a dict or other type
            assert "not found" in str(error_message).lower()


class TestGetCategories:
    """Test cases for getting categories."""

    @pytest.mark.asyncio
    async def test_get_all_categories(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching all categories without filter."""
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "CAT001",
                        "category_name": "ELECTRONICS",
                        "category_slug": "electronics",
                        "category_status": False,  # Active
                    },
                    {
                        "category_id": "CAT002",
                        "category_name": "BOOKS",
                        "category_slug": "books",
                        "category_status": True,  # Inactive
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/categories/")
        body = res.json()

        assert res.status_code == 200
        assert len(body["data"]) == 2
        assert body["message"] == "Categories fetched successfully"

    @pytest.mark.asyncio
    async def test_get_active_categories_only(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching only active categories."""
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "CAT001",
                        "category_name": "ACTIVE",
                        "category_slug": "active",
                        "category_status": False,  # Active
                    },
                    {
                        "category_id": "CAT002",
                        "category_name": "INACTIVE",
                        "category_slug": "inactive",
                        "category_status": True,  # Inactive
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/categories/?status_filter=false")
        body = res.json()

        assert res.status_code == 200
        assert len(body["data"]) == 1
        assert body["data"][0]["category_status"] is False  # Active

    @pytest.mark.asyncio
    async def test_get_inactive_categories_only(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching only inactive categories."""
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "CAT001",
                        "category_name": "ACTIVE",
                        "category_slug": "active",
                        "category_status": False,  # Active
                    },
                    {
                        "category_id": "CAT002",
                        "category_name": "INACTIVE",
                        "category_slug": "inactive",
                        "category_status": True,  # Inactive
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/categories/?status_filter=true")
        body = res.json()

        assert res.status_code == 200
        assert len(body["data"]) == 1
        assert body["data"][0]["category_status"] is True  # Inactive

    @pytest.mark.asyncio
    async def test_get_categories_empty(
        self, test_client: AsyncClient, clean_db
    ):
        """Test fetching categories when none exist."""
        res = await test_client.get("/api/v1/categories/")
        body = res.json()

        assert res.status_code == 200
        assert body["data"] == []


class TestListCategories:
    """Test cases for list categories endpoint."""

    @pytest.mark.asyncio
    async def test_list_all_categories_and_subcategories(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching all categories and subcategories."""
        # Create test categories
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "CAT001",
                        "category_name": "ELECTRONICS",
                        "category_slug": "electronics",
                        "category_status": False,  # Active
                    },
                    {
                        "category_id": "CAT002",
                        "category_name": "BOOKS",
                        "category_slug": "books",
                        "category_status": True,  # Inactive
                    },
                ]
            )
        )

        await test_db_session.commit()

        res = await test_client.get("/api/v1/categories/list-categories")
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Categories fetched successfully"

        # Check that our test categories are present
        category_names = [cat["category_name"] for cat in body["data"]]
        assert "Electronics" in category_names
        assert "Books" in category_names

        # Check that category names are title case
        electronics_cat = next(
            cat for cat in body["data"] if cat["category_name"] == "Electronics"
        )
        books_cat = next(
            cat for cat in body["data"] if cat["category_name"] == "Books"
        )

        assert electronics_cat["category_status"] is False
        assert books_cat["category_status"] is True

    @pytest.mark.asyncio
    async def test_list_active_categories_only(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching only active categories and subcategories."""
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "CAT001",
                        "category_name": "ACTIVE_CAT",
                        "category_slug": "active-cat",
                        "category_status": False,  # Active
                    },
                    {
                        "category_id": "CAT002",
                        "category_name": "INACTIVE_CAT",
                        "category_slug": "inactive-cat",
                        "category_status": True,  # Inactive
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get(
            "/api/v1/categories/list-categories?status_value=false"
        )
        body = res.json()

        assert res.status_code == 200
        assert len(body["data"]) == 1
        assert body["data"][0]["category_status"] is False

    @pytest.mark.asyncio
    async def test_list_inactive_categories_only(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching only inactive categories and subcategories."""
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "CAT001",
                        "category_name": "ACTIVE_CAT",
                        "category_slug": "active-cat",
                        "category_status": False,  # Active
                    },
                    {
                        "category_id": "CAT002",
                        "category_name": "INACTIVE_CAT",
                        "category_slug": "inactive-cat",
                        "category_status": True,  # Inactive
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get(
            "/api/v1/categories/list-categories?status_value=true"
        )
        body = res.json()

        assert res.status_code == 200
        assert len(body["data"]) == 1
        assert body["data"][0]["category_status"] is True


class TestCategoryAnalytics:
    """Test cases for category analytics."""

    @pytest.mark.asyncio
    async def test_get_category_analytics(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching category analytics."""
        # Create test data
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "CAT001",
                        "category_name": "ELECTRONICS",
                        "category_slug": "electronics",
                        "category_status": False,  # Active
                        "featured_category": True,
                    },
                    {
                        "category_id": "CAT002",
                        "category_name": "BOOKS",
                        "category_slug": "books",
                        "category_status": True,  # Inactive
                        "featured_category": False,
                    },
                ]
            )
        )

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

        res = await test_client.get("/api/v1/categories/analytics")
        body = res.json()

        assert res.status_code == 200
        assert "data" in body

        # Check the actual structure based on API response
        assert "totals" in body["data"]
        assert "subcategory_stats" in body["data"]

        # Check totals structure
        totals = body["data"]["totals"]
        assert "total_categories" in totals
        assert "active_categories" in totals
        assert "inactive_categories" in totals

    @pytest.mark.asyncio
    async def test_get_total_categories_count(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching total categories count."""
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "CAT001",
                        "category_name": "ELECTRONICS",
                        "category_slug": "electronics",
                        "category_status": False,
                    },
                    {
                        "category_id": "CAT002",
                        "category_name": "BOOKS",
                        "category_slug": "books",
                        "category_status": True,
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/categories/total_categories_count")
        body = res.json()

        assert res.status_code == 200
        assert "data" in body
        assert "totals" in body["data"]
        assert "total_categories" in body["data"]["totals"]
        assert body["data"]["totals"]["total_categories"] == 2


class TestCategoryValidation:
    """Test cases for category validation."""

    @pytest.mark.asyncio
    async def test_create_category_with_file_upload(
        self, test_client: AsyncClient, clean_db
    ):
        """Test creating category with file upload."""
        from io import BytesIO

        # Create a fake image file
        fake_image = BytesIO(b"fake image content")
        fake_image.name = "category_image.jpg"

        data = {"name": "Electronics"}
        files = {"file": ("category_image.jpg", fake_image, "image/jpeg")}

        res = await test_client.post(
            "/api/v1/categories/create", data=data, files=files
        )
        body = res.json()

        assert res.status_code == 201
        assert "category_id" in body["data"]

    @pytest.mark.asyncio
    async def test_create_category_invalid_filename(
        self, test_client: AsyncClient, clean_db
    ):
        """Test creating category with invalid filename fails."""
        from io import BytesIO

        fake_image = BytesIO(b"fake image content")
        fake_image.name = "invalid*name?.jpg"  # Invalid characters

        data = {"name": "Electronics"}
        files = {"file": (fake_image.name, fake_image, "image/jpeg")}

        res = await test_client.post(
            "/api/v1/categories/create", data=data, files=files
        )
        body = res.json()

        assert res.status_code == 400
        # Handle both string and dict detail formats
        if isinstance(body["detail"], str):
            assert "invalid file name" in body["detail"].lower()
        else:
            assert "invalid file name" in body["detail"]["message"].lower()
