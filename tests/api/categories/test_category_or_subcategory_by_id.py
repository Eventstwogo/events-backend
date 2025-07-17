"""
Test cases for categories_or_subcategories_by_id endpoints.
Tests for endpoints that can handle both categories and subcategories by ID:
- GET /details/{item_id} - Get category or subcategory details by ID
- PUT /update/{item_id} - Update category or subcategory by ID
- DELETE /soft-delete/{item_id} - Soft delete category or subcategory by ID
- PUT /restore/{item_id} - Restore category or subcategory by ID
"""

import uuid
from io import BytesIO

import pytest
from httpx import AsyncClient
from sqlalchemy import insert, select

from db.models import Category, SubCategory


def uuid_str():
    """Generate a UUID string for testing."""
    return str(uuid.uuid4())


class TestGetCategoryOrSubcategoryDetails:
    """Test cases for getting category or subcategory details by ID."""

    @pytest.mark.asyncio
    async def test_get_category_details_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully fetching category details by ID."""
        # Create category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT001",
                category_name="ELECTRONICS",
                category_slug="electronics",
                category_description="Electronic devices and gadgets",
                category_meta_title="Electronics Store",
                category_meta_description="Best electronics deals",
                category_status=False,  # Active
                featured_category=True,
                show_in_menu=True,
            )
        )
        await test_db_session.commit()

        res = await test_client.get(
            "/api/v1/categories_or_subcategories_by_id/details/CAT001"
        )
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Category fetched successfully"
        assert body["data"]["type"] == "category"
        assert body["data"]["category_id"] == "CAT001"
        assert body["data"]["category_name"] == "Electronics"  # Title case
        assert body["data"]["category_slug"] == "electronics"
        assert body["data"]["category_status"] is False  # Active
        assert body["data"]["featured_category"] is True
        assert body["data"]["show_in_menu"] is True

    @pytest.mark.asyncio
    async def test_get_subcategory_details_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully fetching subcategory details by ID."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT002",
                category_name="TECHNOLOGY",
                category_slug="technology",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB001",
                subcategory_name="SMARTPHONES",
                subcategory_slug="smartphones",
                subcategory_description="Mobile phones and accessories",
                subcategory_meta_title="Best Smartphones",
                subcategory_meta_description="Top smartphone deals",
                subcategory_status=False,  # Active
                featured_subcategory=True,
                show_in_menu=True,
                category_id="CAT002",
            )
        )
        await test_db_session.commit()

        res = await test_client.get(
            "/api/v1/categories_or_subcategories_by_id/details/SUB001"
        )
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Subcategory fetched successfully"
        assert body["data"]["type"] == "subcategory"
        assert body["data"]["subcategory_id"] == "SUB001"
        assert body["data"]["subcategory_name"] == "Smartphones"  # Title case
        assert body["data"]["subcategory_slug"] == "smartphones"
        assert body["data"]["subcategory_status"] is False  # Active
        assert body["data"]["featured_subcategory"] is True
        assert body["data"]["show_in_menu"] is True
        assert body["data"]["category_id"] == "CAT002"

    @pytest.mark.asyncio
    async def test_get_details_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test fetching non-existent item returns 404."""
        res = await test_client.get(
            "/api/v1/categories_or_subcategories_by_id/details/INVALID_ID"
        )
        body = res.json()

        assert res.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_get_inactive_category_details(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching inactive category details."""
        # Create inactive category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT003",
                category_name="INACTIVE_CATEGORY",
                category_slug="inactive-category",
                category_status=True,  # Inactive
                featured_category=False,
                show_in_menu=False,
            )
        )
        await test_db_session.commit()

        res = await test_client.get(
            "/api/v1/categories_or_subcategories_by_id/details/CAT003"
        )
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["type"] == "category"
        assert body["data"]["category_status"] is True  # Inactive
        assert body["data"]["featured_category"] is False
        assert body["data"]["show_in_menu"] is False

    @pytest.mark.asyncio
    async def test_get_inactive_subcategory_details(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching inactive subcategory details."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT004",
                category_name="BOOKS",
                category_slug="books",
                category_status=False,
            )
        )

        # Create inactive subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB002",
                subcategory_name="INACTIVE_SUB",
                subcategory_slug="inactive-sub",
                subcategory_status=True,  # Inactive
                featured_subcategory=False,
                show_in_menu=False,
                category_id="CAT004",
            )
        )
        await test_db_session.commit()

        res = await test_client.get(
            "/api/v1/categories_or_subcategories_by_id/details/SUB002"
        )
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["type"] == "subcategory"
        assert body["data"]["subcategory_status"] is True  # Inactive
        assert body["data"]["featured_subcategory"] is False
        assert body["data"]["show_in_menu"] is False


class TestUpdateCategoryOrSubcategory:
    """Test cases for updating category or subcategory by ID."""

    @pytest.mark.asyncio
    async def test_update_category_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully updating a category."""
        # Create category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT100",
                category_name="OLD_NAME",
                category_slug="old-name",
                category_description="Old description",
                category_status=False,
                featured_category=False,
                show_in_menu=False,
            )
        )
        await test_db_session.commit()

        data = {
            "name": "New Category Name",
            "description": "Updated description for category",
            "featured": True,
            "show_in_menu": True,
        }

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/update/CAT100", data=data
        )
        body = res.json()

        assert res.status_code == 200
        assert "updated successfully" in body["message"].lower()

        # Verify in database
        stmt = select(Category).where(Category.category_id == "CAT100")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category.category_name == "NEW CATEGORY NAME"  # Uppercase
        assert (
            category.category_description == "Updated description for category"
        )
        assert category.featured_category is True
        assert category.show_in_menu is True

    @pytest.mark.asyncio
    async def test_update_subcategory_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully updating a subcategory."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT101",
                category_name="GAMING",
                category_slug="gaming",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB100",
                subcategory_name="OLD_SUB_NAME",
                subcategory_slug="old-sub-name",
                subcategory_description="Old subcategory description",
                subcategory_status=False,
                featured_subcategory=False,
                show_in_menu=False,
                category_id="CAT101",
            )
        )
        await test_db_session.commit()

        data = {
            "name": "New Subcategory Name",
            "description": "Updated subcategory description",
            "featured": True,
            "show_in_menu": True,
        }

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/update/SUB100", data=data
        )
        body = res.json()

        assert res.status_code == 200
        assert "updated successfully" in body["message"].lower()

        # Verify in database
        stmt = select(SubCategory).where(SubCategory.subcategory_id == "SUB100")
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert (
            subcategory.subcategory_name == "NEW SUBCATEGORY NAME"
        )  # Uppercase
        assert (
            subcategory.subcategory_description
            == "Updated subcategory description"
        )
        assert subcategory.featured_subcategory is True
        assert subcategory.show_in_menu is True

    @pytest.mark.asyncio
    async def test_update_item_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test updating non-existent item returns 404."""
        data = {"name": "New Name"}

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/update/INVALID_ID",
            data=data,
        )
        body = res.json()

        assert res.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_update_category_with_file(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating category with file upload."""
        # Create category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT102",
                category_name="FASHION",
                category_slug="fashion",
                category_status=False,
            )
        )
        await test_db_session.commit()

        fake_image = BytesIO(b"fake image content")
        fake_image.name = "fashion_image.jpg"

        data = {"name": "Updated Fashion"}
        files = {"file": ("fashion_image.jpg", fake_image, "image/jpeg")}

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/update/CAT102",
            data=data,
            files=files,
        )
        body = res.json()

        assert res.status_code == 200
        assert "updated successfully" in body["message"].lower()

    @pytest.mark.asyncio
    async def test_update_subcategory_with_file(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating subcategory with file upload."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT103",
                category_name="SPORTS",
                category_slug="sports",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB101",
                subcategory_name="FOOTBALL",
                subcategory_slug="football",
                subcategory_status=False,
                category_id="CAT103",
            )
        )
        await test_db_session.commit()

        fake_image = BytesIO(b"fake image content")
        fake_image.name = "football_image.jpg"

        data = {"name": "Updated Football"}
        files = {"file": ("football_image.jpg", fake_image, "image/jpeg")}

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/update/SUB101",
            data=data,
            files=files,
        )
        body = res.json()

        assert res.status_code == 200
        assert "updated successfully" in body["message"].lower()

    @pytest.mark.asyncio
    async def test_update_with_invalid_filename(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating with invalid filename fails."""
        # Create category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT104",
                category_name="TRAVEL",
                category_slug="travel",
                category_status=False,
            )
        )
        await test_db_session.commit()

        fake_image = BytesIO(b"fake image content")
        fake_image.name = "invalid*filename?.jpg"

        data = {"name": "Updated Travel"}
        files = {"file": (fake_image.name, fake_image, "image/jpeg")}

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/update/CAT104",
            data=data,
            files=files,
        )
        body = res.json()

        assert res.status_code == 400
        assert "invalid file name" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_update_no_changes(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating with no changes returns error."""
        # Create category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT105",
                category_name="MUSIC",
                category_slug="music",
                category_status=False,
            )
        )
        await test_db_session.commit()

        data = {}  # No changes

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/update/CAT105", data=data
        )
        body = res.json()

        assert res.status_code == 400
        assert "no changes" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_update_duplicate_name(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating with duplicate name fails."""
        # Create categories
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "CAT106",
                        "category_name": "EXISTING_NAME",
                        "category_slug": "existing-name",
                        "category_status": False,
                    },
                    {
                        "category_id": "CAT107",
                        "category_name": "TO_UPDATE",
                        "category_slug": "to-update",
                        "category_status": False,
                    },
                ]
            )
        )
        await test_db_session.commit()

        data = {"name": "Existing Name"}  # Duplicate name

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/update/CAT107", data=data
        )
        body = res.json()

        assert res.status_code == 400
        assert "already exists" in body["detail"]["message"].lower()


class TestSoftDeleteCategoryOrSubcategory:
    """Test cases for soft deleting category or subcategory by ID."""

    @pytest.mark.asyncio
    async def test_soft_delete_category_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully soft deleting a category."""
        # Create category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT200",
                category_name="TO_DELETE",
                category_slug="to-delete",
                category_status=False,  # Active
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/categories_or_subcategories_by_id/soft-delete/CAT200"
        )
        body = res.json()

        assert res.status_code == 200
        assert "soft deleted successfully" in body["message"].lower()

        # Verify category is now inactive
        stmt = select(Category).where(Category.category_id == "CAT200")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category.category_status is True  # Inactive

    @pytest.mark.asyncio
    async def test_soft_delete_subcategory_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully soft deleting a subcategory."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT201",
                category_name="PARENT",
                category_slug="parent",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB200",
                subcategory_name="TO_DELETE_SUB",
                subcategory_slug="to-delete-sub",
                subcategory_status=False,  # Active
                category_id="CAT201",
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/categories_or_subcategories_by_id/soft-delete/SUB200"
        )
        body = res.json()

        assert res.status_code == 200
        assert "soft deleted successfully" in body["message"].lower()

        # Verify subcategory is now inactive
        stmt = select(SubCategory).where(SubCategory.subcategory_id == "SUB200")
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.subcategory_status is True  # Inactive

    @pytest.mark.asyncio
    async def test_soft_delete_item_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test soft deleting non-existent item returns 404."""
        res = await test_client.delete(
            "/api/v1/categories_or_subcategories_by_id/soft-delete/INVALID_ID"
        )
        body = res.json()

        assert res.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_soft_delete_already_inactive_category(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test soft deleting already inactive category returns error."""
        # Create inactive category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT202",
                category_name="ALREADY_INACTIVE",
                category_slug="already-inactive",
                category_status=True,  # Already inactive
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/categories_or_subcategories_by_id/soft-delete/CAT202"
        )
        body = res.json()

        assert res.status_code == 400
        assert "already inactive" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_soft_delete_already_inactive_subcategory(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test soft deleting already inactive subcategory returns error."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT203",
                category_name="PARENT2",
                category_slug="parent2",
                category_status=False,
            )
        )

        # Create inactive subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB201",
                subcategory_name="ALREADY_INACTIVE_SUB",
                subcategory_slug="already-inactive-sub",
                subcategory_status=True,  # Already inactive
                category_id="CAT203",
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/categories_or_subcategories_by_id/soft-delete/SUB201"
        )
        body = res.json()

        assert res.status_code == 400
        assert "already inactive" in body["detail"]["message"].lower()


