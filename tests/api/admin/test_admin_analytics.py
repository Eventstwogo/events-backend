from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_analytics_success(test_client: AsyncClient):
    """
    Test successful retrieval of admin-user analytics data.
    Assumes real data exists in DB.
    """
    response = await test_client.get("/api/v1/admin-users/analytics")
    body = response.json()

    assert response.status_code == 200
    assert body["message"] == "User analytics fetched successfully."
    assert "summary" in body["data"]
    assert "daily_registrations" in body["data"]
    assert isinstance(body["data"]["summary"], dict)
    assert isinstance(body["data"]["daily_registrations"], list)


@pytest.mark.asyncio
async def test_user_analytics_empty_db(test_client: AsyncClient):
    """
    Test user analytics endpoint with mocked DB data.
    """

    # Dictionary to simulate what your actual SQL function would return
    summary_data_dict = {
        "total_users": 4,
        "active_users": 4,
        "inactive_users": 0,
        "locked_users": 0,
        "with_expiry_flag": 4,
        "expired_passwords": 0,
        "high_failed_attempts": 0,
        "earliest_user": "2025-06-30T05:47:19.107165+00:00",
        "latest_user": "2025-06-30T05:48:45.277493+00:00",
    }

    # Create a MagicMock that behaves like a SQLAlchemy Row
    mock_row = MagicMock()
    mock_row._mapping = summary_data_dict  # pylint: disable=protected-access

    # Mock daily registrations result
    daily_record = MagicMock()
    daily_record.date = "2025-06-30"
    daily_record.count = 4

    with (
        patch(
            "api.v1.endpoints.admin.admin_user.get_admin_user_analytics",
            new=AsyncMock(return_value=mock_row),
        ),
        patch(
            "api.v1.endpoints.admin.admin_user.get_daily_registrations",
            new=AsyncMock(return_value=[daily_record]),
        ),
    ):
        response = await test_client.get("/api/v1/admin-users/analytics")
        body = response.json()

        assert response.status_code == 200
        assert body["message"] == "User analytics fetched successfully."
        assert body["statusCode"] == 200
        assert isinstance(body.get("timestamp"), str)

        # Validate summary payload
        assert body["data"]["summary"] == summary_data_dict

        # Validate daily registrations payload
        assert body["data"]["daily_registrations"] == [
            {"date": "2025-06-30", "count": 4}
        ]


@pytest.mark.asyncio
async def test_user_analytics_failure(test_client: AsyncClient):
    """
    Test analytics endpoint when unexpected server error occurs.
    """

    async def failing_summary(db=None):
        raise Exception("DB Failure")

    with patch(
        "api.v1.endpoints.admin.admin_user.get_admin_user_analytics",
        new=AsyncMock(side_effect=failing_summary),
    ):
        response = await test_client.get("/api/v1/admin-users/analytics")
        body = response.json()

        assert response.status_code == 500
        error_message = body.get("detail") or body.get("message")
        assert error_message is not None
        assert "Something went wrong" in error_message
