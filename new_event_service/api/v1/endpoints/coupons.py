from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_event_service.schemas.coupons import (
    CouponCreateRequest,
    CouponResponse,
    ValidateCouponRequest,
    ValidateCouponResponse,
)
from new_event_service.services.coupons import (
    create_coupon_service,
    delete_coupon_service,
    get_all_coupons_service,
    get_coupons_by_event_service,
    get_coupons_by_user_service,
    validate_coupon_service,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new coupon",
)
@exception_handler
async def create_coupon(
    coupon_data: CouponCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    coupon = await create_coupon_service(db, coupon_data)
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Coupon created successfully",
        data=coupon,
    )


@router.get(
    "/event/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=List[CouponResponse],
    summary="Get all coupons by event",
)
@exception_handler
async def get_coupons_by_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    coupons = await get_coupons_by_event_service(db, event_id)
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Coupons fetched successfully for the event",
        data=coupons,
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=List[CouponResponse],
    summary="Get all coupons",
)
@exception_handler
async def get_all_coupons(
    db: AsyncSession = Depends(get_db),
):
    coupons = await get_all_coupons_service(db)
    return api_response(
        status_code=status.HTTP_200_OK,
        message="All coupons fetched successfully",
        data=coupons,
    )


@router.delete(
    "/{coupon_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a coupon",
)
@exception_handler
async def delete_coupon(
    coupon_id: str,
    db: AsyncSession = Depends(get_db),
):
    success = await delete_coupon_service(db, coupon_id)
    if success:
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Coupon deleted successfully",
        )
    else:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Coupon not found",
        )


@router.post(
    "/validate",
    status_code=status.HTTP_200_OK,
    response_model=ValidateCouponResponse,
    summary="Validate a coupon for tickets",
)
async def validate_coupon(
    payload: ValidateCouponRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await validate_coupon_service(db, payload)
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Coupon is available.",
        data=result,
    )
