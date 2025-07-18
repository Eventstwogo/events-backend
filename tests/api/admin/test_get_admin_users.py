import pytest
from httpx import AsyncClient

from shared.core.security import generate_searchable_hash
from shared.db.models import AdminUser


@pytest.mark.asyncio
async def test_get_admin_users_all(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    """Test fetching all admin users without any filters."""
    role = await seed_roles("MANAGER")
    config = seed_config

    # Seed active and inactive users
    active_user = AdminUser(
        user_id="user01",
        username_encrypted="activeuser",
        email_encrypted="active@admin.com",
        username_hash=generate_searchable_hash("activeuser"),
        email_hash=generate_searchable_hash("active@admin.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,  # False = active user
    )
    inactive_user = AdminUser(
        user_id="user02",
        username_encrypted="inactiveuser",
        email_encrypted="inactive@admin.com",
        username_hash=generate_searchable_hash("inactiveuser"),
        email_hash=generate_searchable_hash("inactive@admin.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=True,  # True = inactive user
    )

    test_db_session.add_all([active_user, inactive_user])
    await test_db_session.commit()

    res = await test_client.get("/api/v1/admin/users/")
    body = res.json()

    # Debug: print response details if not 200
    if res.status_code != 200:
        print(f"Status: {res.status_code}")
        print(f"Response: {body}")

    assert res.status_code == 200
    assert "Admin users fetched successfully." in body["message"]
    assert isinstance(body["data"], list)
    # Should have both active (is_deleted=False) and inactive (is_deleted=True) users
    assert any(u["is_deleted"] is False for u in body["data"])  # active users
    assert any(u["is_deleted"] is True for u in body["data"])  # inactive users


@pytest.mark.asyncio
async def test_get_admin_users_active_only(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    """Test fetching only active admin users."""
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="user03",
        username_encrypted="activeonly",
        email_encrypted="activeonly@admin.com",
        username_hash=generate_searchable_hash("activeonly"),
        email_hash=generate_searchable_hash("activeonly@admin.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,  # False = active user
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.get(
        "/api/v1/admin/users/?is_deleted=false"
    )  # Query for active users (is_deleted=false)
    body = res.json()

    assert res.status_code == 200
    assert all(
        u["is_deleted"] is False for u in body["data"]
    )  # All should be active users


@pytest.mark.asyncio
async def test_get_admin_users_inactive_only(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    """Test fetching only inactive admin users."""
    role = await seed_roles("IT")
    config = seed_config

    user = AdminUser(
        user_id="user04",
        username_encrypted="inactiveonly",
        email_encrypted="inactiveonly@admin.com",
        username_hash=generate_searchable_hash("inactiveonly"),
        email_hash=generate_searchable_hash("inactiveonly@admin.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=True,  # True = inactive user
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.get(
        "/api/v1/admin/users/?is_deleted=true"
    )  # Query for inactive users (is_deleted=true)
    body = res.json()

    assert res.status_code == 200
    assert all(
        u["is_deleted"] is True for u in body["data"]
    )  # All should be inactive users


@pytest.mark.asyncio
async def test_get_admin_users_not_found(test_client: AsyncClient, clean_db):
    """Test case when no users exist and endpoint should return 404."""
    res = await test_client.get("/api/v1/admin/users/?is_deleted=false")
    body = res.json()

    assert res.status_code == 404
    assert "No admin users found" in body["detail"]["message"]
