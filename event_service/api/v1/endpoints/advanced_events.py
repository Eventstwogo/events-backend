from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.advanced_events import (
    EventListResponse,
    EventResponse,
    EventsByOrganizerResponse,
    EventSlugUpdateRequest,
    EventSummaryResponse,
)
from event_service.services.advanced_events import fetch_events_with_filters
from event_service.services.events import (
    check_organizer_exists,
    fetch_event_by_id_with_relations,
    filter_events_advanced,
    get_event_summary,
    get_events_by_hashtag,
    get_events_by_organizer,
    get_upcoming_events,
    search_events,
    update_event_slug,
)
from event_service.services.response_builder import (
    event_not_found_response,
    event_slug_already_exists_response,
    invalid_event_data_response,
    organizer_not_found_response,
)
from shared.core.api_response import api_response
from shared.db.models.events import EventStatus
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


# Advanced Event APIs
@router.get(
    "", status_code=status.HTTP_200_OK, response_model=EventListResponse
)
@exception_handler
async def list_events(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(
        default=10, ge=1, le=100, description="Items per page"
    ),
    status_filter: Optional[EventStatus] = Query(
        None, alias="status", description="Filter by event status"
    ),
    category_id: Optional[str] = Query(
        None, description="Filter by category ID"
    ),
    subcategory_id: Optional[str] = Query(
        None, description="Filter by subcategory ID"
    ),
    organizer_id: Optional[str] = Query(
        None, description="Filter by organizer ID"
    ),
    search: Optional[str] = Query(
        None, min_length=1, max_length=100, description="Search in event title"
    ),
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(
        default="desc", regex="^(asc|desc)$", description="Sort order"
    ),
    db: AsyncSession = Depends(get_db),
):
    """List all events with filters, pagination, and sorting"""

    # Fetch events with filters
    events, total = await fetch_events_with_filters(
        db=db,
        page=page,
        per_page=per_page,
        status=status_filter,
        category_id=category_id,
        subcategory_id=subcategory_id,
        organizer_id=organizer_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Calculate pagination info
    has_next = (page * per_page) < total
    has_prev = page > 1

    # Convert to response format
    event_responses = [EventResponse.model_validate(event) for event in events]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Events retrieved successfully",
        data={
            "events": event_responses,
            "total": total,
            "page": page,
            "per_page": per_page,
            "has_next": has_next,
            "has_prev": has_prev,
        },
    )


