from datetime import date, datetime, timedelta
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from organizer_service.schemas.analytics import (
    BookingAnalyticsApiResponse,
    DashboardOverviewApiResponse,
    EventAnalyticsApiResponse,
    OrganizerFullDetailsApiResponse,
    OrganizerSummaryApiResponse,
    PerformanceMetricsApiResponse,
    QueryAnalyticsApiResponse,
)
from organizer_service.services.analytics import (
    calculate_date_range,
    get_booking_statistics_and_revenue,
    get_event_statistics,
    get_query_statistics,
    get_recent_events,
    validate_user_access,
)
from shared.constants import ONBOARDING_UNDER_REVIEW
from shared.core.api_response import api_response
from shared.core.security import decrypt_data
from shared.db.models import AdminUser, BusinessProfile, Event
from shared.db.models.events import BookingStatus, EventBooking
from shared.db.models.organizer import OrganizerQuery
from shared.db.sessions.database import get_db
from shared.dependencies.admin import get_current_active_user
from shared.utils.data_utils import process_business_profile_data
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url

router = APIRouter()


def calculate_total_slots(slots_data):
    total = 0
    for slot_obj in slots_data:
        slot_data = slot_obj.get("slot_data", {})
        for date, slots_on_date in slot_data.items():
            total += len(slots_on_date)  # count slot_1, slot_2, etc.
    return total


def extra_images_media_urls(value: Optional[List[str]]) -> Optional[List[str]]:
    if not value:
        return None
    result = [get_media_url(url) for url in value]
    result = [r for r in result if r is not None]
    return result if result else None


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
            "card_image": get_media_url(event.card_image),
            "banner_image": get_media_url(event.banner_image),
            "event_extra_images": extra_images_media_urls(
                event.event_extra_images
            ),
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
    business_approved = (
        business_profile.is_approved
        if business_profile
        else ONBOARDING_UNDER_REVIEW
    )

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


# New Dashboard Analytics Endpoints


@router.get(
    "/dashboard-overview",
    status_code=200,
    response_model=DashboardOverviewApiResponse,
    summary="Get Dashboard Overview Analytics",
    description="Fetch comprehensive dashboard analytics for authenticated organizer including events, bookings, queries, and revenue metrics",
)
@exception_handler
async def get_dashboard_overview(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    period: str = Query(
        "30d",
        description="Time period for analytics (7d, 30d, 90d, 1y)",
        regex="^(7d|30d|90d|1y)$",
    ),
    db: AsyncSession = Depends(get_db),
):
    # Validate user access
    access_error = await validate_user_access(current_user, db)
    if access_error:
        return access_error

    # Date range
    start_date, end_date = calculate_date_range(period)

    # Fetch statistics
    event_stats = await get_event_statistics(db, current_user.user_id, end_date)
    booking_stats, revenue_stats = await get_booking_statistics_and_revenue(
        db, current_user.user_id, start_date, end_date
    )
    query_stats = await get_query_statistics(
        db, current_user.user_id, start_date, end_date
    )
    recent_events = await get_recent_events(db, current_user.user_id)

    # Response payload
    dashboard_data = {
        "period": period,
        "date_range": {"start_date": start_date, "end_date": end_date},
        "event_statistics": event_stats,
        "booking_statistics": booking_stats,
        "revenue_statistics": revenue_stats,
        "query_statistics": query_stats,
        "recent_events": recent_events,
    }

    return api_response(
        status_code=200,
        message="Dashboard overview retrieved successfully",
        data=dashboard_data,
    )


