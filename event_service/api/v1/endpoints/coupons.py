"""
Coupon management API endpoints.
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.coupon import (
    BulkCouponCreate,
    BulkCouponResponse,
    CouponCreate,
    CouponListResponse,
    CouponResponse,
    CouponStatsResponse,
    CouponUpdate,
    CouponUsageRequest,
    CouponUsageResponse,
    CouponValidationRequest,
    CouponValidationResponse,
    DiscountTypeEnum,
)
from event_service.services.coupon_service import CouponService
from shared.core.api_response import api_response
from shared.core.exceptions import (
    BaseAPIException,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from shared.db.models.events import DiscountType
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=CouponResponse,
    summary="Create a new coupon",
    description="Create a new coupon with specified discount parameters",
)
@exception_handler
async def create_coupon(
    coupon_data: CouponCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new coupon."""
    try:
        service = CouponService(db)
        coupon = await service.create_coupon(coupon_data)

        return api_response(
            success=True,
            message="Coupon created successfully",
            data=CouponResponse.from_orm(coupon),
            status_code=status.HTTP_201_CREATED,
        )
    except BaseAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create coupon: {str(e)}",
        )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=CouponListResponse,
    summary="List coupons with pagination and filters",
    description="Get paginated list of coupons with optional filtering",
)
@exception_handler
async def list_coupons(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(
        None, description="Filter by active status"
    ),
    discount_type: Optional[DiscountTypeEnum] = Query(
        None, description="Filter by discount type"
    ),
    search: Optional[str] = Query(
        None, description="Search in coupon code or description"
    ),
    db: AsyncSession = Depends(get_db),
):
    """List coupons with pagination and filters."""
    try:
        service = CouponService(db)
        skip = (page - 1) * per_page

        # Convert enum to model enum if provided
        model_discount_type = None
        if discount_type:
            model_discount_type = DiscountType(discount_type.value)

        coupons, total = await service.get_coupons(
            skip=skip,
            limit=per_page,
            is_active=is_active,
            discount_type=model_discount_type,
            search=search,
        )

        total_pages = math.ceil(total / per_page) if total > 0 else 1

        response_data = CouponListResponse(
            coupons=[CouponResponse.from_orm(coupon) for coupon in coupons],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

        return api_response(
            success=True,
            message="Coupons retrieved successfully",
            data=response_data,
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve coupons: {str(e)}",
        )


@router.get(
    "/{coupon_id}",
    status_code=status.HTTP_200_OK,
    response_model=CouponResponse,
    summary="Get coupon by ID",
    description="Retrieve a specific coupon by its ID",
)
@exception_handler
async def get_coupon(coupon_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific coupon by ID."""
    try:
        service = CouponService(db)
        coupon = await service.get_coupon_by_id(coupon_id)

        return api_response(
            success=True,
            message="Coupon retrieved successfully",
            data=CouponResponse.from_orm(coupon),
            status_code=status.HTTP_200_OK,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve coupon: {str(e)}",
        )


@router.put(
    "/{coupon_id}",
    status_code=status.HTTP_200_OK,
    response_model=CouponResponse,
    summary="Update coupon",
    description="Update an existing coupon's details",
)
@exception_handler
async def update_coupon(
    coupon_id: int,
    coupon_data: CouponUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing coupon."""
    try:
        service = CouponService(db)
        coupon = await service.update_coupon(coupon_id, coupon_data)

        return api_response(
            success=True,
            message="Coupon updated successfully",
            data=CouponResponse.from_orm(coupon),
            status_code=status.HTTP_200_OK,
        )
    except BaseAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update coupon: {str(e)}",
        )


@router.delete(
    "/{coupon_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete coupon",
    description="Soft delete a coupon (sets is_active to False)",
)
@exception_handler
async def delete_coupon(coupon_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a coupon (soft delete)."""
    try:
        service = CouponService(db)
        await service.delete_coupon(coupon_id)

        return api_response(
            success=True,
            message="Coupon deleted successfully",
            data=None,
            status_code=status.HTTP_200_OK,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete coupon: {str(e)}",
        )


@router.post(
    "/validate",
    status_code=status.HTTP_200_OK,
    response_model=CouponValidationResponse,
    summary="Validate coupon",
    description="Validate a coupon code and optionally calculate discount",
)
@exception_handler
async def validate_coupon(
    validation_request: CouponValidationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate a coupon code."""
    try:
        service = CouponService(db)
        is_valid, coupon, discount_amount, final_price, error_message = (
            await service.validate_coupon(validation_request)
        )

        response_data = CouponValidationResponse(
            is_valid=is_valid,
            coupon=CouponResponse.from_orm(coupon) if coupon else None,
            discount_amount=discount_amount,
            final_price=final_price,
            error_message=error_message,
        )

        message = (
            "Coupon is valid"
            if is_valid
            else f"Coupon validation failed: {error_message}"
        )

        return api_response(
            success=is_valid,
            message=message,
            data=response_data,
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate coupon: {str(e)}",
        )


@router.post(
    "/use",
    status_code=status.HTTP_200_OK,
    response_model=CouponUsageResponse,
    summary="Use coupon",
    description="Apply a coupon and increment its usage count",
)
@exception_handler
async def use_coupon(
    usage_request: CouponUsageRequest, db: AsyncSession = Depends(get_db)
):
    """Use a coupon and increment its usage count."""
    try:
        service = CouponService(db)
        success, coupon, discount_amount, final_price, message = (
            await service.use_coupon(usage_request)
        )

        response_data = CouponUsageResponse(
            success=success,
            coupon=CouponResponse.from_orm(coupon) if coupon else None,
            discount_amount=discount_amount,
            final_price=final_price,
            message=message,
        )

        return api_response(
            success=success,
            message=message,
            data=response_data,
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to use coupon: {str(e)}",
        )


@router.get(
    "/{coupon_id}/stats",
    status_code=status.HTTP_200_OK,
    response_model=CouponStatsResponse,
    summary="Get coupon statistics",
    description="Get usage statistics for a specific coupon",
)
@exception_handler
async def get_coupon_stats(coupon_id: int, db: AsyncSession = Depends(get_db)):
    """Get statistics for a specific coupon."""
    try:
        service = CouponService(db)
        stats = await service.get_coupon_stats(coupon_id)

        response_data = CouponStatsResponse(**stats)

        return api_response(
            success=True,
            message="Coupon statistics retrieved successfully",
            data=response_data,
            status_code=status.HTTP_200_OK,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve coupon statistics: {str(e)}",
        )


@router.post(
    "/bulk",
    status_code=status.HTTP_201_CREATED,
    response_model=BulkCouponResponse,
    summary="Create bulk coupons",
    description="Create multiple coupons with generated codes",
)
@exception_handler
async def create_bulk_coupons(
    bulk_data: BulkCouponCreate, db: AsyncSession = Depends(get_db)
):
    """Create multiple coupons with generated codes."""
    try:
        service = CouponService(db)
        created_count, coupon_codes = await service.create_bulk_coupons(
            bulk_data
        )

        response_data = BulkCouponResponse(
            created_count=created_count,
            coupon_codes=coupon_codes,
            message=f"Successfully created {created_count} coupons",
        )

        return api_response(
            success=True,
            message=f"Successfully created {created_count} coupons",
            data=response_data,
            status_code=status.HTTP_201_CREATED,
        )
    except BaseAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk coupons: {str(e)}",
        )


@router.get(
    "/active/list",
    status_code=status.HTTP_200_OK,
    response_model=list[CouponResponse],
    summary="Get active coupons",
    description="Get all currently active and valid coupons",
)
@exception_handler
async def get_active_coupons(db: AsyncSession = Depends(get_db)):
    """Get all active and valid coupons."""
    try:
        service = CouponService(db)
        coupons = await service.get_active_coupons()

        response_data = [CouponResponse.from_orm(coupon) for coupon in coupons]

        return api_response(
            success=True,
            message=f"Retrieved {len(coupons)} active coupons",
            data=response_data,
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve active coupons: {str(e)}",
        )


@router.get(
    "/code/{coupon_code}",
    status_code=status.HTTP_200_OK,
    response_model=CouponResponse,
    summary="Get coupon by code",
    description="Retrieve a specific coupon by its code",
)
@exception_handler
async def get_coupon_by_code(
    coupon_code: str, db: AsyncSession = Depends(get_db)
):
    """Get a specific coupon by code."""
    try:
        service = CouponService(db)
        coupon = await service.get_coupon_by_code(coupon_code)

        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Coupon with code '{coupon_code}' not found",
            )

        return api_response(
            success=True,
            message="Coupon retrieved successfully",
            data=CouponResponse.from_orm(coupon),
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve coupon: {str(e)}",
        )
