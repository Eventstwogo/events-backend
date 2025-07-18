import pytest
from httpx import AsyncClient

from shared.db.models import Permission


@pytest.mark.asyncio
async def test_get_all_permissions_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    # Seed two permissions: one active, one inactive
    perms = [
        Permission(
            permission_id="PRM101",
            permission_name="Permission A",
            permission_status=False,
        ),
        Permission(
            permission_id="PRM102",
            permission_name="Permission B",
            permission_status=True,
        ),
    ]
    test_db_session.add_all(perms)
    await test_db_session.commit()

    res = await test_client.get("/api/v1/permissions/")
    body = res.json()

    assert res.status_code == 200
    assert "permissions retrieved successfully" in body["message"].lower()
    assert len(body["data"]) == 2


@pytest.mark.asyncio
async def test_get_permissions_filtered_active(
    test_client: AsyncClient, test_db_session, clean_db
):
    # Seed two permissions: one active, one inactive
    perms = [
        Permission(
            permission_id="PRM201",
            permission_name="Permission C",
            permission_status=False,
        ),
        Permission(
            permission_id="PRM202",
            permission_name="Permission D",
            permission_status=True,
        ),
    ]
    test_db_session.add_all(perms)
    await test_db_session.commit()

    res = await test_client.get("/api/v1/permissions/?is_active=true")
    body = res.json()

    assert res.status_code == 200
    assert all(perm["permission_status"] is True for perm in body["data"])
    assert any(perm["permission_id"] == "PRM202" for perm in body["data"])


@pytest.mark.asyncio
async def test_get_permissions_filtered_inactive(
    test_client: AsyncClient, test_db_session, clean_db
):
    # Seed two permissions: one active, one inactive
    perms = [
        Permission(
            permission_id="PRM301",
            permission_name="Permission E",
            permission_status=False,
        ),
        Permission(
            permission_id="PRM302",
            permission_name="Permission F",
            permission_status=True,
        ),
    ]
    test_db_session.add_all(perms)
    await test_db_session.commit()

    res = await test_client.get("/api/v1/permissions/?is_active=false")
    body = res.json()

    assert res.status_code == 200
    assert all(perm["permission_status"] is False for perm in body["data"])
    assert any(perm["permission_id"] == "PRM301" for perm in body["data"])


@pytest.mark.asyncio
async def test_get_permissions_no_results(
    test_client: AsyncClient, test_db_session, clean_db
):
    # No data seeded
    res = await test_client.get("/api/v1/permissions/?is_active=true")
    body = res.json()

    assert res.status_code == 404
    assert "no permissions found" in body["detail"]["message"].lower()
