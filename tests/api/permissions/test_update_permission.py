import pytest
from httpx import AsyncClient

from db.models import Permission


@pytest.mark.asyncio
async def test_update_permission_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    # Create initial permission
    permission = Permission(
        permission_id="PRM101",
        permission_name="INITIAL PERMISSION",
        permission_status=False,
    )
    test_db_session.add(permission)
    await test_db_session.commit()

    # Update name - using a valid name that won't trigger SQL injection detection
    payload = {"permission_name": "Modified Permission"}
    res = await test_client.put("/api/v1/permissions/PRM101", json=payload)
    body = res.json()

    assert res.status_code == 200
    assert body["message"].lower() == "permission updated successfully."
    assert (
        body["data"]["permission_name"] == "MODIFIED PERMISSION"
    )  # Schema converts to uppercase

    # Check database
    await test_db_session.refresh(permission)
    assert permission.permission_name == "MODIFIED PERMISSION"


@pytest.mark.asyncio
async def test_update_permission_not_found(test_client: AsyncClient, clean_db):
    payload = {"permission_name": "Any Permission"}
    res = await test_client.put("/api/v1/permissions/UNKNOWN123", json=payload)
    body = res.json()

    assert res.status_code == 404
    # For 404 errors, the response structure includes a 'detail' key with the error info
    assert "detail" in body
    assert body["detail"]["message"].lower() == "permission not found."


@pytest.mark.asyncio
async def test_update_permission_empty_payload(
    test_client: AsyncClient, test_db_session, clean_db
):
    # Create a permission for test
    permission = Permission(
        permission_id="PRM102",
        permission_name="BEFORE EMPTY",
        permission_status=False,
    )
    test_db_session.add(permission)
    await test_db_session.commit()

    res = await test_client.put("/api/v1/permissions/PRM102", json={})
    body = res.json()

    assert res.status_code == 200
    assert body["data"]["permission_name"] == "BEFORE EMPTY"  # unchanged
