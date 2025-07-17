import pytest
from httpx import AsyncClient
from sqlalchemy import select

from db.models import AdminUser


@pytest.mark.asyncio
async def test_soft_delete_success(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr001",
        username="softuser",
        email="softuser@example.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_active=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.patch(
        f"/api/v1/admin-users/soft-delete/{user.user_id}"
    )
    body = res.json()

    assert res.status_code == 200
    assert "soft-deleted successfully" in body["message"]

    await test_db_session.refresh(user)
    assert user.is_active is True  # User should be inactive after soft delete


@pytest.mark.asyncio
async def test_soft_delete_user_not_found(test_client: AsyncClient, clean_db):
    res = await test_client.patch("/api/v1/admin-users/soft-delete/doesnt")
    body = res.json()

    assert res.status_code == 404
    assert "User not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_soft_delete_already_inactive(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr002",
        username="inactiveuser",
        email="inactive@example.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_active=True,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.patch(
        f"/api/v1/admin-users/soft-delete/{user.user_id}"
    )
    body = res.json()

    assert res.status_code == 400
    assert "already deactivated" in body["detail"]["message"]


# ------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_restore_success(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr003",
        username="restoreuser",
        email="restore@example.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_active=True,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.patch(f"/api/v1/admin-users/restore/{user.user_id}")
    body = res.json()

    assert res.status_code == 200
    assert "restored successfully" in body["message"]

    await test_db_session.refresh(user)
    assert user.is_active is False  # User should be active after restore


@pytest.mark.asyncio
async def test_restore_user_not_found(test_client: AsyncClient, clean_db):
    res = await test_client.patch("/api/v1/admin-users/restore/unknown123")
    body = res.json()

    assert res.status_code == 404
    assert "User not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_restore_user_already_active(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr004",
        username="alreadyactive",
        email="active@example.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_active=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.patch(f"/api/v1/admin-users/restore/{user.user_id}")
    body = res.json()

    assert res.status_code == 400
    assert "already active" in body["detail"]["message"]


# ------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hard_delete_success(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr005",
        username="deleteuser",
        email="delete@example.com",
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_active=True,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.delete(
        f"/api/v1/admin-users/hard-delete/{user.user_id}"
    )
    body = res.json()

    assert res.status_code == 200
    assert "permanently deleted" in body["message"]

    result = await test_db_session.execute(
        select(AdminUser).where(AdminUser.user_id == user.user_id)
    )
    deleted_user = result.scalar_one_or_none()
    assert deleted_user is None


@pytest.mark.asyncio
async def test_hard_delete_user_not_found(test_client: AsyncClient, clean_db):
    res = await test_client.delete("/api/v1/admin-users/hard-delete/nouserid")
    body = res.json()

    assert res.status_code == 404
    assert "User not found" in body["detail"]["message"]
