from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from organizer_service.schemas.queries import (
    AddMessageRequest,
    CreateQueryRequest,
    QueryFilters,
    ThreadMessage,
    UpdateQueryStatusRequest,
)
from shared.core.api_response import api_response
from shared.db.models.admin_users import AdminUser
from shared.db.models.organizer import OrganizerQuery, QueryStatus


async def get_user_by_id(user_id: str, db: AsyncSession) -> Optional[AdminUser]:
    stmt = (
        select(AdminUser)
        .options(selectinload(AdminUser.role))
        .where(AdminUser.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_query_by_id(
    query_id: int, db: AsyncSession
) -> Optional[OrganizerQuery]:
    stmt = select(OrganizerQuery).where(OrganizerQuery.id == query_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_with_role(
    db: AsyncSession,
    user_id: str,
    # current_admin: Annotated[AdminUser, Depends(get_current_active_admin)],
) -> Optional[AdminUser]:
    """Helper function to get user with role information"""
    user_stmt = (
        select(AdminUser)
        .options(selectinload(AdminUser.role))
        .where(AdminUser.user_id == user_id)
    )
    result = await db.execute(user_stmt)
    return result.scalars().first()


def is_admin_user(user: AdminUser) -> bool:
    """Helper function to check if user is admin"""
    if not user or not user.role:
        return False
    return user.role.role_name.lower() in ["admin", "superadmin"]


async def get_organizer_user(
    db: AsyncSession, user_id: str
) -> Optional[AdminUser]:
    """Helper function to get user and validate they have organizer role"""
    user_stmt = (
        select(AdminUser)
        .options(selectinload(AdminUser.role))
        .where(AdminUser.user_id == user_id)
    )
    result = await db.execute(user_stmt)
    user = result.scalars().first()

    if not user or not user.role:
        return None

    # Check if user has organizer role
    if user.role.role_name.lower() != "organizer":
        return None

    return user


def build_query_filters(role: str, user_id: str, filters: QueryFilters):
    stmt = select(OrganizerQuery)

    if role == "organizer":
        stmt = stmt.where(OrganizerQuery.sender_user_id == user_id)
    elif role == "admin":
        if filters.sender_user_id:
            stmt = stmt.where(
                OrganizerQuery.sender_user_id == filters.sender_user_id
            )
        if filters.receiver_user_id:
            stmt = stmt.where(
                OrganizerQuery.receiver_user_id == filters.receiver_user_id
            )

    if filters.query_status:
        stmt = stmt.where(OrganizerQuery.query_status == filters.query_status)

    if filters.category:
        stmt = stmt.where(
            OrganizerQuery.category.ilike(f"%{filters.category}%")
        )

    return stmt


async def get_total_query_count(db: AsyncSession, stmt):
    count_stmt = select(func.count()).select_from(stmt.subquery())
    result = await db.execute(count_stmt)
    return result.scalar() or 0


def calculate_pagination(page: int, limit: int, total: int) -> Dict[str, Any]:
    total_pages = (total + limit - 1) // limit
    return {
        "current_page": page,
        "total_pages": total_pages,
        "total_items": total,
        "items_per_page": limit,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


async def get_query_stats(
    db: AsyncSession, user_id: str
) -> Dict[str, int] | JSONResponse:
    """Get query statistics for dashboard"""

    # Get user info - eagerly load the role relationship
    user_stmt = (
        select(AdminUser)
        .options(selectinload(AdminUser.role))
        .where(AdminUser.user_id == user_id)
    )
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            log_error=True,
        )

    user_role = user.role.role_name.lower()

    # Base stats query
    base_query = select(func.count()).select_from(OrganizerQuery)

    if user_role == "organizer":
        # Organizer sees only their queries
        stats = {}

        # Total queries by this organizer
        my_queries_stmt = base_query.where(
            OrganizerQuery.sender_user_id == user_id
        )
        result = await db.execute(my_queries_stmt)
        stats["my_queries"] = result.scalar()

        # Status breakdown for organizer's queries
        for qstatus in QueryStatus:
            status_stmt = base_query.where(
                and_(
                    OrganizerQuery.sender_user_id == user_id,
                    OrganizerQuery.query_status == qstatus,
                )
            )
            result = await db.execute(status_stmt)
            stats[f"{qstatus.value.replace('-', '_')}_queries"] = (
                result.scalar()
            )

        stats["total_queries"] = stats["my_queries"]
        stats["assigned_to_me"] = 0  # Not applicable for organizers

    else:  # admin
        stats = {}

        # Total queries in system
        result = await db.execute(base_query)
        stats["total_queries"] = result.scalar()

        # Status breakdown for all queries
        for qstatus in QueryStatus:
            status_stmt = base_query.where(
                OrganizerQuery.query_status == qstatus
            )
            result = await db.execute(status_stmt)
            stats[f"{qstatus.value.replace('-', '_')}_queries"] = (
                result.scalar()
            )

        # Queries assigned to this admin
        assigned_stmt = base_query.where(
            OrganizerQuery.receiver_user_id == user_id
        )
        result = await db.execute(assigned_stmt)
        stats["assigned_to_me"] = result.scalar()

        # My queries (if admin also creates queries)
        my_queries_stmt = base_query.where(
            OrganizerQuery.sender_user_id == user_id
        )
        result = await db.execute(my_queries_stmt)
        stats["my_queries"] = result.scalar()

    return stats


async def _count(db: AsyncSession, stmt) -> int:
    result = await db.execute(stmt)
    return result.scalar() or 0


async def get_query_stats_service(
    db: AsyncSession, user_id: str
) -> Dict[str, int] | JSONResponse:
    user = await get_user_with_role(db, user_id)
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            log_error=True,
        )

    role = user.role.role_name.lower()
    stats = {}
    base_query = select(func.count()).select_from(OrganizerQuery)

    if role == "organizer":
        stats["my_queries"] = await _count(
            db, base_query.where(OrganizerQuery.sender_user_id == user_id)
        )
        for qstatus in QueryStatus:
            key = f"{qstatus.value.replace('-', '_')}_queries"
            condition = and_(
                OrganizerQuery.sender_user_id == user_id,
                OrganizerQuery.query_status == qstatus,
            )
            stats[key] = await _count(db, base_query.where(condition))
        stats["total_queries"] = stats["my_queries"]
        stats["assigned_to_me"] = 0
    elif role == "admin":
        stats["total_queries"] = await _count(db, base_query)
        for qstatus in QueryStatus:
            key = f"{qstatus.value.replace('-', '_')}_queries"
            stats[key] = await _count(
                db, base_query.where(OrganizerQuery.query_status == qstatus)
            )
        stats["assigned_to_me"] = await _count(
            db, base_query.where(OrganizerQuery.receiver_user_id == user_id)
        )
        stats["my_queries"] = await _count(
            db, base_query.where(OrganizerQuery.sender_user_id == user_id)
        )
    else:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Invalid user role",
            log_error=True,
        )

    return stats


async def update_query_status_service(
    db: AsyncSession,
    query_id: int,
    user_id: str,
    request: UpdateQueryStatusRequest,
) -> OrganizerQuery | JSONResponse:
    """Update query status with proper permission validation and message handling"""

    # Get the query
    query_obj = await db.get(OrganizerQuery, query_id)
    if not query_obj:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Query with ID {query_id} not found",
            log_error=True,
        )

    # Get user with role information
    user = await get_user_with_role(db, user_id)
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            log_error=True,
        )

    user_role = user.role.role_name.lower()

    # Permission validation
    can_update = False

    # Special handling for closing queries
    if request.query_status == QueryStatus.QUERY_CLOSED:
        if user_role in ["admin", "superadmin"]:
            return api_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message="Admins cannot close queries. Only organizers can close their own queries.",
                log_error=True,
            )
        elif user_role == "organizer":
            # Organizers can only close their own queries
            can_update = query_obj.sender_user_id == user_id
            if not can_update:
                return api_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message="You can only close your own queries",
                    log_error=True,
                )
    else:
        # For other status updates, use existing logic
        if user_role == "organizer":
            # Organizers can only update their own queries
            can_update = query_obj.sender_user_id == user_id
        elif user_role in ["admin", "superadmin"]:
            # Admins can update any query (except closing)
            can_update = True

        if not can_update:
            return api_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message="You do not have permission to update this query",
                log_error=True,
            )

    # Update the query status
    query_obj.query_status = request.query_status

    # If admin is updating, set them as receiver
    if user_role in ["admin", "superadmin"] and not query_obj.receiver_user_id:
        query_obj.receiver_user_id = user_id

    # Add message to thread if provided
    if request.message:
        from datetime import datetime, timezone

        # Determine sender type based on role
        sender_type = (
            "admin" if user_role in ["admin", "superadmin"] else "organizer"
        )

        # Create thread message
        thread_message = {
            "type": "response",
            "sender_type": sender_type,
            "user_id": user_id,
            "message": request.message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Add to thread
        if query_obj.thread is None:
            query_obj.thread = []
        query_obj.thread.append(thread_message)

    try:
        await db.commit()
        await db.refresh(query_obj)
        return query_obj
    except Exception as e:
        await db.rollback()
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to update query status: {str(e)}",
            log_error=True,
        )


