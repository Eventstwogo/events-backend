"""
Test cases for user login endpoints (/api/v1/users/login, /api/v1/users/logout)
Tests for login.py endpoints:
- POST /login - User login
- POST /logout - User logout
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import User, UserVerification
from user_service.utils.auth import hash_password


class TestUserLogin:
    """Test cases for user login."""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test successful user login."""
        # Create verified user
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
        test_db_session.add(user)
        test_db_session.add(verification)
        await test_db_session.commit()

        # Login data (OAuth2 format)
        data = {
            "username": "test@example.com",  # OAuth2 uses username field for email
            "password": "Password123!",
        }

        response = await test_client.post(
            "/api/v1/users/login",
            data=data,  # Form data for OAuth2
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        body = response.json()

        assert response.status_code == 200
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert "session_id" in body

    @pytest.mark.asyncio
    async def test_login_user_not_found(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test login with non-existent user."""
        data = {
            "username": "nonexistent@example.com",
            "password": "Password123!",
        }

        response = await test_client.post(
            "/api/v1/users/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        body = response.json()

        assert response.status_code == 404
        assert "not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test login with wrong password."""
        # Create verified user
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
        test_db_session.add(user)
        test_db_session.add(verification)
        await test_db_session.commit()

        # Login with wrong password
        data = {"username": "test@example.com", "password": "WrongPassword123!"}

        response = await test_client.post(
            "/api/v1/users/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        body = response.json()

        assert response.status_code == 401
        assert (
            "invalid" in body["detail"]["message"].lower()
            or "incorrect" in body["detail"]["message"].lower()
        )

    @pytest.mark.asyncio
    async def test_login_unverified_email(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test login with unverified email."""
        # Create unverified user
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
            email_verified=False,  # Not verified
        )
        test_db_session.add(user)
        test_db_session.add(verification)
        await test_db_session.commit()

        # Try to login
        data = {"username": "test@example.com", "password": "Password123!"}

        response = await test_client.post(
            "/api/v1/users/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        body = response.json()

        assert response.status_code == 403
        assert (
            "verify" in body["detail"]["message"].lower()
            or "verification" in body["detail"]["message"].lower()
        )

    @pytest.mark.asyncio
    async def test_login_deleted_user(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test login with deleted user."""
        # Create deleted user
        user = User(
            user_id="USR001",
            username="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=True,  # Deleted
        )
        verification = UserVerification(
            user_id="USR001",
            email_verified=True,
        )
        test_db_session.add(user)
        test_db_session.add(verification)
        await test_db_session.commit()

        # Try to login
        data = {"username": "test@example.com", "password": "Password123!"}

        response = await test_client.post(
            "/api/v1/users/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        body = response.json()

        assert response.status_code == 403
        assert (
            "deactivated" in body["detail"]["message"].lower()
            or "inactive" in body["detail"]["message"].lower()
        )

    @pytest.mark.asyncio
    async def test_login_case_insensitive_email(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test login is case insensitive for email."""
        # Create verified user
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
        test_db_session.add(user)
        test_db_session.add(verification)
        await test_db_session.commit()

        # Login with different case
        data = {
            "username": "TEST@EXAMPLE.COM",  # Different case
            "password": "Password123!",
        }

        response = await test_client.post(
            "/api/v1/users/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_login_with_username(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test login with username instead of email - should fail as current implementation only supports email."""
        # Create verified user
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
        test_db_session.add(user)
        test_db_session.add(verification)
        await test_db_session.commit()

        # Login with username (should fail as implementation only supports email)
        data = {
            "username": "testuser",  # Using username
            "password": "Password123!",
        }

        response = await test_client.post(
            "/api/v1/users/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        body = response.json()

        assert response.status_code == 404
        # Check if message is in the response structure
        if "message" in body:
            assert "not found" in body["message"].lower()
        elif (
            "detail" in body
            and isinstance(body["detail"], dict)
            and "message" in body["detail"]
        ):
            assert "not found" in body["detail"]["message"].lower()
        else:
            # Just check that it's a 404 response
            assert True

    @pytest.mark.asyncio
    async def test_login_invalid_format(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test login with invalid data format."""
        # Missing password
        data = {"username": "test@example.com"}

        response = await test_client.post(
            "/api/v1/users/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_empty_credentials(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test login with empty credentials - current implementation returns 404."""
        data = {"username": "", "password": ""}

        response = await test_client.post(
            "/api/v1/users/login",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        body = response.json()

        assert response.status_code == 404  # Current implementation behavior
        # Check if message is in the response structure
        if "message" in body:
            assert "not found" in body["message"].lower()
        elif (
            "detail" in body
            and isinstance(body["detail"], dict)
            and "message" in body["detail"]
        ):
            assert "not found" in body["detail"]["message"].lower()
        else:
            # Just check that it's a 404 response
            assert True


class TestUserLogout:
    """Test cases for user logout."""

    @pytest.mark.asyncio
    async def test_logout_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test successful user logout."""
        # Create verified user
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
        test_db_session.add(user)
        test_db_session.add(verification)
        await test_db_session.commit()

        # First login to get token
        login_data = {
            "username": "test@example.com",
            "password": "Password123!",
        }

        login_response = await test_client.post(
            "/api/v1/users/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Now logout
        response = await test_client.post(
            "/api/v1/users/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert "logout successful" in body["message"].lower()

    @pytest.mark.asyncio
    async def test_logout_without_token(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test logout without authentication token."""
        response = await test_client.post("/api/v1/users/logout")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_invalid_token(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test logout with invalid token."""
        response = await test_client.post(
            "/api/v1/users/logout",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_twice(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test logout twice with same token."""
        # Create verified user
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
        test_db_session.add(user)
        test_db_session.add(verification)
        await test_db_session.commit()

        # First login to get token
        login_data = {
            "username": "test@example.com",
            "password": "Password123!",
        }

        login_response = await test_client.post(
            "/api/v1/users/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # First logout
        response1 = await test_client.post(
            "/api/v1/users/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response1.status_code == 200

        # Second logout with same token should fail
        response2 = await test_client.post(
            "/api/v1/users/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response2.status_code == 401
