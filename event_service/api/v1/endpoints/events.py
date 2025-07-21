from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.advanced_events import (
    CategoryEventListResponse,
    CategoryEventResponse,
    EventListResponse,
    EventResponse,
    EventStatusUpdateRequest,
    LimitedEventListResponse,
    LimitedEventResponse,
)
from event_service.services.events import (
    delete_event,
    fetch_event_by_id_with_relations,
    fetch_event_by_slug_with_relations,
    fetch_events_by_category_or_subcategory_slug,
    fetch_events_without_filters,
    fetch_latest_event_from_each_category,
    fetch_limited_events_without_filters,
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
    "/", status_code=status.HTTP_200_OK, response_model=EventListResponse
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
    "/limited-list",
    status_code=status.HTTP_200_OK,
    response_model=LimitedEventListResponse,
)
@exception_handler
async def limited_list_events(
    db: AsyncSession = Depends(get_db),
):
    """Get all limited events - returns event_id, event_title, slug, card_image, organizer_id, username, etc."""

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
    response_model=EventListResponse,
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
    """Retrieve events by category slug or subcategory slug with pagination"""

    # Fetch events by category or subcategory slug with pagination
    events, total = await fetch_events_by_category_or_subcategory_slug(
        db, slug.lower(), page, per_page
    )

    # Calculate pagination metadata
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1

    if not events:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="No events found for this category or subcategory",
            data={
                "events": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            },
        )

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
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
        },
    )


@router.patch("/{event_id}/status", status_code=status.HTTP_200_OK)
@exception_handler
async def change_event_status(
    event_id: str,
    payload: EventStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Change event status (published/draft)"""

    # Check if event exists
    existing_event = await fetch_event_by_id_with_relations(db, event_id)
    if not existing_event:
        return event_not_found_response()

    # Update event status
    updated_event = await update_event_status(
        db, event_id, payload.event_status
    )
    if not updated_event:
        return invalid_event_data_response("Failed to update event status")

    status_text = "published" if payload.event_status else "draft"

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
    "/by-category/latest",
    status_code=status.HTTP_200_OK,
    response_model=CategoryEventListResponse,
)
@exception_handler
async def get_latest_events_from_each_category(
    db: AsyncSession = Depends(get_db),
):
    """Get the latest event from each category with event_id, slug, title, banner_image, and description"""

    # Fetch latest events from each category
    events, total = await fetch_latest_event_from_each_category(db)

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
            event_slug=event.event_slug,
            event_title=event.event_title,
            banner_image=event.banner_image,
            description=description,
        )
        event_responses.append(event_response)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Latest events from each category retrieved successfully",
        data={
            "events": [event.model_dump() for event in event_responses],
            "total": total,
        },
    )
