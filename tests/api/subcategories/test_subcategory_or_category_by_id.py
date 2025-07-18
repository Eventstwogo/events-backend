"""
Test cases for category-items endpoints (Subcategory perspective).
Tests for endpoints that can handle both categories and subcategories by ID:
- GET /{item_id} - Get category or subcategory details by ID
- PUT /{item_id} - Update category or subcategory by ID
- DELETE /{item_id}/soft - Soft delete category or subcategory by ID
- PUT /{item_id}/restore - Restore category or subcategory by ID

This file focuses on subcategory-specific test scenarios.
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


class TestSubcategoryFocusedScenarios:
    """Test cases focusing on subcategory-specific scenarios."""

    @pytest.mark.asyncio
    async def test_get_subcategory_with_parent_info(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching subcategory includes parent category information."""
        # Create parent category with detailed info
        await test_db_session.execute(
            insert(Category).values(
                category_id="PARENT_001",
                category_name="DETAILED_PARENT",
                category_slug="detailed-parent",
                category_description="Detailed parent category",
                category_status=False,
                featured_category=True,
                show_in_menu=True,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB_DETAILED",
                subcategory_name="DETAILED_SUBCATEGORY",
                subcategory_slug="detailed-subcategory",
                subcategory_description="Detailed subcategory",
                subcategory_status=False,
                featured_subcategory=True,
                show_in_menu=True,
                category_id="PARENT_001",
            )
        )
        await test_db_session.commit()

        res = await test_client.get(
            "/api/v1/category-items/SUB_DETAILED"
        )
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["type"] == "subcategory"
        assert body["data"]["category_id"] == "PARENT_001"
        # The endpoint should include parent category relationship

    @pytest.mark.asyncio
    async def test_update_subcategory_maintains_parent_relationship(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating subcategory maintains parent category relationship."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="PARENT_002",
                category_name="STABLE_PARENT",
                category_slug="stable-parent",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB_UPDATE",
                subcategory_name="SUBCATEGORY_TO_UPDATE",
                subcategory_slug="subcategory-to-update",
                subcategory_status=False,
                category_id="PARENT_002",
            )
        )
        await test_db_session.commit()

        data = {
            "name": "Updated Subcategory Name",
            "description": "Updated description",
        }

        res = await test_client.put(
            "/api/v1/category-items/SUB_UPDATE",
            data=data,
        )
        body = res.json()

        assert res.status_code == 200

        # Verify parent relationship is maintained
        stmt = select(SubCategory).where(
            SubCategory.subcategory_id == "SUB_UPDATE"
        )
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert (
            subcategory.category_id == "PARENT_002"
        )  # Parent relationship maintained
        assert subcategory.subcategory_name == "UPDATED SUBCATEGORY NAME"

    @pytest.mark.asyncio
    async def test_subcategory_operations_with_inactive_parent(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test subcategory operations when parent category is inactive."""
        # Create inactive parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="INACTIVE_PARENT",
                category_name="INACTIVE_PARENT_CAT",
                category_slug="inactive-parent",
                category_status=True,  # Inactive
            )
        )

        # Create subcategory under inactive parent
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB_INACTIVE_PARENT",
                subcategory_name="SUB_WITH_INACTIVE_PARENT",
                subcategory_slug="sub-inactive-parent",
                subcategory_status=False,  # Active subcategory
                category_id="INACTIVE_PARENT",
            )
        )
        await test_db_session.commit()

        # Test getting subcategory details (should work)
        res = await test_client.get(
            "/api/v1/category-items/SUB_INACTIVE_PARENT"
        )
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["type"] == "subcategory"
        assert body["data"]["category_id"] == "INACTIVE_PARENT"

        # Test updating subcategory (should work)
        data = {"name": "Updated Sub Name"}
        res = await test_client.put(
            "/api/v1/category-items/SUB_INACTIVE_PARENT",
            data=data,
        )
        assert res.status_code == 200

        # Test soft deleting subcategory (should work)
        res = await test_client.delete(
            "/api/v1/category-items/SUB_INACTIVE_PARENT/soft"
        )
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_subcategory_name_conflict_validation(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test subcategory name conflict validation during updates."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CONFLICT_PARENT",
                category_name="CONFLICT_PARENT_CAT",
                category_slug="conflict-parent",
                category_status=False,
            )
        )

        # Create two subcategories
        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB_CONFLICT_1",
                        "subcategory_name": "EXISTING_NAME",
                        "subcategory_slug": "existing-name",
                        "subcategory_status": False,
                        "category_id": "CONFLICT_PARENT",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB_CONFLICT_2",
                        "subcategory_name": "TO_BE_UPDATED",
                        "subcategory_slug": "to-be-updated",
                        "subcategory_status": False,
                        "category_id": "CONFLICT_PARENT",
                    },
                ]
            )
        )
        await test_db_session.commit()

        # Try to update second subcategory with existing name
        data = {"name": "Existing Name"}  # Conflicts with SUB_CONFLICT_1

        res = await test_client.put(
            "/api/v1/category-items/SUB_CONFLICT_2",
            data=data,
        )
        body = res.json()

        assert res.status_code == 400
        assert "already exists" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_subcategory_slug_conflict_validation(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test subcategory slug conflict validation during updates."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="SLUG_PARENT",
                category_name="SLUG_PARENT_CAT",
                category_slug="slug-parent",
                category_status=False,
            )
        )

        # Create two subcategories
        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB_SLUG_1",
                        "subcategory_name": "FIRST_SUB",
                        "subcategory_slug": "existing-slug",
                        "subcategory_status": False,
                        "category_id": "SLUG_PARENT",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB_SLUG_2",
                        "subcategory_name": "SECOND_SUB",
                        "subcategory_slug": "second-slug",
                        "subcategory_status": False,
                        "category_id": "SLUG_PARENT",
                    },
                ]
            )
        )
        await test_db_session.commit()

        # Try to update second subcategory with existing slug
        data = {"slug": "existing-slug"}  # Conflicts with SUB_SLUG_1

        res = await test_client.put(
            "/api/v1/category-items/SUB_SLUG_2",
            data=data,
        )
        body = res.json()

        assert res.status_code == 400
        assert "already exists" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_subcategory_vs_category_name_conflict(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test subcategory name cannot conflict with existing category names."""
        # Create categories
        await test_db_session.execute(
            insert(Category).values(
                [
                    {
                        "category_id": "EXISTING_CAT",
                        "category_name": "EXISTING_CATEGORY_NAME",
                        "category_slug": "existing-category",
                        "category_status": False,
                    },
                    {
                        "category_id": "PARENT_FOR_SUB",
                        "category_name": "PARENT_CATEGORY",
                        "category_slug": "parent-category",
                        "category_status": False,
                    },
                ]
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB_NAME_CONFLICT",
                subcategory_name="SUBCATEGORY_TO_UPDATE",
                subcategory_slug="subcategory-to-update",
                subcategory_status=False,
                category_id="PARENT_FOR_SUB",
            )
        )
        await test_db_session.commit()

        # Try to update subcategory with existing category name
        data = {"name": "Existing Category Name"}

        res = await test_client.put(
            "/api/v1/category-items/SUB_NAME_CONFLICT",
            data=data,
        )
        body = res.json()

        assert res.status_code == 400
        assert "cannot be same" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_subcategory_file_upload_path_structure(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test subcategory file uploads follow correct path structure."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="FILE_PARENT",
                category_name="FILE_PARENT_CAT",
                category_slug="file-parent",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB_FILE_TEST",
                subcategory_name="SUBCATEGORY_FILE_TEST",
                subcategory_slug="subcategory-file-test",
                subcategory_status=False,
                category_id="FILE_PARENT",
            )
        )
        await test_db_session.commit()

        fake_image = BytesIO(b"fake image content")
        fake_image.name = "subcategory_image.jpg"

        data = {"name": "Updated with File"}
        files = {"file": ("subcategory_image.jpg", fake_image, "image/jpeg")}

        res = await test_client.put(
            "/api/v1/category-items/SUB_FILE_TEST",
            data=data,
            files=files,
        )
        body = res.json()

        assert res.status_code == 200

        # Verify file was uploaded and path structure is correct
        stmt = select(SubCategory).where(
            SubCategory.subcategory_id == "SUB_FILE_TEST"
        )
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        # File should be uploaded to subcategories/{parent_id}/{slug}/ path
        if subcategory.subcategory_img_thumbnail:
            assert "subcategories" in subcategory.subcategory_img_thumbnail
            assert "FILE_PARENT" in subcategory.subcategory_img_thumbnail

    @pytest.mark.asyncio
    async def test_subcategory_metadata_fields_update(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating subcategory metadata fields (meta_title, meta_description)."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="META_PARENT",
                category_name="META_PARENT_CAT",
                category_slug="meta-parent",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB_META_TEST",
                subcategory_name="SUBCATEGORY_META_TEST",
                subcategory_slug="subcategory-meta-test",
                subcategory_meta_title="Original Meta Title",
                subcategory_meta_description="Original meta description",
                subcategory_status=False,
                category_id="META_PARENT",
            )
        )
        await test_db_session.commit()

        data = {
            "meta_title": "Updated Meta Title",
            "meta_description": "Updated meta description for SEO",
        }

        res = await test_client.put(
            "/api/v1/category-items/SUB_META_TEST",
            data=data,
        )
        body = res.json()

        assert res.status_code == 200

        # Verify metadata fields were updated
        stmt = select(SubCategory).where(
            SubCategory.subcategory_id == "SUB_META_TEST"
        )
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.subcategory_meta_title == "Updated Meta Title"
        assert (
            subcategory.subcategory_meta_description
            == "Updated meta description for SEO"
        )

    @pytest.mark.asyncio
    async def test_subcategory_status_transitions(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test subcategory status transitions (active -> inactive -> active)."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="STATUS_PARENT",
                category_name="STATUS_PARENT_CAT",
                category_slug="status-parent",
                category_status=False,
            )
        )

        # Create active subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB_STATUS_TEST",
                subcategory_name="SUBCATEGORY_STATUS_TEST",
                subcategory_slug="subcategory-status-test",
                subcategory_status=False,  # Active
                category_id="STATUS_PARENT",
            )
        )
        await test_db_session.commit()

        # Test 1: Soft delete (active -> inactive)
        res = await test_client.delete(
            "/api/v1/category-items/SUB_STATUS_TEST/soft"
        )
        assert res.status_code == 200

        # Verify status changed to inactive
        stmt = select(SubCategory).where(
            SubCategory.subcategory_id == "SUB_STATUS_TEST"
        )
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()
        assert subcategory.subcategory_status is True  # Inactive

        # Test 2: Restore (inactive -> active)
        res = await test_client.put(
            "/api/v1/category-items/SUB_STATUS_TEST/restore"
        )
        assert res.status_code == 200

        # Verify status changed back to active
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()
        assert subcategory.subcategory_status is False  # Active

    @pytest.mark.asyncio
    async def test_subcategory_featured_and_menu_flags(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating subcategory featured and menu visibility flags."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="FLAGS_PARENT",
                category_name="FLAGS_PARENT_CAT",
                category_slug="flags-parent",
                category_status=False,
            )
        )

        # Create subcategory with default flags
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB_FLAGS_TEST",
                subcategory_name="SUBCATEGORY_FLAGS_TEST",
                subcategory_slug="subcategory-flags-test",
                subcategory_status=False,
                featured_subcategory=False,
                show_in_menu=False,
                category_id="FLAGS_PARENT",
            )
        )
        await test_db_session.commit()

        # Test updating flags
        data = {
            "featured": True,
            "show_in_menu": True,
        }

        res = await test_client.put(
            "/api/v1/category-items/SUB_FLAGS_TEST",
            data=data,
        )
        body = res.json()

        assert res.status_code == 200

        # Verify flags were updated
        stmt = select(SubCategory).where(
            SubCategory.subcategory_id == "SUB_FLAGS_TEST"
        )
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.featured_subcategory is True
        assert subcategory.show_in_menu is True

        # Test updating flags back to False
        data = {
            "featured": False,
            "show_in_menu": False,
        }

        res = await test_client.put(
            "/api/v1/category-items/SUB_FLAGS_TEST",
            data=data,
        )
        assert res.status_code == 200

        # Verify flags were updated back
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.featured_subcategory is False
        assert subcategory.show_in_menu is False