@router.get(
    "/event-analytics",
    status_code=200,
    response_model=EventAnalyticsApiResponse,
    summary="Get Event Analytics",
    description="Fetch detailed event analytics including performance metrics, booking trends, and event comparisons",
)
@exception_handler
async def get_event_analytics(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    period: str = Query(
        "30d",
        description="Time period for analytics (7d, 30d, 90d, 1y)",
        regex="^(7d|30d|90d|1y)$",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed event analytics for authenticated organizer dashboard.

    Requirements:
    - User must have organizer role
    - User must have a business profile
    - Revenue calculations only include approved bookings with completed payments

    Includes:
    - Event performance metrics
    - Booking trends by event
    - Popular categories
    - Event success rates
    - Seasonal trends
    """

    user_id = current_user.user_id

    # Constraint 1: Check if user has organizer role
    if (
        not current_user.role
        or current_user.role.role_name.lower() != "organizer"
    ):
        return api_response(
            status_code=403,
            message="Access denied. This endpoint is restricted to organizers only.",
            data=None,
        )

    # Constraint 2: Check if user has business profile
    if not current_user.business_id:
        return api_response(
            status_code=400,
            message="Business profile required. Please complete your business profile to access event analytics.",
            data=None,
        )

    # Verify business profile exists
    business_stmt = select(BusinessProfile).where(
        BusinessProfile.business_id == current_user.business_id
    )
    business_result = await db.execute(business_stmt)
    business_profile = business_result.scalars().first()

    if not business_profile:
        return api_response(
            status_code=400,
            message="Business profile not found. Please complete your business profile to access event analytics.",
            data=None,
        )

    # Calculate date range
    end_date = date.today()
    if period == "7d":
        start_date = end_date - timedelta(days=7)
    elif period == "30d":
        start_date = end_date - timedelta(days=30)
    elif period == "90d":
        start_date = end_date - timedelta(days=90)
    elif period == "1y":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)

    # Get events with booking data
    events_with_bookings_stmt = (
        select(
            Event,
            func.count(EventBooking.booking_id).label("total_bookings"),
            func.sum(EventBooking.total_price).label("total_revenue"),
        )
        .outerjoin(EventBooking, Event.event_id == EventBooking.event_id)
        .options(selectinload(Event.category), selectinload(Event.subcategory))
        .where(Event.organizer_id == user_id)
        .group_by(Event.event_id)
        .order_by(desc("total_bookings"))
    )

    events_result = await db.execute(events_with_bookings_stmt)
    events_data = events_result.all()

    # Process event performance data
    event_performance = []
    category_stats = {}

    for event, booking_count, revenue in events_data:
        # Calculate event metrics
        event_revenue = float(revenue) if revenue else 0.0

        event_performance.append(
            {
                "event_id": event.event_id,
                "event_title": event.event_title,
                "category_name": (
                    event.category.category_name
                    if event.category
                    else "Uncategorized"
                ),
                "start_date": event.start_date,
                "end_date": event.end_date,
                "total_bookings": booking_count or 0,
                "total_revenue": round(event_revenue, 2),
                "event_status": event.event_status,
                "is_online": event.is_online,
                "card_image": get_media_url(event.card_image),
            }
        )

        # Aggregate category statistics
        category_name = (
            event.category.category_name if event.category else "Uncategorized"
        )
        if category_name not in category_stats:
            category_stats[category_name] = {
                "category_name": category_name,
                "event_count": 0,
                "total_bookings": 0,
                "total_revenue": 0.0,
            }

        category_stats[category_name]["event_count"] += 1
        category_stats[category_name]["total_bookings"] += booking_count or 0
        category_stats[category_name]["total_revenue"] += event_revenue

    # Convert category stats to list and sort by revenue
    popular_categories = sorted(
        list(category_stats.values()),
        key=lambda x: x["total_revenue"],
        reverse=True,
    )

    # Get booking trends over time
    booking_trends_stmt = (
        select(
            func.date(EventBooking.booking_date).label("booking_date"),
            func.count(EventBooking.booking_id).label("daily_bookings"),
            func.sum(EventBooking.total_price).label("daily_revenue"),
        )
        .join(Event, EventBooking.event_id == Event.event_id)
        .where(
            and_(
                Event.organizer_id == user_id,
                EventBooking.booking_date >= start_date,
                EventBooking.booking_date <= end_date,
                EventBooking.booking_status == BookingStatus.APPROVED,
            )
        )
        .group_by(func.date(EventBooking.booking_date))
        .order_by(func.date(EventBooking.booking_date))
    )

    trends_result = await db.execute(booking_trends_stmt)
    booking_trends = []

    for booking_date, daily_bookings, daily_revenue in trends_result:
        booking_trends.append(
            {
                "date": booking_date,
                "bookings": daily_bookings,
                "revenue": round(float(daily_revenue), 2),
            }
        )

    # Calculate success metrics
    total_events = len(events_data)
    events_with_bookings = sum(
        1 for _, bookings, _ in events_data if bookings and bookings > 0
    )
    success_rate = round(
        (events_with_bookings / total_events * 100) if total_events > 0 else 0,
        2,
    )

    analytics_data = {
        "period": period,
        "date_range": {"start_date": start_date, "end_date": end_date},
        "event_performance": event_performance[:10],  # Top 10 events
        "popular_categories": popular_categories[:5],  # Top 5 categories
        "booking_trends": booking_trends,
        "success_metrics": {
            "total_events": total_events,
            "events_with_bookings": events_with_bookings,
            "success_rate": success_rate,
            "average_bookings_per_event": round(
                (
                    sum(b or 0 for _, b, _ in events_data) / total_events
                    if total_events > 0
                    else 0
                ),
                2,
            ),
        },
    }

    return api_response(
        status_code=200,
        message="Event analytics retrieved successfully",
        data=analytics_data,
    )


@router.get(
    "/booking-analytics",
    status_code=200,
    response_model=BookingAnalyticsApiResponse,
    summary="Get Booking Analytics",
    description="Fetch detailed booking analytics including revenue trends, customer insights, and booking patterns",
)
@exception_handler
async def get_booking_analytics(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    period: str = Query(
        "30d",
        description="Time period for analytics (7d, 30d, 90d, 1y)",
        regex="^(7d|30d|90d|1y)$",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed booking analytics for authenticated organizer dashboard.

    Includes:
    - Revenue trends and forecasting
    - Booking status distribution
    - Customer booking patterns
    - Peak booking times
    - Average booking values
    """

    user_id = current_user.user_id

    # Calculate date range
    end_date = date.today()
    if period == "7d":
        start_date = end_date - timedelta(days=7)
    elif period == "30d":
        start_date = end_date - timedelta(days=30)
    elif period == "90d":
        start_date = end_date - timedelta(days=90)
    elif period == "1y":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)

    # Get all bookings for the organizer in the period
    bookings_stmt = (
        select(EventBooking, Event.event_title, Event.category_id)
        .join(Event, EventBooking.event_id == Event.event_id)
        .options(selectinload(EventBooking.user))
        .where(
            and_(
                Event.organizer_id == user_id,
                EventBooking.booking_date >= start_date,
                EventBooking.booking_date <= end_date,
            )
        )
        .order_by(desc(EventBooking.created_at))
    )

    bookings_result = await db.execute(bookings_stmt)
    bookings_data = bookings_result.all()

    # Process booking statistics
    total_bookings = len(bookings_data)
    status_distribution = {
        "approved": 0,
        "pending": 0,
        "cancelled": 0,
        "failed": 0,
    }

    total_revenue = 0.0
    pending_revenue = 0.0
    customer_bookings = {}
    daily_bookings = {}

    for booking, event_title, category_id in bookings_data:
        # Status distribution
        if booking.booking_status == BookingStatus.APPROVED:
            status_distribution["approved"] += 1
            total_revenue += float(booking.total_price)
        elif booking.booking_status == BookingStatus.PROCESSING:
            status_distribution["pending"] += 1
            pending_revenue += float(booking.total_price)
        elif booking.booking_status == BookingStatus.CANCELLED:
            status_distribution["cancelled"] += 1
        elif booking.booking_status == BookingStatus.FAILED:
            status_distribution["failed"] += 1

        # Customer booking patterns
        user_id_key = booking.user_id
        if user_id_key not in customer_bookings:
            customer_bookings[user_id_key] = {
                "user_id": user_id_key,
                "total_bookings": 0,
                "total_spent": 0.0,
                "last_booking": booking.booking_date,
            }

        customer_bookings[user_id_key]["total_bookings"] += 1
        if booking.booking_status == BookingStatus.APPROVED:
            customer_bookings[user_id_key]["total_spent"] += float(
                booking.total_price
            )

        if (
            booking.booking_date
            > customer_bookings[user_id_key]["last_booking"]
        ):
            customer_bookings[user_id_key][
                "last_booking"
            ] = booking.booking_date

        # Daily booking trends
        booking_date_str = booking.booking_date.strftime("%Y-%m-%d")
        if booking_date_str not in daily_bookings:
            daily_bookings[booking_date_str] = {
                "date": booking.booking_date,
                "bookings": 0,
                "revenue": 0.0,
            }

        daily_bookings[booking_date_str]["bookings"] += 1
        if booking.booking_status == BookingStatus.APPROVED:
            daily_bookings[booking_date_str]["revenue"] += float(
                booking.total_price
            )

    # Get top customers
    top_customers = sorted(
        list(customer_bookings.values()),
        key=lambda x: x["total_spent"],
        reverse=True,
    )[:10]

    # Convert daily bookings to sorted list
    booking_trends = sorted(
        list(daily_bookings.values()), key=lambda x: x["date"]
    )

    # Calculate metrics
    average_booking_value = round(
        (
            (total_revenue / status_distribution["approved"])
            if status_distribution["approved"] > 0
            else 0
        ),
        2,
    )
    conversion_rate = round(
        (
            (status_distribution["approved"] / total_bookings * 100)
            if total_bookings > 0
            else 0
        ),
        2,
    )

    # Get recent bookings
    recent_bookings = []
    for booking, event_title, category_id in bookings_data[:10]:
        recent_bookings.append(
            {
                "booking_id": booking.booking_id,
                "event_title": event_title,
                "user_id": booking.user_id,
                "num_seats": booking.num_seats,
                "total_price": float(booking.total_price),
                "booking_status": booking.booking_status.value,
                "booking_date": booking.booking_date,
                "created_at": booking.created_at,
            }
        )

    analytics_data = {
        "period": period,
        "date_range": {"start_date": start_date, "end_date": end_date},
        "booking_summary": {
            "total_bookings": total_bookings,
            "total_revenue": round(total_revenue, 2),
            "pending_revenue": round(pending_revenue, 2),
            "average_booking_value": average_booking_value,
            "conversion_rate": conversion_rate,
        },
        "status_distribution": status_distribution,
        "booking_trends": booking_trends,
        "top_customers": top_customers,
        "recent_bookings": recent_bookings,
    }

    return api_response(
        status_code=200,
        message="Booking analytics retrieved successfully",
        data=analytics_data,
    )


@router.get(
    "/query-analytics",
    status_code=200,
    response_model=QueryAnalyticsApiResponse,
    summary="Get Query Analytics",
    description="Fetch detailed query analytics including resolution trends, query types, and response times",
)
@exception_handler
async def get_query_analytics(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    period: str = Query(
        "30d",
        description="Time period for analytics (7d, 30d, 90d, 1y)",
        regex="^(7d|30d|90d|1y)$",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed query analytics for authenticated organizer dashboard.

    Includes:
    - Query volume trends
    - Resolution time analytics
    - Query status distribution
    - Common query topics
    - Response performance metrics
    """

    user_id = current_user.user_id

    # Calculate date range
    end_date = date.today()
    if period == "7d":
        start_date = end_date - timedelta(days=7)
    elif period == "30d":
        start_date = end_date - timedelta(days=30)
    elif period == "90d":
        start_date = end_date - timedelta(days=90)
    elif period == "1y":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)

    # Get queries for the organizer in the period - Fixed: queries TO the organizer
    queries_stmt = (
        select(OrganizerQuery)
        .where(
            and_(
                OrganizerQuery.receiver_user_id
                == user_id,  # Fixed: queries TO the organizer
                OrganizerQuery.created_at
                >= datetime.combine(start_date, datetime.min.time()),
                OrganizerQuery.created_at
                <= datetime.combine(end_date, datetime.max.time()),
            )
        )
        .order_by(desc(OrganizerQuery.created_at))
    )

    queries_result = await db.execute(queries_stmt)
    queries = queries_result.scalars().all()

    # Process query statistics
    total_queries = len(queries)
    status_distribution = {
        "open": 0,
        "in-progress": 0,
        "resolved": 0,
        "closed": 0,
    }

    daily_queries = {}
    resolution_times = []

    for query in queries:
        # Status distribution
        status_key = query.query_status.value
        if status_key in status_distribution:
            status_distribution[status_key] += 1

        # Daily query trends
        query_date_str = query.created_at.date().strftime("%Y-%m-%d")
        if query_date_str not in daily_queries:
            daily_queries[query_date_str] = {
                "date": query.created_at.date(),
                "queries": 0,
            }
        daily_queries[query_date_str]["queries"] += 1

        # Calculate resolution time for resolved queries
        if query.query_status.value == "resolved" and query.updated_at:
            resolution_time = (
                query.updated_at - query.created_at
            ).total_seconds() / 3600  # in hours
            resolution_times.append(resolution_time)

    # Convert daily queries to sorted list
    query_trends = sorted(list(daily_queries.values()), key=lambda x: x["date"])

    # Calculate resolution metrics
    average_resolution_time = round(
        (
            sum(resolution_times) / len(resolution_times)
            if resolution_times
            else 0
        ),
        2,
    )
    resolution_rate = round(
        (
            (status_distribution["resolved"] / total_queries * 100)
            if total_queries > 0
            else 0
        ),
        2,
    )

    # Get recent queries
    recent_queries = []
    for query in queries[:10]:
        recent_queries.append(
            {
                "query_id": query.id,  # Using 'id' as per the model
                "title": query.title,
                "category": query.category,
                "status": query.query_status.value,
                "created_at": query.created_at,
                "updated_at": query.updated_at,
            }
        )

    analytics_data = {
        "period": period,
        "date_range": {"start_date": start_date, "end_date": end_date},
        "query_summary": {
            "total_queries": total_queries,
            "resolution_rate": resolution_rate,
            "average_resolution_time_hours": average_resolution_time,
            "pending_queries": status_distribution["open"],
        },
        "status_distribution": status_distribution,
        "query_trends": query_trends,
        "recent_queries": recent_queries,
    }

    return api_response(
        status_code=200,
        message="Query analytics retrieved successfully",
        data=analytics_data,
    )


@router.get(
    "/performance-metrics",
    status_code=200,
    response_model=PerformanceMetricsApiResponse,
    summary="Get Performance Metrics",
    description="Fetch comprehensive performance metrics including growth rates, comparisons, and KPIs",
)
@exception_handler
async def get_performance_metrics(
    current_user: Annotated[AdminUser, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive performance metrics for authenticated organizer dashboard.

    Includes:
    - Growth rates (events, bookings, revenue)
    - Period-over-period comparisons
    - Key performance indicators
    - Trend analysis
    """

    user_id = current_user.user_id

    # Define periods for comparison
    today = date.today()
    current_month_start = today.replace(day=1)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = current_month_start - timedelta(days=1)

    current_quarter_start = date(
        today.year, ((today.month - 1) // 3) * 3 + 1, 1
    )
    last_quarter_end = current_quarter_start - timedelta(days=1)
    last_quarter_start = date(
        last_quarter_end.year, ((last_quarter_end.month - 1) // 3) * 3 + 1, 1
    )

    # Get current month metrics
    current_month_events_stmt = select(func.count(Event.event_id)).where(
        and_(
            Event.organizer_id == user_id,
            Event.created_at
            >= datetime.combine(current_month_start, datetime.min.time()),
            Event.created_at <= datetime.combine(today, datetime.max.time()),
        )
    )
    current_month_events = (
        await db.execute(current_month_events_stmt)
    ).scalar() or 0

    # Get last month metrics
    last_month_events_stmt = select(func.count(Event.event_id)).where(
        and_(
            Event.organizer_id == user_id,
            Event.created_at
            >= datetime.combine(last_month_start, datetime.min.time()),
            Event.created_at
            <= datetime.combine(last_month_end, datetime.max.time()),
        )
    )
    last_month_events = (await db.execute(last_month_events_stmt)).scalar() or 0

    # Get current month bookings and revenue
    current_month_bookings_stmt = (
        select(
            func.count(EventBooking.booking_id),
            func.sum(EventBooking.total_price),
        )
        .join(Event, EventBooking.event_id == Event.event_id)
        .where(
            and_(
                Event.organizer_id == user_id,
                EventBooking.booking_date >= current_month_start,
                EventBooking.booking_date <= today,
                EventBooking.booking_status == BookingStatus.APPROVED,
            )
        )
    )
    current_bookings_result = await db.execute(current_month_bookings_stmt)
    result = current_bookings_result.first()
    if result:
        current_bookings, current_revenue = result
        current_bookings = current_bookings or 0
        current_revenue = float(current_revenue) if current_revenue else 0.0
    else:
        current_bookings = 0
        current_revenue = 0.0

    # Get last month bookings and revenue
    last_month_bookings_stmt = (
        select(
            func.count(EventBooking.booking_id),
            func.sum(EventBooking.total_price),
        )
        .join(Event, EventBooking.event_id == Event.event_id)
        .where(
            and_(
                Event.organizer_id == user_id,
                EventBooking.booking_date >= last_month_start,
                EventBooking.booking_date <= last_month_end,
                EventBooking.booking_status == BookingStatus.APPROVED,
            )
        )
    )
    last_bookings_result = await db.execute(last_month_bookings_stmt)
    result = last_bookings_result.first()
    if result:
        last_bookings, last_revenue = result
        last_bookings = last_bookings or 0
        last_revenue = float(last_revenue) if last_revenue else 0.0
    else:
        last_bookings = 0
        last_revenue = 0.0

    # Calculate growth rates
    events_growth = round(
        (
            (
                (current_month_events - last_month_events)
                / last_month_events
                * 100
            )
            if last_month_events > 0
            else 0
        ),
        2,
    )
    bookings_growth = round(
        (
            ((current_bookings - last_bookings) / last_bookings * 100)
            if last_bookings > 0
            else 0
        ),
        2,
    )
    revenue_growth = round(
        (
            ((current_revenue - last_revenue) / last_revenue * 100)
            if last_revenue > 0
            else 0
        ),
        2,
    )

    # Get overall statistics
    total_events_stmt = select(func.count(Event.event_id)).where(
        Event.organizer_id == user_id
    )
    total_events = (await db.execute(total_events_stmt)).scalar() or 0

    total_bookings_stmt = (
        select(func.count(EventBooking.booking_id))
        .join(Event, EventBooking.event_id == Event.event_id)
        .where(
            and_(
                Event.organizer_id == user_id,
                EventBooking.booking_status == BookingStatus.APPROVED,
            )
        )
    )
    total_bookings = (await db.execute(total_bookings_stmt)).scalar() or 0

    total_revenue_stmt = (
        select(func.sum(EventBooking.total_price))
        .join(Event, EventBooking.event_id == Event.event_id)
        .where(
            and_(
                Event.organizer_id == user_id,
                EventBooking.booking_status == BookingStatus.APPROVED,
            )
        )
    )
    total_revenue = (await db.execute(total_revenue_stmt)).scalar() or 0
    total_revenue = float(total_revenue) if total_revenue else 0.0

    # Calculate KPIs
    average_bookings_per_event = round(
        (total_bookings / total_events) if total_events > 0 else 0, 2
    )
    average_revenue_per_event = round(
        (total_revenue / total_events) if total_events > 0 else 0, 2
    )
    average_revenue_per_booking = round(
        (total_revenue / total_bookings) if total_bookings > 0 else 0, 2
    )

    metrics_data = {
        "current_period": {
            "month": current_month_start.strftime("%B %Y"),
            "events": current_month_events,
            "bookings": current_bookings,
            "revenue": round(current_revenue, 2),
        },
        "previous_period": {
            "month": last_month_start.strftime("%B %Y"),
            "events": last_month_events,
            "bookings": last_bookings,
            "revenue": round(last_revenue, 2),
        },
        "growth_rates": {
            "events_growth": events_growth,
            "bookings_growth": bookings_growth,
            "revenue_growth": revenue_growth,
        },
        "overall_statistics": {
            "total_events": total_events,
            "total_bookings": total_bookings,
            "total_revenue": round(total_revenue, 2),
        },
        "key_performance_indicators": {
            "average_bookings_per_event": average_bookings_per_event,
            "average_revenue_per_event": average_revenue_per_event,
            "average_revenue_per_booking": average_revenue_per_booking,
        },
    }

    return api_response(
        status_code=200,
        message="Performance metrics retrieved successfully",
        data=metrics_data,
    )
