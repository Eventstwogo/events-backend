from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.advanced_events import (
    CategoryEventListResponse,
    CategoryEventResponse,
    EventListResponse,
    EventMinimalResponse,
    EventResponse,
    EventStatusUpdateRequest,
    LimitedEventListResponse,
    LimitedEventResponse,
    SubcategoryWithEvents,
)
from event_service.schemas.events import SubCategoryInfo
from event_service.services.events import (
    delete_event,
    fetch_event_by_id_with_relations,
    fetch_event_by_slug_with_relations,
    fetch_events_by_category_or_subcategory_slug,
    fetch_events_grouped_by_subcategory,
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
    Retrieve events by category slug or subcategory slug with pagination.
    
    - Category slug: Returns events grouped by subcategories (EventListWithSubcategoriesResponse)
    - Subcategory slug: Returns simple list of events (EventListSimpleResponse)
    - Only returns active events (event_status = false)
    """

    # First check if it's a category slug by trying to fetch grouped events
    subcategory_events_list, total_events, total_subcategories = await fetch_events_grouped_by_subcategory(
        db, slug.lower(), page, per_page
    )

    # If we found events grouped by subcategories, it's a category slug
    if subcategory_events_list:
        # Calculate pagination metadata for category response
        total_pages = (total_events + per_page - 1) // per_page if total_events > 0 else 0
        has_next = page < total_pages
        has_prev = page > 1

        # Convert to response format - clean events without nested details
        subcategories = []
        category_info = None
        
        for subcategory, events_list in subcategory_events_list:
            # Convert events to clean format (removing any nested category/subcategory details)
            clean_events = []
            for event in events_list:
                event_data = EventMinimalResponse.model_validate(event)
                clean_events.append(event_data.model_dump())
                
                # Get category info from first event if not already set
                if category_info is None and hasattr(event, 'category') and event.category:
                    category_info = {
                        "category_id": event.category.category_id,
                        "category_slug": event.category.category_slug
                    }
            
            subcategories.append({
                "subcategory_id": subcategory.subcategory_id,
                "subcategory_slug": subcategory.subcategory_slug,
                "events": clean_events,
                "total": len(clean_events)
            })

        response_data = {
            "category_id": category_info["category_id"] if category_info else None,
            "category_slug": category_info["category_slug"] if category_info else None,
            "subcategories": subcategories,
            "total": total_events,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
        }

        return api_response(
            status_code=status.HTTP_200_OK,
            message=f"Events grouped by subcategories retrieved successfully for category '{slug}'",
            data=response_data,
        )
    
    # If not a category slug, try subcategory slug
    events, total, matched_slug, is_category = await fetch_events_by_category_or_subcategory_slug(
        db, slug.lower(), page, per_page
    )
    
    # Calculate pagination metadata
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1

    if not events:
        return api_response(
            status_code=status.HTTP_200_OK,
            message=f"No active events found for '{slug}'",
            data={
                "subcategory_id": None,
                "subcategory_slug": None,
                "events": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            },
        )

    # Convert to clean response format for subcategory
    clean_events = []
    subcategory_info = None
    
    for event in events:
        event_data = EventMinimalResponse.model_validate(event)
        clean_events.append(event_data.model_dump())
        
        # Get subcategory info from first event if not already set
        if subcategory_info is None and hasattr(event, 'subcategory') and event.subcategory:
            subcategory_info = {
                "subcategory_id": event.subcategory.subcategory_id,
                "subcategory_slug": event.subcategory.subcategory_slug
            }

    response_data = {
        "subcategory_id": subcategory_info["subcategory_id"] if subcategory_info else None,
        "subcategory_slug": subcategory_info["subcategory_slug"] if subcategory_info else None,
        "events": clean_events,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev,
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Active events retrieved successfully for subcategory '{matched_slug}'",
        data=response_data,
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
    "/latest/category-or-subcategory/{slug}",
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def get_latest_5_events_by_category_or_subcategory_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the latest 5 events by category slug or subcategory slug.
    
    - Returns the latest 5 events ordered by creation date
    - Only returns active events (event_status = false)
    """

    # Fetch latest 5 events by category or subcategory slug
    events, total, matched_slug, is_category = await fetch_events_by_category_or_subcategory_slug(
        db, slug.lower(), page=1, per_page=5
    )

    if not events:
        return api_response(
            status_code=status.HTTP_200_OK,
            message=f"No active events found for '{slug}'",
            data={
                "events": [],
                "total": 0,
            },
        )

    # Convert to response format without organizer, category, and subcategory details
    event_responses = []
    for event in events:
        event_data = EventResponse.model_validate(event)
        # Convert to dict and remove organizer, category, and subcategory
        event_dict = event_data.model_dump()
        event_dict.pop('organizer', None)
        event_dict.pop('subcategory', None)
        event_dict.pop('category', None)
        event_responses.append(event_dict)
    
    # Prepare response data based on whether it's category or subcategory
    if is_category:
        # Category slug provided - group events by subcategories
        from collections import defaultdict
        subcategory_groups = defaultdict(list)
        
        # Group events by subcategory
        for i, event in enumerate(events):
            subcategory_key = event.subcategory.subcategory_id if event.subcategory else "no_subcategory"
            subcategory_groups[subcategory_key].append(event_responses[i])
        
        # Build subcategories array
        subcategories = []
        for event in events:
            if event.subcategory:
                subcategory_id = event.subcategory.subcategory_id
                # Check if we already added this subcategory
                if not any(sub.get('subcategory_id') == subcategory_id for sub in subcategories):
                    subcategories.append({
                        "subcategory_id": event.subcategory.subcategory_id,
                        "subcategory_slug": event.subcategory.subcategory_slug,
                        "events": subcategory_groups[subcategory_id],
                        "total": len(subcategory_groups[subcategory_id])
                    })
        
        response_data = {
            "category_id": events[0].category.category_id if events[0].category else None,
            "category_slug": events[0].category.category_slug if events[0].category else None,
            "subcategories": subcategories,
            "total": len(events),
        }
    else:
        # Subcategory slug provided - show only subcategory info + events
        response_data = {
            "subcategory_id": events[0].subcategory.subcategory_id if events[0].subcategory else None,
            "subcategory_slug": events[0].subcategory.subcategory_slug if events[0].subcategory else None,
            "events": event_responses,
            "total": len(events),
        }
    
    entity_type = "category" if is_category else "subcategory"
    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Latest {len(events)} events retrieved successfully for {entity_type} '{matched_slug}'",
        data=response_data,
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
