"""
Test cases for user verification endpoints (/api/v1/users/verify)
Tests for verify.py endpoints:
- POST /email/verify - Verify email with token
- POST /email/resend-token - Resend email verification token
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import User, UserVerification
from user_service.utils.auth import hash_password


class TestEmailVerification:
    """Test cases for email verification."""

    @pytest.mark.asyncio
    async def test_verify_email_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test successful email verification."""
        # Create user with verification token
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
            email_verified=False,
            email_verification_token="valid_token_123",
            email_token_expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=30),
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Verify email
        data = {"email": "test@example.com", "token": "valid_token_123"}

        response = await test_client.post(
            "/api/v1/users/email/verify", json=data
        )
        body = response.json()

        assert response.status_code == 200
        assert "Email verified successfully" in body["message"]
        assert body["data"]["verified"] is True
        assert body["data"]["user_id"] == "USR001"

        # Verify in database
        stmt = select(UserVerification).where(
            UserVerification.user_id == "USR001"
        )
        result = await test_db_session.execute(stmt)
        updated_verification = result.scalar_one_or_none()
        assert updated_verification is not None
        assert updated_verification.email_verified is True
        assert updated_verification.email_verification_token is None
        assert updated_verification.email_token_expires_at is None

    @pytest.mark.asyncio
    async def test_verify_email_user_not_found(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test email verification with non-existent user."""
        data = {"email": "nonexistent@example.com", "token": "some_token"}

        response = await test_client.post(
            "/api/v1/users/email/verify", json=data
        )
        body = response.json()

        assert response.status_code == 404
        assert "not found" in body.get("detail", {}).get("message", "").lower()

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test email verification with invalid token."""
        # Create user with verification token
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
            email_verified=False,
            email_verification_token="valid_token_123",
            email_token_expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=30),
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Try to verify with wrong token
        data = {"email": "test@example.com", "token": "wrong_token"}

        response = await test_client.post(
            "/api/v1/users/email/verify", json=data
        )
        body = response.json()

        assert response.status_code == 400
        assert "Invalid verification token" in body.get("detail", {}).get(
            "message", ""
        )

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test email verification with expired token."""
        # Create user with expired verification token
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
            email_verified=False,
            email_verification_token="expired_token",
            email_token_expires_at=datetime.now(timezone.utc)
            - timedelta(minutes=30),  # Expired
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Try to verify with expired token
        data = {"email": "test@example.com", "token": "expired_token"}

        response = await test_client.post(
            "/api/v1/users/email/verify", json=data
        )
        body = response.json()

        assert response.status_code == 400
        assert "expired" in body.get("detail", {}).get("message", "").lower()

    @pytest.mark.asyncio
    async def test_verify_email_no_token(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test email verification when no token exists."""
        # Create user without verification token
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
            email_verified=False,
            email_verification_token=None,  # No token
            email_token_expires_at=None,
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Try to verify without token
        data = {"email": "test@example.com", "token": "some_token"}

        response = await test_client.post(
            "/api/v1/users/email/verify", json=data
        )
        body = response.json()

        assert response.status_code == 400
        assert "No verification token" in body.get("detail", {}).get(
            "message", ""
        )

    @pytest.mark.asyncio
    async def test_verify_email_no_verification_record(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test email verification when no verification record exists."""
        # Create user without verification record
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
        test_db_session.add(user)
        await test_db_session.commit()

        # Try to verify without verification record
        data = {"email": "test@example.com", "token": "some_token"}

        response = await test_client.post(
            "/api/v1/users/email/verify", json=data
        )
        body = response.json()

        assert response.status_code == 400
        assert "No verification record found" in body.get("detail", {}).get(
            "message", ""
        )

    @pytest.mark.asyncio
    async def test_verify_email_case_insensitive(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test email verification is case insensitive."""
        # Create user with verification token
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
            email_verified=False,
            email_verification_token="valid_token_123",
            email_token_expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=30),
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Verify email with different case
        data = {
            "email": "TEST@EXAMPLE.COM",  # Different case
            "token": "valid_token_123",
        }

        response = await test_client.post(
            "/api/v1/users/email/verify", json=data
        )
        body = response.json()

        assert response.status_code == 200
        assert "Email verified successfully" in body["message"]


class TestResendEmailToken:
    """Test cases for resending email verification token."""

    @pytest.mark.asyncio
    async def test_resend_email_token_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test successful resending of email verification token."""
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
            email_verified=False,
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Resend email token
        data = {"email": "test@example.com"}

        response = await test_client.post(
            "/api/v1/users/email/resend-token", json=data
        )
        body = response.json()

        assert response.status_code == 200
        assert "verification email sent" in body["message"].lower()
        assert body["data"]["user_id"] == "USR001"
        assert body["data"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_resend_email_token_user_not_found(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test resending email token for non-existent user."""
        data = {"email": "nonexistent@example.com"}

        response = await test_client.post(
            "/api/v1/users/email/resend-token", json=data
        )
        body = response.json()

        assert response.status_code == 404
        assert "not found" in body.get("detail", {}).get("message", "").lower()

    @pytest.mark.asyncio
    async def test_resend_email_token_already_verified(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test resending email token for already verified user."""
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
            email_verified=True,  # Already verified
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Try to resend email token
        data = {"email": "test@example.com"}

        response = await test_client.post(
            "/api/v1/users/email/resend-token", json=data
        )
        body = response.json()

        assert response.status_code == 400
        assert (
            "already verified"
            in body.get("detail", {}).get("message", "").lower()
        )

    @pytest.mark.asyncio
    async def test_resend_email_token_case_insensitive(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test resending email token is case insensitive."""
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
            email_verified=False,
        )
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Resend email token with different case
        data = {"email": "TEST@EXAMPLE.COM"}  # Different case

        response = await test_client.post(
            "/api/v1/users/email/resend-token", json=data
        )
        body = response.json()

        assert response.status_code == 200
        assert "verification email sent" in body["message"].lower()

    @pytest.mark.asyncio
    async def test_resend_email_token_invalid_email(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test resending email token with invalid email format."""
        data = {"email": "invalid-email"}

        response = await test_client.post(
            "/api/v1/users/email/resend-token", json=data
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_resend_email_token_empty_email(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test resending email token with empty email."""
        data = {"email": ""}

        response = await test_client.post(
            "/api/v1/users/email/resend-token", json=data
        )

        assert response.status_code == 422  # Validation error
