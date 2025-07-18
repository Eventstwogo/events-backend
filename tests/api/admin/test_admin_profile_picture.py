import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from shared.db.models import AdminUser


@pytest.mark.asyncio
async def test_update_profile_picture_success(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, test_app
):
    role = await seed_roles("HR")
    config = seed_config

    # Generate unique test user details
    user_id = uuid.uuid4().hex[:6]
    unique_suffix = uuid.uuid4().hex[:6]
    username = f"testuser_{unique_suffix}"
    email = f"{username}@example.com"

    user = AdminUser(
        user_id=user_id,
        username=username,
        email=email,
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=config.global_180_day_flag,
        created_at=datetime.utcnow(),
        is_deleted=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    # Mock the authentication dependency
    async def mock_get_current_active_user():
        return user

    # Override the dependency
    from shared.dependencies.admin import get_current_active_user

    test_app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_user
    )

    # Mock file upload functions to avoid actual file operations
    mock_upload_url = "uploads/profile_pictures/test_user/profile.jpg"
    mock_media_url = "http://localhost:8000/media/uploads/profile_pictures/test_user/profile.jpg"

    with (
        patch(
            "admin_service.api.v1.endpoints.profile.save_uploaded_file",
            return_value=mock_upload_url,
        ),
        patch("admin_service.api.v1.endpoints.profile.remove_file_if_exists"),
        patch(
            "admin_service.api.v1.endpoints.profile.get_media_url",
            return_value=mock_media_url,
        ),
    ):

        files = {
            "profile_picture": ("profile.jpg", b"dummyimage", "image/jpeg"),
        }

        try:
            response = await test_client.patch(
                "/api/v1/admin/profile/picture", files=files
            )
            body = response.json()

            assert response.status_code == 200
            assert "Profile picture updated successfully" in body["message"]
            assert "profile_picture" in body["data"]
            assert body["data"]["profile_picture"] == mock_media_url
        finally:
            # Clean up the override
            test_app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_update_picture_invalid_file_type(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, test_app
):
    role = await seed_roles("HR")
    config = seed_config

    # Generate fully unique user attributes
    unique_suffix = uuid.uuid4().hex[:6]
    user_id = uuid.uuid4().hex[:6]
    username = f"filetypeuser_{unique_suffix}"
    email = f"{username}@example.com"

    user = AdminUser(
        user_id=user_id,
        username=username,
        email=email,
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=config.global_180_day_flag,
        created_at=datetime.utcnow(),
        is_deleted=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    # Mock the authentication dependency
    async def mock_get_current_active_user():
        return user

    # Override the dependency
    from shared.dependencies.admin import get_current_active_user

    test_app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_user
    )

    files = {
        "profile_picture": (
            "malware.exe",
            b"binarydata",
            "application/octet-stream",
        ),
    }

    try:
        res = await test_client.patch(
            "/api/v1/admin/profile/picture", files=files
        )
        body = res.json()

        assert res.status_code == 400
        assert (
            "Invalid file type for profile picture" in body["detail"]["message"]
        )
    finally:
        # Clean up the override
        test_app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_update_picture_missing_file(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, test_app
):
    role = await seed_roles("HR")
    config = seed_config

    # Generate unique test user details
    user_id = uuid.uuid4().hex[:6]
    unique_suffix = uuid.uuid4().hex[:6]
    username = f"testuser_{unique_suffix}"
    email = f"{username}@example.com"

    user = AdminUser(
        user_id=user_id,
        username=username,
        email=email,
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=config.global_180_day_flag,
        created_at=datetime.utcnow(),
        is_deleted=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    # Mock the authentication dependency
    async def mock_get_current_active_user():
        return user

    # Override the dependency
    from shared.dependencies.admin import get_current_active_user

    test_app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_user
    )

    # Send request without profile_picture file
    try:
        res = await test_client.patch("/api/v1/admin/profile/picture")
        body = res.json()

        assert res.status_code == 422
        assert any(
            err.get("loc", [])[-1] == "profile_picture"
            and err.get("msg") == "Field required"
            for err in body.get("detail", [])
        )
    finally:
        # Clean up the override
        test_app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_update_picture_user_not_found(
    test_client: AsyncClient, test_app
):
    # Mock the authentication dependency to return a user that doesn't exist in DB
    mock_user = AdminUser(
        user_id="nonexistent123",
        username="nonexistentuser",
        email="nonexistent@test.com",
        role_id="role123",
        is_deleted=False,
    )

    async def mock_get_current_active_user():
        return mock_user

    # Override the dependency
    from shared.dependencies.admin import get_current_active_user

    test_app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_user
    )

    files = {
        "profile_picture": ("img.jpg", b"data", "image/jpeg"),
    }

    try:
        res = await test_client.patch(
            "/api/v1/admin/profile/picture", files=files
        )
        body = res.json()

        assert res.status_code == 404
        assert "User not found" in body["detail"]["message"]
    finally:
        # Clean up the override
        test_app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_update_picture_authentication_required(test_client: AsyncClient):
    """Test that authentication is required for profile picture update"""
    files = {
        "profile_picture": ("img.jpg", b"data", "image/jpeg"),
    }

    # Send request without authentication (no dependency override)
    res = await test_client.patch("/api/v1/admin/profile/picture", files=files)
    body = res.json()

    assert res.status_code == 401
    assert "detail" in body
