import pytest
from httpx import AsyncClient
from sqlalchemy import select

from shared.db.models import AdminUser
from shared.core.security import generate_searchable_hash


@pytest.mark.asyncio
async def test_soft_delete_success(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    username = "softuser"
    email = "softuser@example.com"
    
    user = AdminUser(
        user_id="usr001",
        username_encrypted=username,
        email_encrypted=email,
        username_hash=generate_searchable_hash(username),
        email_hash=generate_searchable_hash(email),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,  # User is active
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.patch(
        f"/api/v1/admin/users/{user.user_id}/deactivate"
    )
    body = res.json()

    assert res.status_code == 200
    assert "soft-deleted successfully" in body["message"]

    await test_db_session.refresh(user)
    assert user.is_deleted is True  # User should be inactive (deleted) after soft delete


@pytest.mark.asyncio
async def test_soft_delete_user_not_found(test_client: AsyncClient, clean_db):
    res = await test_client.patch("/api/v1/admin/users/doesnt/deactivate")
    body = res.json()

    assert res.status_code == 404
    assert "User Account not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_soft_delete_already_inactive(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    username = "inactiveuser"
    email = "inactive@example.com"
    
    user = AdminUser(
        user_id="usr002",
        username_encrypted=username,
        email_encrypted=email,
        username_hash=generate_searchable_hash(username),
        email_hash=generate_searchable_hash(email),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=True,  # User is already inactive (deleted)
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.patch(
        f"/api/v1/admin/users/{user.user_id}/deactivate"
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

    username = "restoreuser"
    email = "restore@example.com"
    
    user = AdminUser(
        user_id="usr003",
        username_encrypted=username,
        email_encrypted=email,
        username_hash=generate_searchable_hash(username),
        email_hash=generate_searchable_hash(email),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=True,  # User is inactive (deleted) - ready to be restored
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.patch(f"/api/v1/admin/users/{user.user_id}/reactivate")
    body = res.json()

    assert res.status_code == 200
    assert "restored successfully" in body["message"]

    await test_db_session.refresh(user)
    assert user.is_deleted is False  # User should be active (not deleted) after restore


@pytest.mark.asyncio
async def test_restore_user_not_found(test_client: AsyncClient, clean_db):
    res = await test_client.patch("/api/v1/admin/users/unknown123/reactivate")
    body = res.json()

    assert res.status_code == 404
    assert "User Account not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_restore_user_already_active(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")
    config = seed_config

    username = "alreadyactive"
    email = "active@example.com"
    
    user = AdminUser(
        user_id="usr004",
        username_encrypted=username,
        email_encrypted=email,
        username_hash=generate_searchable_hash(username),
        email_hash=generate_searchable_hash(email),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,  # User is already active
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.patch(f"/api/v1/admin/users/{user.user_id}/reactivate")
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

    username = "deleteuser"
    email = "delete@example.com"
    
    user = AdminUser(
        user_id="usr005",
        username_encrypted=username,
        email_encrypted=email,
        username_hash=generate_searchable_hash(username),
        email_hash=generate_searchable_hash(email),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,  # User is active
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.delete(
        f"/api/v1/admin/users/{user.user_id}"
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
    res = await test_client.delete("/api/v1/admin/users/nouserid")
    body = res.json()

    assert res.status_code == 404
    assert "User Account not found" in body["detail"]["message"]
