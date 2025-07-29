import os
from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.utility_events import (
    EventExistsResponse,
    EventMetricsResponse,
    HealthCheckResponse,
    SlotCountResponse,
)
from event_service.services.events import fetch_event_by_id_with_relations
from event_service.services.response_builder import (
    event_not_found_response,
)
from event_service.services.slots import get_slot_statistics
from event_service.services.utility_events import (
    check_database_health,
    get_event_metrics,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


# Utility APIs for Admin Panel and DevOps
@router.get(
    "/health/",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheckResponse,
)
@exception_handler
async def health_check(
    db: AsyncSession = Depends(get_db),
):
    """Health check API"""

    # Check database health
    db_healthy = await check_database_health(db)
    db_status = "healthy" if db_healthy else "unhealthy"

    # Get service info
    service_name = "Events Service"
    service_version = os.getenv("SERVICE_VERSION", "1.0.0")

    # Calculate uptime (simplified - in production you'd track actual start time)
    uptime = "Service running"

    # Overall status
    overall_status = "healthy" if db_healthy else "unhealthy"

    response_data = {
        "status": overall_status,
        "timestamp": datetime.utcnow(),
        "service": service_name,
        "version": service_version,
        "database": db_status,
        "uptime": uptime,
    }

    response_status = (
        status.HTTP_200_OK
        if db_healthy
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return api_response(
        status_code=response_status,
        message=f"Service is {overall_status}",
        data=response_data,
    )


@router.get(
    "/{event_id}/exists",
    status_code=status.HTTP_200_OK,
    response_model=EventExistsResponse,
)
@exception_handler
async def check_event_exists(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Check if an event exists"""

    # Check if event exists
    event = await fetch_event_by_id_with_relations(db, event_id)

    if event:
        response_data = {
            "event_id": event_id,
            "exists": True,
            "event_status": event.event_status,
            "event_title": event.event_title,
        }
    else:
        response_data = {
            "event_id": event_id,
            "exists": False,
            "event_status": None,
            "event_title": None,
        }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event existence check completed",
        data=response_data,
    )


@router.get(
    "/{event_id}/slots/count",
    status_code=status.HTTP_200_OK,
    response_model=SlotCountResponse,
)
@exception_handler
async def get_event_slot_count(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get number of slots for an event"""

    # Check if event exists
    event = await fetch_event_by_id_with_relations(db, event_id)
    if not event:
        return event_not_found_response()

    # Get slot statistics
    slot_stats = await get_slot_statistics(db, event_id)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot count retrieved successfully",
        data=slot_stats,
    )


@router.get(
    "/metrics/",
    status_code=status.HTTP_200_OK,
    response_model=EventMetricsResponse,
)
@exception_handler
async def get_overall_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Get overall metrics (event counts, active status, etc.)"""

    # Get comprehensive metrics
    metrics = await get_event_metrics(db)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event metrics retrieved successfully",
        data=metrics,
    )
