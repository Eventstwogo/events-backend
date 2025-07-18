from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from shared.core.security import generate_searchable_hash
from shared.db.models import AdminUser


@pytest.mark.asyncio
async def test_login_success(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    username = "loguser"
    email = "log@admin.com"

    user = AdminUser(
        user_id="usr001",
        username_encrypted=username,
        email_encrypted=email,
        username_hash=generate_searchable_hash(username),
        email_hash=generate_searchable_hash(email),
        role_id=role.role_id,
        password_hash=config.default_password_hash,  # assumes hash is correct
        is_deleted=False,
        login_status=0,
        failure_login_attempts=0,
        days_180_flag=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin/login",
        data={"username": user.email, "password": config.default_password},
    )
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Login successful."
    assert "access_token" in body


@pytest.mark.asyncio
async def test_login_initial_login_prompt(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    username = "initlogin"
    email = "init@admin.com"

    user = AdminUser(
        user_id="usr002",
        username_encrypted=username,
        email_encrypted=email,
        username_hash=generate_searchable_hash(username),
        email_hash=generate_searchable_hash(email),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_deleted=False,
        login_status=-1,
        failure_login_attempts=0,
        days_180_flag=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin/login",
        data={"username": user.email, "password": config.default_password},
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

    username = "expiredpass"
    email = "expired@admin.com"

    user = AdminUser(
        user_id="usr003",
        username_encrypted=username,
        email_encrypted=email,
        username_hash=generate_searchable_hash(username),
        email_hash=generate_searchable_hash(email),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_deleted=False,
        login_status=0,
        days_180_flag=True,
        days_180_timestamp=expired_date,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin/login",
        data={"username": user.email, "password": config.default_password},
    )
    body = res.json()

    assert res.status_code == 409
    assert "Password expired" in body["message"]


@pytest.mark.asyncio
async def test_login_account_not_found(test_client: AsyncClient, clean_db):
    res = await test_client.post(
        "/api/v1/admin/login",
        data={"username": "nosuchuser@example.com", "password": "anyvalue"},
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

    username = "deact"
    email = "deact@admin.com"

    user = AdminUser(
        user_id="usr004",
        username_encrypted=username,
        email_encrypted=email,
        username_hash=generate_searchable_hash(username),
        email_hash=generate_searchable_hash(email),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_deleted=True,  # deactivated
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin/login",
        data={"username": email, "password": config.default_password},
    )
    body = res.json()

    assert res.status_code == 403
    assert "inactive" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_login_invalid_password(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    username = "wrongpass"
    email = "wrong@admin.com"

    user = AdminUser(
        user_id="usr005",
        username_encrypted=username,
        email_encrypted=email,
        username_hash=generate_searchable_hash(username),
        email_hash=generate_searchable_hash(email),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_deleted=False,
        login_status=0,
        failure_login_attempts=0,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin/login",
        data={"username": email, "password": "wrongpassword"},
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
        username_encrypted="lockeduser",
        email_encrypted="locked@admin.com",
        username_hash=generate_searchable_hash("lockeduser"),
        email_hash=generate_searchable_hash("locked@admin.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_deleted=False,
        login_status=0,
        failure_login_attempts=2,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin/login",
        data={"username": user.email, "password": "wrongagain"},
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
        username_encrypted="recentlock",
        email_encrypted="recentlock@admin.com",
        username_hash=generate_searchable_hash("recentlock"),
        email_hash=generate_searchable_hash("recentlock@admin.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        is_deleted=False,
        login_status=1,
        failure_login_attempts=3,
        last_login=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/admin/login",
        data={"username": user.email, "password": config.default_password},
    )
    body = res.json()

    assert res.status_code == 423
    assert "temporarily locked" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_login_invalid_input_format(test_client: AsyncClient, clean_db):
    res = await test_client.post(
        "/api/v1/admin/login",
        data={"username": "", "password": ""},  # Invalid format
    )

    assert res.status_code == 404  # Empty username treated as user not found
