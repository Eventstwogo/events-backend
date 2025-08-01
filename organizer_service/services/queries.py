from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
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
