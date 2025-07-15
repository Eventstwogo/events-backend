from typing import Optional

from pydantic import BaseModel, Field


class SubCategoryUpdate(BaseModel):
    """Schema for subcategory update request."""

    name: Optional[str] = Field(None, description="Subcategory name")
    slug: Optional[str] = Field(None, description="Subcategory slug")
    description: Optional[str] = Field(
        None, description="Subcategory description"
    )
    meta_title: Optional[str] = Field(
        None, description="Subcategory meta title"
    )
    meta_description: Optional[str] = Field(
        None, description="Subcategory meta description"
    )
    featured: Optional[bool] = Field(
        None, description="Featured subcategory flag"
    )
    show_in_menu: Optional[bool] = Field(None, description="Show in menu flag")
