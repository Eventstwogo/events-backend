"""
Test cases for subcategory by ID endpoints (/api/v1/subcategories/)
Tests for sub_categories_by_id.py endpoints:
- GET /{subcategory_id} - Get subcategory by ID
- PUT /update/{subcategory_id} - Update subcategory by ID
- DELETE /soft-delete/{subcategory_id} - Soft delete subcategory
- PUT /restore/{subcategory_id} - Restore subcategory
- DELETE /hard-delete/{subcategory_id} - Hard delete subcategory
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


class TestGetSubcategoryById:
    """Test cases for getting subcategory by ID."""

    @pytest.mark.asyncio
    async def test_get_subcategory_by_id_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully fetching a subcategory by ID."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT001",
                category_name="ELECTRONICS",
                category_slug="electronics",
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
                subcategory_meta_description="Top smartphone deals and reviews",
                subcategory_status=False,  # Active
                featured_subcategory=True,
                show_in_menu=True,
                category_id="CAT001",
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/SUB001")
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Subcategory fetched successfully"
        assert body["data"]["subcategory_id"] == "SUB001"
        assert (
            body["data"]["subcategory_name"] == "Smartphones"
        )  # Title case in response
        assert body["data"]["subcategory_slug"] == "smartphones"
        assert body["data"]["subcategory_status"] is False  # Active
        assert body["data"]["featured_subcategory"] is True
        assert body["data"]["show_in_menu"] is True

        # Check parent category information
        assert body["data"]["parent_category"]["category_id"] == "CAT001"
        assert body["data"]["parent_category"]["category_name"] == "ELECTRONICS"

    @pytest.mark.asyncio
    async def test_get_subcategory_by_id_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test fetching non-existent subcategory returns 404."""
        res = await test_client.get("/api/v1/subcategories/INVALID_ID")
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_get_inactive_subcategory_by_id(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching inactive subcategory by ID."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT002",
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
                category_id="CAT002",
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/SUB002")
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["subcategory_status"] is True  # Inactive

    @pytest.mark.asyncio
    async def test_get_subcategory_with_minimal_data(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test fetching subcategory with minimal required data."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT003",
                category_name="SPORTS",
                category_slug="sports",
                category_status=False,
            )
        )

        # Create subcategory with minimal data
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB003",
                subcategory_name="FOOTBALL",
                subcategory_slug="football",
                subcategory_status=False,
                category_id="CAT003",
            )
        )
        await test_db_session.commit()

        res = await test_client.get("/api/v1/subcategories/SUB003")
        body = res.json()

        assert res.status_code == 200
        assert body["data"]["subcategory_id"] == "SUB003"
        assert body["data"]["subcategory_name"] == "Football"


