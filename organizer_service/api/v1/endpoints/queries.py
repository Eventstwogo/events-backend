from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from organizer_service.schemas.queries import (
    AddMessageRequest,
    CreateQueryRequest,
    QueryFilters,
    QueryResponse,
    QueryStatus,
    ThreadMessage,
    UpdateQueryStatusRequest,
)
from organizer_service.services.queries import (
    get_query_by_id,
    get_user_by_id,
)
from shared.core.api_response import api_response
from shared.db.models import AdminUser
from shared.db.models.organizer import OrganizerQuery
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.post(
    "", response_model=QueryResponse, summary="Create a new organizer query"
)
@exception_handler
async def create_query(
    request: CreateQueryRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    sender = await get_user_by_id(request.user_id, db)

    if not sender:
        return api_response(
            status.HTTP_404_NOT_FOUND, "Sender user not found", log_error=True
        )

    if sender.role.role_name.lower() != "organizer":
        return api_response(
            status.HTTP_403_FORBIDDEN,
            "Only organizers can create queries",
            log_error=True,
        )

    initial_message = ThreadMessage(
        type="query",
        sender_type="organizer",
        user_id=sender.user_id,
        message=request.message,
        timestamp=datetime.now(timezone.utc),
    )

    query = OrganizerQuery(
        sender_user_id=sender.user_id,
        title=request.title,
        category=request.category,
        thread=[initial_message.model_dump(mode="json")],
        query_status=QueryStatus.QUERY_OPEN,
    )

    db.add(query)
    await db.commit()
    await db.refresh(query)

    return api_response(
        status.HTTP_201_CREATED,
        "Organizer Query created successfully",
        QueryResponse.model_validate(query).model_dump(),
    )


@router.get("", summary="Get paginated list of queries")
@exception_handler
async def get_queries_list(
    user_id: str,
    status_filter: Optional[QueryStatus] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    sender_user_id: Optional[str] = Query(None),
    receiver_user_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    user = await get_user_by_id(user_id, db)
    if not user:
        return api_response(
            status.HTTP_404_NOT_FOUND, "User not found", log_error=True
        )

    user_role = user.role.role_name.lower()
    filters = QueryFilters(
        query_status=status_filter,
        category=category,
        sender_user_id=sender_user_id,
        receiver_user_id=receiver_user_id,
        page=page,
        limit=limit,
    )

    # Build base query
    query_stmt = select(OrganizerQuery)

    if user_role == "organizer":
        query_stmt = query_stmt.where(OrganizerQuery.sender_user_id == user_id)
    elif user_role == "admin":
        if filters.sender_user_id:
            query_stmt = query_stmt.where(
                OrganizerQuery.sender_user_id == filters.sender_user_id
            )
        if filters.receiver_user_id:
            query_stmt = query_stmt.where(
                OrganizerQuery.receiver_user_id == filters.receiver_user_id
            )
    else:
        return api_response(
            status.HTTP_403_FORBIDDEN, "Invalid user role", log_error=True
        )

    if filters.query_status:
        query_stmt = query_stmt.where(
            OrganizerQuery.query_status == filters.query_status
        )
    if filters.category:
        query_stmt = query_stmt.where(
            OrganizerQuery.category.ilike(f"%{filters.category}%")
        )

    # Get total count
    count_stmt = select(func.count()).select_from(query_stmt.subquery())
    count_result = await db.execute(count_stmt)
    total_count = count_result.scalar() or 0

    # Apply ordering and pagination
    query_stmt = query_stmt.order_by(desc(OrganizerQuery.updated_at))
    query_stmt = query_stmt.offset((filters.page - 1) * filters.limit).limit(
        filters.limit
    )

    result = await db.execute(query_stmt)
    queries = result.scalars().all()

    total_pages = (total_count + filters.limit - 1) // filters.limit

    queries_response = []
    for query in queries:
        query_dict = QueryResponse.model_validate(query).model_dump()
        query_dict["last_message"] = (
            query.thread[-1].get("message", "")[:100] if query.thread else None
        )
        query_dict["unread_count"] = 0
        queries_response.append(query_dict)

    return api_response(
        status.HTTP_200_OK,
        "Queries retrieved successfully",
        {
            "queries": queries_response,
            "pagination": {
                "current_page": filters.page,
                "total_pages": total_pages,
                "total_items": total_count,
                "items_per_page": filters.limit,
                "has_next": filters.page < total_pages,
                "has_prev": filters.page > 1,
            },
        },
    )


@router.get(
    "/{query_id}", response_model=QueryResponse, summary="Get query by ID"
)
@exception_handler
async def get_query(
    user_id: str,
    query_id: int = Path(..., description="Query ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    user = await get_user_by_id(user_id, db)
    if not user:
        return api_response(
            status.HTTP_404_NOT_FOUND, "User not found", log_error=True
        )

    query = await get_query_by_id(query_id, db)
    if not query:
        return api_response(
            status.HTTP_404_NOT_FOUND, "Query not found", log_error=True
        )

    if (
        user.role.role_name.lower() == "organizer"
        and query.sender_user_id != user_id
    ):
        return api_response(
            status.HTTP_403_FORBIDDEN, "Access denied", log_error=True
        )

    return api_response(
        status.HTTP_200_OK,
        "Query retrieved successfully",
        QueryResponse.model_validate(query).model_dump(),
    )


@router.post(
    "/{query_id}/messages",
    response_model=QueryResponse,
    summary="Add message to query",
)
@exception_handler
async def add_message_to_query(
    request: AddMessageRequest,
    query_id: int = Path(..., description="Query ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    user = await get_user_by_id(request.user_id, db)
    if not user:
        return api_response(
            status.HTTP_404_NOT_FOUND, "User not found", log_error=True
        )

    query = await get_query_by_id(query_id, db)
    if not query:
        return api_response(
            status.HTTP_404_NOT_FOUND, "Query not found", log_error=True
        )

    if query.query_status == QueryStatus.QUERY_CLOSED:
        return api_response(
            status.HTTP_400_BAD_REQUEST,
            "Cannot add messages to closed queries",
            log_error=True,
        )

    user_role = user.role.role_name.lower()
    if user_role == "organizer":
        if query.sender_user_id != request.user_id:
            return api_response(
                status.HTTP_403_FORBIDDEN, "Access denied", log_error=True
            )
        sender_type = "organizer"
    elif user_role == "admin":
        sender_type = "admin"
        if not query.receiver_user_id:
            query.receiver_user_id = request.user_id
    else:
        return api_response(
            status.HTTP_403_FORBIDDEN, "Invalid user role", log_error=True
        )

    new_message = ThreadMessage(
        type=request.message_type,
        sender_type=sender_type,
        user_id=request.user_id,
        message=request.message,
        timestamp=datetime.now(timezone.utc),
    )

    query.thread = (query.thread or []) + [new_message.model_dump(mode="json")]

    if sender_type == "admin" and query.query_status == QueryStatus.QUERY_OPEN:
        query.query_status = QueryStatus.QUERY_IN_PROGRESS
    elif sender_type == "admin" and request.message_type == "response":
        query.query_status = QueryStatus.QUERY_ANSWERED

    query.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(query)

    return api_response(
        status.HTTP_200_OK,
        "Message added successfully",
        QueryResponse.model_validate(query).model_dump(),
    )


@router.patch(
    "/{query_id}/status",
    response_model=QueryResponse,
    summary="Update query status",
)
@exception_handler
async def update_query_status(
    request: UpdateQueryStatusRequest,
    query_id: int = Path(..., description="Query ID"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    user = await get_user_by_id(request.user_id, db)
    if not user:
        return api_response(
            status.HTTP_404_NOT_FOUND, "User not found", log_error=True
        )

    if user.role.role_name.lower() != "admin":
        return api_response(
            status.HTTP_403_FORBIDDEN,
            "Only admins can update query status",
            log_error=True,
        )

    query = await get_query_by_id(query_id, db)
    if not query:
        return api_response(
            status.HTTP_404_NOT_FOUND, "Query not found", log_error=True
        )

    query.query_status = request.query_status
    query.updated_at = datetime.now(timezone.utc)
    if not query.receiver_user_id:
        query.receiver_user_id = request.user_id

    if request.message:
        status_message = ThreadMessage(
            type="response",
            sender_type="admin",
            user_id=request.user_id,
            message=request.message,
            timestamp=datetime.now(timezone.utc),
        )
        query.thread = (query.thread or []) + [
            status_message.model_dump(mode="json")
        ]

    await db.commit()
    await db.refresh(query)

    return api_response(
        status.HTTP_200_OK,
        "Query status updated successfully",
        QueryResponse.model_validate(query).model_dump(),
    )