class TestRestoreCategoryOrSubcategory:
    """Test cases for restoring category or subcategory by ID."""

    @pytest.mark.asyncio
    async def test_restore_category_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully restoring a category."""
        # Create inactive category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT300",
                category_name="TO_RESTORE",
                category_slug="to-restore",
                category_status=True,  # Inactive
            )
        )
        await test_db_session.commit()

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/restore/CAT300"
        )
        body = res.json()

        assert res.status_code == 200
        assert "restored successfully" in body["message"].lower()

        # Verify category is now active
        stmt = select(Category).where(Category.category_id == "CAT300")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category.category_status is False  # Active

    @pytest.mark.asyncio
    async def test_restore_subcategory_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully restoring a subcategory."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT301",
                category_name="PARENT3",
                category_slug="parent3",
                category_status=False,
            )
        )

        # Create inactive subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB300",
                subcategory_name="TO_RESTORE_SUB",
                subcategory_slug="to-restore-sub",
                subcategory_status=True,  # Inactive
                category_id="CAT301",
            )
        )
        await test_db_session.commit()

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/restore/SUB300"
        )
        body = res.json()

        assert res.status_code == 200
        assert "restored successfully" in body["message"].lower()

        # Verify subcategory is now active
        stmt = select(SubCategory).where(SubCategory.subcategory_id == "SUB300")
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.subcategory_status is False  # Active

    @pytest.mark.asyncio
    async def test_restore_item_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test restoring non-existent item returns 404."""
        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/restore/INVALID_ID"
        )
        body = res.json()

        assert res.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_restore_already_active_category(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test restoring already active category returns error."""
        # Create active category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT302",
                category_name="ALREADY_ACTIVE",
                category_slug="already-active",
                category_status=False,  # Already active
            )
        )
        await test_db_session.commit()

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/restore/CAT302"
        )
        body = res.json()

        assert res.status_code == 400
        assert "already active" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_restore_already_active_subcategory(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test restoring already active subcategory returns error."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT303",
                category_name="PARENT4",
                category_slug="parent4",
                category_status=False,
            )
        )

        # Create active subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB301",
                subcategory_name="ALREADY_ACTIVE_SUB",
                subcategory_slug="already-active-sub",
                subcategory_status=False,  # Already active
                category_id="CAT303",
            )
        )
        await test_db_session.commit()

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/restore/SUB301"
        )
        body = res.json()

        assert res.status_code == 400
        assert "already active" in body["detail"]["message"].lower()


class TestCategoryOrSubcategoryEdgeCases:
    """Test cases for edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_category_priority_over_subcategory(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test that category is returned when both category and subcategory have same ID."""
        # This is an edge case that shouldn't happen in real scenarios
        # but tests the priority logic in the endpoint

        # Create category with specific ID
        await test_db_session.execute(
            insert(Category).values(
                category_id="SAME_ID",
                category_name="CATEGORY_WITH_SAME_ID",
                category_slug="category-same-id",
                category_status=False,
            )
        )

        # Create parent category for subcategory
        await test_db_session.execute(
            insert(Category).values(
                category_id="PARENT_CAT",
                category_name="PARENT_CATEGORY",
                category_slug="parent-category",
                category_status=False,
            )
        )

        # Create subcategory with same ID (this shouldn't happen in real scenarios)
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SAME_ID",
                subcategory_name="SUBCATEGORY_WITH_SAME_ID",
                subcategory_slug="subcategory-same-id",
                subcategory_status=False,
                category_id="PARENT_CAT",
            )
        )
        await test_db_session.commit()

        res = await test_client.get(
            "/api/v1/categories_or_subcategories_by_id/details/SAME_ID"
        )
        body = res.json()

        assert res.status_code == 200
        # Should return category (priority over subcategory)
        assert body["data"]["type"] == "category"
        assert body["message"] == "Category fetched successfully"

    @pytest.mark.asyncio
    async def test_update_slug_change(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating item with slug change."""
        # Create category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT400",
                category_name="OLD_SLUG_NAME",
                category_slug="old-slug",
                category_status=False,
            )
        )
        await test_db_session.commit()

        data = {
            "name": "New Slug Name",
            "slug": "new-slug",
        }

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/update/CAT400", data=data
        )
        body = res.json()

        assert res.status_code == 200

        # Verify slug was updated
        stmt = select(Category).where(Category.category_id == "CAT400")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category.category_slug == "new-slug"
        assert category.category_name == "NEW SLUG NAME"

    @pytest.mark.asyncio
    async def test_partial_update_fields(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test partial update of specific fields only."""
        # Create subcategory
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT401",
                category_name="PARENT_FOR_PARTIAL",
                category_slug="parent-partial",
                category_status=False,
            )
        )

        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB400",
                subcategory_name="PARTIAL_UPDATE",
                subcategory_slug="partial-update",
                subcategory_description="Original description",
                subcategory_status=False,
                featured_subcategory=False,
                show_in_menu=False,
                category_id="CAT401",
            )
        )
        await test_db_session.commit()

        # Update only featured and show_in_menu flags
        data = {
            "featured": True,
            "show_in_menu": True,
        }

        res = await test_client.put(
            "/api/v1/categories_or_subcategories_by_id/update/SUB400", data=data
        )
        body = res.json()

        assert res.status_code == 200

        # Verify only specified fields were updated
        stmt = select(SubCategory).where(SubCategory.subcategory_id == "SUB400")
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.subcategory_name == "PARTIAL_UPDATE"  # Unchanged
        assert (
            subcategory.subcategory_description == "Original description"
        )  # Unchanged
        assert subcategory.featured_subcategory is True  # Updated
        assert subcategory.show_in_menu is True  # Updated
