import pytest
from httpx import AsyncClient

from db.models import Permission


@pytest.mark.asyncio
async def test_get_permission_id_by_name_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    # Seed a known permission
    permission = Permission(
        permission_id="PRM301",
        permission_name="ReadAccess",
        permission_status=False,
    )
    test_db_session.add(permission)
    await test_db_session.commit()

    res = await test_client.get(
        "/api/v1/permissions/find", params={"permission_name": "ReadAccess"}
    )
    body = res.json()

    assert res.status_code == 200
    assert body["message"].lower() == "permission id retrieved successfully."
    assert body["data"]["permission_id"] == "PRM301"


@pytest.mark.asyncio
async def test_get_permission_id_by_name_not_found(
    test_client: AsyncClient, test_db_session, clean_db
):
    res = await test_client.get(
        "/api/v1/permissions/find",
        params={"permission_name": "NonExistingPerm"},
    )
    body = res.json()

    assert res.status_code == 404
    assert "permission not found" in body["detail"]["message"].lower()
