import pytest
from httpx import AsyncClient

from db.models import Permission, Role, RolePermission


@pytest.mark.asyncio
async def test_soft_delete_role_permission(
    test_client: AsyncClient, test_db_session, clean_db
):
    # First create the required role and permission (max 6 chars for IDs)
    role = Role(role_id="ROL401", role_name="Role 401", role_status=True)
    permission = Permission(
        permission_id="PRM401",
        permission_name="Permission 401",
        permission_status=True,
    )
    test_db_session.add_all([role, permission])
    await test_db_session.commit()

    # Create role-permission with valid foreign keys
    rp = RolePermission(
        id=401, role_id="ROL401", permission_id="PRM401", rp_status=False
    )
    test_db_session.add(rp)
    await test_db_session.commit()

    res = await test_client.delete(f"/api/v1/role-permissions/{rp.id}")
    body = res.json()

    assert res.status_code == 200
    assert "soft-deleted" in body["message"].lower()

    await test_db_session.refresh(rp)
    assert rp.rp_status is True


@pytest.mark.asyncio
async def test_soft_delete_already_soft_deleted(
    test_client: AsyncClient, test_db_session, clean_db
):
    # First create the required role and permission (max 6 chars for IDs)
    role = Role(role_id="ROL402", role_name="Role 402", role_status=True)
    permission = Permission(
        permission_id="PRM402",
        permission_name="Permission 402",
        permission_status=True,
    )
    test_db_session.add_all([role, permission])
    await test_db_session.commit()

    # Create role-permission with valid foreign keys (already soft-deleted)
    rp = RolePermission(
        id=402, role_id="ROL402", permission_id="PRM402", rp_status=True
    )
    test_db_session.add(rp)
    await test_db_session.commit()

    res = await test_client.delete(f"/api/v1/role-permissions/{rp.id}")

    assert res.status_code == 400
    response_data = res.json()
    # The API returns error details in the 'detail' key for 400 errors
    detail = response_data.get("detail", {})
    message = detail.get("message", "").lower()
    assert "already soft-deleted" in message


@pytest.mark.asyncio
async def test_hard_delete_role_permission(
    test_client: AsyncClient, test_db_session, clean_db
):
    # First create the required role and permission (max 6 chars for IDs)
    role = Role(role_id="ROL403", role_name="Role 403", role_status=True)
    permission = Permission(
        permission_id="PRM403",
        permission_name="Permission 403",
        permission_status=True,
    )
    test_db_session.add_all([role, permission])
    await test_db_session.commit()

    # Create role-permission with valid foreign keys
    rp = RolePermission(
        id=403, role_id="ROL403", permission_id="PRM403", rp_status=False
    )
    test_db_session.add(rp)
    await test_db_session.commit()

    res = await test_client.delete(
        f"/api/v1/role-permissions/{rp.id}?hard_delete=true"
    )
    body = res.json()

    assert res.status_code == 200
    assert "permanently deleted" in body["message"].lower()

    rp_check = await test_db_session.get(RolePermission, rp.id)
    assert rp_check is None


@pytest.mark.asyncio
async def test_hard_delete_already_soft_deleted(
    test_client: AsyncClient, test_db_session, clean_db
):
    # First create the required role and permission (max 6 chars for IDs)
    role = Role(role_id="ROL404", role_name="Role 404", role_status=True)
    permission = Permission(
        permission_id="PRM404",
        permission_name="Permission 404",
        permission_status=True,
    )
    test_db_session.add_all([role, permission])
    await test_db_session.commit()

    # Create role-permission with valid foreign keys (already soft-deleted)
    rp = RolePermission(
        id=404, role_id="ROL404", permission_id="PRM404", rp_status=True
    )
    test_db_session.add(rp)
    await test_db_session.commit()

    res = await test_client.delete(
        f"/api/v1/role-permissions/{rp.id}?hard_delete=true"
    )
    body = res.json()

    assert res.status_code == 200
    assert "permanently deleted" in body["message"].lower()

    rp_check = await test_db_session.get(RolePermission, rp.id)
    assert rp_check is None


@pytest.mark.asyncio
async def test_delete_nonexistent_role_permission(
    test_client: AsyncClient, clean_db
):
    res = await test_client.delete("/api/v1/role-permissions/99999")

    assert res.status_code == 404
    response_data = res.json()
    # The API returns error details in the 'detail' key for 404 errors
    detail = response_data.get("detail", {})
    message = detail.get("message", "").lower()
    assert "not found" in message
