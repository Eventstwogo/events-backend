import pytest
from httpx import AsyncClient
from sqlalchemy import select

from shared.db.models import AdminUser


@pytest.mark.asyncio
async def test_register_admin_success(
    test_client: AsyncClient, test_db_session, clean_db, seed_config, seed_roles
):
    """Test successful admin user registration."""
    role = await seed_roles("MANAGER")

    payload = {
        "username": "admin-user",
        "email": "admin@example.com",
        "role_id": role.role_id,
    }

    res = await test_client.post("/api/v1/admin/register", json=payload)
    body = res.json()

    print("Response JSON:", body)

    assert res.status_code == 201
    assert "Welcome email sent" in body["message"]

    # Use the actual payload for the DB query with hash-based lookup
    query = AdminUser.by_username_query(payload["username"])
    result = await test_db_session.execute(query)
    user = result.scalar_one_or_none()

    assert user is not None
    assert user.email == payload["email"]
    assert user.role_id == payload["role_id"]
    assert user.profile_picture is None


@pytest.mark.asyncio
async def test_register_admin_duplicate_user(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    """Test user registration fails if email or username already exists."""
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="abc123",
        username="existing",
        email="exist@example.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=config.global_180_day_flag,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    payload = {
        "username": "existing",
        "email": "exist@example.com",
        "role_id": role.role_id,
    }

    res = await test_client.post("/api/v1/admin/register", json=payload)
    body = res.json()

    assert res.status_code == 409
    assert "already exists" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_register_admin_invalid_role(
    test_client: AsyncClient, seed_config, clean_db
):
    """Test user registration fails if role ID is invalid."""

    payload = {
        "username": "newadmin",
        "email": "newadmin@example.com",
        "role_id": "xyz123",
    }

    res = await test_client.post("/api/v1/admin/register", json=payload)
    body = res.json()

    assert res.status_code == 404
    assert "Role not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_register_admin_superadmin_duplicate(
    test_client: AsyncClient, test_db_session, seed_config, seed_roles, clean_db
):
    """Test only one superadmin is allowed."""
    role = await seed_roles(
        "SUPERADMIN"
    )  # if is_superadmin is not part of model
    config = seed_config

    existing_superadmin = AdminUser(
        user_id="sup123",
        username="superadmin",
        email="super@admin.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=config.global_180_day_flag,
    )
    test_db_session.add(existing_superadmin)
    await test_db_session.commit()

    payload = {
        "username": "secondadmin",
        "email": "second@admin.com",
        "role_id": role.role_id,
    }

    res = await test_client.post("/api/v1/admin/register", json=payload)
    body = res.json()

    assert res.status_code == 409
    assert "Only one Super Admin is allowed" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_register_admin_missing_fields(
    test_client: AsyncClient, clean_db
):
    """Test request fails when required fields are missing."""
    res = await test_client.post("/api/v1/admin/register", json={})
    body = res.json()
    
    assert res.status_code == 422
    detail = body["detail"]
    
    # The model validator will return the first missing field error
    assert len(detail) == 1
    assert detail[0]["type"] == "value_error"
    assert "Username is required" in detail[0]["msg"]
