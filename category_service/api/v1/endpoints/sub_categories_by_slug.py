from datetime import datetime
from typing import Optional, Union, cast

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from category_service.schemas.subcategory_update import SubCategoryUpdate
from category_service.schemas.subcategory_validation import (
    ImageUploadResult,
    SubCategoryValidationData,
    SubCategoryValidationResult,
)
from category_service.services.category_service import (
    check_subcategory_conflicts,
    check_subcategory_vs_category_conflicts,
    validate_subcategory_fields,
)
from shared.core.api_response import api_response
from shared.core.config import settings
from shared.db.models import SubCategory
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url, save_uploaded_file
from shared.utils.format_validators import is_valid_filename

router = APIRouter()


@router.get(
    "/slug/{slug}",
    summary="Not Integrated in any frontend",
    description="Returns a subcategory by its slug.",
)
@exception_handler
async def get_subcategory_by_slug(
    slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Fetch subcategory by slug with parent category
    result = await db.execute(
        select(SubCategory)
        .options(selectinload(SubCategory.category))
        .filter_by(subcategory_slug=slug)
    )
    sub = result.scalars().first()

    if not sub:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    data = {
        "subcategory_id": sub.subcategory_id,
        "subcategory_name": sub.subcategory_name.title(),
        "subcategory_description": sub.subcategory_description,
        "subcategory_slug": sub.subcategory_slug,
        "subcategory_meta_title": sub.subcategory_meta_title,
        "subcategory_meta_description": sub.subcategory_meta_description,
        "subcategory_img_thumbnail": get_media_url(
            sub.subcategory_img_thumbnail
        ),
        "featured_subcategory": sub.featured_subcategory,
        "show_in_menu": sub.show_in_menu,
        "subcategory_status": sub.subcategory_status,
        "subcategory_tstamp": (
            cast(datetime, sub.subcategory_tstamp).isoformat()
            if sub.subcategory_tstamp
            else None
        ),
        "parent_category": (
            {
                "category_id": sub.category.category_id,
                "category_name": sub.category.category_name,
                "category_slug": sub.category.category_slug,
            }
            if sub.category
            else None
        ),
    }

    return api_response(
        status.HTTP_200_OK, "Subcategory fetched successfully", data=data
    )


async def fetch_subcategory_by_slug(
    slug: str, db: AsyncSession
) -> Union[SubCategory, None]:
    """
    Helper function to fetch a subcategory by slug.

    Args:
        slug: The subcategory slug
        db: Database session

    Returns:
        The subcategory object or None if not found
    """
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_slug=slug)
    )
    return result.scalars().first()


async def validate_subcategory_data(
    db: AsyncSession,
    subcategory: SubCategory,
    validation_data: SubCategoryValidationData,
) -> SubCategoryValidationResult:
    """
    Helper function to validate subcategory data.

    Args:
        db: Database session
        subcategory: The subcategory object
        validation_data: The validation data

    Returns:
        Validation result with error message and cleaned data
    """
    # Validate fields
    (
        cleaned_name,
        cleaned_slug,
        cleaned_description,
        cleaned_meta_title,
        cleaned_meta_description,
    ) = validate_subcategory_fields(
        name=validation_data.name,
        slug=validation_data.slug,
        description=validation_data.description,
        meta_title=validation_data.meta_title,
        meta_description=validation_data.meta_description,
    )

    final_slug = slugify(cleaned_slug)

    # Check for subcategory conflicts
    conflict_error = await check_subcategory_conflicts(
        db=db,
        name=cleaned_name,
        slug=final_slug,
        description=cleaned_description,
        meta_title=cleaned_meta_title,
        meta_description=cleaned_meta_description,
        subcategory_id_to_exclude=subcategory.subcategory_id,
    )
    if conflict_error:
        return SubCategoryValidationResult(
            error=conflict_error,
            cleaned_name=cleaned_name,
            final_slug=final_slug,
            cleaned_description=cleaned_description,
            cleaned_meta_title=cleaned_meta_title,
            cleaned_meta_description=cleaned_meta_description,
        )

    # Check for category conflicts
    conflict_error = await check_subcategory_vs_category_conflicts(
        db=db,
        name=cleaned_name,
        slug=final_slug,
        description=cleaned_description,
        meta_title=cleaned_meta_title,
        meta_description=cleaned_meta_description,
    )
    if conflict_error:
        return SubCategoryValidationResult(
            error=conflict_error,
            cleaned_name=cleaned_name,
            final_slug=final_slug,
            cleaned_description=cleaned_description,
            cleaned_meta_title=cleaned_meta_title,
            cleaned_meta_description=cleaned_meta_description,
        )

    return SubCategoryValidationResult(
        error=None,
        cleaned_name=cleaned_name,
        final_slug=final_slug,
        cleaned_description=cleaned_description,
        cleaned_meta_title=cleaned_meta_title,
        cleaned_meta_description=cleaned_meta_description,
    )


