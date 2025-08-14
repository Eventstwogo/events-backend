"""
Pydantic schemas for coupon-related operations.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, root_validator, validator
from pydantic.types import PositiveFloat, PositiveInt


class DiscountTypeEnum(str, Enum):
    """Discount type enumeration."""

    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class CouponBase(BaseModel):
    """Base coupon schema with common fields."""

    coupon_code: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[A-Z0-9_-]+$",
        description="Coupon code (uppercase letters, numbers, underscore, hyphen only)",
    )
    description: Optional[str] = Field(
        None, max_length=255, description="Optional coupon description"
    )
    discount_type: DiscountTypeEnum = Field(
        default=DiscountTypeEnum.PERCENTAGE,
        description="Type of discount: PERCENTAGE or FIXED",
    )
    discount_value: PositiveFloat = Field(
        ..., description="Discount value (percentage or fixed amount)"
    )
    max_uses: Optional[PositiveInt] = Field(
        None, description="Maximum number of times this coupon can be used"
    )
    valid_from: Optional[datetime] = Field(
        None, description="Coupon validity start date"
    )
    valid_until: Optional[datetime] = Field(
        None, description="Coupon validity end date"
    )
    is_active: bool = Field(
        default=True, description="Whether the coupon is active"
    )

    @validator("discount_value")
    def validate_discount_value(cls, v, values):
        """Validate discount value based on discount type."""
        discount_type = values.get("discount_type")
        if discount_type == DiscountTypeEnum.PERCENTAGE and v > 100:
            raise ValueError("Percentage discount cannot exceed 100%")
        if discount_type == DiscountTypeEnum.FIXED and v <= 0:
            raise ValueError("Fixed discount must be positive")
        return v

    @model_validator
    def validate_date_range(cls, values):
        """Validate that valid_from is before valid_until."""
        valid_from = values.get("valid_from")
        valid_until = values.get("valid_until")

        if valid_from and valid_until and valid_from >= valid_until:
            raise ValueError("valid_from must be before valid_until")

        return values

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class CouponCreate(CouponBase):
    """Schema for creating a new coupon."""

    pass


class CouponUpdate(BaseModel):
    """Schema for updating an existing coupon."""

    description: Optional[str] = Field(
        None, max_length=255, description="Optional coupon description"
    )
    discount_type: Optional[DiscountTypeEnum] = Field(
        None, description="Type of discount: PERCENTAGE or FIXED"
    )
    discount_value: Optional[PositiveFloat] = Field(
        None, description="Discount value (percentage or fixed amount)"
    )
    max_uses: Optional[PositiveInt] = Field(
        None, description="Maximum number of times this coupon can be used"
    )
    valid_from: Optional[datetime] = Field(
        None, description="Coupon validity start date"
    )
    valid_until: Optional[datetime] = Field(
        None, description="Coupon validity end date"
    )
    is_active: Optional[bool] = Field(
        None, description="Whether the coupon is active"
    )

    @validator("discount_value")
    def validate_discount_value(cls, v, values):
        """Validate discount value based on discount type."""
        if v is None:
            return v

        discount_type = values.get("discount_type")
        if discount_type == DiscountTypeEnum.PERCENTAGE and v > 100:
            raise ValueError("Percentage discount cannot exceed 100%")
        if discount_type == DiscountTypeEnum.FIXED and v <= 0:
            raise ValueError("Fixed discount must be positive")
        return v

    @root_validator
    def validate_date_range(cls, values):
        """Validate that valid_from is before valid_until."""
        valid_from = values.get("valid_from")
        valid_until = values.get("valid_until")

        if valid_from and valid_until and valid_from >= valid_until:
            raise ValueError("valid_from must be before valid_until")

        return values

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class CouponResponse(CouponBase):
    """Schema for coupon response."""

    coupon_id: int = Field(..., description="Unique coupon identifier")
    used_count: int = Field(
        ..., description="Number of times coupon has been used"
    )
    created_at: datetime = Field(..., description="Coupon creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class CouponListResponse(BaseModel):
    """Schema for paginated coupon list response."""

    coupons: list[CouponResponse] = Field(..., description="List of coupons")
    total: int = Field(..., description="Total number of coupons")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class CouponValidationRequest(BaseModel):
    """Schema for coupon validation request."""

    coupon_code: str = Field(
        ..., min_length=3, max_length=50, description="Coupon code to validate"
    )
    original_price: Optional[PositiveFloat] = Field(
        None, description="Original price to calculate discount (optional)"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {Decimal: lambda v: float(v)}


class CouponValidationResponse(BaseModel):
    """Schema for coupon validation response."""

    is_valid: bool = Field(..., description="Whether the coupon is valid")
    coupon: Optional[CouponResponse] = Field(
        None, description="Coupon details if valid"
    )
    discount_amount: Optional[float] = Field(
        None, description="Calculated discount amount"
    )
    final_price: Optional[float] = Field(
        None, description="Final price after discount"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if invalid"
    )

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class CouponUsageRequest(BaseModel):
    """Schema for coupon usage request."""

    coupon_code: str = Field(
        ..., min_length=3, max_length=50, description="Coupon code to use"
    )
    original_price: PositiveFloat = Field(
        ..., description="Original price before discount"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {Decimal: lambda v: float(v)}


class CouponUsageResponse(BaseModel):
    """Schema for coupon usage response."""

    success: bool = Field(
        ..., description="Whether the coupon was successfully used"
    )
    coupon: Optional[CouponResponse] = Field(
        None, description="Updated coupon details"
    )
    discount_amount: float = Field(..., description="Applied discount amount")
    final_price: float = Field(..., description="Final price after discount")
    message: str = Field(..., description="Success or error message")

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class CouponStatsResponse(BaseModel):
    """Schema for coupon statistics response."""

    coupon_id: int = Field(..., description="Coupon identifier")
    coupon_code: str = Field(..., description="Coupon code")
    total_uses: int = Field(..., description="Total number of uses")
    remaining_uses: Optional[int] = Field(
        None, description="Remaining uses (if max_uses is set)"
    )
    usage_percentage: Optional[float] = Field(
        None, description="Usage percentage (if max_uses is set)"
    )
    is_active: bool = Field(..., description="Whether coupon is active")
    is_valid: bool = Field(..., description="Whether coupon is currently valid")

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class BulkCouponCreate(BaseModel):
    """Schema for bulk coupon creation."""

    prefix: str = Field(
        ...,
        min_length=2,
        max_length=20,
        regex=r"^[A-Z0-9_-]+$",
        description="Prefix for generated coupon codes",
    )
    count: int = Field(
        ..., ge=1, le=1000, description="Number of coupons to generate (1-1000)"
    )
    discount_type: DiscountTypeEnum = Field(
        ..., description="Type of discount for all coupons"
    )
    discount_value: PositiveFloat = Field(
        ..., description="Discount value for all coupons"
    )
    description: Optional[str] = Field(
        None, max_length=255, description="Description for all coupons"
    )
    max_uses: Optional[PositiveInt] = Field(
        None, description="Maximum uses per coupon"
    )
    valid_from: Optional[datetime] = Field(
        None, description="Validity start date for all coupons"
    )
    valid_until: Optional[datetime] = Field(
        None, description="Validity end date for all coupons"
    )

    @validator("discount_value")
    def validate_discount_value(cls, v, values):
        """Validate discount value based on discount type."""
        discount_type = values.get("discount_type")
        if discount_type == DiscountTypeEnum.PERCENTAGE and v > 100:
            raise ValueError("Percentage discount cannot exceed 100%")
        return v

    @root_validator
    def validate_date_range(cls, values):
        """Validate that valid_from is before valid_until."""
        valid_from = values.get("valid_from")
        valid_until = values.get("valid_until")

        if valid_from and valid_until and valid_from >= valid_until:
            raise ValueError("valid_from must be before valid_until")

        return values

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class BulkCouponResponse(BaseModel):
    """Schema for bulk coupon creation response."""

    created_count: int = Field(..., description="Number of coupons created")
    coupon_codes: list[str] = Field(
        ..., description="List of generated coupon codes"
    )
    message: str = Field(..., description="Success message")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
