import pytest
from httpx import AsyncClient

from db.models import AdminUser


@pytest.mark.asyncio
async def test_get_admin_user_by_id_success(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    """Should return user details successfully"""
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr123",
        username="admin1",
        email="admin1@example.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_active=False,
        profile_picture=None,
        days_180_flag=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    response = await test_client.get(
        f"/api/v1/admin-users/admin-users/{user.user_id}"
    )
    body = response.json()

    assert response.status_code == 200
    assert body["message"] == "Admin user fetched successfully."
    assert body["data"]["username"] == "admin1"
    assert body["data"]["email"] == "admin1@example.com"
    assert body["data"]["role_id"] == role.role_id
    assert body["data"]["role_name"] == role.role_name
    assert body["data"]["status"] is False
    assert "profile_picture" in body["data"]


@pytest.mark.asyncio
async def test_get_admin_user_invalid_user_id_format(
    test_client: AsyncClient, clean_db
):
    """Should return 400 for invalid user_id length"""
    response = await test_client.get("/api/v1/admin-users/admin-users/short")
    body = response.json()

    assert response.status_code == 400
    assert "Invalid user ID format" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_get_admin_user_not_found(test_client: AsyncClient, clean_db):
    """Should return 404 for non-existent user"""
    response = await test_client.get("/api/v1/admin-users/admin-users/abc999")
    body = response.json()

    assert response.status_code == 404
    assert "User not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_get_admin_user_null_profile_picture(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    """Should gracefully handle null profile_picture"""
    role = await seed_roles("MANAGER")
    config = seed_config

    user = AdminUser(
        user_id="usr789",
        username="picless",
        email="picless@admin.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_active=False,
        profile_picture=None,  # NULL case
        days_180_flag=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.get(
        f"/api/v1/admin-users/admin-users/{user.user_id}"
    )
    body = res.json()

    assert res.status_code == 200
    assert body["data"]["profile_picture"] is None or isinstance(
        body["data"]["profile_picture"], str
    )