async def handle_subcategory_image_upload(
    file: UploadFile, category_id: str, slug: str
) -> ImageUploadResult:
    """
    Helper function to handle subcategory image upload.

    Args:
        file: The uploaded file
        category_id: The category ID
        slug: The subcategory slug

    Returns:
        Image upload result with error message and URL
    """
    if not file or not file.filename:
        return ImageUploadResult(error=None, url=None)

    if not is_valid_filename(file.filename):
        return ImageUploadResult(error="Invalid file name.", url=None)

    sub_path = settings.SUBCATEGORY_IMAGE_PATH.format(
        category_id=category_id, slug_name=slug
    )

    try:
        uploaded_url = await save_uploaded_file(file, sub_path)
        return ImageUploadResult(error=None, url=uploaded_url)
    except ValueError as ve:
        return ImageUploadResult(error=str(ve), url=None)
    except Exception as e:
        return ImageUploadResult(
            error=f"Failed to save uploaded file: {str(e)}", url=None
        )


async def update_subcategory_fields(
    subcategory: SubCategory,
    update_data: SubCategoryUpdate,
    cleaned_name: str,
    final_slug: str,
    cleaned_description: str,
    cleaned_meta_title: str,
    cleaned_meta_description: str,
    thumbnail_url: Optional[str] = None,
) -> None:
    """
    Helper function to update subcategory fields.

    Args:
        subcategory: The subcategory object
        update_data: The update data
        cleaned_name: Cleaned subcategory name
        final_slug: Final subcategory slug
        cleaned_description: Cleaned subcategory description
        cleaned_meta_title: Cleaned subcategory meta title
        cleaned_meta_description: Cleaned subcategory meta description
        thumbnail_url: Thumbnail URL
    """
    if update_data.name:
        subcategory.subcategory_name = cleaned_name.upper()
    if update_data.slug:
        subcategory.subcategory_slug = final_slug
    if update_data.description:
        subcategory.subcategory_description = cleaned_description
    if update_data.meta_title:
        subcategory.subcategory_meta_title = cleaned_meta_title
    if update_data.meta_description:
        subcategory.subcategory_meta_description = cleaned_meta_description
    if update_data.featured is not None:
        subcategory.featured_subcategory = update_data.featured
    if update_data.show_in_menu is not None:
        subcategory.show_in_menu = update_data.show_in_menu
    if thumbnail_url:
        subcategory.subcategory_img_thumbnail = thumbnail_url


