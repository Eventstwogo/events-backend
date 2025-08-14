"""
Coupon service for handling coupon-related business logic.
"""

import secrets
import string
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.coupon import (
    BulkCouponCreate,
    CouponCreate,
    CouponUpdate,
    CouponUsageRequest,
    CouponValidationRequest,
)
from shared.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from shared.db.models.events import Coupon, DiscountType


class CouponService:
    """Service class for coupon operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_coupon(self, coupon_data: CouponCreate) -> Coupon:
        """Create a new coupon."""
        try:
            coupon = Coupon(**coupon_data.dict())
            self.db.add(coupon)
            await self.db.commit()
            await self.db.refresh(coupon)
            return coupon
        except IntegrityError as e:
            await self.db.rollback()
            if "unique constraint" in str(e).lower():
                raise ConflictError(
                    f"Coupon code '{coupon_data.coupon_code}' already exists"
                )
            raise ValidationError(f"Database constraint violation: {str(e)}")

    async def get_coupon_by_id(self, coupon_id: int) -> Coupon:
        """Get coupon by ID."""
        stmt = select(Coupon).where(Coupon.coupon_id == coupon_id)
        result = await self.db.execute(stmt)
        coupon = result.scalar_one_or_none()

        if not coupon:
            raise NotFoundError(f"Coupon with ID {coupon_id} not found")

        return coupon

    async def get_coupon_by_code(self, coupon_code: str) -> Optional[Coupon]:
        """Get coupon by code."""
        stmt = select(Coupon).where(Coupon.coupon_code == coupon_code.upper())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_coupons(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
        discount_type: Optional[DiscountType] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Coupon], int]:
        """Get paginated list of coupons with optional filters."""
        # Build base query
        stmt = select(Coupon)
        count_stmt = select(func.count(Coupon.coupon_id))

        # Apply filters
        conditions = []

        if is_active is not None:
            conditions.append(Coupon.is_active == is_active)

        if discount_type is not None:
            conditions.append(Coupon.discount_type == discount_type)

        if search:
            search_pattern = f"%{search.upper()}%"
            conditions.append(
                or_(
                    Coupon.coupon_code.ilike(search_pattern),
                    Coupon.description.ilike(search_pattern),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))

        # Get total count
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.order_by(Coupon.created_at.desc()).offset(skip).limit(limit)

        # Execute query
        result = await self.db.execute(stmt)
        coupons = result.scalars().all()

        return list(coupons), total

    async def update_coupon(
        self, coupon_id: int, coupon_data: CouponUpdate
    ) -> Coupon:
        """Update an existing coupon."""
        coupon = await self.get_coupon_by_id(coupon_id)

        # Update only provided fields
        update_data = coupon_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(coupon, field, value)

        try:
            await self.db.commit()
            await self.db.refresh(coupon)
            return coupon
        except IntegrityError as e:
            await self.db.rollback()
            raise ValidationError(f"Database constraint violation: {str(e)}")

    async def delete_coupon(self, coupon_id: int) -> bool:
        """Delete a coupon (soft delete by setting is_active to False)."""
        coupon = await self.get_coupon_by_id(coupon_id)
        coupon.is_active = False

        await self.db.commit()
        return True

    async def validate_coupon(
        self, validation_request: CouponValidationRequest
    ) -> Tuple[
        bool, Optional[Coupon], Optional[float], Optional[float], Optional[str]
    ]:
        """
        Validate a coupon and calculate discount if applicable.

        Returns:
            Tuple of (is_valid, coupon, discount_amount, final_price, error_message)
        """
        coupon = await self.get_coupon_by_code(validation_request.coupon_code)

        if not coupon:
            return False, None, None, None, "Coupon not found"

        if not coupon.is_valid():
            error_msg = self._get_validation_error_message(coupon)
            return False, coupon, None, None, error_msg

        # Calculate discount if original price is provided
        discount_amount = None
        final_price = None

        if validation_request.original_price is not None:
            discount_amount = coupon.calculate_discount(
                validation_request.original_price
            )
            final_price = coupon.calculate_final_price(
                validation_request.original_price
            )

        return True, coupon, discount_amount, final_price, None

    async def use_coupon(
        self, usage_request: CouponUsageRequest
    ) -> Tuple[bool, Optional[Coupon], float, float, str]:
        """
        Use a coupon and increment its usage count.

        Returns:
            Tuple of (success, coupon, discount_amount, final_price, message)
        """
        coupon = await self.get_coupon_by_code(usage_request.coupon_code)

        if not coupon:
            return (
                False,
                None,
                0.0,
                usage_request.original_price,
                "Coupon not found",
            )

        if not coupon.is_valid():
            error_msg = self._get_validation_error_message(coupon)
            return False, coupon, 0.0, usage_request.original_price, error_msg

        # Calculate discount
        discount_amount = coupon.calculate_discount(
            usage_request.original_price
        )
        final_price = coupon.calculate_final_price(usage_request.original_price)

        # Increment usage count
        coupon.increment_usage()

        try:
            await self.db.commit()
            await self.db.refresh(coupon)
            return (
                True,
                coupon,
                discount_amount,
                final_price,
                "Coupon applied successfully",
            )
        except Exception as e:
            await self.db.rollback()
            return (
                False,
                coupon,
                0.0,
                usage_request.original_price,
                f"Failed to apply coupon: {str(e)}",
            )

    async def get_coupon_stats(self, coupon_id: int) -> dict:
        """Get statistics for a specific coupon."""
        coupon = await self.get_coupon_by_id(coupon_id)

        remaining_uses = None
        usage_percentage = None

        if coupon.max_uses:
            remaining_uses = max(0, coupon.max_uses - coupon.used_count)
            usage_percentage = (coupon.used_count / coupon.max_uses) * 100

        return {
            "coupon_id": coupon.coupon_id,
            "coupon_code": coupon.coupon_code,
            "total_uses": coupon.used_count,
            "remaining_uses": remaining_uses,
            "usage_percentage": usage_percentage,
            "is_active": coupon.is_active,
            "is_valid": coupon.is_valid(),
        }

    async def create_bulk_coupons(
        self, bulk_data: BulkCouponCreate
    ) -> Tuple[int, List[str]]:
        """Create multiple coupons with generated codes."""
        created_coupons = []
        generated_codes = []

        for i in range(bulk_data.count):
            # Generate unique coupon code
            coupon_code = self._generate_coupon_code(bulk_data.prefix)

            # Ensure uniqueness
            while await self.get_coupon_by_code(coupon_code):
                coupon_code = self._generate_coupon_code(bulk_data.prefix)

            # Create coupon data
            coupon_data = {
                "coupon_code": coupon_code,
                "description": bulk_data.description,
                "discount_type": bulk_data.discount_type,
                "discount_value": bulk_data.discount_value,
                "max_uses": bulk_data.max_uses,
                "valid_from": bulk_data.valid_from,
                "valid_until": bulk_data.valid_until,
                "is_active": True,
            }

            coupon = Coupon(**coupon_data)
            created_coupons.append(coupon)
            generated_codes.append(coupon_code)

        try:
            self.db.add_all(created_coupons)
            await self.db.commit()
            return len(created_coupons), generated_codes
        except IntegrityError as e:
            await self.db.rollback()
            raise ConflictError(f"Failed to create bulk coupons: {str(e)}")

    async def get_active_coupons(self) -> List[Coupon]:
        """Get all active and valid coupons."""
        now = datetime.now()
        stmt = (
            select(Coupon)
            .where(
                and_(
                    Coupon.is_active == True,
                    or_(Coupon.valid_from.is_(None), Coupon.valid_from <= now),
                    or_(
                        Coupon.valid_until.is_(None), Coupon.valid_until >= now
                    ),
                    or_(
                        Coupon.max_uses.is_(None),
                        Coupon.used_count < Coupon.max_uses,
                    ),
                )
            )
            .order_by(Coupon.created_at.desc())
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _generate_coupon_code(self, prefix: str) -> str:
        """Generate a random coupon code with given prefix."""
        suffix_length = 8
        suffix = "".join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(suffix_length)
        )
        return f"{prefix.upper()}-{suffix}"

    def _get_validation_error_message(self, coupon: Coupon) -> str:
        """Get appropriate error message for invalid coupon."""
        if not coupon.is_active:
            return "Coupon is inactive"

        now = datetime.now()

        if coupon.valid_from and now < coupon.valid_from:
            return f"Coupon is not yet valid (valid from {coupon.valid_from.strftime('%Y-%m-%d %H:%M')})"

        if coupon.valid_until and now > coupon.valid_until:
            return f"Coupon has expired (expired on {coupon.valid_until.strftime('%Y-%m-%d %H:%M')})"

        if coupon.max_uses and coupon.used_count >= coupon.max_uses:
            return "Coupon usage limit has been reached"

        return "Coupon is invalid"
