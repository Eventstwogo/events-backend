from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from shared.db.models.coupons import Coupon
from event_service.schemas.coupons import CouponCreateRequest, CouponResponse, ValidateCouponRequest, ValidateCouponResponse
from shared.utils.id_generators import generate_lower_uppercase


async def create_coupon_service(
    db: AsyncSession, coupon_data: CouponCreateRequest
) -> CouponResponse:
    """
    Create a new coupon in the database.
    """
    try:
        new_coupon = Coupon(
            coupon_id=generate_lower_uppercase(6),
            event_id=coupon_data.event_id,
            organizer_id=coupon_data.organizer_id,
            coupon_name=coupon_data.coupon_name,
            coupon_percentage=coupon_data.coupon_percentage,
            number_of_coupons=coupon_data.number_of_coupons,
            coupon_code= coupon_data.coupon_code,
            sold_coupons=0,
            created_at=datetime.utcnow(),
            coupon_status=False,
        )
        db.add(new_coupon)
        await db.commit()
        await db.refresh(new_coupon)
        return CouponResponse.from_orm(new_coupon)
    except SQLAlchemyError as e:
        await db.rollback()
        raise e


async def get_coupons_by_user_service(
    db: AsyncSession, user_id: str
) -> list[CouponResponse]:
    """
    Fetch all coupons for a specific organizer/user.
    """
    try:
        result = await db.execute(
            select(Coupon).where(Coupon.organizer_id == user_id)
        )
        coupons = result.scalars().all()
        return [CouponResponse.from_orm(c) for c in coupons]
    except SQLAlchemyError as e:
        raise e


async def get_coupons_by_event_service(
    db: AsyncSession, event_id: str
) -> list[CouponResponse]:
    """
    Fetch all coupons for a specific event by event_id.
    """
    try:
        result = await db.execute(
            select(Coupon).where(Coupon.event_id == event_id)
        )
        coupons = result.scalars().all()
        return [CouponResponse.from_orm(c) for c in coupons]
    except SQLAlchemyError as e:
        raise e

async def get_all_coupons_service(db: AsyncSession) -> list[CouponResponse]:
    """
    Fetch all coupons.
    """
    try:
        result = await db.execute(select(Coupon))
        coupons = result.scalars().all()
        return [CouponResponse.from_orm(c) for c in coupons]
    except SQLAlchemyError as e:
        raise e


async def delete_coupon_service(db: AsyncSession, coupon_id: str) -> bool:
    """
    Delete a coupon by coupon_id.
    Returns True if deleted, False if not found.
    """
    try:
        result = await db.execute(
            select(Coupon).where(Coupon.coupon_id == coupon_id)
        )
        coupon = result.scalars().first()
        if not coupon:
            return False

        await db.delete(coupon)
        await db.commit()
        return True
    except SQLAlchemyError as e:
        await db.rollback()
        raise e


async def validate_coupon_service(
    db: AsyncSession, payload: ValidateCouponRequest
) -> ValidateCouponResponse:
    """
    Validate a coupon for an event.
    """
    query = select(Coupon).where(
        Coupon.event_id == payload.event_id,
        Coupon.coupon_code == payload.coupon_code,
    )
    result = await db.execute(query)
    coupon = result.scalars().first()

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found for this event",
        )

    # Check if coupon has enough quota
    if coupon.sold_coupons >= payload.number_of_coupons:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coupon expired or insufficient coupons available",
        )

    return ValidateCouponResponse(
        event_id=coupon.event_id,
        coupon_code=coupon.coupon_code,
        discount=coupon.coupon_percentage,
        remaining_coupons=coupon.number_of_coupons - coupon.sold_coupons,
    )