class TestUpdateSubcategoryById:
    """Test cases for updating subcategory by ID."""

    @pytest.mark.asyncio
    async def test_update_subcategory_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully updating a subcategory."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT100",
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
                subcategory_name="OLD_NAME",
                subcategory_slug="old-name",
                subcategory_status=False,
                category_id="CAT100",
            )
        )
        await test_db_session.commit()

        data = {
            "name": "New Gaming Consoles",
            "description": "Updated description for gaming consoles",
            "featured": "true",
        }

        res = await test_client.put(
            "/api/v1/subcategories/update/SUB100", data=data
        )
        body = res.json()

        assert res.status_code == 200
        assert body["message"] == "Subcategory updated successfully"
        assert "subcategory_id" in body["data"]

        # Verify in database
        stmt = select(SubCategory).where(SubCategory.subcategory_id == "SUB100")
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert (
            subcategory.subcategory_name == "NEW GAMING CONSOLES"
        )  # Uppercase
        assert subcategory.featured_subcategory is True

    @pytest.mark.asyncio
    async def test_update_subcategory_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test updating non-existent subcategory returns 404."""
        data = {"name": "New Name"}

        res = await test_client.put(
            "/api/v1/subcategories/update/INVALID_ID", data=data
        )
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_update_subcategory_no_changes(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating subcategory with no changes returns error."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT101",
                category_name="MOVIES",
                category_slug="movies",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB101",
                subcategory_name="ACTION",
                subcategory_slug="action",
                subcategory_status=False,
                category_id="CAT101",
            )
        )
        await test_db_session.commit()

        data = {}  # No changes

        res = await test_client.put(
            "/api/v1/subcategories/update/SUB101", data=data
        )
        body = res.json()

        assert res.status_code == 400
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "no changes" in error_message.lower()
        else:
            assert "no changes" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_update_subcategory_duplicate_name(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating subcategory with duplicate name fails."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT102",
                category_name="MUSIC",
                category_slug="music",
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
                        "subcategory_name": "ROCK",
                        "subcategory_slug": "rock",
                        "subcategory_status": False,
                        "category_id": "CAT102",
                    },
                    {
                        "id": uuid_str(),
                        "subcategory_id": "SUB103",
                        "subcategory_name": "JAZZ",
                        "subcategory_slug": "jazz",
                        "subcategory_status": False,
                        "category_id": "CAT102",
                    },
                ]
            )
        )
        await test_db_session.commit()

        data = {"name": "Rock"}  # Duplicate name

        res = await test_client.put(
            "/api/v1/subcategories/update/SUB103", data=data
        )
        body = res.json()

        assert res.status_code == 400
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "already exists" in error_message.lower()
        else:
            assert "already exists" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_update_subcategory_with_file(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test updating subcategory with file upload."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT104",
                category_name="FASHION",
                category_slug="fashion",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB104",
                subcategory_name="SHOES",
                subcategory_slug="shoes",
                subcategory_status=False,
                category_id="CAT104",
            )
        )
        await test_db_session.commit()

        fake_image = BytesIO(b"fake image content")
        fake_image.name = "new_image.jpg"

        data = {"name": "Updated Shoes"}
        files = {"file": ("new_image.jpg", fake_image, "image/jpeg")}

        res = await test_client.put(
            "/api/v1/subcategories/update/SUB104", data=data, files=files
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
                category_id="CAT105",
                category_name="TRAVEL",
                category_slug="travel",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB105",
                subcategory_name="HOTELS",
                subcategory_slug="hotels",
                subcategory_status=False,
                category_id="CAT105",
            )
        )
        await test_db_session.commit()

        fake_image = BytesIO(b"fake image content")
        fake_image.name = "invalid*name?.jpg"

        data = {"name": "Updated Hotels"}
        files = {"file": (fake_image.name, fake_image, "image/jpeg")}

        res = await test_client.put(
            "/api/v1/subcategories/update/SUB105", data=data, files=files
        )
        body = res.json()

        assert res.status_code == 400
        # Handle both string and dict detail formats
        if isinstance(body["detail"], str):
            assert "invalid file name" in body["detail"].lower()
        else:
            assert "invalid file name" in body["detail"]["message"].lower()


class TestSoftDeleteSubcategoryById:
    """Test cases for soft deleting subcategory by ID."""

    @pytest.mark.asyncio
    async def test_soft_delete_subcategory_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully soft deleting a subcategory."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT200",
                category_name="FOOD",
                category_slug="food",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB200",
                subcategory_name="TO_DELETE",
                subcategory_slug="to-delete",
                subcategory_status=False,  # Active
                category_id="CAT200",
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/subcategories/soft-delete/SUB200"
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
    async def test_soft_delete_subcategory_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test soft deleting non-existent subcategory returns 404."""
        res = await test_client.delete(
            "/api/v1/subcategories/soft-delete/INVALID_ID"
        )
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_soft_delete_already_inactive_subcategory(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test soft deleting already inactive subcategory returns error."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT201",
                category_name="DRINKS",
                category_slug="drinks",
                category_status=False,
            )
        )

        # Create inactive subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB201",
                subcategory_name="ALREADY_INACTIVE",
                subcategory_slug="already-inactive",
                subcategory_status=True,  # Already inactive
                category_id="CAT201",
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/subcategories/soft-delete/SUB201"
        )
        body = res.json()

        assert res.status_code == 400
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "already inactive" in error_message.lower()
        else:
            assert "already inactive" in str(error_message).lower()


