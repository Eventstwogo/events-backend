import pytest
from httpx import AsyncClient

from shared.db.models import Permission, Role, RolePermission


@pytest.mark.asyncio
async def test_update_role_permission_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    # First create the required roles and permissions (max 6 chars for IDs)
    old_role = Role(role_id="OLDR01", role_name="Old Role", role_status=True)
    old_perm = Permission(
        permission_id="OLDP01",
        permission_name="Old Permission",
        permission_status=True,
    )
    new_role = Role(role_id="NEWR01", role_name="New Role", role_status=True)
    new_perm = Permission(
        permission_id="NEWP01",
        permission_name="New Permission",
        permission_status=True,
    )

    test_db_session.add_all([old_role, old_perm, new_role, new_perm])
    await test_db_session.commit()

    # Now create the role-permission with valid foreign keys
    rp = RolePermission(
        id=200, role_id="OLDR01", permission_id="OLDP01", rp_status=True
    )
    test_db_session.add(rp)
    await test_db_session.commit()

    update_payload = {
        "id": 200,  # The schema requires this field
        "role_id": "NEWR01",
        "permission_id": "NEWP01",
    }

    res = await test_client.put(
        f"/api/v1/role-permissions/{rp.id}", json=update_payload
    )
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Role-permission updated successfully."
    assert body["data"]["id"] == 200
    assert body["data"]["role_id"] == "NEWR01"
    assert body["data"]["permission_id"] == "NEWP01"


@pytest.mark.asyncio
async def test_update_role_permission_not_found(
    test_client: AsyncClient, clean_db
):
    update_payload = {
        "id": 9999,  # The schema requires this field
        "role_id": "ANYR01",
        "permission_id": "ANYP01",
    }

    res = await test_client.put(
        "/api/v1/role-permissions/9999", json=update_payload
    )

    assert res.status_code == 404
    response_data = res.json()
    # The API returns error details in the 'detail' key for 404 errors
    detail = response_data.get("detail", {})
    message = detail.get("message", "").lower()
    assert "not found" in message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_payload,expected_status",
    [
        ({}, 422),  # Empty body - missing required fields
        ({"id": 201}, 422),  # Missing role_id and permission_id
        (
            {"id": 201, "role_id": None, "permission_id": "INITP1"},
            422,
        ),  # None value for role_id
    ],
)
async def test_update_role_permission_invalid_payload(
    test_client: AsyncClient,
    test_db_session,
    clean_db,
    invalid_payload,
    expected_status,
):
    # First create the required role and permission (max 6 chars for IDs)
    init_role = Role(role_id="INITR1", role_name="Init Role", role_status=True)
    init_perm = Permission(
        permission_id="INITP1",
        permission_name="Init Permission",
        permission_status=True,
    )
    test_db_session.add_all([init_role, init_perm])
    await test_db_session.commit()

    # Add dummy RP to hit the route
    rp = RolePermission(
        id=201, role_id="INITR1", permission_id="INITP1", rp_status=True
    )
    test_db_session.add(rp)
    await test_db_session.commit()

    res = await test_client.put(
        f"/api/v1/role-permissions/{rp.id}", json=invalid_payload
    )

    # Pydantic validation should trigger 422 for invalid payloads
    assert res.status_code == expected_status

    # Rollback the session to clean up after any potential errors
    try:
        await test_db_session.rollback()
    except Exception as e:
        # Session might already be rolled back, log for debugging if needed
        print(f"Session rollback failed (expected): {e}")
