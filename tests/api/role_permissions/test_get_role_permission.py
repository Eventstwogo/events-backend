import pytest
from httpx import AsyncClient

from shared.db.models import Permission, Role, RolePermission


@pytest.mark.asyncio
async def test_get_all_role_permissions_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    # First create the required roles and permissions
    roles = [
        Role(role_id="R001", role_name="Test Role 1", role_status=True),
        Role(role_id="R002", role_name="Test Role 2", role_status=True),
        Role(role_id="R003", role_name="Test Role 3", role_status=True),
    ]
    permissions = [
        Permission(
            permission_id="P001",
            permission_name="Test Permission 1",
            permission_status=True,
        ),
        Permission(
            permission_id="P002",
            permission_name="Test Permission 2",
            permission_status=True,
        ),
        Permission(
            permission_id="P003",
            permission_name="Test Permission 3",
            permission_status=True,
        ),
    ]
    test_db_session.add_all(roles + permissions)
    await test_db_session.commit()

    # Now create role-permissions with valid foreign keys
    seed_data = [
        RolePermission(
            id=1, role_id="R001", permission_id="P001", rp_status=True
        ),
        RolePermission(
            id=2, role_id="R002", permission_id="P002", rp_status=False
        ),
        RolePermission(
            id=3, role_id="R003", permission_id="P003", rp_status=True
        ),
    ]
    test_db_session.add_all(seed_data)
    await test_db_session.commit()

    # Test all active records
    res = await test_client.get("/api/v1/role-permissions/?is_active=true")
    assert res.status_code == 200
    body = res.json()
    assert body["message"] == "Role-permissions retrieved successfully."
    assert isinstance(body["data"], list)
    assert all(item["rp_status"] is True for item in body["data"])

    # Test all inactive records
    res = await test_client.get("/api/v1/role-permissions/?is_active=false")
    assert res.status_code == 200
    body = res.json()
    assert all(item["rp_status"] is False for item in body["data"])


@pytest.mark.asyncio
async def test_get_all_role_permissions_empty(
    test_client: AsyncClient, test_db_session, clean_db
):
    # No data inserted
    res = await test_client.get("/api/v1/role-permissions/?is_active=true")
    assert res.status_code == 404
    response_data = res.json()
    # The API returns error details in the 'detail' key for 404 errors
    detail = response_data.get("detail", {})
    message = detail.get("message", "").lower()
    assert "no role-permissions found" in message


@pytest.mark.asyncio
async def test_get_all_role_permissions_all_status(
    test_client: AsyncClient, test_db_session, clean_db
):
    # First create the required roles and permissions
    roles = [
        Role(role_id="R010", role_name="Test Role 10", role_status=True),
        Role(role_id="R011", role_name="Test Role 11", role_status=True),
    ]
    permissions = [
        Permission(
            permission_id="P010",
            permission_name="Test Permission 10",
            permission_status=True,
        ),
        Permission(
            permission_id="P011",
            permission_name="Test Permission 11",
            permission_status=True,
        ),
    ]
    test_db_session.add_all(roles + permissions)
    await test_db_session.commit()

    # Insert some role-permission records
    test_db_session.add_all(
        [
            RolePermission(
                id=4, role_id="R010", permission_id="P010", rp_status=True
            ),
            RolePermission(
                id=5, role_id="R011", permission_id="P011", rp_status=False
            ),
        ]
    )
    await test_db_session.commit()

    # No query param: should return all
    res = await test_client.get("/api/v1/role-permissions/")
    assert res.status_code == 200
    body = res.json()
    assert len(body["data"]) >= 2
