from datetime import datetime

from pydantic import BaseModel, Field


class CouponCreateRequest(BaseModel):
    event_id: str = Field(..., max_length=6)
    organizer_id: str = Field(..., max_length=6)
    coupon_name: str = Field(..., max_length=100)
    coupon_code: str
    coupon_percentage: float = Field(..., ge=0, le=100)
    number_of_coupons: int = Field(..., gt=0)

    model_config = {"from_attributes": True}


class CouponResponse(BaseModel):
    coupon_id: str
    event_id: str
    organizer_id: str
    coupon_name: str
    coupon_percentage: float
    number_of_coupons: int
    sold_coupons: int
    created_at: datetime
    coupon_status: bool
    coupon_code: str

    model_config = {"from_attributes": True}


class ValidateCouponRequest(BaseModel):
    event_id: str = Field(
        ..., description="Event ID for which coupon is applied"
    )
    coupon_code: str = Field(..., description="Coupon code to validate")
    number_of_coupons: int = Field(
        ..., gt=0, description="Total Number of coupons"
    )


class ValidateCouponResponse(BaseModel):
    event_id: str
    coupon_code: str
    discount: float
    remaining_coupons: int
