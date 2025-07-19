"""
Test cases for user registration endpoints (/api/v1/users/register)
Tests for register.py endpoints:
- POST /register - Register a new user
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.security import generate_searchable_hash
from shared.db.models import Config, User, UserVerification
from user_service.utils.auth import hash_password


class TestUserRegistration:
    """Test cases for user registration."""

    @pytest.mark.asyncio
    async def test_register_user_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test successful user registration."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe123",
            "email": "john.doe@example.com",
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)
        body = response.json()

        assert response.status_code == 201
        assert (
            body["message"]
            == "User registered successfully. Verification email sent to your email address."
        )
        assert "data" in body
        assert "user_id" in body["data"]
        assert body["data"]["email"] == "john.doe@example.com"

        # Verify user was created in database
        stmt = select(User).where(
            User.email_hash == generate_searchable_hash("john.doe@example.com")
        )
        result = await test_db_session.execute(stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.username == "johndoe123"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.email == "john.doe@example.com"
        assert user.is_deleted is False

        # Verify verification record was created
        stmt = select(UserVerification).where(
            UserVerification.user_id == user.user_id
        )
        result = await test_db_session.execute(stmt)
        verification = result.scalar_one_or_none()

        assert verification is not None
        assert verification.email_verified is False
        assert verification.email_verification_token is not None

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test registration with duplicate email fails."""
        # Create existing user
        existing_user = User(
            user_id="USR001",
            username="existinguser",
            first_name="Existing",
            last_name="User",
            email="test@example.com",
            password_hash=hash_password("password123"),
            days_180_flag=True,
        )
        test_db_session.add(existing_user)
        await test_db_session.commit()

        data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe123",
            "email": "test@example.com",  # Same email
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)
        body = response.json()

        assert response.status_code == 409
        assert "already exists" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test registration with duplicate username fails."""
        # Create existing user
        existing_user = User(
            user_id="USR001",
            username="johndoe123",
            first_name="Existing",
            last_name="User",
            email="existing@example.com",
            password_hash=hash_password("password123"),
            days_180_flag=True,
        )
        test_db_session.add(existing_user)
        await test_db_session.commit()

        data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe123",  # Same username
            "email": "john.doe@example.com",
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)
        body = response.json()

        assert response.status_code == 409
        assert "already exists" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_user_same_first_last_name(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test registration with same first and last name fails."""
        data = {
            "first_name": "John",
            "last_name": "John",  # Same as first name
            "username": "johndoe123",
            "email": "john.doe@example.com",
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)
        body = response.json()

        assert response.status_code == 400
        assert (
            "First name and last name cannot be the same"
            in body["detail"]["message"]
        )

    @pytest.mark.asyncio
    async def test_register_user_invalid_email(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test registration with invalid email fails."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe123",
            "email": "invalid-email",
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_user_weak_password(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test registration with weak password fails."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe123",
            "email": "john.doe@example.com",
            "password": "weak",
        }

        response = await test_client.post("/api/v1/users/register", json=data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_user_invalid_username(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test registration with invalid username fails."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "jo",  # Too short
            "email": "john.doe@example.com",
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_user_invalid_first_name(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test registration with invalid first name fails."""
        data = {
            "first_name": "",  # Empty
            "last_name": "Doe",
            "username": "johndoe123",
            "email": "john.doe@example.com",
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_user_invalid_last_name(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test registration with invalid last name fails."""
        data = {
            "first_name": "John",
            "last_name": "",  # Empty
            "username": "johndoe123",
            "email": "john.doe@example.com",
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_user_missing_config(
        self, test_client: AsyncClient, clean_db, test_db_session: AsyncSession
    ):
        """Test registration fails when system config is missing."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe123",
            "email": "john.doe@example.com",
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)
        body = response.json()

        assert response.status_code == 404
        assert "configuration not found" in body["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_register_user_username_with_numbers_only_start(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test registration with username starting with numbers fails."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "123johndoe",  # Starts with numbers
            "email": "john.doe@example.com",
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_user_special_characters_in_name(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test registration with special characters in names."""
        data = {
            "first_name": "John-Paul",  # Hyphen allowed
            "last_name": "O'Connor",  # Apostrophe allowed
            "username": "johnpaul123",
            "email": "john.paul@example.com",
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)
        body = response.json()

        assert response.status_code == 201
        assert (
            body["message"]
            == "User registered successfully. Verification email sent to your email address."
        )

    @pytest.mark.asyncio
    async def test_register_user_case_insensitive_email(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test that email is stored in lowercase."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe123",
            "email": "John.Doe@EXAMPLE.COM",  # Mixed case
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)
        body = response.json()

        assert response.status_code == 201
        assert (
            body["data"]["email"] == "john.doe@example.com"
        )  # Should be lowercase

        # Verify in database
        stmt = select(User).where(
            User.email_hash == generate_searchable_hash("john.doe@example.com")
        )
        result = await test_db_session.execute(stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.email == "john.doe@example.com"

    @pytest.mark.asyncio
    async def test_register_user_case_insensitive_username(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test that username is stored in lowercase."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "username": "JohnDoe123",  # Mixed case
            "email": "john.doe@example.com",
            "password": "Password123!",
        }

        response = await test_client.post("/api/v1/users/register", json=data)

        assert response.status_code == 201

        # Verify in database
        stmt = select(User).where(
            User.username_hash == generate_searchable_hash("johndoe123")
        )
        result = await test_db_session.execute(stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.username == "johndoe123"  # Should be lowercase
