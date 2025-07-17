import pytest
from httpx import AsyncClient
from sqlalchemy import insert, select

from db.models import Role  # Adjust import path if needed


@pytest.mark.asyncio
async def test_soft_delete_role_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test soft-deleting a role successfully."""
    await test_db_session.execute(
        insert(Role).values(role_id="r001", role_name="Temp", role_status=False)
    )
    await test_db_session.commit()

    res = await test_client.delete("/api/v1/roles/r001")
    body = res.json()

    assert res.status_code == 200
    assert "soft-deleted" in body["message"]

    result = await test_db_session.execute(
        select(Role).where(Role.role_id == "r001")
    )
    role = result.scalar_one()
    assert role.role_status is True


@pytest.mark.asyncio
async def test_hard_delete_role_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test hard-deleting a role successfully."""
    await test_db_session.execute(
        insert(Role).values(role_id="r002", role_name="Perm", role_status=False)
    )
    await test_db_session.commit()

    res = await test_client.delete("/api/v1/roles/r002?hard_delete=true")
    body = res.json()

    assert res.status_code == 200
    assert "hard delete" in body["message"]

    result = await test_db_session.execute(
        select(Role).where(Role.role_id == "r002")
    )
    role = result.scalar_one_or_none()
    assert role is None


@pytest.mark.asyncio
async def test_delete_role_not_found(test_client: AsyncClient, clean_db):
    """Test deletion of a non-existent role."""
    res = await test_client.delete("/api/v1/roles/nonexistent")
    body = res.json()

    assert res.status_code == 404
    assert "not found" in body["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_soft_delete_already_deleted_role(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test trying to soft-delete an already soft-deleted role."""
    await test_db_session.execute(
        insert(Role).values(role_id="r003", role_name="Old", role_status=True)
    )
    await test_db_session.commit()

    res = await test_client.delete("/api/v1/roles/r003")  # no hard_delete param
    body = res.json()

    assert res.status_code == 400
    assert "already soft-deleted" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_soft_then_hard_delete(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test soft-deleting then hard-deleting a role."""
    await test_db_session.execute(
        insert(Role).values(
            role_id="r004", role_name="Archived", role_status=False
        )
    )
    await test_db_session.commit()

    # Step 1: Soft delete
    res1 = await test_client.delete("/api/v1/roles/r004")
    assert res1.status_code == 200

    # Step 2: Hard delete
    res2 = await test_client.delete("/api/v1/roles/r004?hard_delete=true")
    body = res2.json()

    assert res2.status_code == 200
    assert "hard delete" in body["message"]

    result = await test_db_session.execute(
        select(Role).where(Role.role_id == "r004")
    )
    role = result.scalar_one_or_none()
    assert role is None
