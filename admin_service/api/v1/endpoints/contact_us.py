from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.schemas.contact_us import (
    ContactUsCreateRequest,
    ContactUsResponse,
    ContactUsUpdateRequest,
)
from shared.core.api_response import api_response
from shared.db.models.contact_us import ContactUs, ContactUsStatus
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.post(
    "", response_model=ContactUsResponse, status_code=status.HTTP_201_CREATED
)
@exception_handler
async def create_contact_us(
    contact_us_data: ContactUsCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Create a new contact_us.

    Args:
        contact_us_data: The contact_us data to create
        db: Database session

    Returns:
        JSONResponse: The created contact_us details
    """
    # # Check if contact_us with same email and message already exists
    # existing_contact_us_stmt = select(ContactUs).where(
    #     ContactUs.email == contact_us_data.email,
    #     ContactUs.message == contact_us_data.message,
    # )
    # result = await db.execute(existing_contact_us_stmt)
    # existing_contact_us = result.scalar_one_or_none()

    # if existing_contact_us:
    #     return api_response(
    #         status_code=status.HTTP_409_CONFLICT,
    #         message="ContactUs already sent. An contact_us with the same email and message already exists.",
    #         log_error=True,
    #     )

    # Create new contact_us
    new_contact_us = ContactUs(
        firstname=contact_us_data.firstname,
        lastname=contact_us_data.lastname,
        email=contact_us_data.email,
        phone_number=contact_us_data.phone_number,
        message=contact_us_data.message,
        contact_us_status=ContactUsStatus.PENDING,
    )

    db.add(new_contact_us)
    await db.commit()
    await db.refresh(new_contact_us)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="ContactUs created successfully",
        data=ContactUsResponse.model_validate(new_contact_us),
    )


@router.get("", response_model=List[ContactUsResponse])
@exception_handler
async def get_all_enquiries(
    status_filter: Optional[ContactUsStatus] = Query(
        None,
        description="Filter enquiries by status",
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of records to return"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all enquiries with optional filtering and pagination.

    Args:
        status_filter: Optional filter by contact_us status
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        db: Database session

    Returns:
        JSONResponse: List of enquiries
    """
    # Build query
    stmt = select(ContactUs)

    # Apply status filter if provided
    if status_filter:
        stmt = stmt.where(ContactUs.contact_us_status == status_filter)

    # Apply pagination and ordering
    stmt = stmt.order_by(ContactUs.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    enquiries = result.scalars().all()

    contact_us_responses = [
        ContactUsResponse.model_validate(contact_us) for contact_us in enquiries
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Enquiries retrieved successfully",
        data=contact_us_responses,
    )


@router.get("/{contact_us_id}", response_model=ContactUsResponse)
@exception_handler
async def get_contact_us_by_id(
    contact_us_id: int,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get a specific contact_us by ID.

    Args:
        contact_us_id: The ID of the contact_us to retrieve
        db: Database session

    Returns:
        JSONResponse: The contact_us details
    """
    stmt = select(ContactUs).where(ContactUs.contact_us_id == contact_us_id)
    result = await db.execute(stmt)
    contact_us = result.scalar_one_or_none()

    if not contact_us:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"ContactUs with ID {contact_us_id} not found",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="ContactUs retrieved successfully",
        data=ContactUsResponse.model_validate(contact_us),
    )


@router.put("/{contact_us_id}", response_model=ContactUsResponse)
@exception_handler
async def update_contact_us(
    contact_us_id: int,
    contact_us_update: ContactUsUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update an contact_us (e.g., status).

    Args:
        contact_us_id: The ID of the contact_us to update
        contact_us_update: The update data
        db: Database session

    Returns:
        JSONResponse: The updated contact_us details
    """
    # Find the contact_us
    stmt = select(ContactUs).where(ContactUs.contact_us_id == contact_us_id)
    result = await db.execute(stmt)
    contact_us = result.scalar_one_or_none()

    if not contact_us:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"ContactUs with ID {contact_us_id} not found",
            log_error=True,
        )

    # Update fields if provided
    if contact_us_update.contact_us_status is not None:
        contact_us.contact_us_status = contact_us_update.contact_us_status

    await db.commit()
    await db.refresh(contact_us)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="ContactUs updated successfully",
        data=ContactUsResponse.model_validate(contact_us),
    )


@router.delete(
    "/{contact_us_id}",
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def delete_contact_us(
    contact_us_id: int,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Delete an contact_us.

    Args:
        contact_us_id: The ID of the contact_us to delete
        db: Database session

    Returns:
        JSONResponse: Success message
    """
    # Check if contact_us exists
    stmt = select(ContactUs).where(ContactUs.contact_us_id == contact_us_id)
    result = await db.execute(stmt)
    contact_us = result.scalar_one_or_none()

    if not contact_us:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"ContactUs with ID {contact_us_id} not found",
            log_error=True,
        )

    # Delete the contact_us
    delete_stmt = delete(ContactUs).where(
        ContactUs.contact_us_id == contact_us_id
    )
    await db.execute(delete_stmt)
    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="ContactUs deleted successfully",
    )
