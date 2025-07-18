import pytest
from httpx import AsyncClient
from sqlalchemy import insert

from shared.db.models import Role  # Adjust path if needed


@pytest.mark.asyncio
async def test_find_role_by_exact_name(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test finding a role using the exact name (case-insensitive)."""
    role = {"role_id": "r001", "role_name": "Team Lead", "role_status": False}
    await test_db_session.execute(insert(Role).values(role))
    await test_db_session.commit()

    res = await test_client.get(
        "/api/v1/roles/search", params={"role_name": "Team Lead"}
    )
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Role found successfully."
    assert body["data"]["role_id"] == "r001"


@pytest.mark.asyncio
async def test_find_role_case_insensitive(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test role lookup works regardless of case."""
    role = {
        "role_id": "r002",
        "role_name": "Administrator",
        "role_status": False,
    }
    await test_db_session.execute(insert(Role).values(role))
    await test_db_session.commit()

    # Try with lowercase input
    res = await test_client.get(
        "/api/v1/roles/search", params={"role_name": "administrator"}
    )
    body = res.json()

    assert res.status_code == 200
    assert body["data"]["role_id"] == "r002"


@pytest.mark.asyncio
async def test_find_role_not_found(test_client: AsyncClient, clean_db):
    """Test 404 response when role name does not exist."""
    res = await test_client.get(
        "/api/v1/roles/search", params={"role_name": "Ghost Role"}
    )
    body = res.json()

    assert res.status_code == 404
    assert "not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_find_role_missing_param(test_client: AsyncClient):
    """Test validation error if role_name is not provided."""
    res = await test_client.get("/api/v1/roles/search")  # No query param
    body = res.json()

    assert res.status_code == 422
    assert any(err["loc"][-1] == "role_name" for err in body["detail"])
