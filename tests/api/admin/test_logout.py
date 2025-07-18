import pytest
from httpx import AsyncClient

from shared.db.models import AdminUser
from user_service.utils.auth import hash_password


@pytest.mark.asyncio
async def test_logout_success(
    test_client: AsyncClient, test_db_session, seed_roles, seed_config, clean_db
):
    # First create a user and login to get a real token
    role = await seed_roles("HR")
    config = seed_config

    user = AdminUser(
        user_id="usr999",
        username="logoutuser",
        email="logout@admin.com",
        role_id=role.role_id,
        password_hash=hash_password(config.default_password),
        login_status=1,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    # Login to get a real token
    login_response = await test_client.post(
        "/api/v1/admin/login",
        data={"username": user.email, "password": config.default_password},
    )
    login_body = login_response.json()
    access_token = login_body["access_token"]

    # Now test logout with the real token
    response = await test_client.post(
        "/api/v1/admin/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["message"] == "Logout successful."
    assert body["statusCode"] == 200
    assert "timestamp" in body
