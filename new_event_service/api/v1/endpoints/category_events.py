from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_event_service.schemas.category_events import (
    CategoryInfoResponse,
    CategoryWithEventsResponse,
    PaginatedEventResponse,
    PaginationMeta,
    SimplifiedCategoryEventsResponse,
    SimplifiedSlugEventsResponse,
)
from new_event_service.services.category_events import (
    fetch_categories_with_all_events,
    fetch_events_by_category_slug_unified,
)
from new_event_service.services.event_fetcher import EventTypeStatus
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get(
    "/categories-with-events",
    status_code=status.HTTP_200_OK,
    response_model=SimplifiedCategoryEventsResponse,
    summary="Integrated in application frontend",
)
@exception_handler
async def get_categories_with_latest_events(
    event_type: Literal[EventTypeStatus.ALL, EventTypeStatus.LIVE, EventTypeStatus.UPCOMING] = Query(
        EventTypeStatus.UPCOMING,
        description="Filter events by type: 'all' for all events, 'ongoing' for current events (current date between start_date and end_date), 'upcoming' for future events (end_date >= current date)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get all categories with their latest 5 events each (including events from subcategories)

    Args:
        event_type: Filter events by type:
            - 'all': Return all published events
            - 'ongoing': Return events where current date is between start_date and end_date (inclusive)
            - 'upcoming': Return events where end_date is greater than or equal to current date
        db: Database session
    """

    # Fetch categories with all their events (including subcategory events)
    categories_data = await fetch_categories_with_all_events(
        db, event_type=event_type
    )

    # Convert to response format
    categories_response = [
        CategoryWithEventsResponse.model_validate(category_data)
        for category_data in categories_data
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Categories with latest {event_type} events retrieved successfully",
        data={
            "categories": [cat.model_dump() for cat in categories_response],
            "total_categories": len(categories_response),
            "event_type": event_type,
        },
    )


@router.get(
    "/events-by-slug/{slug}",
    status_code=status.HTTP_200_OK,
    response_model=SimplifiedSlugEventsResponse,
    summary="Integrated in Application frontend",
)
@exception_handler
async def get_events_by_category_or_subcategory_slug(
    slug: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(
        10, ge=1, le=100, description="Number of events per page (max 100)"
    ),
    event_type: Literal[EventTypeStatus.ALL, EventTypeStatus.LIVE, EventTypeStatus.UPCOMING] = Query(
        EventTypeStatus.UPCOMING,
        description="Filter events by type: 'all' for all events, 'ongoing' for current events (current date between start_date and end_date), 'upcoming' for future events (end_date >= current date)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated events by category slug or subcategory slug, unified under category context

    This endpoint accepts either a category slug or subcategory slug and returns:
    - Paginated events in descending order of created_at timestamp
    - All events grouped under their parent category context
    - Pagination metadata
    - Response format matching categories-with-events endpoint

    Args:
        slug: Category slug or subcategory slug
        page: Page number (default: 1)
        limit: Number of events per page (default: 10, max: 100)
        event_type: Filter events by type:
            - 'all': Return all published events
            - 'ongoing': Return events where current date is between start_date and end_date (inclusive)
            - 'upcoming': Return events where end_date is greater than or equal to current date
        db: Database session

    Returns:
        Response with events under category context, pagination info, matching format

    Raises:
        HTTPException: If slug is not found or no events exist for the slug
    """

    # Fetch events and metadata using unified approach
    events_data, total_count, category_data = (
        await fetch_events_by_category_slug_unified(
            db=db,
            slug=slug,
            page=page,
            limit=limit,
            event_type=event_type,
        )
    )

    # Check if slug was found
    if not category_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No category or subcategory found with slug: {slug}",
        )

    # Check if any events exist
    if total_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No published events found for slug: {slug}",
        )

    # Calculate pagination metadata
    total_count = total_count or 0
    total_pages = (total_count + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_prev = page > 1

    # Convert events to response format
    events_response = [
        PaginatedEventResponse.model_validate(event_data)
        for event_data in events_data
    ]

    # Create pagination metadata
    pagination = PaginationMeta(
        current_page=page,
        per_page=limit,
        total_items=total_count,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
    )

    # Determine slug type by checking if slug matches category or subcategory
    slug_type = (
        "category" if category_data["category_slug"] == slug else "subcategory"
    )

    # Create category response
    category_response = CategoryInfoResponse.model_validate(category_data)

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"{event_type.capitalize()} events for {slug_type} '{slug}' retrieved successfully under category context",
        data={
            "events": [event.model_dump() for event in events_response],
            "pagination": pagination.model_dump(),
            "category": category_response.model_dump(),
            "total_events": total_count,
            "slug": slug,
            "slug_type": slug_type,
            "event_type": event_type,
        },
    )
