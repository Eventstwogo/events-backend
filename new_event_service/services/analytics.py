from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_event_service.services.event_fetcher import EventTypeStatus, get_event_conditions
from shared.constants import ONBOARDING_UNDER_REVIEW
from shared.core.logging_config import get_logger
from shared.core.security import decrypt_data
from shared.db.models import (
    AdminUser,
    BusinessProfile,
)
from shared.db.models.new_events import (
    BookingStatus,
    EventStatus,
    NewEvent,
    NewEventBooking,
    NewEventBookingOrder,
    NewEventSlot,
    PaymentStatus,
)
from shared.db.models.rbac import Role
from shared.utils.data_utils import process_business_profile_data
from shared.utils.file_uploads import get_media_url

logger = get_logger(__name__)


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


async def get_organizer_full_details(
    user_id: str, db: AsyncSession, event_type: EventTypeStatus
) -> Dict:
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
    current_date = date.today()

    # Step 3: Build event filter conditions
    base_conditions = [NewEvent.organizer_id == user_id]

    # Unpack conditions + alias from helper
    base_conditions.extend(get_event_conditions(event_type))

    # Step 4: Fetch new events with filters
    events_stmt = (
        select(NewEvent)
        .options(
            selectinload(NewEvent.new_category),
            selectinload(NewEvent.new_subcategory),
            selectinload(NewEvent.new_slots).selectinload(
                NewEventSlot.new_seat_categories
            ),
        )
        .where(and_(*base_conditions))
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


async def fetch_organizer_events_analytics(db: AsyncSession) -> Dict:
    """
    Fetch analytics for all organizer-created events (new tables).
    """

    # Get all events created by organizers
    events_query = (
        select(NewEvent)
        .options(
            selectinload(NewEvent.new_category),
            selectinload(NewEvent.new_subcategory),
            selectinload(NewEvent.new_organizer).selectinload(AdminUser.role),
            selectinload(NewEvent.new_slots),
        )
        .join(AdminUser, NewEvent.organizer_id == AdminUser.user_id)
        .join(Role, AdminUser.role_id == Role.role_id)
        .filter(Role.role_name.ilike("organizer"))
        .order_by(desc(NewEvent.created_at))
    )
    events_result = await db.execute(events_query)
    events = list(events_result.scalars().all())

    # Calculate analytics
    analytics = calculate_events_analytics(events)

    # Organizer statistics
    organizer_stats_query = (
        select(
            AdminUser.user_id,
            AdminUser.username_hash,
            func.count(NewEvent.event_id).label("event_count"),
        )
        .join(NewEvent, AdminUser.user_id == NewEvent.organizer_id)
        .join(Role, AdminUser.role_id == Role.role_id)
        .filter(Role.role_name.ilike("organizer"))
        .group_by(AdminUser.user_id, AdminUser.username_hash)
        .order_by(desc("event_count"))
        .limit(10)
    )
    organizer_stats_result = await db.execute(organizer_stats_query)
    top_organizers = [
        {
            "organizer_id": row.user_id,
            "username_hash": row.username_hash,
            "event_count": row.event_count,
        }
        for row in organizer_stats_result
    ]

    # Total organizers
    total_organizers_query = (
        select(func.count(AdminUser.user_id))
        .join(Role, AdminUser.role_id == Role.role_id)
        .filter(Role.role_name.ilike("organizer"))
    )
    total_organizers_result = await db.execute(total_organizers_query)
    total_organizers = total_organizers_result.scalar() or 0

    return {
        "events_analytics": analytics["events_analytics"],
        "slots_analytics": analytics["slots_analytics"],
        "organizer_statistics": {
            "total_organizers": total_organizers,
            "top_organizers": top_organizers,
        },
    }


async def fetch_admin_events_analytics(db: AsyncSession) -> Dict:
    """
    Fetch comprehensive analytics for all events in the system (new tables).
    Separates organizer-created and admin-created events.
    """

    # Fetch all events with organizer & role
    all_events_query = (
        select(NewEvent)
        .options(
            selectinload(NewEvent.new_category),
            selectinload(NewEvent.new_subcategory),
            selectinload(NewEvent.new_organizer).selectinload(AdminUser.role),
            selectinload(NewEvent.new_slots),
        )
        .order_by(desc(NewEvent.created_at))
    )
    all_events_result = await db.execute(all_events_query)
    all_events = list(all_events_result.scalars().all())

    # Separate organizer vs admin created
    organizer_events = []
    admin_events = []
    for event in all_events:
        if (
            event.new_organizer
            and event.new_organizer.role
            and event.new_organizer.role.role_name.lower() == "organizer"
        ):
            organizer_events.append(event)
        else:
            admin_events.append(event)

    # Calculate analytics
    organizer_analytics = calculate_events_analytics(organizer_events)
    admin_analytics = calculate_events_analytics(admin_events)
    overall_analytics = calculate_events_analytics(all_events)

    # User statistics
    # Total users by role
    user_stats_query = (
        select(
            Role.role_name, func.count(AdminUser.user_id).label("user_count")
        )
        .join(AdminUser, Role.role_id == AdminUser.role_id)
        .group_by(Role.role_name)
    )
    user_stats_result = await db.execute(user_stats_query)
    users_by_role = {row.role_name: row.user_count for row in user_stats_result}

    # Top organizers by event count
    top_organizers_query = (
        select(
            AdminUser.user_id,
            AdminUser.username_hash,
            func.count(NewEvent.event_id).label("event_count"),
        )
        .join(NewEvent, AdminUser.user_id == NewEvent.organizer_id)
        .join(Role, AdminUser.role_id == Role.role_id)
        .filter(Role.role_name.ilike("organizer"))
        .group_by(AdminUser.user_id, AdminUser.username_hash)
        .order_by(desc("event_count"))
        .limit(10)
    )
    top_organizers_result = await db.execute(top_organizers_query)
    top_organizers = [
        {
            "organizer_id": row.user_id,
            "username_hash": row.username_hash,
            "event_count": row.event_count,
        }
        for row in top_organizers_result
    ]

    # Top admins by event count
    top_admins_query = (
        select(
            AdminUser.user_id,
            AdminUser.username_hash,
            func.count(NewEvent.event_id).label("event_count"),
        )
        .join(NewEvent, AdminUser.user_id == NewEvent.organizer_id)
        .join(Role, AdminUser.role_id == Role.role_id)
        .filter(Role.role_name.ilike("admin"))
        .group_by(AdminUser.user_id, AdminUser.username_hash)
        .order_by(desc("event_count"))
        .limit(10)
    )
    top_admins_result = await db.execute(top_admins_query)
    top_admins = [
        {
            "admin_id": row.user_id,
            "username_hash": row.username_hash,
            "event_count": row.event_count,
        }
        for row in top_admins_result
    ]

    return {
        "overall_analytics": {
            "events_analytics": overall_analytics["events_analytics"],
            "slots_analytics": overall_analytics["slots_analytics"],
        },
        "organizer_created_analytics": {
            "events_analytics": organizer_analytics["events_analytics"],
            "slots_analytics": organizer_analytics["slots_analytics"],
        },
        "admin_created_analytics": {
            "events_analytics": admin_analytics["events_analytics"],
            "slots_analytics": admin_analytics["slots_analytics"],
        },
        "user_statistics": {
            "users_by_role": users_by_role,
            "top_organizers": top_organizers,
            "top_admins": top_admins,
        },
    }


def calculate_events_analytics(events: List[NewEvent]) -> Dict:
    """
    Calculate analytics for a list of new events.
    """

    total_events = len(events)
    active_events = len(
        [e for e in events if e.event_status == EventStatus.ACTIVE]
    )
    draft_events = len(
        [e for e in events if e.event_status == EventStatus.INACTIVE]
    )
    pending_events = len(
        [e for e in events if e.event_status == EventStatus.PENDING]
    )
    featured_events = len([e for e in events if e.featured_event])

    today = date.today()

    # Upcoming = has future date in event_dates or slots
    upcoming_events = len(
        [
            e
            for e in events
            if e.event_status == EventStatus.ACTIVE
            and (
                any(d >= today for d in e.event_dates)
                or any(slot.slot_date >= today for slot in e.new_slots)
            )
        ]
    )

    # Past = all event dates and slots are < today
    past_events = len(
        [
            e
            for e in events
            if e.event_status == EventStatus.ACTIVE
            and all(d < today for d in e.event_dates)
            and all(slot.slot_date < today for slot in e.new_slots)
        ]
    )

    # Slots analytics
    total_slots = 0
    active_slots = 0
    draft_slots = 0

    for event in events:
        for slot in event.new_slots:
            total_slots += 1
            if slot.slot_status:  # True = draft (based on your schema)
                draft_slots += 1
            else:
                active_slots += 1

    # Events by category
    events_by_category = {}
    for event in events:
        if event.new_category:
            category_name = event.new_category.category_name
            if category_name not in events_by_category:
                events_by_category[category_name] = {
                    "total": 0,
                    "active": 0,
                    "draft": 0,
                    "pending": 0,
                }
            events_by_category[category_name]["total"] += 1
            if event.event_status == EventStatus.INACTIVE:
                events_by_category[category_name]["draft"] += 1
            elif event.event_status == EventStatus.ACTIVE:
                events_by_category[category_name]["active"] += 1
            else:
                events_by_category[category_name]["pending"] += 1

    # Events by month (created_at)
    events_by_month = {}
    for event in events:
        month_key = event.created_at.strftime("%Y-%m")
        if month_key not in events_by_month:
            events_by_month[month_key] = 0
        events_by_month[month_key] += 1

    return {
        "events_analytics": {
            "total_events": total_events,
            "active_events": active_events,
            "draft_events": draft_events,
            "pending_events": pending_events,
            "featured_events": featured_events,
            "upcoming_events": upcoming_events,
            "past_events": past_events,
            "events_by_category": events_by_category,
            "events_by_month": events_by_month,
        },
        "slots_analytics": {
            "total_slots": total_slots,
            "active_slots": active_slots,
            "draft_slots": draft_slots,
        },
    }


async def fetch_event_statistics(db: AsyncSession) -> Dict:
    """
    Fetch simple event statistics including active events, upcoming events,
    and monthly growth percentage based on new event tables.
    """
    logger.info("Fetching event statistics")

    # Get current date and calculate date ranges
    today = date.today()
    current_month_start = today.replace(day=1)

    # Calculate previous month start
    if current_month_start.month == 1:
        previous_month_start = current_month_start.replace(
            year=current_month_start.year - 1, month=12
        )
    else:
        previous_month_start = current_month_start.replace(
            month=current_month_start.month - 1
        )

    # -------------------- Active events -------------------- #
    active_events_query = select(func.count(NewEvent.event_id)).filter(
        NewEvent.event_status == EventStatus.ACTIVE
    )
    active_events_result = await db.execute(active_events_query)
    active_events_count = active_events_result.scalar() or 0

    # -------------------- Upcoming events -------------------- #
    # Get conditions for upcoming events (present + future dates)
    event_conditions = get_event_conditions(EventTypeStatus.UPCOMING)
    upcoming_events_query = select(func.count(NewEvent.event_id)).filter(
        and_(
            NewEvent.event_status == EventStatus.ACTIVE,
            *event_conditions  # unpack list of conditions
        )
    )
    upcoming_events_result = await db.execute(upcoming_events_query)
    upcoming_events_count = upcoming_events_result.scalar() or 0

    # -------------------- Current month events -------------------- #
    current_month_events_query = select(func.count(NewEvent.event_id)).filter(
        NewEvent.created_at >= current_month_start
    )
    current_month_events_result = await db.execute(current_month_events_query)
    current_month_events = current_month_events_result.scalar() or 0

    # -------------------- Previous month events -------------------- #
    previous_month_events_query = select(func.count(NewEvent.event_id)).filter(
        and_(
            NewEvent.created_at >= previous_month_start,
            NewEvent.created_at < current_month_start,
        )
    )
    previous_month_events_result = await db.execute(previous_month_events_query)
    previous_month_events = previous_month_events_result.scalar() or 0

    # -------------------- Growth percentage -------------------- #
    if previous_month_events > 0:
        monthly_growth_percentage = round(
            (
                (current_month_events - previous_month_events)
                / previous_month_events
            )
            * 100,
            2,
        )
    else:
        monthly_growth_percentage = 100.0 if current_month_events > 0 else 0.0

    logger.info(
        f"Event stats: active={active_events_count}, upcoming={upcoming_events_count}, "
        f"growth={monthly_growth_percentage}%, current_month={current_month_events}, prev_month={previous_month_events}"
    )

    return {
        "active_events_count": active_events_count,
        "upcoming_events_count": upcoming_events_count,
        "monthly_growth_percentage": monthly_growth_percentage,
        "current_month_events": current_month_events,
        "previous_month_events": previous_month_events,
    }


async def fetch_booking_analytics(db: AsyncSession) -> Dict:
    """
    Fetch comprehensive booking analytics from new booking tables.

    Returns:
    - Total bookings (count of booking line items)
    - Total revenue (sum of order total_amount for approved+completed payments)
    - Approved bookings (count of orders with status APPROVED)
    - Average booking value (average order total_amount)
    """
    logger.info("Fetching booking analytics")

    # -------------------- Total bookings -------------------- #
    # Count booking line items (not seats)
    total_bookings_query = select(func.count(NewEventBooking.booking_id))
    total_bookings_result = await db.execute(total_bookings_query)
    total_bookings = total_bookings_result.scalar() or 0

    # -------------------- Total revenue -------------------- #
    # Use total_amount from orders with APPROVED + COMPLETED
    total_revenue_query = select(
        func.coalesce(func.sum(NewEventBookingOrder.total_amount), 0)
    ).filter(
        NewEventBookingOrder.booking_status == BookingStatus.APPROVED,
        NewEventBookingOrder.payment_status == PaymentStatus.COMPLETED,
    )
    total_revenue_result = await db.execute(total_revenue_query)
    total_revenue = float(total_revenue_result.scalar() or 0)

    # -------------------- Approved bookings count -------------------- #
    approved_bookings_query = select(
        func.count(NewEventBookingOrder.order_id)
    ).filter(NewEventBookingOrder.booking_status == BookingStatus.APPROVED)
    approved_bookings_result = await db.execute(approved_bookings_query)
    approved_bookings = approved_bookings_result.scalar() or 0

    # -------------------- Average booking value -------------------- #
    avg_booking_value_query = select(
        func.avg(NewEventBookingOrder.total_amount)
    )
    avg_booking_value_result = await db.execute(avg_booking_value_query)
    average_booking_value = float(avg_booking_value_result.scalar() or 0)

    logger.info(
        f"Booking analytics: total_bookings={total_bookings}, "
        f"total_revenue={total_revenue}, approved_bookings={approved_bookings}, "
        f"average_booking_value={average_booking_value}"
    )

    return {
        "booking_analytics": {
            "total_bookings": total_bookings,
            "total_revenue": round(total_revenue, 2),
            "approved_bookings": approved_bookings,
            "average_booking_value": round(average_booking_value, 2),
        }
    }


async def fetch_event_booking_stats_by_time_range(db: AsyncSession) -> Dict:
    """
    Fetch event booking statistics for different time ranges.

    Returns statistics for each event including:
    - Total seats booked
    - Total revenue

    Time ranges: daily, weekly, monthly, yearly, and all-time
    """
    logger.info("Fetching event booking statistics by time range")

    # Get current date and calculate date ranges
    today = date.today()

    # Daily: today
    daily_start = today

    # Weekly: last 7 days
    weekly_start = today - timedelta(days=7)

    # Monthly: current month
    monthly_start = today.replace(day=1)

    # Yearly: current year
    yearly_start = today.replace(month=1, day=1)

    async def get_event_stats_for_period(
        start_date: Optional[date] = None,
    ) -> List[Dict]:
        """Helper function to get event booking stats for a specific period"""
        query = (
            select(
                NewEvent.event_id,
                NewEvent.event_title,
                func.sum(NewEventBooking.num_seats).label("total_seats_booked"),
                func.sum(NewEventBooking.total_price).label("total_revenue"),
            )
            .join(
                NewEventBookingOrder,
                NewEventBookingOrder.event_ref_id == NewEvent.event_id,
            )
            .join(
                NewEventBooking,
                NewEventBooking.order_id == NewEventBookingOrder.order_id,
            )
            .group_by(NewEvent.event_id, NewEvent.event_title)
            .order_by(desc("total_revenue"))
        )

        # Add date filter if specified
        if start_date:
            query = query.filter(NewEventBooking.created_at >= start_date)

        result = await db.execute(query)
        return [
            {
                "event_id": row.event_id,
                "event_title": row.event_title,
                "total_seats_booked": int(row.total_seats_booked or 0),
                "total_revenue": float(row.total_revenue or 0),
            }
            for row in result
        ]

    # Get statistics for each time range
    daily_stats = await get_event_stats_for_period(daily_start)
    weekly_stats = await get_event_stats_for_period(weekly_start)
    monthly_stats = await get_event_stats_for_period(monthly_start)
    yearly_stats = await get_event_stats_for_period(yearly_start)
    all_time_stats = await get_event_stats_for_period()  # No filter

    logger.info(
        f"Event booking stats calculated: daily={len(daily_stats)}, "
        f"weekly={len(weekly_stats)}, monthly={len(monthly_stats)}, "
        f"yearly={len(yearly_stats)}, all_time={len(all_time_stats)}"
    )

    return {
        "event_booking_stats": {
            "daily": daily_stats,
            "weekly": weekly_stats,
            "monthly": monthly_stats,
            "yearly": yearly_stats,
            "all_time": all_time_stats,
        }
    }
