import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_logout_success(test_client: AsyncClient):
    # Simulate existing login cookie (optional, depends on implementation)
    cookies = {"access_token": "testtoken123"}

    response = await test_client.post(
        "/api/v1/admin-auth/logout", cookies=cookies
    )
    body = response.json()

    assert response.status_code == 200
    assert body["message"] == "Logout successful."
    assert body["statusCode"] == 200
    assert "timestamp" in body
