import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient

from db.models import AdminUser


@pytest.mark.asyncio
async def test_update_profile_picture_success(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config
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
        is_active=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    files = {
        "user_id": (None, user.user_id),
        "profile_picture": ("profile.jpg", b"dummyimage", "image/jpeg"),
    }

    response = await test_client.patch(
        "/api/v1/admin-users/profile-picture", files=files
    )
    body = response.json()

    assert response.status_code == 200
    assert "Profile picture updated successfully" in body["message"]
    assert "profile_picture" in body["data"]
    assert body["data"]["user_id"] == user.user_id
    assert body["data"]["email"] == user.email


@pytest.mark.asyncio
async def test_update_picture_invalid_file_type(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config
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
        is_active=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    files = {
        "user_id": (None, user.user_id),
        "profile_picture": (
            "malware.exe",
            b"binarydata",
            "application/octet-stream",
        ),
    }

    res = await test_client.patch(
        "/api/v1/admin-users/profile-picture", files=files
    )
    body = res.json()

    assert res.status_code == 400
    assert "Invalid file type" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_update_picture_invalid_user_id_format(test_client: AsyncClient):
    files = {
        "user_id": (None, "bad"),  # Invalid: not 6+ characters
        "profile_picture": ("img.jpg", b"data", "image/jpeg"),
    }

    res = await test_client.patch(
        "/api/v1/admin-users/profile-picture", files=files
    )
    body = res.json()

    assert res.status_code == 400
    assert "Invalid user ID format" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_update_picture_user_not_found(test_client: AsyncClient):
    files = {
        "user_id": (None, "abc123"),  # Assuming this ID doesn't exist
        "profile_picture": ("img.jpg", b"data", "image/jpeg"),
    }

    res = await test_client.patch(
        "/api/v1/admin-users/profile-picture", files=files
    )
    body = res.json()

    assert res.status_code == 404
    assert "User not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_update_picture_missing_file(test_client: AsyncClient):
    files = {
        "user_id": (None, "abc123"),
    }

    res = await test_client.patch(
        "/api/v1/admin-users/profile-picture", files=files
    )
    body = res.json()

    assert res.status_code == 422
    assert any(
        err.get("loc", [])[-1] == "profile_picture"
        and err.get("msg") == "Field required"
        for err in body.get("detail", [])
    )
