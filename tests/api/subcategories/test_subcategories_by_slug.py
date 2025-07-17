"""
Test cases for subcategory by slug endpoints (/api/v1/subcategories/)
Tests for sub_categories_by_slug.py endpoints:
- GET /slug/{slug} - Get subcategory by slug
- PUT /update/slug/{slug} - Update subcategory by slug
- DELETE /soft-delete/slug/{slug} - Soft delete subcategory by slug
- PUT /restore/slug/{slug} - Restore subcategory by slug
- DELETE /hard-delete/slug/{slug} - Hard delete subcategory by slug
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


class TestGetSubcategoryBySlug:
    """Test cases for getting subcategory by slug."""

    @pytest.mark.asyncio
    async def test_get_subcategory_by_slug_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully fetching a subcategory by slug."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT001",
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
                subcategory_name="ARTIFICIAL_INTELLIGENCE",
                subcategory_slug="artificial-intelligence",
                subcategory_description="AI and machine learning topics",
                subcategory_meta_title="AI Technology",
                subcategory_meta_description="Latest in AI and ML",
                subcategory_status=False,  # Active
                featured_subcategory=True,
                show_in_menu=True,
                category_id="CAT001",
            )
        )
        await test_db_session.commit()

        res = await test_client.get(
            "/api/v1/subcategories/slug/artificial-intelligence"
        )
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Subcategory fetched successfully"
        assert body["data"]["subcategory_slug"] == "artificial-intelligence"
        assert (
            body["data"]["subcategory_name"] == "Artificial_Intelligence"
        )  # Title case with underscores
        assert body["data"]["subcategory_status"] is False  # Active
        assert body["data"]["featured_subcategory"] is True

        # Check parent category information
        assert body["data"]["parent_category"]["category_id"] == "CAT001"
        assert body["data"]["parent_category"]["category_name"] == "TECHNOLOGY"

    @pytest.mark.asyncio
    async def test_get_subcategory_by_slug_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test fetching non-existent subcategory by slug returns 404."""
        res = await test_client.get(
            "/api/v1/subcategories/slug/nonexistent-slug"
        )
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_get_inactive_subcategory_by_slug(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching inactive subcategory by slug."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT002",
                category_name="SCIENCE",
                category_slug="science",
                category_status=False,
            )
        )

        # Create inactive subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB002",
                subcategory_name="PHYSICS",
                subcategory_slug="physics",
                subcategory_status=True,  # Inactive
                category_id="CAT002",
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/slug/physics")
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["subcategory_status"] is True  # Inactive

    @pytest.mark.asyncio
    async def test_get_subcategory_with_special_characters_in_slug(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching subcategory with special characters in slug."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT003",
                category_name="PROGRAMMING",
                category_slug="programming",
                category_status=False,
            )
        )

        # Create subcategory with special characters in slug
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB003",
                subcategory_name="C_PLUS_PLUS",
                subcategory_slug="c-plus-plus",
                subcategory_status=False,
                category_id="CAT003",
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/slug/c-plus-plus")
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["subcategory_slug"] == "c-plus-plus"
        assert body["data"]["subcategory_name"] == "C_Plus_Plus"


