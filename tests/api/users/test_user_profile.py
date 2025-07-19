"""
Test cases for user profile endpoints (/api/v1/users/profile)
Tests for profile.py endpoints:
- GET / - Get current user profile
- PUT / - Update user profile
- PATCH /picture - Update profile picture
- DELETE / - Delete current user account
"""

import io

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import User, UserVerification
from user_service.utils.auth import hash_password


class TestGetProfile:
    """Test cases for getting user profile."""

    @pytest.mark.asyncio
    async def test_get_profile_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test getting user profile successfully."""
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
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Login to get token
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

        # Get profile
        response = await test_client.get(
            "/api/v1/users/profile/",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert "Profile fetched successfully" in body["message"]
        assert body["data"]["user_id"] == "USR001"
        assert body["data"]["username"] == "testuser"
        assert body["data"]["first_name"] == "Test"
        assert body["data"]["last_name"] == "User"
        assert body["data"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_profile_unauthorized(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test getting profile without authentication."""
        response = await test_client.get("/api/v1/users/profile/")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_profile_invalid_token(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test getting profile with invalid token."""
        response = await test_client.get(
            "/api/v1/users/profile/",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401


class TestUpdateProfile:
    """Test cases for updating user profile."""

    @pytest.mark.asyncio
    async def test_update_profile_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test updating user profile successfully."""
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
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Login to get token
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

        # Update profile
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "username": "updateduser",
            "email": "updated@example.com",
        }

        response = await test_client.put(
            "/api/v1/users/profile/",
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert "Profile updated successfully" in body["message"]
        assert body["data"]["first_name"] == "Updated"
        assert body["data"]["last_name"] == "Name"
        assert body["data"]["username"] == "updateduser"
        assert body["data"]["email"] == "updated@example.com"

        # Verify in database
        stmt = select(User).where(User.user_id == "USR001")
        result = await test_db_session.execute(stmt)
        updated_user = result.scalar_one_or_none()
        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "Name"
        assert updated_user.username == "updateduser"
        assert updated_user.email == "updated@example.com"

    @pytest.mark.asyncio
    async def test_update_profile_same_first_last_name(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test updating profile with same first and last name fails."""
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
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Login to get token
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

        # Update profile with same first and last name
        update_data = {
            "first_name": "Same",
            "last_name": "Same",  # Same as first name
            "username": "testuser",
            "email": "test@example.com",
        }

        response = await test_client.put(
            "/api/v1/users/profile/",
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 400
        assert (
            "First name and last name cannot be the same"
            in body["detail"]["message"]
        )

    @pytest.mark.asyncio
    async def test_update_profile_duplicate_username(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test updating profile with duplicate username fails."""
        # Create verified users
        user1 = User(
            user_id="USR001",
            username="testuser1",
            first_name="Test",
            last_name="User1",
            email="test1@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=False,
        )
        user2 = User(
            user_id="USR002",
            username="testuser2",
            first_name="Test",
            last_name="User2",
            email="test2@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=False,
        )
        verification1 = UserVerification(
            user_id="USR001",
            email_verified=True,
        )
        verification2 = UserVerification(
            user_id="USR002",
            email_verified=True,
        )
        test_db_session.add_all([user1, user2, verification1, verification2])
        await test_db_session.commit()

        # Login as user1
        login_data = {
            "username": "test1@example.com",
            "password": "Password123!",
        }
        login_response = await test_client.post(
            "/api/v1/users/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Try to update username to user2's username
        update_data = {
            "first_name": "Test",
            "last_name": "User1",
            "username": "testuser2",  # Duplicate username
            "email": "test1@example.com",
        }

        response = await test_client.put(
            "/api/v1/users/profile/",
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 409
        assert "Username already exists" in body["detail"]["message"]

    @pytest.mark.asyncio
    async def test_update_profile_duplicate_email(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test updating profile with duplicate email fails."""
        # Create verified users
        user1 = User(
            user_id="USR001",
            username="testuser1",
            first_name="Test",
            last_name="User1",
            email="test1@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=False,
        )
        user2 = User(
            user_id="USR002",
            username="testuser2",
            first_name="Test",
            last_name="User2",
            email="test2@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=False,
        )
        verification1 = UserVerification(
            user_id="USR001",
            email_verified=True,
        )
        verification2 = UserVerification(
            user_id="USR002",
            email_verified=True,
        )
        test_db_session.add_all([user1, user2, verification1, verification2])
        await test_db_session.commit()

        # Login as user1
        login_data = {
            "username": "test1@example.com",
            "password": "Password123!",
        }
        login_response = await test_client.post(
            "/api/v1/users/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Try to update email to user2's email
        update_data = {
            "first_name": "Test",
            "last_name": "User1",
            "username": "testuser1",
            "email": "test2@example.com",  # Duplicate email
        }

        response = await test_client.put(
            "/api/v1/users/profile/",
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 409
        assert "Email already exists" in body["detail"]["message"]

    @pytest.mark.asyncio
    async def test_update_profile_invalid_username(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test updating profile with invalid username fails."""
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
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Login to get token
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

        # Update profile with invalid username
        update_data = {
            "first_name": "Test",
            "last_name": "User",
            "username": "123invalid",  # Starts with numbers
            "email": "test@example.com",
        }

        response = await test_client.put(
            "/api/v1/users/profile/",
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 400
        assert (
            "First three characters of username must be letters"
            in body["detail"]["message"]
        )

    @pytest.mark.asyncio
    async def test_update_profile_invalid_first_name(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test updating profile with invalid first name fails."""
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
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Login to get token
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

        # Update profile with XSS in first name
        update_data = {
            "first_name": "<script>alert('xss')</script>",
            "last_name": "User",
            "username": "testuser",
            "email": "test@example.com",
        }

        response = await test_client.put(
            "/api/v1/users/profile/",
            json=update_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 400
        assert "malicious content" in body["detail"]["message"]

    @pytest.mark.asyncio
    async def test_update_profile_unauthorized(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test updating profile without authentication."""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "username": "updateduser",
            "email": "updated@example.com",
        }

        response = await test_client.put(
            "/api/v1/users/profile/", json=update_data
        )

        assert response.status_code == 401


class TestUpdateProfilePicture:
    """Test cases for updating profile picture."""

    @pytest.mark.asyncio
    async def test_update_profile_picture_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test updating profile picture successfully."""
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
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Login to get token
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

        # Create a mock image file
        image_content = b"fake image content"
        files = {
            "profile_picture": (
                "test.jpg",
                io.BytesIO(image_content),
                "image/jpeg",
            )
        }

        # Update profile picture
        response = await test_client.patch(
            "/api/v1/users/profile/picture",
            files=files,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert "Profile picture updated successfully" in body["message"]
        assert "profile_picture" in body["data"]

    @pytest.mark.asyncio
    async def test_update_profile_picture_invalid_type(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test updating profile picture with invalid file type fails."""
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
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Login to get token
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

        # Create a mock text file
        text_content = b"not an image"
        files = {
            "profile_picture": (
                "test.txt",
                io.BytesIO(text_content),
                "text/plain",
            )
        }

        # Try to update profile picture with invalid type
        response = await test_client.patch(
            "/api/v1/users/profile/picture",
            files=files,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 400
        assert "Invalid file type" in body["detail"]["message"]

    @pytest.mark.asyncio
    async def test_update_profile_picture_unauthorized(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test updating profile picture without authentication."""
        # Create a mock image file
        image_content = b"fake image content"
        files = {
            "profile_picture": (
                "test.jpg",
                io.BytesIO(image_content),
                "image/jpeg",
            )
        }

        response = await test_client.patch(
            "/api/v1/users/profile/picture", files=files
        )

        assert response.status_code == 401


class TestDeleteAccount:
    """Test cases for deleting user account."""

    @pytest.mark.asyncio
    async def test_delete_account_success(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test deleting user account successfully."""
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
        test_db_session.add_all([user, verification])
        await test_db_session.commit()

        # Login to get token
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

        # Delete account
        response = await test_client.delete(
            "/api/v1/users/profile/",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        body = response.json()

        assert response.status_code == 200
        assert "Account deactivated successfully" in body["message"]

        # Verify user is soft deleted in database
        stmt = select(User).where(User.user_id == "USR001")
        result = await test_db_session.execute(stmt)
        deleted_user = result.scalar_one_or_none()
        assert deleted_user.is_deleted is True

    @pytest.mark.asyncio
    async def test_delete_already_deleted_account(
        self,
        test_client: AsyncClient,
        clean_db,
        test_db_session: AsyncSession,
        seed_config,
    ):
        """Test deleting already deleted account fails."""
        # Create active user first
        active_user = User(
            user_id="USR002",
            username="activeuser",
            first_name="Active",
            last_name="User",
            email="active@example.com",
            password_hash=hash_password("Password123!"),
            days_180_flag=True,
            is_deleted=False,
        )
        active_verification = UserVerification(
            user_id="USR002",
            email_verified=True,
        )
        test_db_session.add_all([active_user, active_verification])
        await test_db_session.commit()

        # Login as active user
        login_data = {
            "username": "active@example.com",
            "password": "Password123!",
        }
        login_response = await test_client.post(
            "/api/v1/users/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Delete account first time
        response = await test_client.delete(
            "/api/v1/users/profile/",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200

        # Verify that the first deletion worked
        stmt = select(User).where(User.user_id == "USR002")
        result = await test_db_session.execute(stmt)
        deleted_user = result.scalar_one_or_none()
        assert deleted_user.is_deleted is True

    @pytest.mark.asyncio
    async def test_delete_account_unauthorized(
        self, test_client: AsyncClient, clean_db, seed_config
    ):
        """Test deleting account without authentication."""
        response = await test_client.delete("/api/v1/users/profile/")

        assert response.status_code == 401
