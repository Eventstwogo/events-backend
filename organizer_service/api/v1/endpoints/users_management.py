from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from organizer_service.schemas.users_management import (
    UsersListApiResponse,
    UserTypeEnum,
)
from shared.core.api_response import api_response
from shared.db.models import AdminUser, Event, Role
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url

router = APIRouter()


@router.get(
    "/users-list",
    status_code=200,
    response_model=UsersListApiResponse,
    summary="Get All Users List",
    description="Fetch all users from AdminUsers table divided into Admin and Organizer users based on role_name",
)
@exception_handler
async def get_users_list(
    user_type: UserTypeEnum = Query(
        UserTypeEnum.ORGANIZER,
        description="Filter users by type: 'organizer' (default), 'admin', or 'all'",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch all users from AdminUsers table and categorize them based on role_name.

    This endpoint:
    1. Fetches all users from AdminUser table with their roles
    2. Categorizes users into Admin and Organizer based on role_name
    3. For each user, fetches their events and includes event names
    4. Returns categorized user data with event information

    Args:
        user_type: Filter to return specific user types (organizer by default)
        db: Database session

    Returns:
        Categorized list of users with their events information
    """

    # Build the base query for users with their roles
    users_stmt = (
        select(AdminUser)
        .options(
            selectinload(AdminUser.role),
        )
        .where(AdminUser.is_deleted == False)  # Only active users
        .order_by(AdminUser.created_at.desc())
    )

    # Execute the query
    result = await db.execute(users_stmt)
    all_users = result.scalars().all()

    if not all_users:
        return api_response(
            status_code=200,
            message="No users found",
            data={
                "admin_users": [],
                "organizer_users": [],
                "total_admin_users": 0,
                "total_organizer_users": 0,
                "total_users": 0,
            },
        )

    # Initialize lists for categorizing users
    admin_users = []
    organizer_users = []

    # Process each user
    for user in all_users:
        # Get user's role name
        role_name = user.role.role_name if user.role else "Unknown"

        # Fetch events for this user
        events_stmt = (
            select(Event)
            .where(Event.organizer_id == user.user_id)
            .order_by(Event.created_at.desc())
        )

        events_result = await db.execute(events_stmt)
        user_events = events_result.scalars().all()

        # Process events data
        events_info = []
        for event in user_events:
            events_info.append(
                {
                    "event_id": event.event_id,
                    "event_title": event.event_title,
                    "event_status": event.event_status,
                    "created_at": event.created_at,
                }
            )

        # Create user info object
        user_info = {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "profile_picture": get_media_url(user.profile_picture),
            "role_name": role_name,
            "is_verified": user.is_verified,
            "is_deleted": user.is_deleted,
            "created_at": user.created_at,
            "total_events": len(events_info),
            "events": events_info,
        }

        # Categorize user based on role_name
        if role_name.lower() == "organizer":
            organizer_users.append(user_info)
        else:
            admin_users.append(user_info)

    # Prepare response data based on user_type filter
    response_data = {
        "admin_users": (
            admin_users
            if user_type in [UserTypeEnum.ALL, UserTypeEnum.ADMIN]
            else []
        ),
        "organizer_users": (
            organizer_users
            if user_type in [UserTypeEnum.ALL, UserTypeEnum.ORGANIZER]
            else []
        ),
        "total_admin_users": len(admin_users),
        "total_organizer_users": len(organizer_users),
        "total_users": len(admin_users) + len(organizer_users),
    }

    # Determine success message based on filter
    if user_type == UserTypeEnum.ORGANIZER:
        message = f"Organizer users retrieved successfully. Found {len(organizer_users)} organizers."
    elif user_type == UserTypeEnum.ADMIN:
        message = f"Admin users retrieved successfully. Found {len(admin_users)} admins."
    else:
        message = f"All users retrieved successfully. Found {len(admin_users)} admins and {len(organizer_users)} organizers."

    return api_response(status_code=200, message=message, data=response_data)


@router.get(
    "/users-summary",
    status_code=200,
    summary="Get Users Summary Statistics",
    description="Get summary statistics of all users without detailed event information",
)
@exception_handler
async def get_users_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary statistics of users categorized by role.

    This is a lightweight endpoint that provides counts and basic statistics
    without fetching detailed event information.

    Args:
        db: Database session

    Returns:
        Summary statistics of users
    """

    # Get all active users with their roles
    users_stmt = (
        select(AdminUser)
        .options(selectinload(AdminUser.role))
        .where(AdminUser.is_deleted == False)
    )

    result = await db.execute(users_stmt)
    all_users = result.scalars().all()

    # Initialize counters
    admin_count = 0
    organizer_count = 0
    verified_users = 0
    unverified_users = 0

    # Count users by category
    for user in all_users:
        role_name = user.role.role_name if user.role else "Unknown"

        if role_name.lower() == "organizer":
            organizer_count += 1
        else:
            admin_count += 1

        if user.is_verified == 1:
            verified_users += 1
        else:
            unverified_users += 1

    # Get total events count
    events_stmt = select(Event)
    events_result = await db.execute(events_stmt)
    total_events = len(events_result.scalars().all())

    summary_data = {
        "total_users": len(all_users),
        "admin_users_count": admin_count,
        "organizer_users_count": organizer_count,
        "verified_users_count": verified_users,
        "unverified_users_count": unverified_users,
        "total_events_in_system": total_events,
        "statistics": {
            "admin_percentage": (
                round((admin_count / len(all_users)) * 100, 2)
                if all_users
                else 0
            ),
            "organizer_percentage": (
                round((organizer_count / len(all_users)) * 100, 2)
                if all_users
                else 0
            ),
            "verification_rate": (
                round((verified_users / len(all_users)) * 100, 2)
                if all_users
                else 0
            ),
        },
    }

    return api_response(
        status_code=200,
        message="Users summary retrieved successfully",
        data=summary_data,
    )
