from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from shared.db.models import AdminUser


@pytest.mark.asyncio
async def test_user_analytics_success(test_client: AsyncClient, test_app):
    """
    Test successful retrieval of admin-user analytics data.
    Assumes real data exists in DB.
    """
    # Mock the authentication dependency
    mock_admin_user = AdminUser(
        user_id="admin123",
        username="testadmin",
        email="admin@test.com",
        role_id="role123",
        is_deleted=False,
    )

    async def mock_get_current_active_user():
        return mock_admin_user

    # Override the dependency
    from shared.dependencies.admin import get_current_active_user

    test_app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_user
    )

    try:
        response = await test_client.get("/api/v1/admin/analytics")
        body = response.json()

        assert response.status_code == 200
        assert body["message"] == "User analytics fetched successfully."
        assert "summary" in body["data"]
        assert "daily_registrations" in body["data"]
        assert isinstance(body["data"]["summary"], dict)
        assert isinstance(body["data"]["daily_registrations"], list)
    finally:
        # Clean up the override
        test_app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_user_analytics_empty_db(test_client: AsyncClient, test_app):
    """
    Test user analytics endpoint with mocked DB data.
    """
    # Mock the authentication dependency
    mock_admin_user = AdminUser(
        user_id="admin123",
        username="testadmin",
        email="admin@test.com",
        role_id="role123",
        is_deleted=False,
    )

    async def mock_get_current_active_user():
        return mock_admin_user

    # Override the dependency
    from shared.dependencies.admin import get_current_active_user

    test_app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_user
    )

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

    try:
        with (
            patch(
                "admin_service.api.v1.endpoints.analytics.get_admin_user_analytics",
                new=AsyncMock(return_value=mock_row),
            ),
            patch(
                "admin_service.api.v1.endpoints.analytics.get_daily_registrations",
                new=AsyncMock(return_value=[daily_record]),
            ),
        ):
            response = await test_client.get("/api/v1/admin/analytics")
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
    finally:
        # Clean up the override
        test_app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_user_analytics_failure(test_client: AsyncClient, test_app):
    """
    Test analytics endpoint when unexpected server error occurs.
    """
    # Mock the authentication dependency
    mock_admin_user = AdminUser(
        user_id="admin123",
        username="testadmin",
        email="admin@test.com",
        role_id="role123",
        is_deleted=False,
    )

    async def mock_get_current_active_user():
        return mock_admin_user

    # Override the dependency
    from shared.dependencies.admin import get_current_active_user

    test_app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_user
    )

    async def failing_summary(db=None):
        raise Exception("DB Failure")

    try:
        with patch(
            "admin_service.api.v1.endpoints.analytics.get_admin_user_analytics",
            new=AsyncMock(side_effect=failing_summary),
        ):
            response = await test_client.get("/api/v1/admin/analytics")
            body = response.json()

            assert response.status_code == 500
            error_message = body.get("detail") or body.get("message")
            assert error_message is not None
            assert "Something went wrong" in error_message
    finally:
        # Clean up the override
        test_app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_dashboard_analytics_success(test_client: AsyncClient, test_app):
    """
    Test successful retrieval of dashboard analytics data.
    """
    # Mock the authentication dependency
    mock_admin_user = AdminUser(
        user_id="admin123",
        username="testadmin",
        email="admin@test.com",
        role_id="role123",
        is_deleted=False,
    )

    async def mock_get_current_active_user():
        return mock_admin_user

    # Override the dependency
    from shared.dependencies.admin import get_current_active_user

    test_app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_user
    )

    # Mock dashboard analytics data
    mock_dashboard_data = {
        "categories": {
            "total": 12,
            "added_this_month": 2,
            "percentage_change": 16.7,
            "trend": "up",
        },
        "users": {
            "total": 1234,
            "added_this_week": 48,
            "percentage_change": 4.1,
            "trend": "up",
        },
        "revenue": {
            "current_month": 45678.0,
            "last_month": 39000.0,
            "difference": 6678.0,
            "percentage_change": 17.1,
            "trend": "up",
            "note": "Estimated revenue based on events. Implement actual payment tracking for accurate data.",
        },
        "settings": {
            "total": 28,
            "changes_this_week": 3,
            "percentage_change": 50.0,
            "trend": "up",
        },
        "generated_at": "2024-01-15T10:30:00+00:00",
    }

    try:
        with patch(
            "admin_service.api.v1.endpoints.analytics.get_dashboard_analytics",
            new=AsyncMock(return_value=mock_dashboard_data),
        ):
            response = await test_client.get("/api/v1/admin/dashboard")
            body = response.json()

            assert response.status_code == 200
            assert (
                body["message"] == "Dashboard analytics fetched successfully."
            )
            assert body["statusCode"] == 200
            assert isinstance(body.get("timestamp"), str)

            # Validate dashboard data structure
            data = body["data"]
            assert "categories" in data
            assert "users" in data
            assert "revenue" in data
            assert "settings" in data
            assert "generated_at" in data

            # Validate categories data
            categories = data["categories"]
            assert categories["total"] == 12
            assert categories["added_this_month"] == 2
            assert categories["percentage_change"] == 16.7
            assert categories["trend"] == "up"

            # Validate users data
            users = data["users"]
            assert users["total"] == 1234
            assert users["added_this_week"] == 48
            assert users["percentage_change"] == 4.1
            assert users["trend"] == "up"

            # Validate revenue data
            revenue = data["revenue"]
            assert revenue["current_month"] == 45678.0
            assert revenue["last_month"] == 39000.0
            assert revenue["difference"] == 6678.0
            assert revenue["percentage_change"] == 17.1
            assert revenue["trend"] == "up"
            assert "note" in revenue

            # Validate settings data
            settings = data["settings"]
            assert settings["total"] == 28
            assert settings["changes_this_week"] == 3
            assert settings["percentage_change"] == 50.0
            assert settings["trend"] == "up"

    finally:
        # Clean up the override
        test_app.dependency_overrides.pop(get_current_active_user, None)


@pytest.mark.asyncio
async def test_dashboard_analytics_failure(test_client: AsyncClient, test_app):
    """
    Test dashboard analytics endpoint when unexpected server error occurs.
    """
    # Mock the authentication dependency
    mock_admin_user = AdminUser(
        user_id="admin123",
        username="testadmin",
        email="admin@test.com",
        role_id="role123",
        is_deleted=False,
    )

    async def mock_get_current_active_user():
        return mock_admin_user

    # Override the dependency
    from shared.dependencies.admin import get_current_active_user

    test_app.dependency_overrides[get_current_active_user] = (
        mock_get_current_active_user
    )

    async def failing_dashboard_analytics(db=None):
        raise Exception("DB Connection Failed")

    try:
        with patch(
            "admin_service.api.v1.endpoints.analytics.get_dashboard_analytics",
            new=AsyncMock(return_value=failing_dashboard_analytics),
        ):
            response = await test_client.get("/api/v1/admin/dashboard")
            body = response.json()

            assert response.status_code == 500
            error_message = body.get("detail") or body.get("message")
            assert error_message is not None
            assert "Something went wrong" in error_message
    finally:
        # Clean up the override
        test_app.dependency_overrides.pop(get_current_active_user, None)
