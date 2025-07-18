import pytest
from httpx import AsyncClient
from sqlalchemy import select

from shared.db.models import Role  # adjust import path based on your structure


@pytest.mark.asyncio
async def test_create_new_role_success(
    test_client: AsyncClient, clean_db, test_db_session
):
    """Test successful creation of a new role."""
    payload = {"role_name": "Event Manager"}

    res = await test_client.post("/api/v1/roles/", json=payload)
    body = res.json()

    assert res.status_code == 201
    assert body["message"] == "Role created successfully."
    assert "role_id" in body["data"]
    assert len(body["data"]["role_id"]) == 6

    # Check DB state
    stmt = select(Role).where(Role.role_name == "EVENT MANAGER")
    result = await test_db_session.execute(stmt)
    role = result.scalar_one_or_none()
    assert role is not None
    assert role.role_status is False


@pytest.mark.asyncio
async def test_duplicate_active_role_conflict(
    test_client: AsyncClient, clean_db, test_db_session
):
    """Test conflict if the same active role already exists."""
    role = Role(role_id="abc123", role_name="DEVELOPER", role_status=False)
    test_db_session.add(role)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/roles/", json={"role_name": "Developer"}
    )
    body = res.json()

    assert res.status_code == 409
    assert "already exists" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_reactivate_soft_deleted_role(
    test_client: AsyncClient, clean_db, test_db_session
):
    """Test reactivation of a soft-deleted role."""
    role = Role(role_id="abc123", role_name="AUDITOR", role_status=True)
    test_db_session.add(role)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/roles/", json={"role_name": "Auditor"}
    )
    body = res.json()

    assert res.status_code == 200
    assert "reactivated" in body["message"]
    assert body["data"]["role_id"] == "abc123"

    # Ensure role_status is now False
    await test_db_session.refresh(role)
    assert role.role_status is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_name",
    [
        "",  # empty
        "ab",  # too short
        "a" * 51,  # too long
        "Invalid@Role!",  # special characters
    ],
)
async def test_invalid_role_name(test_client: AsyncClient, invalid_name):
    """Test role creation validation errors."""
    res = await test_client.post(
        "/api/v1/roles/", json={"role_name": invalid_name}
    )
    assert res.status_code == 422
    assert "detail" in res.json()


@pytest.mark.asyncio
async def test_missing_role_name(test_client: AsyncClient):
    """Test when 'role_name' is missing from payload."""
    res = await test_client.post("/api/v1/roles/", json={})
    assert res.status_code == 422
    assert any(err["loc"][-1] == "role_name" for err in res.json()["detail"])
