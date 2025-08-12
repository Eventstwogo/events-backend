from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.schemas.about_us import (
    AboutUsCreateRequest,
    AboutUsResponse,
    AboutUsUpdateRequest,
)
from shared.core.api_response import api_response
from shared.db.models.admin_users import AboutUs
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.id_generators import generate_digits_upper_lower_case

router = APIRouter()


@router.post(
    "", response_model=AboutUsResponse, status_code=status.HTTP_201_CREATED
)
@exception_handler
async def create_about_us(
    about_us_data: AboutUsCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Create a new about us record.

    Args:
        about_us_data: The about us data to create
        db: Database session

    Returns:
        JSONResponse: The created about us details
    """
    # Generate unique ID
    about_us_id = generate_digits_upper_lower_case(6)

    # Ensure ID is unique
    while True:
        existing_stmt = select(AboutUs).where(
            AboutUs.about_us_id == about_us_id
        )
        result = await db.execute(existing_stmt)
        if not result.scalar_one_or_none():
            break
        about_us_id = generate_digits_upper_lower_case(6)

    # Create new about us record
    new_about_us = AboutUs(
        about_us_id=about_us_id,
        about_us_data=about_us_data.about_us_data,
    )

    db.add(new_about_us)
    await db.commit()
    await db.refresh(new_about_us)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="About Us record created successfully",
        data=AboutUsResponse.model_validate(new_about_us),
    )


@router.get("", response_model=List[AboutUsResponse])
@exception_handler
async def get_all_about_us(
    status_filter: Optional[bool] = Query(
        None,
        description="Filter about us records by status",
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of records to return"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all about us records with optional filtering and pagination.

    Args:
        status_filter: Optional filter by about us status
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        db: Database session

    Returns:
        JSONResponse: List of about us records
    """
    # Build query
    stmt = select(AboutUs)

    # Apply status filter if provided
    if status_filter is not None:
        stmt = stmt.where(AboutUs.about_us_status == status_filter)

    # Apply pagination and ordering
    stmt = stmt.order_by(AboutUs.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    about_us_records = result.scalars().all()

    about_us_responses = [
        AboutUsResponse.model_validate(about_us)
        for about_us in about_us_records
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="About Us records retrieved successfully",
        data=about_us_responses,
    )


@router.get("/active/latest", response_model=AboutUsResponse)
@exception_handler
async def get_active_about_us(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get the latest active about us record.

    Args:
        db: Database session

    Returns:
        JSONResponse: The latest active about us record
    """
    stmt = (
        select(AboutUs)
        .where(AboutUs.about_us_status == False)
        .order_by(AboutUs.updated_at.desc(), AboutUs.created_at.desc())
        .limit(1)
    )

    result = await db.execute(stmt)
    about_us = result.scalar_one_or_none()

    if not about_us:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No active About Us record found",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Active About Us record retrieved successfully",
        data=AboutUsResponse.model_validate(about_us),
    )


@router.get("/{about_us_id}", response_model=AboutUsResponse)
@exception_handler
async def get_about_us_by_id(
    about_us_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get a specific about us record by ID.

    Args:
        about_us_id: The ID of the about us record to retrieve
        db: Database session

    Returns:
        JSONResponse: The about us record details
    """
    stmt = select(AboutUs).where(AboutUs.about_us_id == about_us_id)
    result = await db.execute(stmt)
    about_us = result.scalar_one_or_none()

    if not about_us:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"About Us record with ID {about_us_id} not found",
            log_error=True,
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="About Us record retrieved successfully",
        data=AboutUsResponse.model_validate(about_us),
    )


@router.put("/{about_us_id}", response_model=AboutUsResponse)
@exception_handler
async def update_about_us(
    about_us_id: str,
    about_us_update: AboutUsUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update an about us record.

    Args:
        about_us_id: The ID of the about us record to update
        about_us_update: The update data
        db: Database session

    Returns:
        JSONResponse: The updated about us record details
    """
    # Find the about us record
    stmt = select(AboutUs).where(AboutUs.about_us_id == about_us_id)
    result = await db.execute(stmt)
    about_us = result.scalar_one_or_none()

    if not about_us:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"About Us record with ID {about_us_id} not found",
            log_error=True,
        )

    # Update fields if provided
    if about_us_update.about_us_data is not None:
        about_us.about_us_data = about_us_update.about_us_data

    if about_us_update.about_us_status is not None:
        about_us.about_us_status = about_us_update.about_us_status

    await db.commit()
    await db.refresh(about_us)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="About Us record updated successfully",
        data=AboutUsResponse.model_validate(about_us),
    )


@router.delete(
    "/{about_us_id}",
    status_code=status.HTTP_200_OK,
)
@exception_handler
async def delete_about_us(
    about_us_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Delete an about us record.

    Args:
        about_us_id: The ID of the about us record to delete
        db: Database session

    Returns:
        JSONResponse: Success message
    """
    # Check if about us record exists
    stmt = select(AboutUs).where(AboutUs.about_us_id == about_us_id)
    result = await db.execute(stmt)
    about_us = result.scalar_one_or_none()

    if not about_us:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"About Us record with ID {about_us_id} not found",
            log_error=True,
        )

    # Delete the about us record
    delete_stmt = delete(AboutUs).where(AboutUs.about_us_id == about_us_id)
    await db.execute(delete_stmt)
    await db.commit()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="About Us record deleted successfully",
    )


@router.patch("/status/{about_us_id}", response_model=AboutUsResponse)
@exception_handler
async def toggle_about_us_status(
    about_us_id: str,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Toggle About Us status (active/inactive).

    Args:
        about_us_id (str): The ID of the About Us entry to toggle status.
        db (AsyncSession): Database session.

    Returns:
        JSONResponse: The updated About Us entry.
    """
    # Find the About Us entry
    stmt = select(AboutUs).where(AboutUs.about_us_id == about_us_id)
    result = await db.execute(stmt)
    about_us = result.scalar_one_or_none()

    if not about_us:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"About Us entry with ID {about_us_id} not found",
            log_error=True,
        )

    # Toggle status
    about_us.about_us_status = not about_us.about_us_status

    await db.commit()
    await db.refresh(about_us)

    status_text = "deactivated" if about_us.about_us_status else "activated"

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"About Us entry {status_text} successfully",
        data=AboutUsResponse.model_validate(about_us),
    )
