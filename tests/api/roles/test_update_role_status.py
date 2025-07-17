import pytest
from httpx import AsyncClient
from sqlalchemy import insert

from db.models import Role  # Adjust this import if needed


@pytest.mark.asyncio
async def test_activate_role_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test successfully activating a role (status = true)."""
    await test_db_session.execute(
        insert(Role).values(
            role_id="r001", role_name="INACTIVE_ROLE", role_status=False
        )
    )
    await test_db_session.commit()

    res = await test_client.patch("/api/v1/roles/r001/status?role_status=true")
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Role status updated to Inactive."
    assert body["data"]["role_status"] is True


@pytest.mark.asyncio
async def test_deactivate_role_success(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test successfully deactivating a role (status = false)."""
    await test_db_session.execute(
        insert(Role).values(
            role_id="r002", role_name="ACTIVE_ROLE", role_status=True
        )
    )
    await test_db_session.commit()

    res = await test_client.patch("/api/v1/roles/r002/status?role_status=false")
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Role status updated to Active."
    assert body["data"]["role_status"] is False


@pytest.mark.asyncio
async def test_update_status_role_not_found(test_client: AsyncClient, clean_db):
    """Test 404 when role_id does not exist."""
    res = await test_client.patch(
        "/api/v1/roles/invalid-id/status?role_status=true"
    )
    body = res.json()

    assert res.status_code == 404
    assert "not found" in body["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_update_status_default_false(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test default role_status = false if not passed."""
    await test_db_session.execute(
        insert(Role).values(
            role_id="r003", role_name="ROLE_WITH_DEFAULT", role_status=True
        )
    )
    await test_db_session.commit()

    res = await test_client.patch(
        "/api/v1/roles/r003/status"
    )  # no role_status param
    body = res.json()

    assert res.status_code == 200
    assert body["message"] == "Role status updated to Active."
    assert body["data"]["role_status"] is False


@pytest.mark.asyncio
async def test_update_status_invalid_bool_value(
    test_client: AsyncClient, test_db_session, clean_db
):
    """Test FastAPI validation failure on invalid boolean query param."""
    await test_db_session.execute(
        insert(Role).values(
            role_id="r004", role_name="INVALID_BOOL", role_status=False
        )
    )
    await test_db_session.commit()

    res = await test_client.patch(
        "/api/v1/roles/r004/status?role_status=notabool"
    )

    assert res.status_code == 422
    assert any(err["loc"][-1] == "role_status" for err in res.json()["detail"])