class TestUpdateSubcategoryBySlug:
    """Test cases for updating subcategory by slug."""

    @pytest.mark.asyncio
    async def test_update_subcategory_by_slug_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully updating a subcategory by slug."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT100",
                category_name="AUTOMOTIVE",
                category_slug="automotive",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB100",
                subcategory_name="ELECTRIC_CARS",
                subcategory_slug="electric-cars",
                subcategory_status=False,
                category_id="CAT100",
            )
        )
        await test_db_session.commit()

        data = {
            "name": "Electric Vehicles",
            "description": "All about electric vehicles and sustainability",
            "featured": "true",
        }

        res = await test_client.put(
            "/api/v1/subcategories/update/slug/electric-cars", data=data
        )
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Subcategory updated successfully"
        assert "subcategory_id" in body["data"]
        assert "subcategory_slug" in body["data"]

        # Verify in database
        stmt = select(SubCategory).where(
            SubCategory.subcategory_slug == "electric-cars"
        )
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.subcategory_name == "ELECTRIC VEHICLES"  # Uppercase
        assert subcategory.featured_subcategory is True

    @pytest.mark.asyncio
    async def test_update_subcategory_by_slug_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test updating non-existent subcategory by slug returns 404."""
        data = {"name": "New Name"}

        res = await test_client.put(
            "/api/v1/subcategories/update/slug/nonexistent", data=data
        )
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_update_subcategory_slug_change(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating subcategory with slug change."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT101",
                category_name="COOKING",
                category_slug="cooking",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB101",
                subcategory_name="ITALIAN_CUISINE",
                subcategory_slug="italian-cuisine",
                subcategory_status=False,
                category_id="CAT101",
            )
        )
        await test_db_session.commit()

        data = {
            "name": "Mediterranean Cuisine",
            "new_slug": "mediterranean-cuisine",
        }

        res = await test_client.put(
            "/api/v1/subcategories/update/slug/italian-cuisine", data=data
        )
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Subcategory updated successfully"

        # Verify slug was updated
        stmt = select(SubCategory).where(SubCategory.subcategory_id == "SUB101")
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.subcategory_slug == "mediterranean-cuisine"
        assert subcategory.subcategory_name == "MEDITERRANEAN CUISINE"

    @pytest.mark.asyncio
    async def test_update_subcategory_duplicate_name(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating subcategory with duplicate name fails."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT102",
                category_name="ANIMALS",
                category_slug="animals",
                category_status=False,
            )
        )

        # Create subcategories
        await test_db_session.execute(
            insert(SubCategory).values(
                [
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB102",
                        "subcategory_name": "DOGS",
                        "subcategory_slug": "dogs",
                        "subcategory_status": False,
                        "category_id": "CAT102",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB103",
                        "subcategory_name": "CATS",
                        "subcategory_slug": "cats",
                        "subcategory_status": False,
                        "category_id": "CAT102",
                    },
                ]
            )
        )
        await test_db_session.commit()

        data = {"name": "Dogs"}  # Duplicate name

        res = await test_client.put(
            "/api/v1/subcategories/update/slug/cats", data=data
        )
        body = res.json()

        assert res.status_code == 400
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "already exists" in error_message.lower()
        else:
            assert "already exists" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_update_subcategory_with_file_upload(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating subcategory with file upload."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT103",
                category_name="ART",
                category_slug="art",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB104",
                subcategory_name="PAINTING",
                subcategory_slug="painting",
                subcategory_status=False,
                category_id="CAT103",
            )
        )
        await test_db_session.commit()

        fake_image = BytesIO(b"fake image content")
        fake_image.name = "painting_thumbnail.jpg"

        data = {"name": "Oil Painting"}
        files = {"file": ("painting_thumbnail.jpg", fake_image, "image/jpeg")}

        res = await test_client.put(
            "/api/v1/subcategories/update/slug/painting", data=data, files=files
        )
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Subcategory updated successfully"

    @pytest.mark.asyncio
    async def test_update_subcategory_invalid_filename(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating subcategory with invalid filename fails."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT104",
                category_name="PHOTOGRAPHY",
                category_slug="photography",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB105",
                subcategory_name="PORTRAITS",
                subcategory_slug="portraits",
                subcategory_status=False,
                category_id="CAT104",
            )
        )
        await test_db_session.commit()

        fake_image = BytesIO(b"fake image content")
        fake_image.name = "invalid*filename?.jpg"

        data = {"name": "Portrait Photography"}
        files = {"file": (fake_image.name, fake_image, "image/jpeg")}

        res = await test_client.put(
            "/api/v1/subcategories/update/slug/portraits",
            data=data,
            files=files,
        )
        body = res.json()

        assert res.status_code == 400
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "invalid file name" in error_message.lower()
        else:
            assert "invalid file name" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_update_subcategory_partial_update(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test partial update of subcategory fields."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT105",
                category_name="MUSIC",
                category_slug="music",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB106",
                subcategory_name="CLASSICAL",
                subcategory_slug="classical",
                subcategory_description="Classical music genres",
                subcategory_status=False,
                featured_subcategory=False,
                show_in_menu=False,
                category_id="CAT105",
            )
        )
        await test_db_session.commit()

        # Update only featured and show_in_menu flags
        data = {
            "featured": "true",
            "show_in_menu": "true",
        }

        res = await test_client.put(
            "/api/v1/subcategories/update/slug/classical", data=data
        )
        body = res.json()

        assert res.status_code == 200

        # Verify only specified fields were updated
        stmt = select(SubCategory).where(
            SubCategory.subcategory_slug == "classical"
        )
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.subcategory_name == "CLASSICAL"  # Unchanged
        assert (
            subcategory.subcategory_description == "Classical music genres"
        )  # Unchanged
        assert subcategory.featured_subcategory is True  # Updated
        assert subcategory.show_in_menu is True  # Updated


class TestSoftDeleteSubcategoryBySlug:
    """Test cases for soft deleting subcategory by slug."""

    @pytest.mark.asyncio
    async def test_soft_delete_subcategory_by_slug_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully soft deleting a subcategory by slug."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT200",
                category_name="SPORTS",
                category_slug="sports",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB200",
                subcategory_name="TENNIS",
                subcategory_slug="tennis",
                subcategory_status=False,  # Active
                category_id="CAT200",
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/subcategories/soft-delete/slug/tennis"
        )
        body = res.json()

        assert res.status_code == 200
        assert "soft deleted successfully" in body["message"].lower()

        # Verify subcategory is now inactive
        stmt = select(SubCategory).where(
            SubCategory.subcategory_slug == "tennis"
        )
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.subcategory_status is True  # Inactive

    @pytest.mark.asyncio
    async def test_soft_delete_subcategory_by_slug_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test soft deleting non-existent subcategory by slug returns 404."""
        res = await test_client.delete(
            "/api/v1/subcategories/soft-delete/slug/nonexistent"
        )
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_soft_delete_already_inactive_subcategory_by_slug(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test soft deleting already inactive subcategory by slug returns error."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT201",
                category_name="GAMES",
                category_slug="games",
                category_status=False,
            )
        )

        # Create inactive subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB201",
                subcategory_name="CHESS",
                subcategory_slug="chess",
                subcategory_status=True,  # Already inactive
                category_id="CAT201",
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/subcategories/soft-delete/slug/chess"
        )
        body = res.json()

        assert res.status_code == 400
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "already inactive" in error_message.lower()
        else:
            assert "already inactive" in str(error_message).lower()