@router.put(
    "/slug/{slug}",
    summary="Not Integrated in any frontend",
    description="Update a subcategory by slug.",
)
@exception_handler
async def update_subcategory_by_slug(
    slug: str,
    name: Optional[str] = Form(None),
    new_slug: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    featured: Optional[bool] = Form(None),
    show_in_menu: Optional[bool] = Form(None),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update a subcategory by slug.

    Args:
        slug: The subcategory slug
        name: New subcategory name
        new_slug: New subcategory slug
        description: New subcategory description
        meta_title: New subcategory meta title
        meta_description: New subcategory meta description
        featured: New featured flag
        show_in_menu: New show in menu flag
        file: New subcategory image
        db: Database session

    Returns:
        JSON response with the updated subcategory
    """
    # Fetch subcategory by slug
    subcategory = await fetch_subcategory_by_slug(slug, db)
    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    # Create update data object
    update_data = SubCategoryUpdate(
        name=name,
        slug=new_slug,
        description=description,
        meta_title=meta_title,
        meta_description=meta_description,
        featured=featured,
        show_in_menu=show_in_menu,
    )

    # Apply fallback for unchanged fields and ensure we have strings
    validation_data = SubCategoryValidationData(
        name=name or subcategory.subcategory_name or "",
        slug=new_slug or subcategory.subcategory_slug or "",
        description=description or subcategory.subcategory_description or "",
        meta_title=meta_title or subcategory.subcategory_meta_title or "",
        meta_description=meta_description
        or subcategory.subcategory_meta_description
        or "",
    )

    # Validate subcategory data
    validation_result = await validate_subcategory_data(
        db=db,
        subcategory=subcategory,
        validation_data=validation_data,
    )
    if validation_result.error:
        return api_response(
            status.HTTP_400_BAD_REQUEST, validation_result.error
        )

    # Handle file upload
    if file and file.filename:
        upload_result = await handle_subcategory_image_upload(
            file=file,
            category_id=subcategory.category_id,
            slug=validation_result.final_slug,
        )
        if upload_result.error:
            return api_response(
                status.HTTP_400_BAD_REQUEST, upload_result.error
            )
        uploaded_url = upload_result.url
    else:
        uploaded_url = None

    # Update subcategory fields
    await update_subcategory_fields(
        subcategory=subcategory,
        update_data=update_data,
        cleaned_name=validation_result.cleaned_name,
        final_slug=validation_result.final_slug,
        cleaned_description=validation_result.cleaned_description,
        cleaned_meta_title=validation_result.cleaned_meta_title,
        cleaned_meta_description=validation_result.cleaned_meta_description,
        thumbnail_url=uploaded_url,
    )

    # Commit changes
    await db.commit()
    await db.refresh(subcategory)

    return api_response(
        status.HTTP_200_OK,
        "Subcategory updated successfully",
        data={
            "subcategory_id": subcategory.subcategory_id,
            "subcategory_slug": subcategory.subcategory_slug,
            "subcategory_name": subcategory.subcategory_name,
        },
    )


@router.delete(
    "/slug/soft/{slug}",
    summary="Not Integrated in any frontend",
    description="Soft delete a subcategory by slug.",
)
@exception_handler
async def soft_delete_subcategory_by_slug(
    slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_slug=slug)
    )
    subcategory = result.scalars().first()

    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    if subcategory.subcategory_status:
        return api_response(
            status.HTTP_400_BAD_REQUEST, "Subcategory already inactive"
        )

    subcategory.subcategory_status = True
    await db.commit()

    return api_response(
        status.HTTP_200_OK, "Subcategory soft deleted successfully"
    )


@router.put(
    "/slug/restore/{slug}",
    summary="Not Integrated in any frontend",
    description="Restore a soft-deleted subcategory by slug.",
)
@exception_handler
async def restore_subcategory_by_slug(
    slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_slug=slug)
    )
    subcategory = result.scalars().first()

    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    if not subcategory.subcategory_status:
        return api_response(
            status.HTTP_400_BAD_REQUEST, "Subcategory is already active"
        )

    subcategory.subcategory_status = False
    await db.commit()

    return api_response(status.HTTP_200_OK, "Subcategory restored successfully")


@router.delete(
    "/slug/hard/{slug}",
    summary="Not Integrated in any frontend",
    description="Permanently delete a subcategory by slug.",
)
@exception_handler
async def hard_delete_subcategory_by_slug(
    slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_slug=slug)
    )
    subcategory = result.scalars().first()

    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    await db.delete(subcategory)
    await db.commit()

    return api_response(status.HTTP_200_OK, "Subcategory permanently deleted")
