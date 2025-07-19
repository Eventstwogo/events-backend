"""
Test cases for user management endpoints (/api/v1/users)
Tests for user_management.py endpoints:
- GET / - Get all users with filtering
- GET /{user_id} - Get specific user
- PATCH /{user_id}/deactivate - Deactivate user
- PATCH /{user_id}/reactivate - Reactivate user
- DELETE /{user_id} - Hard delete user
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import User, UserVerification
from user_service.utils.auth import hash_password


async def get_access_token(
    test_client: AsyncClient,
    test_db_session: AsyncSession,
    user_suffix: str = "01",
) -> str:
    """Helper function to get access token for authentication."""
    # Create a verified user for authentication
    user_id = f"AUTH{user_suffix}"
    user = User(
        user_id=user_id,
        username=f"authuser{user_suffix}",
        first_name="Auth",
        last_name="User",
        email=f"auth{user_suffix}@example.com",
        password_hash=hash_password("Password123!"),
        days_180_flag=True,
        is_deleted=False,
    )
    verification = UserVerification(
        user_id=user_id,
        email_verified=True,
    )
    test_db_session.add(user)
    test_db_session.add(verification)
    await test_db_session.commit()

    # Login to get token
    login_data = {
        "username": f"auth{user_suffix}@example.com",
        "password": "Password123!",
    }
    login_response = await test_client.post(
        "/api/v1/users/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


class TestGetUsers:
    """Test cases for getting users."""

    @pytest.mark.asyncio
    async def test_get_users_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test getting all users successfully."""
        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "01"
        )

        # Create multiple users
        users = [
            User(
                user_id="USR001",
                username="user1",
                first_name="User",
                last_name="One",
                email="user1@example.com",
                password_hash=hash_password("Password123!"),
                days_180_flag=True,
                is_deleted=False,
            ),
            User(
                user_id="USR002",
                username="user2",
                first_name="User",
                last_name="Two",
                email="user2@example.com",
                password_hash=hash_password("Password123!"),
                days_180_flag=True,
                is_deleted=False,
            ),
        ]
        verifications = [
            UserVerification(
                user_id="USR001",
                email_verified=True,
            ),
            UserVerification(
                user_id="USR002",
                email_verified=True,
            ),
        ]
        test_db_session.add_all(users + verifications)
        await test_db_session.commit()

        # Get users with authentication
        response = await test_client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert "data" in body
        assert len(body["data"]) >= 2

    @pytest.mark.asyncio
    async def test_get_users_with_filters(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test getting users with filters."""
        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "02"
        )

        # Create users with different statuses
        users = [
            User(
                user_id="USR001",
                username="activeuser",
                first_name="Active",
                last_name="User",
                email="active@example.com",
                password_hash=hash_password("Password123!"),
                days_180_flag=True,
                is_deleted=False,
            ),
            User(
                user_id="USR002",
                username="deleteduser",
                first_name="Deleted",
                last_name="User",
                email="deleted@example.com",
                password_hash=hash_password("Password123!"),
                days_180_flag=True,
                is_deleted=True,
            ),
        ]
        verifications = [
            UserVerification(
                user_id="USR001",
                email_verified=True,
            ),
            UserVerification(
                user_id="USR002",
                email_verified=True,
            ),
        ]
        test_db_session.add_all(users + verifications)
        await test_db_session.commit()

        # Get only active users
        response = await test_client.get(
            "/api/v1/users/?is_deleted=false",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert len(body["data"]) >= 1
        # Verify all returned users are active
        for user in body["data"]:
            assert user["is_deleted"] is False

    @pytest.mark.asyncio
    async def test_get_users_pagination(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test getting users with pagination."""
        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "03"
        )
        # Create multiple users
        users = []
        verifications = []
        for i in range(5):
            user = User(
                user_id=f"USR{i:03d}",
                username=f"user{i}",
                first_name=f"User",
                last_name=f"{i}",
                email=f"user{i}@example.com",
                password_hash=hash_password("Password123!"),
                days_180_flag=True,
                is_deleted=False,
            )
            verification = UserVerification(
                user_id=f"USR{i:03d}",
                email_verified=True,
            )
            users.append(user)
            verifications.append(verification)

        test_db_session.add_all(users + verifications)
        await test_db_session.commit()

        # Get users with pagination
        response = await test_client.get(
            "/api/v1/users/?skip=0&limit=3",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert len(body["data"]) <= 3

    @pytest.mark.asyncio
    async def test_get_users_empty_result(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test getting users when no users exist."""
        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "04"
        )

        response = await test_client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        # Should only contain the auth user
        assert len(body["data"]) == 1
        assert body["data"][0]["user_id"] == "AUTH04"


class TestGetUserById:
    """Test cases for getting user by ID."""

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test getting user by ID successfully."""
        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "05"
        )
        # Create user
        user = User(
            user_id="USR001",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=False,
        )
        verification = UserVerification(
            user_id="USR001",
            email_verified=True,
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Get user by ID
        response = await test_client.get(
            "/api/v1/users/USR001",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert body["data"]["username"] == "testuser"
        assert body["data"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test getting non-existent user by ID."""
        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "06"
        )

        response = await test_client.get(
            "/api/v1/users/NOTFND",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_get_deleted_user_by_id(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test getting deleted user by ID."""
        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "07"
        )
        # Create deleted user
        user = User(
            user_id="USR001",
            username="deleteduser",
            first_name="Deleted",
            last_name="User",
            email="deleted@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=True,
        )
        verification = UserVerification(
            user_id="USR001",
            email_verified=True,
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Get deleted user by ID
        response = await test_client.get(
            "/api/v1/users/USR001",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert (
            body["data"]["status"] is True
        )  # API returns 'status' instead of 'is_deleted'


class TestDeactivateUser:
    """Test cases for deactivating users."""

    @pytest.mark.asyncio
    async def test_deactivate_user_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test deactivating user successfully."""
        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "08"
        )
        # Create active user
        user = User(
            user_id="USR001",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=False,
        )
        verification = UserVerification(
            user_id="USR001",
            email_verified=True,
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Deactivate user
        response = await test_client.patch(
            "/api/v1/users/USR001/deactivate",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert "soft-deleted" in body["message"].lower()

        # Verify user is deactivated in database
        stmt = select(User).where(User.user_id == "USR001")
        result = await test_db_session.execute(stmt)
        updated_user = result.scalar_one_or_none()
        assert updated_user.is_deleted is True

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test deactivating non-existent user."""
        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "09"
        )

        response = await test_client.patch(
            "/api/v1/users/NOTFND/deactivate",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_deactivate_already_deactivated_user(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test deactivating already deactivated user."""
        # Create already deactivated user
        user = User(
            user_id="USR001",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=True,  # Already deactivated
        )
        verification = UserVerification(
            user_id="USR001",
            email_verified=True,
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "10"
        )

        # Try to deactivate again
        response = await test_client.patch(
            "/api/v1/users/USR001/deactivate",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 400
        assert "already" in body["detail"]["message"].lower()


class TestReactivateUser:
    """Test cases for reactivating users."""

    @pytest.mark.asyncio
    async def test_reactivate_user_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test reactivating user successfully."""
        # Create deactivated user
        user = User(
            user_id="USR001",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=True,  # Deactivated
        )
        verification = UserVerification(
            user_id="USR001",
            email_verified=True,
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "11"
        )

        # Reactivate user
        response = await test_client.patch(
            "/api/v1/users/USR001/reactivate",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert (
            "restored" in body["message"].lower()
        )  # API returns "restored" not "reactivated"

        # Verify user is reactivated in database
        stmt = select(User).where(User.user_id == "USR001")
        result = await test_db_session.execute(stmt)
        updated_user = result.scalar_one_or_none()
        assert updated_user.is_deleted is False

    @pytest.mark.asyncio
    async def test_reactivate_user_not_found(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test reactivating non-existent user."""
        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "12"
        )

        response = await test_client.patch(
            "/api/v1/users/NOTFND/reactivate",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_reactivate_already_active_user(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test reactivating already active user."""
        # Create active user
        user = User(
            user_id="USR001",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=False,  # Already active
        )
        verification = UserVerification(
            user_id="USR001",
            email_verified=True,
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "13"
        )

        # Try to reactivate
        response = await test_client.patch(
            "/api/v1/users/USR001/reactivate",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 400
        assert "already" in body["detail"]["message"].lower()


class TestDeleteUser:
    """Test cases for hard deleting users."""

    @pytest.mark.asyncio
    async def test_delete_user_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test hard deleting user successfully."""
        # Create user
        user = User(
            user_id="USR001",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=False,
        )
        verification = UserVerification(
            user_id="USR001",
            email_verified=True,
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "14"
        )

        # Delete user
        response = await test_client.delete(
            "/api/v1/users/USR001",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert "deleted" in body["message"].lower()

        # Verify user is deleted from database
        stmt = select(User).where(User.user_id == "USR001")
        result = await test_db_session.execute(stmt)
        deleted_user = result.scalar_one_or_none()
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_user_not_found(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test hard deleting non-existent user."""
        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "15"
        )

        response = await test_client.delete(
            "/api/v1/users/NOTFND",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_user_with_verification_record(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test hard deleting user with verification record."""
        # Create user with verification
        user = User(
            user_id="USR001",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=False,
        )
        verification = UserVerification(
            user_id="USR001",
            email_verified=True,
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Get access token for authentication
        access_token = await get_access_token(
            test_client, test_db_session, "16"
        )

        # Delete user
        response = await test_client.delete(
            "/api/v1/users/USR001",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert "deleted" in body["message"].lower()

        # Verify both user and verification are deleted
        stmt = select(User).where(User.user_id == "USR001")
        result = await test_db_session.execute(stmt)
        deleted_user = result.scalar_one_or_none()
        assert deleted_user is None

        stmt = select(UserVerification).where(
            UserVerification.user_id == "USR001"
        )
        result = await test_db_session.execute(stmt)
        deleted_verification = result.scalar_one_or_none()
        assert deleted_verification is None
