from datetime import date, datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from new_event_service.schemas.slots import (
    EventSlotCreateRequest,
    EventSlotResponseWrapper,
    EventSlotUpdateRequest,
)
from new_event_service.services.events import (
    check_event_exists,
    check_event_status_created_or_not_by_event_id,
)
from new_event_service.services.response_builder import (
    event_not_created_response,
    event_not_found_response,
    invalid_slot_data_response,
    slot_not_found_response,
)
from new_event_service.utils.utils import (
    minutes_to_duration_string,
    parse_duration_to_minutes,
)
from shared.core.api_response import api_response
from shared.db.models.new_events import (
    EventStatus,
    NewEventSeatCategory,
    NewEventSlot,
)
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.id_generators import generate_digits_upper_lower_case

router = APIRouter()


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    summary="Create event slots with seat categories",
)
@exception_handler
async def create_event_slot_endpoint(
    slot_request: EventSlotCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:

    # 1. Validate that the event exists
    event = await check_event_exists(db, slot_request.event_ref_id)
    if not event:
        return event_not_found_response()

    # 2. Check event status must be PENDING
    if event.event_status != EventStatus.PENDING:
        return invalid_slot_data_response(
            f"Cannot create slots. Event status must be PENDING, found '{event.event_status}'."
        )

    # 3. Insert/Update event dates (merge with existing)
    existing_dates: List[date] = event.event_dates or []
    new_dates = set(existing_dates) | set(slot_request.event_dates)
    event.event_dates = sorted(new_dates)
    event.event_status = EventStatus.ACTIVE

    # 4. Validate slot data
    if not slot_request.slot_data:
        return invalid_slot_data_response("Slot data cannot be empty")

    # 5. Validate slot dates strictly match event.event_dates
    for date_key in slot_request.slot_data.keys():
        slot_date = datetime.strptime(date_key, "%Y-%m-%d").date()
        if slot_date not in event.event_dates:
            return invalid_slot_data_response(
                f"Slot date '{date_key}' must be one of event dates: {event.event_dates}"
            )

    created_slot_ids = {}  # map date_key -> list of slot_ids for response

    # 6. Process each slot and insert NewEventSlot + NewEventSeatCategory
    for date_key, slots in slot_request.slot_data.items():
        created_slot_ids[date_key] = []

        for slot in slots:
            slot_id = generate_digits_upper_lower_case(8)
            duration_minutes = parse_duration_to_minutes(slot.duration)

            # Create NewEventSlot row
            new_slot = NewEventSlot(
                slot_id=slot_id,
                event_ref_id=slot_request.event_ref_id,
                slot_date=datetime.strptime(date_key, "%Y-%m-%d").date(),
                start_time=slot.time,
                duration_minutes=duration_minutes,
            )
            db.add(new_slot)
            await db.flush()  # ensure slot is persisted

            # Create seat categories
            for seat in slot.seatCategories:
                seat_category_id = generate_digits_upper_lower_case(8)
                new_seat = NewEventSeatCategory(
                    seat_category_id=seat_category_id,
                    slot_ref_id=slot_id,
                    category_label=seat.label,
                    price=seat.price,
                    total_tickets=seat.totalTickets,
                    booked=seat.booked or 0,
                    held=seat.held or 0,
                )
                db.add(new_seat)

            created_slot_ids[date_key].append(slot_id)

    # Save changes
    await db.commit()
    await db.refresh(event)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Event slots created successfully",
    )


