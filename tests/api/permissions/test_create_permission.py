from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from shared.db.models import Permission


@pytest.mark.asyncio
async def test_create_new_permission(
    test_client: AsyncClient, test_db_session, clean_db
):
    payload = {"permission_name": "View Dashboard"}

    response = await test_client.post("/api/v1/permissions/", json=payload)
    body = response.json()

    assert response.status_code == 201
    assert body["message"] == "Permission created successfully."
    assert "permission_id" in body["data"]
    assert len(body["data"]["permission_id"]) == 6

    # Verify in DB
    result = await test_db_session.execute(
        select(Permission).where(Permission.permission_name == "VIEW DASHBOARD")
    )
    permission = result.scalar_one_or_none()
    assert permission is not None
    assert permission.permission_status is False


@pytest.mark.asyncio
async def test_duplicate_permission_conflict(
    test_client: AsyncClient, test_db_session, clean_db
):
    # Add an existing active permission
    perm = Permission(
        permission_id="abc001",
        permission_name="MANAGE USERS",  # Store in uppercase to match schema behavior
        permission_status=False,
    )
    test_db_session.add(perm)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/permissions/", json={"permission_name": "Manage Users"}
    )
    body = res.json()

    assert res.status_code == 409
    assert "already exists" in body["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_reactivate_soft_deleted_permission(
    test_client: AsyncClient, test_db_session, clean_db
):
    perm = Permission(
        permission_id="abc002",
        permission_name="EDIT SETTINGS",  # Store in uppercase to match schema behavior
        permission_status=True,  # Soft-deleted
        permission_tstamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
    )
    test_db_session.add(perm)
    await test_db_session.commit()

    res = await test_client.post(
        "/api/v1/permissions/", json={"permission_name": "Edit Settings"}
    )
    body = res.json()

    assert res.status_code == 200
    assert "reactivated" in body["message"].lower()
    assert body["data"]["permission_id"] == "abc002"

    await test_db_session.refresh(perm)
    assert perm.permission_status is False
    assert perm.permission_tstamp > datetime(2023, 1, 1, tzinfo=timezone.utc)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_name", ["", "a", "@" * 101])
async def test_invalid_permission_name(test_client: AsyncClient, invalid_name):
    res = await test_client.post(
        "/api/v1/permissions/", json={"permission_name": invalid_name}
    )
    assert res.status_code == 422
    assert "detail" in res.json()


@pytest.mark.asyncio
async def test_missing_permission_name_field(test_client: AsyncClient):
    res = await test_client.post("/api/v1/permissions/", json={})
    body = res.json()

    assert res.status_code == 422
    assert any(err["loc"][-1] == "permission_name" for err in body["detail"])
