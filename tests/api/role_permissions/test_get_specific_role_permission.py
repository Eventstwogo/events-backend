import pytest
from httpx import AsyncClient

from shared.db.models import Permission, Role, RolePermission


@pytest.mark.asyncio
async def test_get_specific_role_permission_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    # First create the required role and permission
    role = Role(role_id="R101", role_name="Test Role 101", role_status=True)
    permission = Permission(
        permission_id="P101",
        permission_name="Test Permission 101",
        permission_status=True,
    )
    test_db_session.add_all([role, permission])
    await test_db_session.commit()

    # Now create the role-permission with valid foreign keys
    rp = RolePermission(
        id=101, role_id="R101", permission_id="P101", rp_status=True
    )
    test_db_session.add(rp)
    await test_db_session.commit()

    res = await test_client.get(f"/api/v1/role-permissions/{rp.id}")
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Role-permission retrieved successfully."
    assert body["data"]["id"] == 101
    assert body["data"]["role_id"] == "R101"
    assert body["data"]["permission_id"] == "P101"
    assert body["data"]["rp_status"] is True


@pytest.mark.asyncio
async def test_get_specific_role_permission_not_found(
    test_client: AsyncClient, clean_db
):
    res = await test_client.get("/api/v1/role-permissions/9999")

    assert res.status_code == 404
    response_data = res.json()
    # The API returns error details in the 'detail' key for 404 errors
    detail = response_data.get("detail", {})
    message = detail.get("message", "").lower()
    assert "not found" in message
