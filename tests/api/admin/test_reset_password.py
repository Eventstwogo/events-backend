import os

import pytest
from httpx import AsyncClient

from shared.db.models import AdminUser
from user_service.utils.auth import hash_password

TEST_OLD_PASSWORD = os.getenv("TEST_OLD_PASSWORD", "OldPass@123")
TEST_NEW_PASSWORD = os.getenv("TEST_NEW_PASSWORD", "NewPass@456")
SAME_OLD_PASSWORD = os.getenv("SAME_OLD_PASSWORD", "SamePass@123")


@pytest.mark.asyncio
async def test_reset_password_success(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")

    old_password = TEST_OLD_PASSWORD
    new_password = TEST_NEW_PASSWORD

    user = AdminUser(
        user_id="usr101",
        username="resetuser",
        email="reset@admin.com",
        role_id=role.role_id,
        password_hash=hash_password(old_password),
        login_status=1,
    )
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)

    res = await test_client.patch(
        "/api/v1/admin-auth/reset-password",
        json={"email": user.email, "new_password": new_password},
    )
    body = res.json()

    assert res.status_code == 200
    assert "reset successfully" in body["message"]

    await test_db_session.refresh(user)
    assert user.login_status == 0
    assert user.password_hash != hash_password(old_password)


@pytest.mark.asyncio
async def test_reset_password_user_not_found(
    test_client: AsyncClient, clean_db
):
    res = await test_client.patch(
        "/api/v1/admin-auth/reset-password",
        json={"email": "nonexistent@admin.com", "new_password": "SomePass@123"},
    )
    body = res.json()

    assert res.status_code == 404
    assert "User Account not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_reset_password_same_as_old(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    role = await seed_roles("HR")

    user = AdminUser(
        user_id="usr102",
        username="samepass",
        email="same@admin.com",
        role_id=role.role_id,
        password_hash=hash_password(SAME_OLD_PASSWORD),
        login_status=1,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    res = await test_client.patch(
        "/api/v1/admin-auth/reset-password",
        json={"email": user.email, "new_password": SAME_OLD_PASSWORD},
    )
    body = res.json()

    assert res.status_code == 409
    assert "same as old password" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_reset_password_invalid_payload(
    test_client: AsyncClient, clean_db
):
    # Missing fields
    res = await test_client.patch("/api/v1/admin-auth/reset-password", json={})
    assert res.status_code == 422

    # Empty email
    res2 = await test_client.patch(
        "/api/v1/admin-auth/reset-password",
        json={"email": "", "new_password": "Valid@Pass123"},
    )
    assert res2.status_code == 422

    # Empty password
    res3 = await test_client.patch(
        "/api/v1/admin-auth/reset-password",
        json={"email": "valid@admin.com", "new_password": ""},
    )
    assert res3.status_code == 422
