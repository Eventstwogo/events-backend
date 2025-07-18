import pytest
from httpx import AsyncClient

from shared.db.models import Permission, Role, RolePermission


@pytest.mark.asyncio
async def test_update_role_permission_status_active(
    test_client: AsyncClient, test_db_session, clean_db
):
    # First create the required role and permission (max 6 chars for IDs)
    role = Role(role_id="TESTR1", role_name="Test Role", role_status=True)
    permission = Permission(
        permission_id="TESTP1",
        permission_name="Test Permission",
        permission_status=True,
    )
    test_db_session.add_all([role, permission])
    await test_db_session.commit()

    # Setup a role-permission with inactive status
    rp = RolePermission(
        id=300, role_id="TESTR1", permission_id="TESTP1", rp_status=False
    )
    test_db_session.add(rp)
    await test_db_session.commit()

    res = await test_client.patch(
        f"/api/v1/role-permissions/{rp.id}/status?role_perm_status=true"
    )
    body = res.json()

    assert res.status_code == 200
    assert "status updated" in body["message"].lower()
    assert body["data"]["id"] == rp.id
    assert body["data"]["rp_status"] is True


@pytest.mark.asyncio
async def test_update_role_permission_status_inactive(
    test_client: AsyncClient, test_db_session, clean_db
):
    # First create the required role and permission (max 6 chars for IDs)
    role = Role(role_id="TESTR2", role_name="Test Role 2", role_status=True)
    permission = Permission(
        permission_id="TESTP2",
        permission_name="Test Permission 2",
        permission_status=True,
    )
    test_db_session.add_all([role, permission])
    await test_db_session.commit()

    # Setup a role-permission with active status
    rp = RolePermission(
        id=301, role_id="TESTR2", permission_id="TESTP2", rp_status=True
    )
    test_db_session.add(rp)
    await test_db_session.commit()

    res = await test_client.patch(
        f"/api/v1/role-permissions/{rp.id}/status?role_perm_status=false"
    )
    body = res.json()

    assert res.status_code == 200
    assert "status updated" in body["message"].lower()
    assert body["data"]["rp_status"] is False


@pytest.mark.asyncio
async def test_update_role_permission_status_not_found(
    test_client: AsyncClient, clean_db
):
    res = await test_client.patch(
        "/api/v1/role-permissions/9999/status?role_perm_status=true"
    )

    assert res.status_code == 404
    response_data = res.json()
    # The API returns error details in the 'detail' key for 404 errors
    detail = response_data.get("detail", {})
    message = detail.get("message", "").lower()
    assert "not found" in message
