from datetime import date, datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, Path, status
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
    fetch_event_by_slug,
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
        return invalid_slot_data_response(
            "Invalid request: 'slot_data' is missing or empty. "
            "Please provide slot details for each event date."
        )

    # 5. Validate slot dates strictly match event.event_dates
    for date_key in slot_request.slot_data.keys():
        slot_date = datetime.strptime(date_key, "%Y-%m-%d").date()
        # if slot_date not in event.event_dates:
        #     return invalid_slot_data_response(
        #         f"Slot date '{date_key}' must be one of event dates: {event.event_dates}"
        #     )  
        min_date, max_date = min(event.event_dates), max(event.event_dates)
        if not (min_date <= slot_date <= max_date):
            return invalid_slot_data_response(
                f"Slot date '{date_key}' must fall within event date range {min_date} to {max_date}"
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
    2. Event must already have slots created
    3. Event dates are merged with provided ones
    4. Newly added dates must also have slots provided in slot_data
    5. Slot dates must belong to event.event_dates
    6. Existing slots are updated, missing ones are created
    """

    # 1. Validate event exists
    event = await check_event_exists(db, event_ref_id)
    if not event:
        return event_not_found_response()

    # 2. Ensure event has slots created
    slot_created_event = await check_event_status_created_or_not_by_event_id(
        db, event.event_id
    )
    if not slot_created_event:
        return event_not_created_response()

    # 3. Merge event dates
    if slot_update_request.event_dates:
        existing_dates: List[date] = event.event_dates or []
        new_dates = set(existing_dates) | set(slot_update_request.event_dates)
        event.event_dates = sorted(new_dates)

        if slot_update_request.slot_data is None:
            return invalid_slot_data_response(
                "Invalid request: 'slot_data' is missing or empty. "
                "Please provide slot details for each event date."
            )

        # Ensure all new dates have slot data
        missing_dates = [
            d.strftime("%Y-%m-%d")
            for d in new_dates
            if d not in existing_dates
            and d.strftime("%Y-%m-%d")
            not in slot_update_request.slot_data.keys()
        ]
        if missing_dates:
            return invalid_slot_data_response(
                f"Missing slot_data for newly added dates: {missing_dates}"
            )

    if slot_update_request.slot_data is None:
        return invalid_slot_data_response(
            "Invalid request: 'slot_data' is missing or empty. "
            "Please provide slot details for each event date."
        )

    updated_slots = []
    created_slots = []

    # 4. Loop through dates and slots
    for date_key, slots in slot_update_request.slot_data.items():
        slot_date_obj = datetime.strptime(date_key, "%Y-%m-%d").date()

        # Ensure slot_date is part of event.event_dates
        # if slot_date_obj not in (event.event_dates or []):
        #     return invalid_slot_data_response(
        #         f"Slot date '{date_key}' must be one of event dates: {event.event_dates}"
        #     )
        
        min_date, max_date = min(event.event_dates), max(event.event_dates)
        if not (min_date <= slot_date_obj <= max_date):
            return invalid_slot_data_response(
                f"Slot date '{date_key}' must fall within event date range {min_date} to {max_date}"
            )

        # Skip if no slots provided for this date
        if not slots:
            continue

        for slot in slots:
            existing_slot = None

            # ---- Lookup existing slot ----
            if slot.slot_id:  # preferred lookup
                query = select(NewEventSlot).where(
                    NewEventSlot.slot_id == slot.slot_id,
                    NewEventSlot.event_ref_id == event_ref_id,
                )
                existing_slot = (await db.execute(query)).scalars().first()
            elif slot.time:  # fallback lookup by date + time
                query = select(NewEventSlot).where(
                    NewEventSlot.event_ref_id == event_ref_id,
                    NewEventSlot.slot_date == slot_date_obj,
                    NewEventSlot.start_time == slot.time,
                )
                existing_slot = (await db.execute(query)).scalars().first()

            if existing_slot:
                # Update existing slot
                if slot.time:
                    existing_slot.start_time = slot.time
                if slot.duration:
                    existing_slot.duration_minutes = parse_duration_to_minutes(
                        slot.duration
                    )

                updated_slots.append(existing_slot.slot_id)

                # ---- Update or create seat categories ----
                if slot.seatCategories:
                    for seat in slot.seatCategories:
                        existing_seat = None

                        # 1. If id is given, check by id
                        if seat.seat_category_id:
                            query_seat = select(NewEventSeatCategory).where(
                                NewEventSeatCategory.seat_category_id == seat.seat_category_id,
                                NewEventSeatCategory.slot_ref_id == existing_slot.slot_id,
                            )
                            existing_seat = (await db.execute(query_seat)).scalars().first()

                        # 2. Else check by label within same slot
                        if not existing_seat and seat.label:
                            query_seat = select(NewEventSeatCategory).where(
                                NewEventSeatCategory.slot_ref_id == existing_slot.slot_id,
                                func.lower(NewEventSeatCategory.category_label) == seat.label.lower(),
                            )
                            existing_seat = (await db.execute(query_seat)).scalars().first()

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
                                seat_category_id=generate_digits_upper_lower_case(8),
                                slot_ref_id=existing_slot.slot_id,
                                category_label=seat.label,
                                price=seat.price or 0.0,
                                total_tickets=seat.totalTickets or 0,
                                booked=seat.booked or 0,
                                held=seat.held or 0,
                            )
                            db.add(new_seat)

            else:
                # Create new slot since it didn’t exist
                slot_id = generate_digits_upper_lower_case(8)
                duration_minutes = (
                    parse_duration_to_minutes(slot.duration)
                    if slot.duration is not None
                    else None
                )

                new_slot = NewEventSlot(
                    slot_id=slot_id,
                    event_ref_id=event_ref_id,
                    slot_date=slot_date_obj,
                    start_time=slot.time,
                    duration_minutes=duration_minutes,
                )
                db.add(new_slot)
                await db.flush()

                created_slots.append(slot_id)

                # Create seat categories
                if slot.seatCategories:
                    for seat in slot.seatCategories:
                        seat_category_id = generate_digits_upper_lower_case(8)
                        new_seat = NewEventSeatCategory(
                            seat_category_id=seat_category_id,
                            slot_ref_id=slot_id,
                            category_label=seat.label,
                            price=seat.price or 0.0,
                            total_tickets=seat.totalTickets or 0,
                            booked=seat.booked or 0,
                            held=seat.held or 0,
                        )
                        db.add(new_seat)

    # Commit all updates
    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event slots updated successfully",
        data={
            "updated_slots": updated_slots,
            "created_slots": created_slots,
        },
    )


@router.put(
    "/replace",
    status_code=status.HTTP_200_OK,
    summary="Replace event dates, slots, and seat categories",
)
@exception_handler
async def replace_event_slots_endpoint(
    event_ref_id: str,
    slot_update_request: EventSlotUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Replaces event dates, slots, and seat categories with the provided data.

    Rules:
    1. Event must exist
    2. Event must already have slots created
    3. Event dates are replaced (missing ones are deleted)
    4. Slot dates must belong to event.event_dates (strict check)
    5. Existing slots not present in request are deleted
    6. Existing seat categories not present in request are deleted
    """

    # 1. Validate event exists
    event = await check_event_exists(db, event_ref_id)
    if not event:
        return event_not_found_response()

    # 2. Ensure event has slots created
    slot_created_event = await check_event_status_created_or_not_by_event_id(
        db, event.event_id
    )
    if not slot_created_event:
        return event_not_created_response()

    # 3. Replace event dates
    new_event_dates = slot_update_request.event_dates or []
    event.event_dates = sorted(new_event_dates)

    if not slot_update_request.slot_data:
        return invalid_slot_data_response(
            "Invalid request: 'slot_data' is missing or empty. "
            "Please provide slot details for each event date."
        )

    # Load existing slots for this event
    query_slots = select(NewEventSlot).where(NewEventSlot.event_ref_id == event_ref_id)
    existing_slots = (await db.execute(query_slots)).scalars().all()
    existing_slots_map = {s.slot_id: s for s in existing_slots}

    updated_slots = []
    created_slots = []
    kept_slot_ids = set()

    # 4. Process incoming slot_data
    for date_key, slots in slot_update_request.slot_data.items():
        slot_date_obj = datetime.strptime(date_key, "%Y-%m-%d").date()

        # Strict: slot_date must belong to event.event_dates
        if slot_date_obj not in new_event_dates:
            return invalid_slot_data_response(
                f"Slot date '{date_key}' must be one of event dates: {new_event_dates}"
            )

        for slot in slots:
            existing_slot = None

            if slot.slot_id and slot.slot_id in existing_slots_map:
                existing_slot = existing_slots_map[slot.slot_id]

            if existing_slot:
                # Update existing slot
                if slot.time:
                    existing_slot.start_time = slot.time
                if slot.duration:
                    existing_slot.duration_minutes = parse_duration_to_minutes(slot.duration)
                kept_slot_ids.add(existing_slot.slot_id)
                updated_slots.append(existing_slot.slot_id)

                # --- Replace seat categories for this slot ---
                query_seats = select(NewEventSeatCategory).where(
                    NewEventSeatCategory.slot_ref_id == existing_slot.slot_id
                )
                existing_seats = (await db.execute(query_seats)).scalars().all()
                existing_seat_map = {s.seat_category_id: s for s in existing_seats}
                kept_seat_ids = set()

                for seat in slot.seatCategories or []:
                    existing_seat = None
                    if seat.seat_category_id and seat.seat_category_id in existing_seat_map:
                        existing_seat = existing_seat_map[seat.seat_category_id]

                    if existing_seat:
                        existing_seat.category_label = seat.label or existing_seat.category_label
                        existing_seat.price = seat.price or existing_seat.price
                        existing_seat.total_tickets = seat.totalTickets or existing_seat.total_tickets
                        existing_seat.booked = seat.booked or existing_seat.booked
                        existing_seat.held = seat.held or existing_seat.held
                        kept_seat_ids.add(existing_seat.seat_category_id)
                    else:
                        # Create new seat category
                        new_seat = NewEventSeatCategory(
                            seat_category_id=generate_digits_upper_lower_case(8),
                            slot_ref_id=existing_slot.slot_id,
                            category_label=seat.label,
                            price=seat.price or 0.0,
                            total_tickets=seat.totalTickets or 0,
                            booked=seat.booked or 0,
                            held=seat.held or 0,
                        )
                        db.add(new_seat)

                # Delete seat categories not kept
                for seat in existing_seats:
                    if seat.seat_category_id not in kept_seat_ids:
                        await db.delete(seat)

            else:
                # Create new slot
                slot_id = generate_digits_upper_lower_case(8)
                duration_minutes = (
                    parse_duration_to_minutes(slot.duration)
                    if slot.duration else None
                )
                new_slot = NewEventSlot(
                    slot_id=slot_id,
                    event_ref_id=event_ref_id,
                    slot_date=slot_date_obj,
                    start_time=slot.time,
                    duration_minutes=duration_minutes,
                )
                db.add(new_slot)
                await db.flush()
                kept_slot_ids.add(slot_id)
                created_slots.append(slot_id)

                # Create seat categories
                for seat in slot.seatCategories or []:
                    new_seat = NewEventSeatCategory(
                        seat_category_id=generate_digits_upper_lower_case(8),
                        slot_ref_id=slot_id,
                        category_label=seat.label,
                        price=seat.price or 0.0,
                        total_tickets=seat.totalTickets or 0,
                        booked=seat.booked or 0,
                        held=seat.held or 0,
                    )
                    db.add(new_seat)

    # 5. Delete slots not in request
    for slot in existing_slots:
        if slot.slot_id not in kept_slot_ids:
            await db.delete(slot)

    # Commit everything
    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event dates, slots, and seat categories replaced successfully",
        data={
            "updated_slots": updated_slots,
            "created_slots": created_slots,
            "deleted_slots": [s.slot_id for s in existing_slots if s.slot_id not in kept_slot_ids],
        },
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


@router.get(
    "/date-details/{event_slug}/{event_date}",
    status_code=status.HTTP_200_OK,
    summary="Get slots and seat categories for a specific event on a given date",
)
@exception_handler
async def get_event_slots_by_date(
    event_slug: str,
    event_date: str = Path(..., description="Event date in YYYY-MM-DD format"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Fetch slots and seat categories for a given event on a specific date.
    """

    # 1. Validate event exists
    event = await fetch_event_by_slug(db, event_slug)
    if not event:
        return event_not_found_response()

    # 2. Validate event status
    if event.event_status != EventStatus.ACTIVE:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Event '{event.event_slug}' is not active",
            data={},
        )

    # 3. Parse and validate date
    try:
        target_date = datetime.strptime(event_date, "%Y-%m-%d").date()
    except ValueError:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Invalid date format '{event_date}', expected YYYY-MM-DD",
            data={},
        )

    # 4. Fetch slots for event on this date
    query_slots = (
        select(NewEventSlot)
        .where(
            NewEventSlot.event_ref_id == event.event_id,
            NewEventSlot.slot_date == target_date,
        )
        .order_by(NewEventSlot.start_time)
    )
    slots = (await db.execute(query_slots)).scalars().all()

    if not slots:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="No slots found for this event on the given date",
            data={
                "event_ref_id": event.event_id,
                "event_dates": [target_date],
                "slot_data": {event_date: []},
            },
        )

    # 5. Build slot_data_input for wrapper
    slot_data_input: Dict[str, List[dict]] = {}

    for slot in slots:
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
            "time": slot.start_time,
            "duration": minutes_to_duration_string(slot.duration_minutes),
            "seatCategories": seat_responses,
        }

        slot_data_input.setdefault(event_date, []).append(slot_dict)

    # 6. Use wrapper class for consistent response
    response_wrapper = EventSlotResponseWrapper.from_input(
        event_ref_id=event.event_id, slot_data_input=slot_data_input
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event slots fetched successfully for the given date",
        data=response_wrapper.model_dump(),
    )
