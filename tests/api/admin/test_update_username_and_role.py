import pytest
from httpx import AsyncClient
from sqlalchemy import select

from shared.db.models import AdminUser, Role
from shared.core.security import generate_searchable_hash


@pytest.mark.asyncio
async def test_update_username_success(
    test_client: AsyncClient, test_db_session, seed_config, clean_db
):
    """Test successful username update for active user"""
    # Create test data
    role = Role(role_id="hr0001", role_name="HR", role_status=False)
    test_db_session.add(role)
    config = seed_config

    user = AdminUser(
        user_id="usr001",
        username_encrypted="testuser",
        email_encrypted="testuser@example.com",
        username_hash=generate_searchable_hash("testuser"),
        email_hash=generate_searchable_hash("testuser@example.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    update_data = {"new_username": "updated-username", "new_role_id": None}

    response = await test_client.put(
        f"/api/v1/admin/users/{user.user_id}", data=update_data
    )

    assert response.status_code == 200
    body = response.json()
    assert body["statusCode"] == 200

    # Verify user was updated in database
    result = await test_db_session.execute(
        select(AdminUser).where(AdminUser.user_id == user.user_id)
    )
    updated_user = result.scalar_one()
    assert updated_user.username == "updated-username"


@pytest.mark.asyncio
async def test_update_role_success(
    test_client: AsyncClient, test_db_session, seed_config, clean_db
):
    """Test successful role update for active user"""
    # Create test data
    old_role = Role(role_id="hr0002", role_name="HR", role_status=False)
    new_role = Role(role_id="mgr001", role_name="MANAGER", role_status=False)
    test_db_session.add(old_role)
    test_db_session.add(new_role)
    config = seed_config

    user = AdminUser(
        user_id="usr002",
        username_encrypted="testuser2",
        email_encrypted="testuser2@example.com",
        username_hash=generate_searchable_hash("testuser2"),
        email_hash=generate_searchable_hash("testuser2@example.com"),
        role_id=old_role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    update_data = {"new_username": None, "new_role_id": new_role.role_id}

    response = await test_client.put(
        f"/api/v1/admin/users/{user.user_id}", data=update_data
    )

    assert response.status_code == 200
    body = response.json()
    assert body["statusCode"] == 200

    # Verify user role was updated in database
    result = await test_db_session.execute(
        select(AdminUser).where(AdminUser.user_id == user.user_id)
    )
    updated_user = result.scalar_one()
    assert updated_user.role_id == new_role.role_id


@pytest.mark.asyncio
async def test_update_username_and_role_success(
    test_client: AsyncClient, test_db_session, seed_config, clean_db
):
    """Test successful username and role update for active user"""
    # Create test data
    old_role = Role(role_id="hr0003", role_name="HR", role_status=False)
    new_role = Role(role_id="edt001", role_name="EDITOR", role_status=False)
    test_db_session.add(old_role)
    test_db_session.add(new_role)
    config = seed_config

    user = AdminUser(
        user_id="usr003",
        username_encrypted="testuser3",
        email_encrypted="testuser3@example.com",
        username_hash=generate_searchable_hash("testuser3"),
        email_hash=generate_searchable_hash("testuser3@example.com"),
        role_id=old_role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    update_data = {
        "new_username": "new-username",
        "new_role_id": new_role.role_id,
    }

    response = await test_client.put(
        f"/api/v1/admin/users/{user.user_id}", data=update_data
    )

    assert response.status_code == 200
    body = response.json()
    assert body["statusCode"] == 200

    # Verify both username and role were updated
    result = await test_db_session.execute(
        select(AdminUser).where(AdminUser.user_id == user.user_id)
    )
    updated_user = result.scalar_one()
    assert updated_user.username == "new-username"
    assert updated_user.role_id == new_role.role_id


@pytest.mark.asyncio
async def test_update_inactive_user_fails(
    test_client: AsyncClient, test_db_session, seed_config, clean_db
):
    """Test that updating an inactive user fails"""
    # Create icactive user
    role = Role(role_id="hr0004", role_name="HR", role_status=False)
    test_db_session.add(role)
    config = seed_config

    inactive_user = AdminUser(
        user_id="usr004",
        username_encrypted="inactiveuser",
        email_encrypted="inactiveuser@example.com",
        username_hash=generate_searchable_hash("inactiveuser"),
        email_hash=generate_searchable_hash("inactiveuser@example.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=True,
    )
    test_db_session.add(inactive_user)
    await test_db_session.commit()

    update_data = {"new_username": "should-fail", "new_role_id": None}

    response = await test_client.put(
        f"/api/v1/admin/users/{inactive_user.user_id}",
        data=update_data,
    )

    # Debug: print response details if not 400
    if response.status_code != 400:
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

    assert response.status_code == 400
    body = response.json()
    assert "Cannot update inactive user" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_update_nonexistent_user_fails(
    test_client: AsyncClient, clean_db
):
    """Test that updating a non-existent user fails"""
    update_data = {"new_username": "should-fail", "new_role_id": None}

    response = await test_client.put(
        "/api/v1/admin/users/usr999",  # Use valid format but non-existent ID (6 chars)
        json=update_data,
    )

    # Debug: print response details if not 404
    if response.status_code != 404:
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

    assert response.status_code == 404
    body = response.json()
    assert "User not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_update_username_conflict_fails(
    test_client: AsyncClient, test_db_session, seed_config, clean_db
):
    """Test that updating to an existing username fails"""
    # Create two users
    role = Role(role_id="hr0005", role_name="HR", role_status=False)
    test_db_session.add(role)
    config = seed_config

    user1 = AdminUser(
        user_id="usr005",
        username_encrypted="user1",
        email_encrypted="user1@example.com",
        username_hash=generate_searchable_hash("user1"),
        email_hash=generate_searchable_hash("user1@example.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,
    )
    user2 = AdminUser(
        user_id="usr006",
        username_encrypted="user2",
        email_encrypted="user2@example.com",
        username_hash=generate_searchable_hash("user2"),
        email_hash=generate_searchable_hash("user2@example.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,
    )
    test_db_session.add(user1)
    test_db_session.add(user2)
    await test_db_session.commit()

    # Try to update user1's username to user2's username
    update_data = {"new_username": user2.username, "new_role_id": None}

    response = await test_client.put(
        f"/api/v1/admin/users/{user1.user_id}", data=update_data
    )

    assert response.status_code == 409
    body = response.json()
    assert "Username already exists" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_update_nonexistent_role_fails(
    test_client: AsyncClient, test_db_session, seed_config, clean_db
):
    """Test that updating to a non-existent role fails"""
    # Create user
    role = Role(role_id="hr0006", role_name="HR", role_status=False)
    test_db_session.add(role)
    config = seed_config

    user = AdminUser(
        user_id="usr007",
        username_encrypted="testuser7",
        email_encrypted="testuser7@example.com",
        username_hash=generate_searchable_hash("testuser7"),
        email_hash=generate_searchable_hash("testuser7@example.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    update_data = {
        "new_username": None,
        "new_role_id": "xyz999",  # Non-existent role ID (6 chars)
    }

    response = await test_client.put(
        f"/api/v1/admin/users/{user.user_id}", data=update_data
    )

    assert response.status_code == 404
    body = response.json()
    assert "Role not found" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_update_inactive_role_fails(
    test_client: AsyncClient, test_db_session, seed_config, clean_db
):
    """Test that updating to an inactive role fails"""
    # Create user with inactive role
    inactive_role = Role(role_id="hr0007", role_name="HR", role_status=False)
    test_db_session.add(inactive_role)
    config = seed_config

    user = AdminUser(
        user_id="usr008",
        username_encrypted="testuser8",
        email_encrypted="testuser8@example.com",
        username_hash=generate_searchable_hash("testuser8"),
        email_hash=generate_searchable_hash("testuser8@example.com"),
        role_id=inactive_role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,
    )
    test_db_session.add(user)

    # Create inactive role
    inactive_role = Role(
        role_id="inact0",
        role_name="INACTIVE_ROLE",
        role_status=True,
    )
    test_db_session.add(inactive_role)
    await test_db_session.commit()

    update_data = {"new_username": None, "new_role_id": inactive_role.role_id}

    response = await test_client.put(
        f"/api/v1/admin/users/{user.user_id}", data=update_data
    )

    assert response.status_code == 400
    body = response.json()
    assert "Cannot assign an inactive role" in body["detail"]["message"]


@pytest.mark.asyncio
async def test_update_no_changes_fails(
    test_client: AsyncClient, test_db_session, seed_config, clean_db
):
    """Test that updating with no changes fails"""
    # Create user
    role = Role(role_id="hr0008", role_name="HR", role_status=False)
    test_db_session.add(role)
    config = seed_config

    user = AdminUser(
        user_id="usr009",
        username_encrypted="testuser9",
        email_encrypted="testuser9@example.com",
        username_hash=generate_searchable_hash("testuser9"),
        email_hash=generate_searchable_hash("testuser9@example.com"),
        role_id=role.role_id,
        password_hash=config.default_password_hash,
        days_180_flag=False,
        is_deleted=False,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    # Try to update with same values
    update_data = {
        "new_username": user.username,  # Same username
        "new_role_id": user.role_id,  # Same role
    }

    response = await test_client.put(
        f"/api/v1/admin/users/{user.user_id}", data=update_data
    )

    assert response.status_code == 400
    body = response.json()
    assert "No changes detected" in body["detail"]["message"]
