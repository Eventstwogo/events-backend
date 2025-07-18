from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from shared.db.models import Permission, Role, RolePermission


@pytest.mark.asyncio
async def test_create_role_permission_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    role = Role(role_id="ROL001", role_name="Test Role", role_status=False)
    permission = Permission(
        permission_id="PRM001",
        permission_name="Test Permission",
        permission_status=True,
    )
    test_db_session.add_all([role, permission])
    await test_db_session.commit()

    payload = {"role_id": "ROL001", "permission_id": "PRM001"}
    res = await test_client.post("/api/v1/role-permissions/", json=payload)
    body = res.json()

    assert res.status_code == 201
    assert body["message"] == "Role-permission created successfully."
    assert "id" in body["data"]

    result = await test_db_session.execute(
        select(RolePermission).where(
            RolePermission.role_id == "ROL001",
            RolePermission.permission_id == "PRM001",
        )
    )
    mapping = result.scalar_one_or_none()
    assert mapping is not None
    assert mapping.rp_status is False


@pytest.mark.asyncio
async def test_create_role_permission_invalid_role(
    test_client: AsyncClient, test_db_session, clean_db
):
    permission = Permission(
        permission_id="PRM002",
        permission_name="Valid Perm",
        permission_status=True,
    )
    test_db_session.add(permission)
    await test_db_session.commit()

    payload = {"role_id": "INVALID_ROLE", "permission_id": "PRM002"}
    res = await test_client.post("/api/v1/role-permissions/", json=payload)

    assert res.status_code == 404
    response_data = res.json()
    # The API returns error details in the 'detail' key
    detail = response_data.get("detail", {})
    message = detail.get("message", "").lower()
    assert "role" in message


@pytest.mark.asyncio
async def test_create_role_permission_invalid_permission(
    test_client: AsyncClient, test_db_session, clean_db
):
    role = Role(role_id="ROL002", role_name="Another Role", role_status=False)
    test_db_session.add(role)
    await test_db_session.commit()

    payload = {"role_id": "ROL002", "permission_id": "INVALID_PERMISSION"}
    res = await test_client.post("/api/v1/role-permissions/", json=payload)

    assert res.status_code == 404
    response_data = res.json()
    # The API returns error details in the 'detail' key
    detail = response_data.get("detail", {})
    message = detail.get("message", "").lower()
    assert "permission" in message


@pytest.mark.asyncio
async def test_create_duplicate_role_permission(
    test_client: AsyncClient, test_db_session, clean_db
):
    role = Role(role_id="ROL003", role_name="Dup Role", role_status=False)
    permission = Permission(
        permission_id="PRM003",
        permission_name="Dup Perm",
        permission_status=True,
    )
    test_db_session.add_all([role, permission])
    await test_db_session.commit()

    existing = RolePermission(
        role_id="ROL003",
        permission_id="PRM003",
        rp_status=False,
        timestamp=datetime.now(timezone.utc),
    )
    test_db_session.add(existing)
    await test_db_session.commit()

    payload = {"role_id": "ROL003", "permission_id": "PRM003"}
    res = await test_client.post("/api/v1/role-permissions/", json=payload)

    # The API returns 200 when role-permission relationship already exists and is active
    assert res.status_code == 200
    response_data = res.json()
    # For 200 responses, message is directly in the response body
    message = response_data.get("message", "").lower()
    assert "already active" in message

    # Rollback the session to clean up after the integrity error
    # This prevents issues with the clean_db fixture
    try:
        await test_db_session.rollback()
    except Exception as e:
        # Session might already be rolled back, log for debugging if needed
        print(f"Session rollback failed (expected): {e}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_payload,expected_status",
    [
        (
            {"role_id": "", "permission_id": "PRM004"},
            404,
        ),  # Empty string passes validation but fails at business logic
        (
            {"role_id": "ROL004", "permission_id": ""},
            404,
        ),  # Empty string passes validation but fails at business logic
        (
            {"role_id": None, "permission_id": "PRM004"},
            422,
        ),  # None values fail Pydantic validation
        (
            {"role_id": "ROL004", "permission_id": None},
            422,
        ),  # None values fail Pydantic validation
        ({}, 422),  # Missing required fields fail Pydantic validation
    ],
)
async def test_create_role_permission_invalid_payload(
    test_client: AsyncClient, invalid_payload, expected_status
):
    res = await test_client.post(
        "/api/v1/role-permissions/", json=invalid_payload
    )

    assert res.status_code == expected_status
    assert "detail" in res.json()