@router.put(
    "/update",
    status_code=status.HTTP_200_OK,
    summary="Update event slots with optional fields",
)
@exception_handler
async def update_event_slot_endpoint(
    event_ref_id: str,
    slot_update_request: EventSlotUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Updates slots and seat categories for a given event.
    Rules:
    1. Event must exist
    2. Event status must allow slot updates
    3. Event dates are merged if provided
    4. Slot dates must belong to event.event_dates
    5. Existing slots are updated, new seat categories can be added
    6. No response data returned on success
    """

    # 1. Validate event exists
    event = await check_event_exists(db, event_ref_id)
    if not event:
        return event_not_found_response()

    # 2. Check event status
    slot_created_event = await check_event_status_created_or_not_by_event_id(
        db, event.event_id
    )
    if not slot_created_event:
        return event_not_created_response()

    # 3. Merge event dates if provided
    if slot_update_request.event_dates:
        existing_dates: List[date] = event.event_dates or []
        new_dates = set(existing_dates) | set(slot_update_request.event_dates)
        event.event_dates = sorted(new_dates)

    if not slot_update_request.slot_data:
        return invalid_slot_data_response("Slot data cannot be empty")

    # 4. Loop through dates and slots
    for date_key, slots in slot_update_request.slot_data.items():
        slot_date_obj = datetime.strptime(date_key, "%Y-%m-%d").date()

        # Ensure slot_date is part of event.event_dates
        if slot_date_obj not in (event.event_dates or []):
            return invalid_slot_data_response(
                f"Slot date '{date_key}' must be one of event dates: {event.event_dates}"
            )

        for slot in slots:
            # ---- Lookup existing slot ----
            query = select(NewEventSlot).where(
                NewEventSlot.event_ref_id == event_ref_id,
                NewEventSlot.slot_date == slot_date_obj,
            )
            if slot.time:  # If provided, match time
                query = query.where(NewEventSlot.start_time == slot.time)

            existing_slot = (await db.execute(query)).scalars().first()
            if not existing_slot:
                return slot_not_found_response()

            # ---- Update slot fields ----
            if slot.time:
                existing_slot.start_time = slot.time
            if slot.duration:
                existing_slot.duration_minutes = parse_duration_to_minutes(
                    slot.duration
                )

            # ---- Update seat categories ----
            if slot.seatCategories:
                for seat in slot.seatCategories:
                    existing_seat = None

                    # 1. If id is given, check by id (within the same slot)
                    if seat.id:
                        query_seat = select(NewEventSeatCategory).where(
                            NewEventSeatCategory.seat_category_id == seat.id,
                            NewEventSeatCategory.slot_ref_id
                            == existing_slot.slot_id,
                        )
                        existing_seat = (
                            (await db.execute(query_seat)).scalars().first()
                        )

                    # 2. If not found by id, check by label within the same slot
                    if not existing_seat and seat.label:
                        query_seat = select(NewEventSeatCategory).where(
                            NewEventSeatCategory.slot_ref_id
                            == existing_slot.slot_id,
                            func.lower(NewEventSeatCategory.category_label)
                            == seat.label.lower(),
                        )
                        existing_seat = (
                            (await db.execute(query_seat)).scalars().first()
                        )

                    # 3. Update or create
                    if existing_seat:
                        if seat.label is not None:
                            existing_seat.category_label = seat.label
                        if seat.price is not None:
                            existing_seat.price = seat.price
                        if seat.totalTickets is not None:
                            existing_seat.total_tickets = seat.totalTickets
                        if seat.booked is not None:
                            existing_seat.booked = seat.booked
                        if seat.held is not None:
                            existing_seat.held = seat.held
                    else:
                        # Create new seat category
                        new_seat = NewEventSeatCategory(
                            seat_category_id=generate_digits_upper_lower_case(
                                8
                            ),
                            slot_ref_id=existing_slot.slot_id,
                            category_label=seat.label,
                            price=seat.price or 0.0,
                            total_tickets=seat.totalTickets or 0,
                            booked=seat.booked or 0,
                            held=seat.held or 0,
                        )
                        db.add(new_seat)

    # Commit all updates
    await db.commit()

    # 5. Return success response without slot/seat data
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event slots updated successfully",
    )


@router.get(
    "/get/{event_ref_id}",
    status_code=status.HTTP_200_OK,
    summary="Get all slots with seat categories for an event",
)
@exception_handler
async def get_event_slots(
    event_ref_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Fetch all slots and their seat categories for a given event.
    Response is wrapped in EventSlotResponseWrapper for consistency.
    """

    # 1. Validate that the event exists
    event = await check_event_exists(db, event_ref_id)
    if not event:
        return event_not_found_response()

    # 2. Fetch all slots for this event
    query_slots = select(NewEventSlot).where(
        NewEventSlot.event_ref_id == event_ref_id
    )
    slots = (await db.execute(query_slots)).scalars().all()

    if not slots:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="No slots found for this event",
            data={
                "event_ref_id": event_ref_id,
                "event_dates": [],
                "slot_data": {},
            },
        )

    # 3. Build slot_data_input compatible with EventSlotResponseWrapper.from_input()
    slot_data_input: Dict[str, List[dict]] = {}

    for slot in slots:
        date_str = slot.slot_date.strftime("%Y-%m-%d")

        # Fetch seat categories for this slot
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
            "time": slot.start_time,  # assuming already "HH:MM AM/PM"
            "duration": minutes_to_duration_string(
                slot.duration_minutes
            ),  # e.g. "1 hours 30 minutes"
            "seatCategories": seat_responses,
        }

        slot_data_input.setdefault(date_str, []).append(slot_dict)

    # 4. Use wrapper class to format response properly
    response_wrapper = EventSlotResponseWrapper.from_input(
        event_ref_id=event_ref_id, slot_data_input=slot_data_input
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event slots fetched successfully",
        data=response_wrapper.model_dump(),
    )
