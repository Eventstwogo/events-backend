from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.services.response_builder import (
    event_not_found_response,
)
from new_event_service.schemas.featured_events import (
    FeaturedEventCreate,
    FeaturedEventResponse,
    FeaturedEventUpdateRequest,
    FeaturedEventUpdateResponse,
    OldFeaturedEventListResponse,
    OldFeaturedEventResponse,
)
from new_event_service.services.featured_events import (
    create_featured_event,
    fetch_featured_events,
    get_featured_events_count,
    list_featured_events,
    update_event_featured_status,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get(
    "/old",
    status_code=status.HTTP_200_OK,
    response_model=OldFeaturedEventListResponse,
    summary="Get Featured Events",
)
@exception_handler
async def get_featured_eventss(
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch featured events in descending order with a limit of 6.

    Returns:
        - event_id: Event ID
        - slot_id: Slot ID
        - event_title: Event title
        - card_image: Card image URL
        - event_slug: Event slug
        - category_title: Category title
        - sub_category_title: Sub category title
        - start_date: Event start date
        - end_date: Event end date
        - featured_event: Featured event status
        - is_online: Is online event
    """
    # Fetch featured events
    events = await fetch_featured_events(db, limit=6)

    # Get total count
    total = await get_featured_events_count(db)

    # Transform events to response format
    featured_events_data = []
    for event in events:
        event_data = {
            "event_id": event.event_id,
            "event_title": event.event_title,
            "card_image": event.card_image,
            "event_slug": event.event_slug,
            "event_type": event.event_type,
            "category_title": (
                event.new_category.category_name if event.new_category else ""
            ),
            "sub_category_title": (
                event.new_subcategory.subcategory_name
                if event.new_subcategory
                else None
            ),
            "event_dates": event.event_dates,
            "featured_event": event.featured_event,
            "is_online": event.is_online,
        }
        featured_events_data.append(OldFeaturedEventResponse(**event_data))

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Featured events retrieved successfully",
        data={"events": featured_events_data, "total": total},
    )


@router.patch(
    "/featured/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=FeaturedEventUpdateResponse,
    summary="Update Event Featured Status",
)
@exception_handler
async def update_event_featured(
    request: FeaturedEventUpdateRequest,
    event_id: str = Path(..., description="Event ID to update"),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the featured_event column of an event by taking event_id as input.

    Args:
        event_id: The ID of the event to update
        request: Request body containing the featured_event status

    Returns:
        Success message with updated event data
    """
    # Update the event's featured status
    updated_event = await update_event_featured_status(
        db, event_id, request.featured_event
    )

    if not updated_event:
        return event_not_found_response()

    # Prepare response data
    response_data = {
        "event_id": updated_event.event_id,
        "featured_event": updated_event.featured_event,
        "updated_at": updated_event.updated_at.isoformat(),
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event featured status updated successfully",
        data=response_data,
    )


# POST: create featured event
@router.post(
    "/",
    response_model=FeaturedEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a featured event",
)
@exception_handler
async def add_featured_event(
    request: FeaturedEventCreate,
    db: AsyncSession = Depends(get_db),
):
    event = await create_featured_event(db, request)
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Featured event created successfully",
        data=FeaturedEventResponse.model_validate(event),
    )


# GET: fetch featured events
@router.get(
    "/",
    response_model=list[FeaturedEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all featured events",
)
@exception_handler
async def get_featured_events(
    db: AsyncSession = Depends(get_db),
):
    events = await list_featured_events(db)
    response_data = [FeaturedEventResponse.model_validate(e) for e in events]
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Fetched featured events successfully",
        data=response_data,
    )