async def fetch_query_statistics(db: AsyncSession) -> Dict:
    """
    Fetch simple query statistics including counts by status and monthly growth.
    """
    from shared.core.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Fetching query statistics")

    # Get current date and calculate date ranges
    today = date.today()
    current_month_start = today.replace(day=1)

    # Calculate previous month start
    if current_month_start.month == 1:
        previous_month_start = current_month_start.replace(
            year=current_month_start.year - 1, month=12
        )
    else:
        previous_month_start = current_month_start.replace(
            month=current_month_start.month - 1
        )

    # Get counts for each query status
    open_queries_query = select(func.count(OrganizerQuery.id)).filter(
        OrganizerQuery.query_status == QueryStatus.QUERY_OPEN
    )
    open_queries_result = await db.execute(open_queries_query)
    open_queries_count = open_queries_result.scalar() or 0

    closed_queries_query = select(func.count(OrganizerQuery.id)).filter(
        OrganizerQuery.query_status == QueryStatus.QUERY_CLOSED
    )
    closed_queries_result = await db.execute(closed_queries_query)
    closed_queries_count = closed_queries_result.scalar() or 0

    resolved_queries_query = select(func.count(OrganizerQuery.id)).filter(
        OrganizerQuery.query_status == QueryStatus.QUERY_ANSWERED
    )
    resolved_queries_result = await db.execute(resolved_queries_query)
    resolved_queries_count = resolved_queries_result.scalar() or 0

    in_progress_queries_query = select(func.count(OrganizerQuery.id)).filter(
        OrganizerQuery.query_status == QueryStatus.QUERY_IN_PROGRESS
    )
    in_progress_queries_result = await db.execute(in_progress_queries_query)
    in_progress_queries_count = in_progress_queries_result.scalar() or 0

    # Get current month open queries count
    current_month_open_queries_query = select(
        func.count(OrganizerQuery.id)
    ).filter(
        and_(
            OrganizerQuery.query_status == QueryStatus.QUERY_OPEN,
            OrganizerQuery.created_at >= current_month_start,
        )
    )
    current_month_open_queries_result = await db.execute(
        current_month_open_queries_query
    )
    current_month_open_queries = current_month_open_queries_result.scalar() or 0

    # Get previous month open queries count
    previous_month_open_queries_query = select(
        func.count(OrganizerQuery.id)
    ).filter(
        and_(
            OrganizerQuery.query_status == QueryStatus.QUERY_OPEN,
            OrganizerQuery.created_at >= previous_month_start,
            OrganizerQuery.created_at < current_month_start,
        )
    )
    previous_month_open_queries_result = await db.execute(
        previous_month_open_queries_query
    )
    previous_month_open_queries = (
        previous_month_open_queries_result.scalar() or 0
    )

    # Calculate monthly growth percentage for open queries
    if previous_month_open_queries > 0:
        monthly_growth_percentage = round(
            (
                (current_month_open_queries - previous_month_open_queries)
                / previous_month_open_queries
            )
            * 100,
            2,
        )
    else:
        # If no open queries in previous month, show 100% if current month has queries, else 0%
        monthly_growth_percentage = (
            100.0 if current_month_open_queries > 0 else 0.0
        )

    logger.info(
        f"Query statistics calculated: open={open_queries_count}, closed={closed_queries_count}, resolved={resolved_queries_count}, in_progress={in_progress_queries_count}, growth={monthly_growth_percentage}%"
    )

    return {
        "open_queries_count": open_queries_count,
        "closed_queries_count": closed_queries_count,
        "resolved_queries_count": resolved_queries_count,
        "in_progress_queries_count": in_progress_queries_count,
        "monthly_growth_percentage": monthly_growth_percentage,
        "current_month_open_queries": current_month_open_queries,
        "previous_month_open_queries": previous_month_open_queries,
    }