@router.get(
    "/search/", status_code=status.HTTP_200_OK, response_model=EventListResponse
)
@exception_handler
async def search_events_advanced(
    query: str = Query(
        ..., min_length=1, max_length=200, description="Search query"
    ),
    search_fields: Optional[str] = Query(
        default="title,slug,hashtags",
        description="Comma-separated fields to search: title,slug,organizer,hashtags",
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(
        default=10, ge=1, le=100, description="Items per page"
    ),
    status_filter: Optional[EventStatus] = Query(
        None, alias="status", description="Filter by event status"
    ),
    category_id: Optional[str] = Query(
        None, description="Filter by category ID"
    ),
    subcategory_id: Optional[str] = Query(
        None, description="Filter by subcategory ID"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Search events by title, slug, organizer, hashtags"""

    # Parse search fields
    search_fields_value = (
        search_fields if search_fields is not None else "title,slug,hashtags"
    )
    fields_list = [
        field.strip()
        for field in search_fields_value.split(",")
        if field.strip()
    ]
    allowed_fields = ["title", "slug", "organizer", "hashtags"]
    fields_list = [field for field in fields_list if field in allowed_fields]

    if not fields_list:
        fields_list = ["title", "slug", "hashtags"]

    # Search events
    events, total = await search_events(
        db=db,
        query=query,
        search_fields=fields_list,
        page=page,
        per_page=per_page,
        status=status_filter,
        category_id=category_id,
        subcategory_id=subcategory_id,
    )

    # Calculate pagination info
    has_next = (page * per_page) < total
    has_prev = page > 1

    # Convert to response format
    event_responses = [EventResponse.model_validate(event) for event in events]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Events search completed successfully",
        data={
            "events": event_responses,
            "total": total,
            "page": page,
            "per_page": per_page,
            "has_next": has_next,
            "has_prev": has_prev,
            "search_query": query,
            "search_fields": fields_list,
        },
    )


@router.get(
    "/filter/", status_code=status.HTTP_200_OK, response_model=EventListResponse
)
@exception_handler
async def filter_events_endpoint(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(
        default=10, ge=1, le=100, description="Items per page"
    ),
    status_filter: Optional[EventStatus] = Query(
        None, alias="status", description="Filter by event status"
    ),
    category_id: Optional[str] = Query(
        None, description="Filter by category ID"
    ),
    subcategory_id: Optional[str] = Query(
        None, description="Filter by subcategory ID"
    ),
    organizer_id: Optional[str] = Query(
        None, description="Filter by organizer ID"
    ),
    created_after: Optional[str] = Query(
        None, description="Filter events created after this date (ISO format)"
    ),
    created_before: Optional[str] = Query(
        None, description="Filter events created before this date (ISO format)"
    ),
    has_slots: Optional[EventStatus] = Query(
        None, description="Filter events that have/don't have slots"
    ),
    min_slots: Optional[int] = Query(
        None, ge=0, description="Minimum number of slots"
    ),
    max_slots: Optional[int] = Query(
        None, ge=0, description="Maximum number of slots"
    ),
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(
        default="desc", regex="^(asc|desc)$", description="Sort order"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Filter events by category, subcategory, date, status"""

    # Parse date filters
    created_after_dt = None
    created_before_dt = None

    if created_after:
        try:
            from datetime import datetime

            created_after_dt = datetime.fromisoformat(
                created_after.replace("Z", "+00:00")
            )
        except ValueError:
            return invalid_event_data_response(
                "Invalid created_after date format. Use ISO format."
            )

    if created_before:
        try:
            from datetime import datetime

            created_before_dt = datetime.fromisoformat(
                created_before.replace("Z", "+00:00")
            )
        except ValueError:
            return invalid_event_data_response(
                "Invalid created_before date format. Use ISO format."
            )

    # Filter events
    events, total = await filter_events_advanced(
        db=db,
        page=page,
        per_page=per_page,
        status=status_filter,
        category_id=category_id,
        subcategory_id=subcategory_id,
        organizer_id=organizer_id,
        created_after=created_after_dt,
        created_before=created_before_dt,
        has_slots=has_slots,
        min_slots=min_slots,
        max_slots=max_slots,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Calculate pagination info
    has_next = (page * per_page) < total
    has_prev = page > 1

    # Convert to response format
    event_responses = [EventResponse.model_validate(event) for event in events]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Events filtered successfully",
        data={
            "events": event_responses,
            "total": total,
            "page": page,
            "per_page": per_page,
            "has_next": has_next,
            "has_prev": has_prev,
        },
    )


@router.get(
    "/organizer/{organizer_id}",
    status_code=status.HTTP_200_OK,
    response_model=EventsByOrganizerResponse,
)
@exception_handler
async def get_events_by_organizer_endpoint(
    organizer_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(
        default=10, ge=1, le=100, description="Items per page"
    ),
    status_filter: Optional[EventStatus] = Query(
        None, alias="status", description="Filter by event status"
    ),
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(
        default="desc", regex="^(asc|desc)$", description="Sort order"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get events created by a specific organizer"""

    # Check if organizer exists
    organizer = await check_organizer_exists(db, organizer_id)
    if not organizer:
        return organizer_not_found_response()

    # Get events by organizer
    events, filtered_total, stats = await get_events_by_organizer(
        db=db,
        organizer_id=organizer_id,
        page=page,
        per_page=per_page,
        status=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Calculate pagination info
    has_next = (page * per_page) < filtered_total
    has_prev = page > 1

    # Convert to response format
    event_responses = [EventResponse.model_validate(event) for event in events]

    # Get organizer info
    from event_service.schemas.events import OrganizerInfo

    organizer_info = OrganizerInfo.model_validate(organizer)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Events by organizer retrieved successfully",
        data={
            "organizer_id": organizer_id,
            "organizer_info": organizer_info.model_dump(),
            "events": event_responses,
            "total_events": stats["total_events"],
            "active_events": stats["active_events"],
            "inactive_events": stats["inactive_events"],
            "page": page,
            "per_page": per_page,
            "has_next": has_next,
            "has_prev": has_prev,
        },
    )


@router.get(
    "/{event_id}/summary",
    status_code=status.HTTP_200_OK,
    response_model=EventSummaryResponse,
)
@exception_handler
async def get_event_summary_endpoint(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get analytics (slot count, duration total, etc.)"""

    # Get event summary
    summary = await get_event_summary(db, event_id)
    if not summary:
        return event_not_found_response()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event summary retrieved successfully",
        data=summary,
    )


@router.get(
    "/upcoming/",
    status_code=status.HTTP_200_OK,
    response_model=EventListResponse,
)
@exception_handler
async def get_upcoming_events_endpoint(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(
        default=10, ge=1, le=100, description="Items per page"
    ),
    category_id: Optional[str] = Query(
        None, description="Filter by category ID"
    ),
    subcategory_id: Optional[str] = Query(
        None, description="Filter by subcategory ID"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming published events"""

    # Get upcoming events
    events, total = await get_upcoming_events(
        db=db,
        page=page,
        per_page=per_page,
        category_id=category_id,
        subcategory_id=subcategory_id,
    )

    # Calculate pagination info
    has_next = (page * per_page) < total
    has_prev = page > 1

    # Convert to response format
    event_responses = [EventResponse.model_validate(event) for event in events]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Upcoming events retrieved successfully",
        data={
            "events": event_responses,
            "total": total,
            "page": page,
            "per_page": per_page,
            "has_next": has_next,
            "has_prev": has_prev,
        },
    )


@router.get(
    "/hashtag/{tag}",
    status_code=status.HTTP_200_OK,
    response_model=EventListResponse,
)
@exception_handler
async def get_events_by_hashtag_endpoint(
    tag: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(
        default=10, ge=1, le=100, description="Items per page"
    ),
    status_filter: Optional[EventStatus] = Query(
        None, alias="status", description="Filter by event status"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Find events by hashtag"""

    # Get events by hashtag
    events, total = await get_events_by_hashtag(
        db=db, hashtag=tag, page=page, per_page=per_page, status=status_filter
    )

    # Calculate pagination info
    has_next = (page * per_page) < total
    has_prev = page > 1

    # Convert to response format
    event_responses = [EventResponse.model_validate(event) for event in events]

    # Ensure hashtag starts with #
    display_tag = tag if tag.startswith("#") else f"#{tag}"

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Events with hashtag '{display_tag}' retrieved successfully",
        data={
            "events": event_responses,
            "total": total,
            "page": page,
            "per_page": per_page,
            "has_next": has_next,
            "has_prev": has_prev,
            "hashtag": display_tag,
        },
    )


@router.patch("/{event_id}/slug", status_code=status.HTTP_200_OK)
@exception_handler
async def update_event_slug_endpoint(
    event_id: str,
    payload: EventSlugUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Regenerate or update event slug (admin use)"""

    # Check if event exists
    existing_event = await fetch_event_by_id_with_relations(db, event_id)
    if not existing_event:
        return event_not_found_response()

    # Update event slug
    updated_event = await update_event_slug(db, event_id, payload.new_slug)
    if not updated_event:
        return event_slug_already_exists_response()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event slug updated successfully",
        data={
            "event_id": updated_event.event_id,
            "old_slug": existing_event.event_slug,
            "new_slug": updated_event.event_slug,
        },
    )
