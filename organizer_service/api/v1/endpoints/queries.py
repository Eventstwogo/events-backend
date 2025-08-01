from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import and_, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from organizer_service.schemas.queries import (
    QueryAnswerRequest,
    QueryAnswerResponse,
    QueryCreateRequest,
    QueryCreateResponse,
    QueryListResponse,
    QueryResponse,
    QueryStatusUpdateResponse,
)
from shared.core.api_response import api_response
from shared.db.models import AdminUser, OrganizerQuery
from shared.db.models.organizer import QueryStatus
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.id_generators import (
    generate_digits_lowercase,
    generate_digits_upper_lower_case,
)


def get_status_name(status_value: str) -> str:
    """Convert status string value to enum value string"""
    for status in QueryStatus:
        if status.value == status_value:
            return status.value
    return "unknown"


async def get_user_with_role(
    db: AsyncSession, user_id: str
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


router = APIRouter()


@router.post(
    "",
    response_model=QueryCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
@exception_handler
async def create_query(
    query_data: QueryCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Create a new query by an organizer.

    - **query**: The query text (10-2000 characters)

    Returns the created query ID and success message.
    """

    # check user is organizer or not
    organizer_role_user = await get_organizer_user(db, query_data.user_id)
    if not organizer_role_user:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only organizers can create queries",
            log_error=True,
        )

    # Create new query with proper timezone-aware datetime
    new_query = OrganizerQuery(
        query_id=generate_digits_upper_lower_case(length=8),
        organizer_id=query_data.user_id,
        query=query_data.query,
        query_status=QueryStatus.QUERY_OPEN.value,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(new_query)
    await db.commit()
    await db.refresh(new_query)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Query created successfully",
        data={
            "query_id": new_query.query_id,
            "message": "Your query has been submitted and will be reviewed by our team.",
        },
    )


@router.post(
    "/{query_id}/answer",
    response_model=QueryAnswerResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def add_answer_to_query(
    answer_data: QueryAnswerRequest,
    query_id: str = Path(..., description="The query ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Add an answer/reply to a query.

    Can be used by:
    - Admins to respond to organizer queries
    - Organizers to add follow-up questions or clarifications

    - **query_id**: The ID of the query to answer
    - **answer**: The answer text (1-2000 characters)
    """
    # Get the query
    query_stmt = select(OrganizerQuery).where(
        OrganizerQuery.query_id == query_id
    )
    result = await db.execute(query_stmt)
    query = result.scalars().first()

    if not query:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND, message="Query not found"
        )

    # Get user with role information
    user_with_role = await get_user_with_role(db, answer_data.user_id)
    if not user_with_role:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )

    is_admin = is_admin_user(user_with_role)
    is_query_owner = query.organizer_id == answer_data.user_id

    if not (is_admin or is_query_owner):
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You don't have permission to answer this query",
        )

    # Additional validation for answer content
    if not answer_data.answer.strip():
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Answer cannot be empty",
        )

    # Create answer object with timezone-aware datetime
    current_time = datetime.now(timezone.utc)
    answer_obj = {
        "answer_id": generate_digits_lowercase(8),
        "answer": answer_data.answer,
        "answered_by": answer_data.user_id,
        "answered_by_username": user_with_role.username,
        "answered_at": current_time.isoformat(),
        "is_admin_response": is_admin,
    }

    # Add answer to existing answers or create new list
    # Create a new list to ensure SQLAlchemy detects the change
    current_answers = query.answers or []
    current_answers.append(answer_obj)
    query.answers = current_answers

    # Update query status and timestamp
    if is_admin and query.query_status == QueryStatus.QUERY_OPEN.value:
        query.query_status = QueryStatus.QUERY_ANSWERED.value
        query.admin_user_id = answer_data.user_id

    query.updated_at = current_time

    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Answer added successfully",
        data={
            "answer_id": answer_obj["answer_id"],
            "query_status": get_status_name(query.query_status),
        },
    )


