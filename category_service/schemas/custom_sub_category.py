from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CustomSubCategoryBase(BaseModel):
    category_ref_id: str
    subcategory_ref_id: str
    event_ref_id: str
    custom_subcategory_name: str = Field(..., min_length=2, max_length=255)


class CustomSubCategoryCreate(CustomSubCategoryBase):
    pass


class CustomSubCategoryUpdate(BaseModel):
    category_ref_id: Optional[str] = None
    subcategory_ref_id: Optional[str] = None
    event_ref_id: Optional[str] = None
    custom_subcategory_name: Optional[str] = None


class CustomSubCategoryStatusUpdate(BaseModel):
    custom_subcategory_status: bool


class CustomSubCategoryOut(CustomSubCategoryBase):
    custom_subcategory_id: str
    custom_subcategory_status: bool

    class Config:
        from_attributes = True  # for ORM mode in Pydantic v2
