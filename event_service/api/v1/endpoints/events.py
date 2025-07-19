from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.advanced_events import (
    EventListResponse,
    EventResponse,
    EventStatusUpdateRequest,
)
from event_service.schemas.events import (
    EventCreateRequest,
    EventUpdateRequest,
)
from event_service.services.events import (
    check_category_and_subcategory_exists_using_joins,
    check_category_exists,
    check_event_exists_with_slug,
    check_event_exists_with_title,
    check_event_slug_unique_for_update,
    check_event_title_unique_for_update,
    check_organizer_exists,
    check_subcategory_exists,
    delete_event,
    fetch_event_by_id_with_relations,
    fetch_event_by_slug_with_relations,
    fetch_events_without_filters,
    update_event,
    update_event_status,
)
from event_service.services.response_builder import (
    category_and_subcategory_not_found_response,
    category_not_found_response,
    event_alreay_exists_with_slug_response,
    event_not_found_response,
    event_slug_already_exists_response,
    event_title_already_exists_response,
    invalid_event_data_response,
    organizer_not_found_response,
    subcategory_not_found_response,
)
from shared.core.api_response import api_response
from shared.db.models import Event
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.id_generators import generate_digits_upper_lower_case

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
@exception_handler
async def create_event(
    payload: EventCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    # check if event title is unique
    existing_title = await check_event_exists_with_title(
        db, payload.event_title.lower()
    )
    if existing_title:
        return event_title_already_exists_response()

    # normalize and slugify the event slug
    payload.event_slug = slugify(payload.event_slug.lower())
    # check if an event with the same slug already exists
    existing_event = await check_event_exists_with_slug(db, payload.event_slug)
    if existing_event:
        return event_alreay_exists_with_slug_response()

    # check if the organizer exists
    organizer = await check_organizer_exists(db, payload.organizer_id)
    if not organizer:
        return organizer_not_found_response()

    # check if the category and subcategory exist
    category = await check_category_exists(db, payload.category_id)
    if not category:
        return category_not_found_response()
    subcategory = await check_subcategory_exists(db, payload.subcategory_id)
    if not subcategory:
        return subcategory_not_found_response()

    existing_category_subcategory = (
        await check_category_and_subcategory_exists_using_joins(
            db, payload.category_id, payload.subcategory_id
        )
    )
    if not existing_category_subcategory:
        return category_and_subcategory_not_found_response()

    # generate a new event ID
    new_event_id = generate_digits_upper_lower_case(length=6)

    new_event = Event(
        event_id=new_event_id,
        event_title=payload.event_title.title(),
        event_slug=payload.event_slug.lower(),
        category_id=payload.category_id,
        subcategory_id=payload.subcategory_id,
        organizer_id=payload.organizer_id,
        card_image=payload.card_image,
        banner_image=payload.banner_image,
        event_extra_images=payload.event_extra_images or [],
        extra_data=payload.extra_data,
        hash_tags=payload.hash_tags,
    )
    # Add to database
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)

    # Return success response
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Event created successfully",
        data={
            "event_id": new_event.event_id,
        },
    )


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


@router.put("/{event_id}", status_code=status.HTTP_200_OK)
@exception_handler
async def update_event_details(
    event_id: str,
    payload: EventUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update event details"""

    # Check if event exists
    existing_event = await fetch_event_by_id_with_relations(db, event_id)
    if not existing_event:
        return event_not_found_response()

    # Prepare update data
    update_data = {}

    # Validate and prepare title update
    if payload.event_title is not None:
        # Check if title is unique (excluding current event)
        if not await check_event_title_unique_for_update(
            db, event_id, payload.event_title.lower()
        ):
            return event_title_already_exists_response()
        update_data["event_title"] = payload.event_title.title()

    # Validate and prepare slug update
    if payload.event_slug is not None:
        # Check if slug is unique (excluding current event)
        if not await check_event_slug_unique_for_update(
            db, event_id, payload.event_slug.lower()
        ):
            return event_slug_already_exists_response()
        update_data["event_slug"] = payload.event_slug.lower()

    # Validate category if provided
    if payload.category_id is not None:
        category = await check_category_exists(db, payload.category_id)
        if not category:
            return category_not_found_response()
        update_data["category_id"] = payload.category_id

    # Validate subcategory if provided
    if payload.subcategory_id is not None:
        subcategory = await check_subcategory_exists(db, payload.subcategory_id)
        if not subcategory:
            return subcategory_not_found_response()
        update_data["subcategory_id"] = payload.subcategory_id

    # Add other fields
    if payload.card_image is not None:
        update_data["card_image"] = payload.card_image

    if payload.banner_image is not None:
        update_data["banner_image"] = payload.banner_image

    if payload.extra_data is not None:
        update_data["extra_data"] = payload.extra_data

    if payload.hash_tags is not None:
        update_data["hash_tags"] = payload.hash_tags

    # Update the event
    updated_event = await update_event(db, event_id, update_data)
    if not updated_event:
        return invalid_event_data_response("Failed to update event")

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event updated successfully",
        data={
            "event_id": updated_event.event_id,
            "updated_fields": list(update_data.keys()),
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
