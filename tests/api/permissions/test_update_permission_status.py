import pytest
from httpx import AsyncClient

from db.models import Permission


@pytest.mark.asyncio
async def test_update_permission_status_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    # Setup: Create permission
    permission = Permission(
        permission_id="PRM201",
        permission_name="TogglePermission",
        permission_status=False,
    )
    test_db_session.add(permission)
    await test_db_session.commit()

    # Change status to True (soft-deleted / inactive)
    res = await test_client.patch(
        "/api/v1/permissions/PRM201/status?perm_status=true"
    )
    body = res.json()

    assert res.status_code == 200
    assert "status updated to inactive" in body["message"].lower()
    assert body["data"]["permission_status"] is True

    # Change status back to False (active)
    res = await test_client.patch(
        "/api/v1/permissions/PRM201/status?perm_status=false"
    )
    body = res.json()

    assert res.status_code == 200
    assert "status updated to active" in body["message"].lower()
    assert body["data"]["permission_status"] is False


@pytest.mark.asyncio
async def test_update_permission_status_not_found(
    test_client: AsyncClient, clean_db
):
    res = await test_client.patch(
        "/api/v1/permissions/UNKNOWN/status?perm_status=true"
    )
    body = res.json()

    assert res.status_code == 404
    assert "detail" in body
    assert "permission not found" in body["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_update_permission_status_invalid_query_param(
    test_client: AsyncClient, clean_db
):
    # Missing `perm_status` query param
    res = await test_client.patch("/api/v1/permissions/PRM999/status")
    assert res.status_code == 422  # validation error
    assert "detail" in res.json()
