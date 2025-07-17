from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from db.models import AdminUser


@pytest.mark.asyncio
async def test_login_success(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr001",
        username="loguser",
        email="log@admin.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,  # assumes hash is correct
        is_active=False,
        login_status=0,
        login_attempts=0,
        days_180_flag=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin-auth/login",
        json={"email": user.email, "password": config.default_password},
    )
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Login successful."
    assert "access_token" in body["data"]


@pytest.mark.asyncio
async def test_login_initial_login_prompt(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr002",
        username="initlogin",
        email="init@admin.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_active=False,
        login_status=-1,
        login_attempts=0,
        days_180_flag=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin-auth/login",
        json={"email": user.email, "password": config.default_password},
    )
    body = res.json()

    assert res.status_code == 201
    assert "Initial login" in body["message"]


@pytest.mark.asyncio
async def test_login_password_expired(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config
    expired_date = datetime.now(timezone.utc) - timedelta(days=181)

    user = AdminUser(
        user_id="usr003",
        username="expiredpass",
        email="expired@admin.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_active=False,
        login_status=0,
        days_180_flag=True,
        days_180_timestamp=expired_date,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin-auth/login",
        json={"email": user.email, "password": config.default_password},
    )
    body = res.json()

    assert res.status_code == 409
    assert "Password expired" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_login_account_not_found(test_client: AsyncClient, clean_db):
    res = await test_client.post(
        "/api/v1/admin-auth/login",
        json={"email": "nosuchuser@example.com", "password": "anyvalue"},
    )
    body = res.json()

    assert res.status_code == 404
    assert "Account not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_login_account_deactivated(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr004",
        username="deact",
        email="deact@admin.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_active=True,  # deactivated
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin-auth/login",
        json={"email": user.email, "password": config.default_password},
    )
    body = res.json()

    assert res.status_code == 404
    assert "deactivated" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_login_invalid_password(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr005",
        username="wrongpass",
        email="wrong@admin.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_active=False,
        login_status=0,
        login_attempts=0,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin-auth/login",
        json={"email": user.email, "password": "wrongpassword"},
    )
    body = res.json()

    assert res.status_code == 401
    assert "Invalid credentials" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_login_locked_after_3_attempts(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr006",
        username="lockeduser",
        email="locked@admin.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_active=False,
        login_status=0,
        login_attempts=2,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin-auth/login",
        json={"email": user.email, "password": "wrongagain"},
    )
    body = res.json()

    assert res.status_code == 423
    assert "Account locked" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_login_locked_within_24h(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr007",
        username="recentlock",
        email="recentlock@admin.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_active=False,
        login_status=1,
        login_attempts=3,
        last_login=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin-auth/login",
        json={"email": user.email, "password": config.default_password},
    )
    body = res.json()

    assert res.status_code == 423
    assert "temporarily locked" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_login_invalid_input_format(test_client: AsyncClient, clean_db):
    res = await test_client.post(
        "/api/v1/admin-auth/login",
        json={"email": "", "password": ""},  # Invalid format
    )

    assert res.status_code == 422  # FastAPI input validation
