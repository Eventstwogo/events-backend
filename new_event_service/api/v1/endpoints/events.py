from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Form, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_event_service.schemas.events import (
    CategoryInfo,
    EventListResponse,
    EventResponse,
    EventSearchResponse,
    EventSlotResponseWrapper,
    NewEventSlotResponse,
    OrganizerInfo,
    SubCategoryInfo,
)
from new_event_service.services.events import (
    fetch_event_by_id,
    fetch_event_by_id_with_relations,
    search_events_for_global,
)
from new_event_service.services.response_builder import event_not_found_response
from new_event_service.utils.utils import minutes_to_duration_string
from shared.core.api_response import api_response
from shared.db.models import NewEvent, NewEventSeatCategory, NewEventSlot
from shared.db.models.new_events import EventStatus
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get(
    "",
    response_model=EventListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get paginated list of events",
)
@exception_handler
async def list_new_events(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit

    # Proper total count
    result = await db.scalar(select(func.count()).select_from(NewEvent))
    total_count: int = result if result is not None else 0

    # Proper relationship loading
    query = (
        select(NewEvent)
        .options(
            selectinload(NewEvent.new_category),
            selectinload(NewEvent.new_subcategory),
            selectinload(NewEvent.new_organizer),
        )
        .order_by(NewEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    events = result.scalars().all()

    # Format into schema
    items = [
        EventResponse(
            event_id=e.event_id,
            event_title=e.event_title,
            event_slug=e.event_slug,
            event_type=e.event_type,
            card_image=e.card_image,
            location=e.location,
            extra_data=e.extra_data,
            category_title=(
                e.new_category.category_name if e.new_category else None
            ),
            subcategory_title=(
                e.new_subcategory.subcategory_name
                if e.new_subcategory
                else None
            ),
            organizer_name=(
                e.new_organizer.username if e.new_organizer else None
            ),
            event_status=e.event_status,
            created_at=e.created_at,
            featured=e.featured_event,
        )
        for e in events
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event records retrieved successfully",
        data=EventListResponse(
            events=items, page=page, limit=limit, total=total_count
        ),
    )


@router.get("/search", response_model=list[EventSearchResponse])
async def search_endpoint(
    q: Optional[str] = Query(
        None,
        description="Search term: category, subcategory, or event. If empty, latest 5 events are returned.",
    ),
    db: AsyncSession = Depends(get_db),
):
    events = await search_events_for_global(db, q)

    return [
        EventSearchResponse(
            event_title=item["event"].event_title,
            event_slug=item["event"].event_slug,
            card_image=item["event"].card_image,
            category_title=item["event"].new_category.category_name,
            subcategory_title=(
                item["event"].new_subcategory.subcategory_name
                if item["event"].new_subcategory
                else None
            ),
            next_event_date=item["next_event_date"],
        )
        for item in events
    ]


@router.get(
    "/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=NewEventSlotResponse,
    summary="Get full event details with slots and seat categories",
)
@exception_handler
async def get_event_by_id(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full event details by event_id"""

    # 1. Fetch event with relations
    event = await fetch_event_by_id_with_relations(db, event_id)
    if not event:
        return event_not_found_response()

    # 2. Fetch slots for this event
    query_slots = select(NewEventSlot).where(
        NewEventSlot.event_ref_id == event_id
    )
    slots = (await db.execute(query_slots)).scalars().all()

    # Dictionary to hold grouped slots by date
    slot_data_input: Dict[str, List[dict]] = {}

    for slot in slots:
        date_str = slot.slot_date.strftime("%Y-%m-%d")

        # 2. Fetch seat categories for this slot
        query_seats = select(NewEventSeatCategory).where(
            NewEventSeatCategory.slot_ref_id == slot.slot_id
        )
        seats = (await db.execute(query_seats)).scalars().all()

        seat_responses = [
            {
                "seat_category_id": s.seat_category_id,
                "label": s.category_label,
                "price": s.price,
                "totalTickets": s.total_tickets,
                "booked": s.booked,
                "held": s.held,
            }
            for s in seats
        ]

        slot_dict = {
            "slot_id": slot.slot_id,
            "time": slot.start_time,  # already in "HH:MM AM/PM" format
            "duration": minutes_to_duration_string(slot.duration_minutes),
            "seatCategories": seat_responses,
        }

        # Group by date
        if date_str not in slot_data_input:
            slot_data_input[date_str] = []
        slot_data_input[date_str].append(slot_dict)

    # 3. Build ONE wrapper with all slots grouped
    slot_wrapper = EventSlotResponseWrapper.from_input(
        event_ref_id=event_id, slot_data_input=slot_data_input
    )

    # 3. Build final response
    event_response = NewEventSlotResponse(
        event_id=event.event_id,
        event_title=event.event_title,
        event_slug=event.event_slug,
        event_type=event.event_type,
        event_dates=sorted({s.slot_date for s in slots}),
        location=event.location,
        is_online=event.is_online,
        event_status=event.event_status,
        featured_event=event.featured_event,
        category=(
            CategoryInfo.model_validate(event.new_category)
            if event.new_category
            else None
        ),
        subcategory=(
            SubCategoryInfo.model_validate(event.new_subcategory)
            if event.new_subcategory
            else None
        ),
        organizer=(
            OrganizerInfo.model_validate(event.new_organizer)
            if event.new_organizer
            else None
        ),
        slots=(
            [EventSlotResponseWrapper.model_validate(slot_wrapper)]
            if slot_wrapper
            else []
        ),
        card_image=event.card_image,
        banner_image=event.banner_image,
        event_extra_images=event.event_extra_images,
        extra_data=event.extra_data,
        hash_tags=event.hash_tags,
        created_at=event.created_at,
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event retrieved successfully",
        data=event_response.model_dump(),
    )


@router.patch(
    "/status/{event_id}",
    status_code=status.HTTP_200_OK,
    summary="Update event status (publish/draft)",
)
@exception_handler
async def change_event_status(
    event_id: str,
    event_status: EventStatus = Form(
        ...,
        example=EventStatus.ACTIVE,
        description="Event status (ACTIVE for published, INACTIVE for draft)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Change the status of an event (ACTIVE = published, INACTIVE = draft)

    Business Rules:
    - Events with existing slots cannot be set to PENDING status
    - Events without slots cannot be set to ACTIVE status
    - PENDING status is only for events being set up (no slots yet)
    - Events automatically become ACTIVE when slots are created
    """
    # Fetch event by event_id
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return event_not_found_response()

    # Check if trying to set status to PENDING when event already has slots
    if event_status == EventStatus.PENDING:
        # Check if event has any slots
        query_slots = select(NewEventSlot).where(
            NewEventSlot.event_ref_id == event_id
        )
        existing_slots = (await db.execute(query_slots)).scalars().first()

        if existing_slots:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot set event status to PENDING when event already has slots",
                data={
                    "event_id": event.event_id,
                    "current_status": event.event_status,
                    "requested_status": event_status,
                },
            )

    # Check if trying to set status to ACTIVE from PENDING when event doesn't have slots
    if (
        event_status == EventStatus.ACTIVE
        and event.event_status == EventStatus.PENDING
    ):
        # Check if event has any slots
        query_slots = select(NewEventSlot).where(
            NewEventSlot.event_ref_id == event_id
        )
        existing_slots = (await db.execute(query_slots)).scalars().first()

        if not existing_slots:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot set event status to ACTIVE when event has no slots",
                data={
                    "event_id": event.event_id,
                    "current_status": event.event_status,
                    "requested_status": event_status,
                },
            )

    # Update status
    event.event_status = event_status
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Determine appropriate status text and message
    if event_status == EventStatus.ACTIVE:
        status_text = "published"
        message = "Event status updated to published"
    elif event_status == EventStatus.INACTIVE:
        status_text = "draft"
        message = "Event status updated to draft"
    else:  # EventStatus.PENDING
        status_text = "pending"
        message = "Event status updated to pending"

    return api_response(
        status_code=status.HTTP_200_OK,
        message=message,
        data={
            "event_id": event.event_id,
            "event_status": event.event_status,
            "status_text": status_text,
        },
    )


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete event and cascade delete all slots & seat categories",
)
@exception_handler
async def delete_event_by_id(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an event by ID. Cascade deletes associated slots and seat categories.
    """

    # Fetch the event to ensure it exists
    event = await db.scalar(
        select(NewEvent)
        .where(NewEvent.event_id == event_id)
        .options(selectinload(NewEvent.new_slots))
    )

    if not event:
        return event_not_found_response()

    # Delete the event (cascade delete will remove slots and seat categories)
    await db.delete(event)
    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event deleted successfully",
        data={"event_id": event_id, "deleted": True},
    )