class TestRestoreSubcategoryBySlug:
    """Test cases for restoring subcategory by slug."""

    @pytest.mark.asyncio
    async def test_restore_subcategory_by_slug_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully restoring a subcategory by slug."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT300",
                category_name="LITERATURE",
                category_slug="literature",
                category_status=False,
            )
        )

        # Create inactive subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB300",
                subcategory_name="POETRY",
                subcategory_slug="poetry",
                subcategory_status=True,  # Inactive
                category_id="CAT300",
            )
        )
        await test_db_session.commit()

        res = await test_client.put("/api/v1/subcategories/restore/slug/poetry")
        body = res.json()

        assert res.status_code == 200
        assert "restored successfully" in body["message"].lower()

        # Verify subcategory is now active
        stmt = select(SubCategory).where(
            SubCategory.subcategory_slug == "poetry"
        )
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.subcategory_status is False  # Active

    @pytest.mark.asyncio
    async def test_restore_subcategory_by_slug_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test restoring non-existent subcategory by slug returns 404."""
        res = await test_client.put(
            "/api/v1/subcategories/restore/slug/nonexistent"
        )
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_restore_already_active_subcategory_by_slug(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test restoring already active subcategory by slug returns error."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT301",
                category_name="HISTORY",
                category_slug="history",
                category_status=False,
            )
        )

        # Create active subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB301",
                subcategory_name="ANCIENT_HISTORY",
                subcategory_slug="ancient-history",
                subcategory_status=False,  # Already active
                category_id="CAT301",
            )
        )
        await test_db_session.commit()

        res = await test_client.put(
            "/api/v1/subcategories/restore/slug/ancient-history"
        )
        body = res.json()

        assert res.status_code == 400
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "already active" in error_message.lower()
        else:
            assert "already active" in str(error_message).lower()


class TestHardDeleteSubcategoryBySlug:
    """Test cases for hard deleting subcategory by slug."""

    @pytest.mark.asyncio
    async def test_hard_delete_subcategory_by_slug_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully hard deleting a subcategory by slug."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT400",
                category_name="NATURE",
                category_slug="nature",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB400",
                subcategory_name="FORESTS",
                subcategory_slug="forests",
                subcategory_status=False,
                category_id="CAT400",
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/subcategories/hard-delete/slug/forests"
        )
        body = res.json()

        assert res.status_code == 200
        assert "permanently deleted" in body["message"].lower()

        # Verify subcategory is completely removed
        stmt = select(SubCategory).where(
            SubCategory.subcategory_slug == "forests"
        )
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory is None

    @pytest.mark.asyncio
    async def test_hard_delete_subcategory_by_slug_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test hard deleting non-existent subcategory by slug returns 404."""
        res = await test_client.delete(
            "/api/v1/subcategories/hard-delete/slug/nonexistent"
        )
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()
