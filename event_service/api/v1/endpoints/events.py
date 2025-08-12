from typing import Literal

from fastapi import APIRouter, Depends, Form, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.advanced_events import (
    CategoryEventListResponse,
    CategoryEventResponse,
    ComprehensiveCategoryEventResponse,
    EventListResponse,
    EventMinimalResponse,
    EventResponse,
    LimitedEventListResponse,
    LimitedEventResponse,
    SubcategoryEventGroup,
)
from event_service.services.events import (
    delete_event,
    fetch_event_by_id_with_relations,
    fetch_event_by_slug_with_relations,
    fetch_events_by_category_or_subcategory_slug,
    fetch_events_by_slug_comprehensive,
    fetch_events_without_filters,
    fetch_latest_event_from_each_category,
    fetch_limited_events_with_filter,
    fetch_limited_events_without_filters,
    fetch_upcoming_events,
    update_event_status,
)
from event_service.services.response_builder import (
    event_not_found_response,
    invalid_event_data_response,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get(
    "", status_code=status.HTTP_200_OK, response_model=EventListResponse
)
@exception_handler
async def list_events(
    db: AsyncSession = Depends(get_db),
):
    """List all events with filters, pagination, and sorting"""

    # Fetch events with filters
    events, total = await fetch_events_without_filters(db)

    # Convert to response format
    event_responses = [EventResponse.model_validate(event) for event in events]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Events retrieved successfully",
        data={
            "events": event_responses,
            "total": total,
        },
    )


@router.get(
    "/upcoming",
    status_code=status.HTTP_200_OK,
    response_model=EventListResponse,
)
@exception_handler
async def list_upcoming_events(
    db: AsyncSession = Depends(get_db),
):
    """List upcoming events based on start date and end date"""

    # Fetch upcoming events
    events, total = await fetch_upcoming_events(db)

    # Convert to response format
    event_responses = [EventResponse.model_validate(event) for event in events]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Upcoming events retrieved successfully",
        data={
            "events": event_responses,
            "total": total,
        },
    )


