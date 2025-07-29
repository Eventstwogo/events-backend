from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CreateIndustry(BaseModel):
    industry_name: Optional[str]
    industry_slug: str


class IndustryUpdate(BaseModel):
    industry_name: Optional[str] = None
    industry_slug: Optional[str] = None


class IndustryDetails(BaseModel):
    industry_id: str
    industry_name: str
    industry_slug: str
    is_active: bool
    timestamp: datetime

    class Config:
        from_attributes = True


class VendorCategoryRequest(BaseModel):
    vendor_ref_id: str
    category_id: str
    subcategory_id: Optional[str] = None
