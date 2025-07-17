import pytest
from httpx import AsyncClient
from sqlalchemy import insert

from db.models import Role  # Adjust import if needed


@pytest.mark.asyncio
async def test_update_role_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test successful role name update."""
    role = {"role_id": "r001", "role_name": "SUPPORT", "role_status": False}
    await test_db_session.execute(insert(Role).values(role))
    await test_db_session.commit()

    res = await test_client.put(
        "/api/v1/roles/r001", json={"role_name": "Customer Support"}
    )
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Role updated successfully."
    assert (
        body["data"]["role_name"] == "CUSTOMER SUPPORT"
    )  # validator returns uppercase


@pytest.mark.asyncio
async def test_update_role_not_found(test_client: AsyncClient, clean_db):
    """Test update with non-existent role ID."""
    res = await test_client.put(
        "/api/v1/roles/invalid001", json={"role_name": "Ghost"}
    )
    body = res.json()

    assert res.status_code == 404
    assert "not found" in body["detail"]["message"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_name",
    [
        "",  # empty
        "a",  # too short
        "a" * 60,  # too long
        "Invalid@Name#",  # special characters
    ],
)
async def test_update_role_invalid_data(
    test_client: AsyncClient, test_db_session, clean_db, invalid_name
):
    """Test update failure due to validation errors."""
    await test_db_session.execute(
        insert(Role).values(role_id="r002", role_name="TEST", role_status=False)
    )
    await test_db_session.commit()

    res = await test_client.put(
        "/api/v1/roles/r002", json={"role_name": invalid_name}
    )
    assert res.status_code == 422
    assert any(err["loc"][-1] == "role_name" for err in res.json()["detail"])


@pytest.mark.asyncio
async def test_update_role_no_payload(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test update when no data is sent in the payload
    (should succeed with no changes)."""
    await test_db_session.execute(
        insert(Role).values(
            role_id="r003", role_name="Original", role_status=False
        )
    )
    await test_db_session.commit()

    res = await test_client.put("/api/v1/roles/r003", json={})
    body = res.json()

    assert res.status_code == 200
    assert body["data"]["role_name"].upper() == "ORIGINAL"
