from typing import Optional

from pydantic import BaseModel, Field


class SubCategoryValidationData(BaseModel):
    """Schema for subcategory validation data."""

    name: str = Field(..., description="Subcategory name")
    slug: str = Field(..., description="Subcategory slug")
    description: str = Field("", description="Subcategory description")
    meta_title: str = Field("", description="Subcategory meta title")
    meta_description: str = Field("", description="Subcategory meta description")


class SubCategoryValidationResult(BaseModel):
    """Schema for subcategory validation result."""

    error: Optional[str] = Field(None, description="Error message if validation failed")
    cleaned_name: str = Field(..., description="Cleaned subcategory name")
    final_slug: str = Field(..., description="Final subcategory slug")
    cleaned_description: str = Field(..., description="Cleaned subcategory description")
    cleaned_meta_title: str = Field(..., description="Cleaned subcategory meta title")
    cleaned_meta_description: str = Field(..., description="Cleaned subcategory meta description")


class ImageUploadResult(BaseModel):
    """Schema for image upload result."""

    error: Optional[str] = Field(None, description="Error message if upload failed")
    url: Optional[str] = Field(None, description="Uploaded image URL")
