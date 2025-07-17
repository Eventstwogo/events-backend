import pytest
from httpx import AsyncClient
from sqlalchemy import insert

from db.models import Role  # Adjust path if different


@pytest.mark.asyncio
async def test_get_all_roles(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test fetching all roles regardless of status."""
    # Insert test roles
    roles = [
        {"role_id": "r001", "role_name": "ADMIN", "role_status": False},
        {"role_id": "r002", "role_name": "MODERATOR", "role_status": True},
        {"role_id": "r003", "role_name": "VIEWER", "role_status": False},
    ]
    await test_db_session.execute(insert(Role), roles)
    await test_db_session.commit()

    res = await test_client.get("/api/v1/roles/")
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Roles retrieved successfully."
    assert len(body["data"]) == 3
    assert any(role["role_name"] == "ADMIN" for role in body["data"])


@pytest.mark.asyncio
async def test_get_only_active_roles(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test fetching only active roles (role_status=True)."""
    roles = [
        {"role_id": "r101", "role_name": "MANAGER", "role_status": True},
        {"role_id": "r102", "role_name": "HELPDESK", "role_status": False},
    ]
    await test_db_session.execute(insert(Role), roles)
    await test_db_session.commit()

    res = await test_client.get("/api/v1/roles/?is_active=true")
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Roles retrieved successfully."
    assert len(body["data"]) == 1
    assert body["data"][0]["role_name"] == "MANAGER"
    assert body["data"][0]["role_status"] is True


@pytest.mark.asyncio
async def test_get_only_inactive_roles(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test fetching only inactive roles (role_status=False)."""
    roles = [
        {"role_id": "r201", "role_name": "ANALYST", "role_status": False},
        {"role_id": "r202", "role_name": "COORDINATOR", "role_status": True},
    ]
    await test_db_session.execute(insert(Role), roles)
    await test_db_session.commit()

    res = await test_client.get("/api/v1/roles/?is_active=false")
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Roles retrieved successfully."
    assert len(body["data"]) == 1
    assert body["data"][0]["role_name"] == "ANALYST"
    assert body["data"][0]["role_status"] is False


@pytest.mark.asyncio
async def test_get_roles_not_found(test_client: AsyncClient, clean_db):
    """Test when no roles exist at all."""
    res = await test_client.get("/api/v1/roles/")
    body = res.json()

    assert res.status_code == 404
    assert "No roles found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_get_roles_not_found_with_filter(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test when roles exist, but no match for given filter."""
    # Insert only active roles
    roles = [
        {"role_id": "r301", "role_name": "LEAD", "role_status": True},
    ]
    await test_db_session.execute(insert(Role), roles)
    await test_db_session.commit()

    # Try to fetch inactive
    res = await test_client.get("/api/v1/roles/?is_active=false")
    body = res.json()

    assert res.status_code == 404
    assert "No roles found" in body["detail"]["message"]
