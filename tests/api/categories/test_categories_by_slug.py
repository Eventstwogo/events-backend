"""
Test cases for category by slug endpoints (/api/v1/categories/)
Tests for categories_by_slug.py endpoints:
- GET /slug/{slug} - Get category by slug
- PUT /slug/{category_slug} - Update category by slug
- DELETE /slug/{category_slug}/soft - Soft delete by slug
- PUT /slug/{category_slug}/restore - Restore by slug
- DELETE /slug/{category_slug}/hard - Hard delete by slug
"""

import uuid
from io import BytesIO

import pytest
from httpx import AsyncClient
from sqlalchemy import insert, select

from shared.db.models import Category, SubCategory


def uuid_str():
    """Generate a UUID string for testing."""
    return str(uuid.uuid4())


class TestGetCategoryBySlug:
    """Test cases for getting category by slug."""

    @pytest.mark.asyncio
    async def test_get_category_by_slug_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully fetching a category by slug."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT001",
                category_name="ELECTRONICS",
                category_slug="electronics",
                category_description="Electronic items and devices",
                category_meta_title="Electronics Store",
                category_meta_description="Top tech and electronics",
                category_status=False,
                featured_category=True,
                show_in_menu=True,
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/categories/slug/electronics")
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Category fetched successfully"
        assert body["data"]["category_id"] == "CAT001"
        assert (
            body["data"]["category_name"] == "Electronics"
        )  # Title case in response
        assert body["data"]["category_slug"] == "electronics"
        assert body["data"]["category_status"] is False
        assert body["data"]["featured_category"] is True

    @pytest.mark.asyncio
    async def test_get_category_by_slug_with_subcategories(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching category by slug that has subcategories."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT002",
                category_name="BOOKS",
                category_slug="books",
                category_status=False,
            )
        )

        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB001",
                        "subcategory_name": "FICTION",
                        "subcategory_slug": "fiction",
                        "subcategory_status": False,
                        "category_id": "CAT002",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB002",
                        "subcategory_name": "NON_FICTION",
                        "subcategory_slug": "non-fiction",
                        "subcategory_status": False,
                        "category_id": "CAT002",
                    },
                ]
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/categories/slug/books")
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["category_id"] == "CAT002"
        assert body["data"]["category_name"] == "Books"
        assert body["data"]["category_slug"] == "books"

    @pytest.mark.asyncio
    async def test_get_category_by_slug_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test fetching non-existent category by slug returns 404."""
        res = await test_client.get("/api/v1/categories/slug/nonexistent")
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_get_inactive_category_by_slug(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching inactive category by slug."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT003",
                category_name="INACTIVE_CAT",
                category_slug="inactive-cat",
                category_status=True,
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/categories/slug/inactive-cat")
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["category_status"] is True

    @pytest.mark.asyncio
    async def test_get_category_by_slug_special_characters(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching category with special characters in slug."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT004",
                category_name="ARTS_AND_CRAFTS",
                category_slug="arts-and-crafts",
                category_status=False,
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/categories/slug/arts-and-crafts")
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["category_slug"] == "arts-and-crafts"


class TestUpdateCategoryBySlug:
    """Test cases for updating category by slug."""

    @pytest.mark.asyncio
    async def test_update_category_by_slug_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully updating a category by slug."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT100",
                category_name="OLD_NAME",
                category_slug="old-name",
                category_status=False,
            )
        )
        await test_db_session.commit()

        data = {
            "name": "New Electronics",
            "description": "Updated description",
            "featured": "true",
        }

        res = await test_client.put(
            "/api/v1/categories/slug/old-name", data=data
        )
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Category updated successfully"
        assert "category_id" in body["data"]
        assert "category_slug" in body["data"]

        # Verify in database
        stmt = select(Category).where(Category.category_id == "CAT100")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category.category_name == "NEW ELECTRONICS"  # Uppercase
        assert category.featured_category is True

    @pytest.mark.asyncio
    async def test_update_category_by_slug_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test updating non-existent category by slug returns 404."""
        data = {"name": "New Name"}

        res = await test_client.put(
            "/api/v1/categories/slug/nonexistent", data=data
        )
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_update_category_by_slug_no_changes(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating category by slug with no changes returns error."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT101",
                category_name="ELECTRONICS",
                category_slug="electronics",
                category_status=False,
            )
        )
        await test_db_session.commit()

        data = {}  # No changes

        res = await test_client.put(
            "/api/v1/categories/slug/electronics", data=data
        )
        body = res.json()

        assert res.status_code == 400
        assert "no changes" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_update_category_by_slug_duplicate_name(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating category by slug with duplicate name fails."""
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "CAT102",
                        "category_name": "ELECTRONICS",
                        "category_slug": "electronics",
                        "category_status": False,
                    },
                    {
                        "category_id": "CAT103",
                        "category_name": "BOOKS",
                        "category_slug": "books",
                        "category_status": False,
                    },
                ]
            )
        )
        await test_db_session.commit()

        data = {"name": "Electronics"}  # Duplicate name

        res = await test_client.put(
            "/api/v1/categories/slug/books", data=data
        )
        body = res.json()

        assert res.status_code == 400
        assert "already exists" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_update_category_by_slug_with_file(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating category by slug with file upload."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT104",
                category_name="ELECTRONICS",
                category_slug="electronics",
                category_status=False,
            )
        )
        await test_db_session.commit()

        fake_image = BytesIO(b"fake image content")
        fake_image.name = "new_image.jpg"

        data = {"name": "Updated Electronics"}
        files = {"file": ("new_image.jpg", fake_image, "image/jpeg")}

        res = await test_client.put(
            "/api/v1/categories/slug/electronics",
            data=data,
            files=files,
        )
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Category updated successfully"

    @pytest.mark.asyncio
    async def test_update_category_by_slug_change_slug(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating category slug changes the slug."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT105",
                category_name="ELECTRONICS",
                category_slug="old-electronics",
                category_status=False,
            )
        )
        await test_db_session.commit()

        data = {"slug": "new-electronics"}

        res = await test_client.put(
            "/api/v1/categories/slug/old-electronics", data=data
        )
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["category_slug"] == "new-electronics"

        # Verify in database
        stmt = select(Category).where(Category.category_id == "CAT105")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category.category_slug == "new-electronics"


class TestSoftDeleteCategoryBySlug:
    """Test cases for soft deleting category by slug."""

    @pytest.mark.asyncio
    async def test_soft_delete_category_by_slug_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully soft deleting a category by slug."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT200",
                category_name="TO_DELETE",
                category_slug="to-delete",
                category_status=False,
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/categories/slug/to-delete/soft"
        )
        body = res.json()

        assert res.status_code == 200
        assert "soft deleted successfully" in body["message"].lower()

        # Verify category is now inactive
        stmt = select(Category).where(Category.category_slug == "to-delete")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category.category_status is True

    @pytest.mark.asyncio
    async def test_soft_delete_category_by_slug_with_subcategories(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test soft deleting category by slug also soft deletes its subcategories."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT201",
                category_name="PARENT",
                category_slug="parent",
                category_status=False,
            )
        )

        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB201",
                subcategory_name="CHILD",
                subcategory_slug="child",
                subcategory_status=False,
                category_id="CAT201",
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/categories/slug/parent/soft"
        )
        body = res.json()

        assert res.status_code == 200
        assert "soft deleted successfully" in body["message"].lower()

        # Verify both category and subcategory are
        stmt = select(Category).where(Category.category_slug == "parent")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()
        assert category.category_status is True

        stmt = select(SubCategory).where(SubCategory.subcategory_id == "SUB201")
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()
        assert subcategory.subcategory_status is True

    @pytest.mark.asyncio
    async def test_soft_delete_category_by_slug_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test soft deleting non-existent category by slug returns 404."""
        res = await test_client.delete(
            "/api/v1/categories/slug/nonexistent/soft"
        )
        body = res.json()

        assert res.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_soft_delete_already_inactive_category_by_slug(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test soft deleting already inactive category by slug succeeds."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT202",
                category_name="INACTIVE",
                category_slug="inactive",
                category_status=True,  # Already inactive
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/categories/slug/inactive/soft"
        )
        body = res.json()

        assert res.status_code == 200
        assert "soft deleted successfully" in body["message"].lower()


class TestRestoreCategoryBySlug:
    """Test cases for restoring category by slug."""

    @pytest.mark.asyncio
    async def test_restore_category_by_slug_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully restoring a soft-deleted category by slug."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT300",
                category_name="TO_RESTORE",
                category_slug="to-restore",
                category_status=True,
            )
        )
        await test_db_session.commit()

        res = await test_client.put(
            "/api/v1/categories/slug/to-restore/restore"
        )
        body = res.json()

        assert res.status_code == 200
        assert "restored successfully" in body["message"].lower()

        # Verify category is now active
        stmt = select(Category).where(Category.category_slug == "to-restore")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category.category_status is False

    @pytest.mark.asyncio
    async def test_restore_category_by_slug_with_subcategories(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test restoring category by slug also restores its subcategories."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT301",
                category_name="PARENT",
                category_slug="parent",
                category_status=True,
            )
        )

        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB301",
                subcategory_name="CHILD",
                subcategory_slug="child",
                subcategory_status=True,
                category_id="CAT301",
            )
        )
        await test_db_session.commit()

        res = await test_client.put("/api/v1/categories/slug/parent/restore")
        body = res.json()

        assert res.status_code == 200
        assert "restored successfully" in body["message"].lower()

        # Verify both category and subcategory are active
        stmt = select(Category).where(Category.category_slug == "parent")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()
        assert category.category_status is False

        stmt = select(SubCategory).where(SubCategory.subcategory_id == "SUB301")
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()
        assert subcategory.subcategory_status is False

    @pytest.mark.asyncio
    async def test_restore_category_by_slug_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test restoring non-existent category by slug returns 404."""
        res = await test_client.put(
            "/api/v1/categories/slug/nonexistent/restore"
        )
        body = res.json()

        assert res.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_restore_already_active_category_by_slug(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test restoring already active category by slug succeeds."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT302",
                category_name="ACTIVE",
                category_slug="active",
                category_status=False,  # Already active
            )
        )
        await test_db_session.commit()

        res = await test_client.put("/api/v1/categories/slug/active/restore")
        body = res.json()

        assert res.status_code == 200
        assert "restored successfully" in body["message"].lower()


class TestHardDeleteCategoryBySlug:
    """Test cases for hard deleting category by slug."""

    @pytest.mark.asyncio
    async def test_hard_delete_category_by_slug_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully hard deleting a category by slug."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT400",
                category_name="TO_DELETE",
                category_slug="to-delete",
                category_status=True,
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/categories/slug/to-delete/hard"
        )
        body = res.json()

        assert res.status_code == 200
        assert "permanently deleted" in body["message"].lower()

        # Verify category is completely removed
        stmt = select(Category).where(Category.category_slug == "to-delete")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category is None

    @pytest.mark.asyncio
    async def test_hard_delete_category_by_slug_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test hard deleting non-existent category by slug returns 404."""
        res = await test_client.delete(
            "/api/v1/categories/slug/nonexistent/hard"
        )
        body = res.json()

        assert res.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_hard_delete_active_category_by_slug(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test hard deleting active category by slug (should still work)."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT401",
                category_name="ACTIVE",
                category_slug="active",
                category_status=False,
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/categories/slug/active/hard"
        )
        body = res.json()

        assert res.status_code == 200
        assert "permanently deleted" in body["message"].lower()

        # Verify category is completely removed
        stmt = select(Category).where(Category.category_slug == "active")
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category is None

    @pytest.mark.asyncio
    async def test_hard_delete_category_by_slug_with_subcategories(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test hard deleting category by slug with subcategories."""
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT402",
                category_name="PARENT",
                category_slug="parent-to-delete",
                category_status=True,
            )
        )

        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB402",
                subcategory_name="CHILD",
                subcategory_slug="child",
                subcategory_status=True,
                category_id="CAT402",
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/categories/slug/parent-to-delete/hard"
        )
        body = res.json()

        assert res.status_code == 200
        assert "permanently deleted" in body["message"].lower()

        # Verify category is completely removed
        stmt = select(Category).where(
            Category.category_slug == "parent-to-delete"
        )
        result = await test_db_session.execute(stmt)
        category = result.scalar_one_or_none()

        assert category is None

        # Note: Subcategories might be cascade deleted or orphaned depending on DB constraints