@router.get(
    "/limited-list",
    status_code=status.HTTP_200_OK,
    response_model=LimitedEventListResponse,
)
@exception_handler
async def limited_list_events(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all limited events - returns event_id, event_title, slug, card_image,
    organizer_id, username, etc.
    """

    # Fetch events with filters
    events, total = await fetch_limited_events_without_filters(db)

    # Convert to response format
    event_responses = [
        LimitedEventResponse.model_validate(event) for event in events
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Events retrieved successfully",
        data={
            "events": event_responses,
            "total": total,
        },
    )


@router.get(
    "/limited-list/filter",
    status_code=status.HTTP_200_OK,
    response_model=LimitedEventListResponse,
)
@exception_handler
async def limited_list_events_with_filter(
    event_type: str = Query(
        default="all",
        description="Filter events by type: 'all' for all events, 'upcoming' for upcoming events only",
        regex="^(all|upcoming)$",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get limited events with filter option.

    Query Parameters:
    - event_type: "all" (default) for all events, "upcoming" for upcoming events only

    Returns limited event data: event_id, event_title, slug, card_image, dates, location, etc.
    """

    # Fetch events based on filter
    events, total = await fetch_limited_events_with_filter(db, event_type)

    # Convert to response format
    event_responses = [
        LimitedEventResponse.model_validate(event) for event in events
    ]

    # Determine message based on filter
    message = (
        "All events retrieved successfully"
        if event_type == "all"
        else "Upcoming events retrieved successfully"
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message=message,
        data={
            "events": event_responses,
            "total": total,
        },
    )


@router.get(
    "/{event_id}", status_code=status.HTTP_200_OK, response_model=EventResponse
)
@exception_handler
async def get_event_by_id(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full event details by event_id"""

    # Fetch event with all relations
    event = await fetch_event_by_id_with_relations(db, event_id)
    if not event:
        return event_not_found_response()

    # Convert to response format
    event_response = EventResponse.model_validate(event)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event retrieved successfully",
        data=event_response.model_dump(),
    )


@router.get(
    "/slug/{event_slug}",
    status_code=status.HTTP_200_OK,
    response_model=EventResponse,
)
@exception_handler
async def get_event_by_slug(
    event_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve event by SEO-friendly event_slug"""

    # Fetch event with all relations
    event = await fetch_event_by_slug_with_relations(db, event_slug.lower())
    if not event:
        return event_not_found_response()

    # Convert to response format
    event_response = EventResponse.model_validate(event)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event retrieved successfully",
        data=event_response.model_dump(),
    )


@router.get(
    "/category-or-subcategory/{slug}",
    status_code=status.HTTP_200_OK,
    response_model=ComprehensiveCategoryEventResponse,
)
@exception_handler
async def get_events_by_category_or_subcategory_slug(
    slug: str,
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    per_page: int = Query(
        10, ge=1, le=100, description="Number of events per page (max 100)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Comprehensive event retrieval by slug that checks both category and subcategory tables.

    This endpoint:
    1. Checks if the slug exists in category table
    2. Checks if the slug exists in subcategory table
    3. Fetches ALL events that match either category_id or subcategory_id
    4. Returns structured response with separate category and subcategory events
    5. Provides separate counts for proper pagination

    - Only returns active events (event_status = false)
    - Supports pagination for both category and subcategory events
    """

    # Use comprehensive slug-based fetching
    (
        category_events,
        subcategory_events_grouped,
        total_category_events,
        total_subcategory_events,
        matched_category_id,
        matched_subcategory_id,
    ) = await fetch_events_by_slug_comprehensive(
        db, slug.lower(), page, per_page
    )

    # Calculate pagination metadata
    total_events = total_category_events + total_subcategory_events
    total_pages = (
        (total_events + per_page - 1) // per_page if total_events > 0 else 0
    )
    has_next = page < total_pages
    has_prev = page > 1

    # Process category events (events with only category_id, no subcategory_id)
    category_events_data = []
    category_info = None

    for event in category_events:
        event_data = EventMinimalResponse.model_validate(event)
        category_events_data.append(event_data.model_dump())

        # Get category info from first event if not already set
        if (
            category_info is None
            and hasattr(event, "category")
            and event.category
        ):
            category_info = {
                "category_id": event.category.category_id,
                "category_slug": event.category.category_slug,
                "category_name": getattr(event.category, "category_name", None),
            }

    # Process subcategory events (grouped by subcategory)
    subcategory_groups = []

    for subcategory_id, group_data in subcategory_events_grouped.items():
        # Convert events to response format
        events_data = []
        for event in group_data["events"]:
            event_data = EventMinimalResponse.model_validate(event)
            events_data.append(event_data)

        # Create SubCategoryInfo from the subcategory_info dict
        from event_service.schemas.events import SubCategoryInfo

        subcategory_info = SubCategoryInfo(**group_data["subcategory_info"])

        # Create subcategory group
        subcategory_group = SubcategoryEventGroup(
            subcategory_info=subcategory_info,
            events=events_data,
            total=group_data["total"],
        )
        subcategory_groups.append(subcategory_group)

    # Build comprehensive response
    response_data = ComprehensiveCategoryEventResponse(
        slug=slug,
        matched_category_id=matched_category_id,
        matched_subcategory_id=matched_subcategory_id,
        category_events={
            "events": category_events_data,
            "total": total_category_events,
            "category_info": category_info,
        },
        subcategory_groups=subcategory_groups,
        total_events=total_events,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
    )

    # Determine appropriate message based on what was found
    message_parts = []
    if subcategory_groups:
        total_subcategory_count = sum(
            group.total for group in subcategory_groups
        )
        message_parts.append(
            f"{total_subcategory_count} events across {len(subcategory_groups)} subcategories"
        )
    if category_events:
        message_parts.append(f"{total_category_events} category events")

    if not message_parts:
        message = f"No active events found for slug '{slug}'"
    else:
        message = f"Retrieved {' and '.join(message_parts)} for slug '{slug}'"

    return api_response(
        status_code=status.HTTP_200_OK,
        message=message,
        data=response_data.model_dump(),
    )


@router.patch("/status/{event_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def change_event_status(
    event_id: str,
    event_status: bool = Form(
        ...,
        example=False,
        description="Event status (false for published, true for draft)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Change event status (published/draft)"""

    # Check if event exists
    existing_event = await fetch_event_by_id_with_relations(db, event_id)
    if not existing_event:
        return event_not_found_response()

    # Update event status
    updated_event = await update_event_status(db, event_id, event_status)
    if not updated_event:
        return invalid_event_data_response("Failed to update event status")

    status_text = "draft" if event_status else "published"

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Event status updated to {status_text}",
        data={
            "event_id": updated_event.event_id,
            "event_status": updated_event.event_status,
            "status_text": status_text,
        },
    )


@router.delete("/{event_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def delete_event_by_id(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete event (and cascade delete slots)"""

    # Check if event exists
    existing_event = await fetch_event_by_id_with_relations(db, event_id)
    if not existing_event:
        return event_not_found_response()

    # Delete the event
    success = await delete_event(db, event_id)
    if not success:
        return invalid_event_data_response("Failed to delete event")

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event deleted successfully",
        data={"event_id": event_id, "deleted": True},
    )


@router.get(
    "/latest/category-or-subcategory/{slug}",
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def get_latest_5_events_by_category_or_subcategory_slug(
    slug: str,
    event_type: Literal["all", "ongoing", "upcoming"] = Query(
        "upcoming",
        description="Filter events by type: 'all' for all events, 'ongoing' for current events (current date between start_date and end_date), 'upcoming' for future events (end_date >= current date)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the latest 5 events by category slug or subcategory slug.

    Args:
        slug: Category slug or subcategory slug
        event_type: Filter events by type:
            - 'all': Return all published events
            - 'ongoing': Return events where current date is between start_date and end_date (inclusive)
            - 'upcoming': Return events where end_date is greater than or equal to current date
        db: Database session

    Returns:
        - Latest 5 events ordered by creation date
        - Only returns active events (event_status = false)
    """

    # Fetch latest 5 events by category or subcategory slug
    events, total, matched_slug, is_category = (
        await fetch_events_by_category_or_subcategory_slug(
            db, slug.lower(), page=1, per_page=5, event_type=event_type
        )
    )

    if not events:
        return api_response(
            status_code=status.HTTP_200_OK,
            message=f"No active {event_type} events found for '{slug}'",
            data={
                "events": [],
                "total": 0,
                "event_type": event_type,
            },
        )

    # Convert to response format without organizer, category, and subcategory details
    event_responses = []
    for event in events:
        event_data = EventResponse.model_validate(event)
        # Convert to dict and remove organizer, category, and subcategory
        event_dict = event_data.model_dump()
        event_dict.pop("organizer", None)
        event_dict.pop("subcategory", None)
        event_dict.pop("category", None)
        event_responses.append(event_dict)

    # Prepare response data based on whether it's category or subcategory
    if is_category:
        # Category slug provided - show category info and events without subcategory details
        response_data = {
            "category_id": (
                events[0].category.category_id if events[0].category else None
            ),
            "category_slug": (
                events[0].category.category_slug if events[0].category else None
            ),
            "events": event_responses,
            "total": len(events),
            "event_type": event_type,
        }
    else:
        # Subcategory slug provided - show subcategory info and events
        response_data = {
            "subcategory_id": (
                events[0].subcategory.subcategory_id
                if events[0].subcategory
                else None
            ),
            "subcategory_slug": (
                events[0].subcategory.subcategory_slug
                if events[0].subcategory
                else None
            ),
            "events": event_responses,
            "total": len(events),
            "event_type": event_type,
        }

    entity_type = "category" if is_category else "subcategory"
    message = (
        f"Latest {len(events)} {event_type} events retrieved successfully for "
        f"{entity_type} '{matched_slug}'"
    )
    return api_response(
        status_code=status.HTTP_200_OK,
        message=message,
        data=response_data,
    )


@router.get(
    "/by-category/latest",
    status_code=status.HTTP_200_OK,
    response_model=CategoryEventListResponse,
)
@exception_handler
async def get_latest_events_from_each_category(
    event_type: Literal["all", "ongoing", "upcoming"] = Query(
        "upcoming",
        description="Filter events by type: 'all' for all events, 'ongoing' for current events (current date between start_date and end_date), 'upcoming' for future events (end_date >= current date)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the latest event from each category with event_id, slug, title,
    banner_image, and description

    Args:
        event_type: Filter events by type:
            - 'all': Return all published events
            - 'ongoing': Return events where current date is between start_date and end_date (inclusive)
            - 'upcoming': Return events where end_date is greater than or equal to current date
        db: Database session
    """

    # Fetch latest events from each category
    events, total = await fetch_latest_event_from_each_category(
        db, event_type=event_type
    )

    # Convert to response format with description extraction
    event_responses = []
    for event in events:
        # Extract description from extra_data if present
        description = None
        if event.extra_data and isinstance(event.extra_data, dict):
            description = event.extra_data.get("description")

        # Create response object
        event_response = CategoryEventResponse(
            event_id=event.event_id,
            slot_id=event.slot_id,
            event_slug=event.event_slug,
            event_title=event.event_title,
            card_image=event.card_image,
            banner_image=event.banner_image,
            description=description,
            start_date=event.start_date,
            end_date=event.end_date,
            location=event.location,
            is_online=event.is_online,
        )
        event_responses.append(event_response)

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Latest {event_type} events from each category retrieved successfully",
        data={
            "events": [event.model_dump() for event in event_responses],
            "total": total,
            "event_type": event_type,
        },
    )