@router.get(
    "/{query_id}",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def get_query_with_answers(
    user_id: str,
    query_id: str = Path(..., description="The query ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get a specific query with all its answers.

    - **query_id**: The ID of the query to retrieve

    Returns the complete query with all answers and metadata.
    """
    # Get query with related user information
    query_stmt = (
        select(OrganizerQuery)
        .options(
            selectinload(OrganizerQuery.organizer),
            selectinload(OrganizerQuery.admin_user),
        )
        .where(OrganizerQuery.query_id == query_id)
    )

    result = await db.execute(query_stmt)
    query = result.scalars().first()

    if not query:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND, message="Query not found"
        )

    # Check permissions - users can only see their own queries unless they're admin
    user_with_role = await get_user_with_role(db, user_id)
    if not user_with_role:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )

    is_admin = is_admin_user(user_with_role)
    is_query_owner = query.organizer_id == user_id

    if not (is_admin or is_query_owner):
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You don't have permission to view this query",
        )

    # Prepare response data
    query_data = {
        "query_id": query.query_id,
        "organizer_id": query.organizer_id,
        "organizer_username": (
            query.organizer.username if query.organizer else None
        ),
        "admin_user_id": query.admin_user_id,
        "admin_username": (
            query.admin_user.username if query.admin_user else None
        ),
        "query": query.query,
        "answers": query.answers or [],
        "query_status": get_status_name(query.query_status),
        "created_at": query.created_at,
        "updated_at": query.updated_at,
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Query retrieved successfully",
        data=query_data,
    )


@router.get(
    "/",
    response_model=QueryListResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def list_queries(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        10, ge=1, le=100, description="Number of items per page"
    ),
    status_filter: Optional[int] = Query(
        None, description="Filter by status (open, answered, closed)"
    ),
    organizer_id: Optional[str] = Query(
        None, description="Filter by organizer ID"
    ),
    search: Optional[str] = Query(None, description="Search in query text"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    List all queries with optional filters.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 10, max: 100)
    - **status_filter**: Filter by status (open, answered, closed)
    - **organizer_id**: Filter by specific organizer (admin only)
    - **search**: Search text in query content

    Returns paginated list of queries with metadata.
    """
    # Check user permissions
    user_with_role = await get_user_with_role(db, user_id)
    if not user_with_role:
        return api_response(status_code=404, message="User not found")

    is_admin = is_admin_user(user_with_role)

    # Build base query
    base_query = select(OrganizerQuery).options(
        selectinload(OrganizerQuery.organizer),
        selectinload(OrganizerQuery.admin_user),
    )

    # Apply filters based on user role
    conditions = []

    if not is_admin:
        # Non-admin users can only see their own queries
        conditions.append(OrganizerQuery.organizer_id == user_id)
    elif organizer_id:
        # Admin can filter by specific organizer
        conditions.append(OrganizerQuery.organizer_id == organizer_id)

    # Apply status filter
    if status_filter:
        conditions.append(OrganizerQuery.query_status == status_filter)

    # Apply search filter with parameterized query to prevent SQL injection
    if search:
        # Sanitize search input
        search_clean = search.strip()
        if search_clean:
            search_param = f"%{search_clean}%"
            conditions.append(OrganizerQuery.query.ilike(search_param))

    # Apply all conditions
    if conditions:
        base_query = base_query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count(OrganizerQuery.query_id))
    if conditions:
        count_query = count_query.where(and_(*conditions))

    count_result = await db.execute(count_query)
    total_count = count_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    queries_query = (
        base_query.order_by(desc(OrganizerQuery.created_at))
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(queries_query)
    queries = result.scalars().all()

    # Prepare response data
    queries_data = []
    for query in queries:
        query_data = {
            "query_id": query.query_id,
            "organizer_id": query.organizer_id,
            "organizer_username": (
                query.organizer.username if query.organizer else None
            ),
            "admin_user_id": query.admin_user_id,
            "admin_username": (
                query.admin_user.username if query.admin_user else None
            ),
            "query": query.query,
            "answers": query.answers or [],
            "query_status": get_status_name(query.query_status),
            "created_at": query.created_at,
            "updated_at": query.updated_at,
        }
        queries_data.append(query_data)

    # Calculate pagination metadata
    total_pages = (
        (total_count + page_size - 1) // page_size if total_count > 0 else 0
    )

    response_data = {
        "queries": queries_data,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }

    return api_response(
        status_code=200,
        message="Queries retrieved successfully",
        data=response_data,
    )


@router.patch(
    "/{query_id}/status",
    response_model=QueryStatusUpdateResponse,
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def update_query_status(
    user_id: str,
    query_id: str = Path(..., description="The query ID"),
    new_status: int = Query(
        ..., description="New status (open, answered, closed)"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update the status of a query (Admin only).

    - **query_id**: The ID of the query to update
    - **new_status**: New status value (open, answered, closed)

    Only admins can change query status.
    """
    # Check if user is admin
    user_with_role = await get_user_with_role(db, user_id)
    if not user_with_role:
        return api_response(status_code=404, message="User not found")

    if not is_admin_user(user_with_role):
        return api_response(
            status_code=403, message="Only admins can update query status"
        )

    # Get and update query
    query_stmt = select(OrganizerQuery).where(
        OrganizerQuery.query_id == query_id
    )
    result = await db.execute(query_stmt)
    query = result.scalars().first()

    if not query:
        return api_response(status_code=404, message="Query not found")

    old_status = query.query_status

    # Check if status is already the same
    if old_status == new_status:
        return api_response(
            status_code=400,
            message=f"Query is already in '{get_status_name(new_status)}' status",
        )

    query.query_status = new_status
    query.updated_at = datetime.now(timezone.utc)

    # If status is being changed to answered or closed, assign admin
    if (
        new_status
        in [QueryStatus.QUERY_ANSWERED.value, QueryStatus.QUERY_CLOSED.value]
        and not query.admin_user_id
    ):
        query.admin_user_id = user_id

    await db.commit()

    return api_response(
        status_code=200,
        message=f"Query status updated from '{get_status_name(old_status)}' to '{get_status_name(new_status)}'",
        data={
            "query_id": query.query_id,
            "old_status": get_status_name(old_status),
            "new_status": get_status_name(new_status),
            "admin_user_id": query.admin_user_id,
        },
    )
