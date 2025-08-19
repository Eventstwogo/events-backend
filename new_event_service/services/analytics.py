from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.constants import ONBOARDING_UNDER_REVIEW
from shared.core.security import decrypt_data
from shared.db.models import (
    AdminUser,
    BusinessProfile,
)
from shared.db.models.new_events import (
    EventStatus,
    NewEvent,
    NewEventSeatCategory,
    NewEventSlot,
)
from shared.utils.data_utils import process_business_profile_data
from shared.utils.file_uploads import get_media_url


def calculate_total_slots(slots_data: List[Dict]) -> int:
    """Calculate total number of slots from new event slots data."""
    return len(slots_data)


def extra_images_media_urls(value: Optional[List[str]]) -> Optional[List[str]]:
    """Convert extra images to media URLs."""
    if not value:
        return None
    result = [get_media_url(url) for url in value]
    result = [r for r in result if r is not None]
    return result if result else None


async def get_organizer_full_details(user_id: str, db: AsyncSession) -> Dict:
    """
    Fetch full details of an organizer including associated events and event slots.

    This function:
    1. Fetches user from AdminUser table
    2. Checks if business profile exists using business_id from admin user table
    3. Fetches any events associated with the user and their event slots
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
        return {
            "status_code": 404,
            "message": "Organizer not found",
            "data": None,
        }

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

    # Step 3: Fetch new events associated with the user
    events_stmt = (
        select(NewEvent)
        .options(
            selectinload(NewEvent.new_category),
            selectinload(NewEvent.new_subcategory),
            selectinload(NewEvent.new_slots).selectinload(
                NewEventSlot.new_seat_categories
            ),
        )
        .where(NewEvent.organizer_id == user_id)
        .order_by(NewEvent.created_at.desc())
    )

    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    # Process new events data
    events_data = []
    total_events = len(events)
    active_events = 0

    for event in events:
        if event.event_status == EventStatus.ACTIVE:
            active_events += 1

        # Process new event slots
        slots_data = []
        for slot in event.new_slots:
            # Process seat categories for each slot
            seat_categories = []
            for seat_category in slot.new_seat_categories:
                seat_categories.append(
                    {
                        "seat_category_id": seat_category.seat_category_id,
                        "category_label": seat_category.category_label,
                        "price": float(seat_category.price),
                        "total_tickets": seat_category.total_tickets,
                        "booked": seat_category.booked,
                        "held": seat_category.held,
                        "seat_category_status": seat_category.seat_category_status,
                    }
                )

            slots_data.append(
                {
                    "slot_id": slot.slot_id,
                    "slot_date": slot.slot_date,
                    "start_time": slot.start_time,
                    "duration_minutes": slot.duration_minutes,
                    "slot_status": slot.slot_status,
                    "seat_categories": seat_categories,
                }
            )

        event_data = {
            "event_id": event.event_id,
            "event_slug": event.event_slug,
            "event_title": event.event_title,
            "category": (
                {
                    "category_id": event.new_category.category_id,
                    "category_name": event.new_category.category_name,
                }
                if event.new_category
                else None
            ),
            "subcategory": (
                {
                    "subcategory_id": event.new_subcategory.subcategory_id,
                    "subcategory_name": event.new_subcategory.subcategory_name,
                }
                if event.new_subcategory
                else None
            ),
            "event_dates": event.event_dates,
            "location": event.location,
            "is_online": event.is_online,
            "card_image": get_media_url(event.card_image),
            "banner_image": get_media_url(event.banner_image),
            "event_extra_images": extra_images_media_urls(
                event.event_extra_images
            ),
            "extra_data": event.extra_data,
            "hash_tags": event.hash_tags,
            "event_status": event.event_status,
            "featured_event": event.featured_event,
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
            "profile_picture": get_media_url(admin_user.profile_picture),
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

    return {
        "status_code": 200,
        "message": "New event organizer details retrieved successfully",
        "data": response_data,
    }


async def get_organizer_summary(user_id: str, db: AsyncSession) -> Dict:
    """
    Fetch a summary of organizer details without full event data.

    This is a lighter version that provides basic organizer info,
    business profile status, and event statistics.
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
        return {
            "status_code": 404,
            "message": "Organizer not found",
            "data": None,
        }

    # Check business profile status
    business_profile = admin_user.business_profile
    has_business_profile = business_profile is not None
    business_approved = (
        business_profile.is_approved
        if business_profile
        else ONBOARDING_UNDER_REVIEW
    )

    # Get new event statistics
    events_stmt = select(NewEvent).where(NewEvent.organizer_id == user_id)
    events_result = await db.execute(events_stmt)
    events = events_result.scalars().all()

    total_events = len(events)
    active_events = sum(
        1 for event in events if event.event_status == EventStatus.ACTIVE
    )

    # Calculate profile completion percentage
    completion_score = 0
    if admin_user.user_profile:
        completion_score += 25
    if has_business_profile:
        completion_score += 25
    if business_approved == 1:
        completion_score += 25
    if admin_user.is_verified:
        completion_score += 25

    # Prepare summary response
    summary_data = {
        "organizer_info": {
            "user_id": admin_user.user_id,
            "username": admin_user.username,
            "email": admin_user.email,
            "profile_picture": get_media_url(admin_user.profile_picture),
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
            "completion_percentage": completion_score,
        },
    }

    return {
        "status_code": 200,
        "message": "New event organizer summary retrieved successfully",
        "data": summary_data,
    }