class TestRestoreSubcategoryById:
    """Test cases for restoring subcategory by ID."""

    @pytest.mark.asyncio
    async def test_restore_subcategory_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully restoring a subcategory."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT300",
                category_name="HEALTH",
                category_slug="health",
                category_status=False,
            )
        )

        # Create inactive subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB300",
                subcategory_name="TO_RESTORE",
                subcategory_slug="to-restore",
                subcategory_status=True,  # Inactive
                category_id="CAT300",
            )
        )
        await test_db_session.commit()

        res = await test_client.put("/api/v1/subcategories/restore/SUB300")
        body = res.json()

        assert res.status_code == 200
        assert "restored successfully" in body["message"].lower()

        # Verify subcategory is now active
        stmt = select(SubCategory).where(SubCategory.subcategory_id == "SUB300")
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory.subcategory_status is False  # Active

    @pytest.mark.asyncio
    async def test_restore_subcategory_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test restoring non-existent subcategory returns 404."""
        res = await test_client.put("/api/v1/subcategories/restore/INVALID_ID")
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()

    @pytest.mark.asyncio
    async def test_restore_already_active_subcategory(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test restoring already active subcategory returns error."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT301",
                category_name="FITNESS",
                category_slug="fitness",
                category_status=False,
            )
        )

        # Create active subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB301",
                subcategory_name="ALREADY_ACTIVE",
                subcategory_slug="already-active",
                subcategory_status=False,  # Already active
                category_id="CAT301",
            )
        )
        await test_db_session.commit()

        res = await test_client.put("/api/v1/subcategories/restore/SUB301")
        body = res.json()

        assert res.status_code == 400
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "already active" in error_message.lower()
        else:
            assert "already active" in str(error_message).lower()


class TestHardDeleteSubcategoryById:
    """Test cases for hard deleting subcategory by ID."""

    @pytest.mark.asyncio
    async def test_hard_delete_subcategory_success(
        self, test_client: AsyncClient, test_db_session, clean_db
    ):
        """Test successfully hard deleting a subcategory."""
        # Create parent category
        await test_db_session.execute(
            insert(Category).values(
                category_id="CAT400",
                category_name="EDUCATION",
                category_slug="education",
                category_status=False,
            )
        )

        # Create subcategory
        await test_db_session.execute(
            insert(SubCategory).values(
                id=uuid_str(),
                subcategory_id="SUB400",
                subcategory_name="TO_HARD_DELETE",
                subcategory_slug="to-hard-delete",
                subcategory_status=False,
                category_id="CAT400",
            )
        )
        await test_db_session.commit()

        res = await test_client.delete(
            "/api/v1/subcategories/hard-delete/SUB400"
        )
        body = res.json()

        assert res.status_code == 200
        assert "permanently deleted" in body["message"].lower()

        # Verify subcategory is completely removed
        stmt = select(SubCategory).where(SubCategory.subcategory_id == "SUB400")
        result = await test_db_session.execute(stmt)
        subcategory = result.scalar_one_or_none()

        assert subcategory is None

    @pytest.mark.asyncio
    async def test_hard_delete_subcategory_not_found(
        self, test_client: AsyncClient, clean_db
    ):
        """Test hard deleting non-existent subcategory returns 404."""
        res = await test_client.delete(
            "/api/v1/subcategories/hard-delete/INVALID_ID"
        )
        body = res.json()

        assert res.status_code == 404
        error_message = body.get("detail", body.get("message", ""))
        if isinstance(error_message, str):
            assert "not found" in error_message.lower()
        else:
            assert "not found" in str(error_message).lower()
