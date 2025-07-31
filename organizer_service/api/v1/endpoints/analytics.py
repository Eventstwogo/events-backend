from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from organizer_service.schemas.analytics import (
    OrganizerFullDetailsApiResponse,
    OrganizerSummaryApiResponse,
)
from shared.core.api_response import api_response
from shared.core.security import decrypt_data
from shared.db.models import AdminUser, BusinessProfile, Event, EventSlot
from shared.db.sessions.database import get_db
from shared.utils.data_utils import process_business_profile_data
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


def calculate_total_slots(slots_data):
    total = 0
    for slot_obj in slots_data:
        slot_data = slot_obj.get("slot_data", {})
        for date, slots_on_date in slot_data.items():
            total += len(slots_on_date)  # count slot_1, slot_2, etc.
    return total


@router.get(
    "/organizer-details/{user_id}",
    status_code=200,
    response_model=OrganizerFullDetailsApiResponse,
    summary="Get Full Organizer Details",
    description="Fetch complete organizer details including business profile, events, and event slots",
)
@exception_handler
async def get_organizer_full_details(
    user_id: str = Path(
        ..., min_length=6, max_length=12, description="User ID of the organizer"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch full details of an organizer including associated events and event slots.

    This endpoint:
    1. Fetches user from AdminUser table
    2. Checks if business profile exists using business_id from admin user table
    3. Fetches any events associated with the user and their event slots
    4. Returns complete details as response

    Args:
        user_id: The user ID of the organizer
        db: Database session

    Returns:
        Complete organizer details with business profile, events, and event slots
    """

    # Step 1: Fetch user from AdminUser table with related data
    user_stmt = (
        select(AdminUser)
        .options(
            selectinload(AdminUser.user_profile),
            selectinload(AdminUser.business_profile),
            selectinload(AdminUser.role),
        )
        .where(AdminUser.user_id == user_id)
    )

    result = await db.execute(user_stmt)
    admin_user = result.scalars().first()

    if not admin_user:
        return api_response(
            status_code=404, message="Organizer not found", data=None
        )

    # Step 2: Check if business profile exists
    business_profile = None
    business_profile_data = None

    if admin_user.business_id:
        business_stmt = select(BusinessProfile).where(
            BusinessProfile.business_id == admin_user.business_id
        )
        business_result = await db.execute(business_stmt)
        business_profile = business_result.scalars().first()

        if business_profile:
            try:
                # Process business profile data using existing utility
                decrypted_profile, purpose_list = process_business_profile_data(
                    business_profile.profile_details,
                    business_profile.purpose,
                    use_fallback=False,
                )
                business_profile_data = {
                    "business_id": business_profile.business_id,
                    "abn_id": decrypt_data(business_profile.abn_id),
                    "profile_details": decrypted_profile,
                    "business_logo": business_profile.business_logo,
                    "store_name": business_profile.store_name,
                    "store_url": business_profile.store_url,
                    "location": business_profile.location,
                    "ref_number": business_profile.ref_number,
                    "purpose": purpose_list,
                    "is_approved": business_profile.is_approved,
                    "timestamp": business_profile.timestamp,
                }
            except ValueError as e:
                # If decryption fails, still return basic business profile info
                business_profile_data = {
                    "business_id": business_profile.business_id,
                    "abn_id": decrypt_data(business_profile.abn_id),
                    "business_logo": business_profile.business_logo,
                    "store_name": business_profile.store_name,
                    "store_url": business_profile.store_url,
                    "location": business_profile.location,
                    "ref_number": business_profile.ref_number,
                    "is_approved": business_profile.is_approved,
                    "timestamp": business_profile.timestamp,
                    "error": f"Failed to decrypt profile data: {str(e)}",
                }

    # Step 3: Fetch events associated with the user
    events_stmt = (
        select(Event)
        .options(
            selectinload(Event.category),
            selectinload(Event.subcategory),
            selectinload(Event.slots),
        )
        .where(Event.organizer_id == user_id)
        .order_by(Event.created_at.desc())
    )

    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    # Process events data
    events_data = []
    total_events = len(events)
    active_events = 0

    for event in events:
        if not event.event_status:
            active_events += 1

        # Process event slots
        slots_data = []
        for slot in event.slots:
            slots_data.append(
                {
                    "slot_id": slot.slot_id,
                    "slot_data": slot.slot_data,
                    "slot_status": slot.slot_status,
                    "created_at": slot.created_at,
                    "updated_at": slot.updated_at,
                }
            )

        event_data = {
            "event_id": event.event_id,
            "event_slug": event.event_slug,
            "event_title": event.event_title,
            "category": (
                {
                    "category_id": event.category.category_id,
                    "category_name": event.category.category_name,
                }
                if event.category
                else None
            ),
            "subcategory": (
                {
                    "subcategory_id": event.subcategory.subcategory_id,
                    "subcategory_name": event.subcategory.subcategory_name,
                }
                if event.subcategory
                else None
            ),
            "start_date": event.start_date,
            "end_date": event.end_date,
            "location": event.location,
            "is_online": event.is_online,
            "card_image": event.card_image,
            "banner_image": event.banner_image,
            "event_extra_images": event.event_extra_images,
            "extra_data": event.extra_data,
            "hash_tags": event.hash_tags,
            "event_status": event.event_status,
            "slot_id": event.slot_id,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
            "slots": slots_data,
            "total_slots": calculate_total_slots(slots_data),
        }
        events_data.append(event_data)

    # Prepare user profile data
    user_profile_data = None
    if admin_user.user_profile:
        user_profile_data = {
            "profile_id": admin_user.user_profile.profile_id,
            "full_name": admin_user.user_profile.full_name,
            "phone": admin_user.user_profile.phone,
            "address": admin_user.user_profile.address,
            "social_links": admin_user.user_profile.social_links,
            "preferences": admin_user.user_profile.preferences,
            "profile_bio": admin_user.user_profile.profile_bio,
        }

    # Prepare complete response data
    response_data = {
        "organizer_info": {
            "user_id": admin_user.user_id,
            "username": admin_user.username,
            "email": admin_user.email,
            "profile_picture": admin_user.profile_picture,
            "role": (
                {
                    "role_id": admin_user.role.role_id,
                    "role_name": admin_user.role.role_name,
                }
                if admin_user.role
                else None
            ),
            "is_verified": admin_user.is_verified,
            "is_deleted": admin_user.is_deleted,
        },
        "user_profile": user_profile_data,
        "business_profile": business_profile_data,
        "events_summary": {
            "total_events": total_events,
            "active_events": active_events,
            "inactive_events": total_events - active_events,
        },
        "events": events_data,
    }

    return api_response(
        status_code=200,
        message="Organizer details retrieved successfully",
        data=response_data,
    )


@router.get(
    "/organizer-summary/{user_id}",
    status_code=200,
    response_model=OrganizerSummaryApiResponse,
    summary="Get Organizer Summary",
    description="Fetch a lightweight summary of organizer details with statistics",
)
@exception_handler
async def get_organizer_summary(
    user_id: str = Path(
        ..., min_length=6, max_length=12, description="User ID of the organizer"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch a summary of organizer details without full event data.

    This is a lighter version that provides basic organizer info,
    business profile status, and event statistics.

    Args:
        user_id: The user ID of the organizer
        db: Database session

    Returns:
        Summary of organizer details
    """

    # Fetch user with basic relationships
    user_stmt = (
        select(AdminUser)
        .options(
            selectinload(AdminUser.user_profile),
            selectinload(AdminUser.business_profile),
            selectinload(AdminUser.role),
        )
        .where(AdminUser.user_id == user_id)
    )

    result = await db.execute(user_stmt)
    admin_user = result.scalars().first()

    if not admin_user:
        return api_response(
            status_code=404, message="Organizer not found", data=None
        )

    # Check business profile status
    business_profile = admin_user.business_profile
    has_business_profile = business_profile is not None
    business_approved = business_profile.is_approved if business_profile else 0

    # Get event statistics
    events_stmt = select(Event).where(Event.organizer_id == user_id)
    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    total_events = len(events)
    active_events = sum(1 for event in events if not event.event_status)

    # Prepare summary response
    summary_data = {
        "organizer_info": {
            "user_id": admin_user.user_id,
            "username": admin_user.username,
            "email": admin_user.email,
            "profile_picture": admin_user.profile_picture,
            "role_name": admin_user.role.role_name if admin_user.role else None,
            "is_verified": admin_user.is_verified,
            "created_at": admin_user.created_at,
        },
        "business_profile_status": {
            "has_business_profile": has_business_profile,
            "is_approved": business_approved,
            "business_id": (
                admin_user.business_id if has_business_profile else None
            ),
            "store_name": (
                business_profile.store_name if business_profile else None
            ),
        },
        "events_statistics": {
            "total_events": total_events,
            "active_events": active_events,
            "inactive_events": total_events - active_events,
        },
        "profile_completion": {
            "has_user_profile": admin_user.user_profile is not None,
            "has_business_profile": has_business_profile,
            "business_approved": business_approved == 1,
            "completion_percentage": calculate_profile_completion(
                admin_user, has_business_profile, business_approved
            ),
        },
    }

    return api_response(
        status_code=200,
        message="Organizer summary retrieved successfully",
        data=summary_data,
    )


def calculate_profile_completion(
    admin_user: AdminUser, has_business_profile: bool, business_approved: int
) -> int:
    """
    Calculate profile completion percentage based on available data.

    Args:
        admin_user: The AdminUser instance
        has_business_profile: Whether business profile exists
        business_approved: Business approval status

    Returns:
        Completion percentage (0-100)
    """
    completion_score = 0
    total_possible = 4

    # Basic user info (always present if user exists)
    completion_score += 1

    # # User profile exists
    # if admin_user.user_profile:
    #     completion_score += 1

    # Business profile exists
    if has_business_profile:
        completion_score += 1

    # Business profile approved
    if business_approved == 1:
        completion_score += 1

    # Email verified
    if admin_user.is_verified == 1:
        completion_score += 1

    return int((completion_score / total_possible) * 100)
