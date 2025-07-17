import pytest
from httpx import AsyncClient

from db.models import Permission


@pytest.mark.asyncio
async def test_soft_delete_permission_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    # Setup: create active permission
    permission = Permission(
        permission_id="PRM001",
        permission_name="SOFT DELETE TEST",
        permission_status=False,
    )
    test_db_session.add(permission)
    await test_db_session.commit()

    # Perform soft delete
    res = await test_client.delete("/api/v1/permissions/PRM001")
    body = res.json()

    assert res.status_code == 200
    assert "soft-deleted" in body["message"].lower()

    await test_db_session.refresh(permission)
    assert permission.permission_status is True


@pytest.mark.asyncio
async def test_soft_delete_already_deleted_permission(
    test_client: AsyncClient, test_db_session, clean_db
):
    # Setup: already soft-deleted
    permission = Permission(
        permission_id="PRM002",
        permission_name="ALREADY SOFT DELETED",
        permission_status=True,
    )
    test_db_session.add(permission)
    await test_db_session.commit()

    res = await test_client.delete("/api/v1/permissions/PRM002")
    body = res.json()

    assert res.status_code == 400
    assert "detail" in body
    assert "already soft-deleted" in body["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_hard_delete_permission_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    permission = Permission(
        permission_id="PRM003",
        permission_name="HARD DELETE TEST",
        permission_status=False,
    )
    test_db_session.add(permission)
    await test_db_session.commit()

    res = await test_client.delete(
        "/api/v1/permissions/PRM003?hard_delete=true"
    )
    body = res.json()

    assert res.status_code == 200
    assert "permanently deleted" in body["message"].lower()

    # Confirm deletion
    result = await test_db_session.get(Permission, "PRM003")
    assert result is None


@pytest.mark.asyncio
async def test_hard_delete_after_soft_delete(
    test_client: AsyncClient, test_db_session, clean_db
):
    permission = Permission(
        permission_id="PRM004",
        permission_name="SOFT THEN HARD DELETE",
        permission_status=True,
    )
    test_db_session.add(permission)
    await test_db_session.commit()

    res = await test_client.delete(
        "/api/v1/permissions/PRM004?hard_delete=true"
    )
    body = res.json()

    assert res.status_code == 200
    assert "permanently deleted" in body["message"].lower()


@pytest.mark.asyncio
async def test_delete_permission_not_found(test_client: AsyncClient, clean_db):
    res = await test_client.delete("/api/v1/permissions/UNKNOW")
    body = res.json()

    assert res.status_code == 404
    assert "detail" in body
    assert "not found" in body["detail"]["message"].lower()
