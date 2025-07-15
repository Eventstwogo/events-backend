from dataclasses import dataclass
from datetime import datetime
from typing import Optional, cast

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

from shared.core.api_response import api_response
from shared.core.config import settings
from shared.db.models import Category
from shared.db.sessions.database import get_db
from category_service.services.category_service import (
    CategoryData,
    ConflictCheckData,
    validate_category_conflicts,
    validate_category_data,
)
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url, save_uploaded_file
from shared.utils.format_validators import is_valid_filename
from shared.utils.security_validators import sanitize_input
from shared.utils.validators import normalize_whitespace

router = APIRouter()


@dataclass
class UpdateCategoryBySlugParams:  # pylint: disable=too-many-instance-attributes
    """Parameters for category update by slug operation."""

    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    featured: Optional[bool] = None
    show_in_menu: Optional[bool] = None
    file: Optional[UploadFile] = None


def _check_no_changes_by_slug(
    params: UpdateCategoryBySlugParams, category: Category
) -> bool:
    """Check if there are no changes in the update parameters."""
    return (
        (params.name is None or params.name.strip() == "")
        and (params.slug is None or params.slug.strip() == "")
        and (params.description is None or params.description.strip() == "")
        and (params.meta_title is None or params.meta_title.strip() == "")
        and (
            params.meta_description is None
            or params.meta_description.strip() == ""
        )
        and (
            params.featured is None
            or params.featured == category.featured_category
        )
        and (
            params.show_in_menu is None
            or params.show_in_menu == category.show_in_menu
        )
        and not (params.file and params.file.filename)
    )


def _prepare_input_values_by_slug(
    params: UpdateCategoryBySlugParams, category: Category
) -> tuple[str, str, str, str, str] | JSONResponse:
    """Prepare input values with fallback to existing category values."""
    input_name = (
        category.category_name
        if (params.name is None or params.name.strip() == "")
        else params.name
    )
    input_slug = (
        category.category_slug
        if (params.slug is None or params.slug.strip() == "")
        else params.slug
    )
    input_description = (
        category.category_description
        if (params.description is None or params.description.strip() == "")
        else params.description
    )
    input_meta_title = (
        category.category_meta_title
        if (params.meta_title is None or params.meta_title.strip() == "")
        else params.meta_title
    )
    input_meta_description = (
        category.category_meta_description
        if (
            params.meta_description is None
            or params.meta_description.strip() == ""
        )
        else params.meta_description
    )

    # Sanitize inputs
    if input_name:
        sanitized_name = sanitize_input(input_name)
        if isinstance(sanitized_name, JSONResponse):
            return sanitized_name
        input_name = normalize_whitespace(sanitized_name)
    else:
        input_name = ""
    
    if input_slug:
        sanitized_slug = sanitize_input(input_slug)
        if isinstance(sanitized_slug, JSONResponse):
            return sanitized_slug
        input_slug = normalize_whitespace(sanitized_slug)
    else:
        input_slug = ""
    
    if input_description:
        sanitized_description = sanitize_input(input_description)
        if isinstance(sanitized_description, JSONResponse):
            return sanitized_description
        input_description = normalize_whitespace(sanitized_description)
    else:
        input_description = ""
    
    if input_meta_title:
        sanitized_meta_title = sanitize_input(input_meta_title)
        if isinstance(sanitized_meta_title, JSONResponse):
            return sanitized_meta_title
        input_meta_title = normalize_whitespace(sanitized_meta_title)
    else:
        input_meta_title = ""
    
    if input_meta_description:
        sanitized_meta_description = sanitize_input(input_meta_description)
        if isinstance(sanitized_meta_description, JSONResponse):
            return sanitized_meta_description
        input_meta_description = normalize_whitespace(sanitized_meta_description)
    else:
        input_meta_description = ""
    
    return (
        input_name,
        input_slug,
        input_description,
        input_meta_title,
        input_meta_description,
    )


def _has_field_changes_by_slug(params: UpdateCategoryBySlugParams) -> bool:
    """Check if any field has changes."""
    has_name = params.name is not None and len(params.name.strip()) > 0
    has_slug = params.slug is not None and len(params.slug.strip()) > 0
    has_description = (
        params.description is not None and len(params.description.strip()) > 0
    )
    has_meta_title = (
        params.meta_title is not None and len(params.meta_title.strip()) > 0
    )
    has_meta_description = (
        params.meta_description is not None
        and len(params.meta_description.strip()) > 0
    )

    return (
        has_name
        or has_slug
        or has_description
        or has_meta_title
        or has_meta_description
    )


async def _apply_category_updates_by_slug(
    category: Category,
    params: UpdateCategoryBySlugParams,
    validated_data: tuple[
        str, str, Optional[str], Optional[str], Optional[str]
    ],
) -> None:
    """Apply updates to the category."""
    (
        validated_name,
        validated_slug,
        validated_description,
        validated_meta_title,
        validated_meta_description,
    ) = validated_data

    final_slug = slugify(validated_slug)

    if params.name is not None and params.name.strip():
        category.category_name = params.name.upper()
    if params.slug is not None and params.slug.strip():
        category.category_slug = final_slug
    if params.description is not None and params.description.strip():
        category.category_description = validated_description
    if params.meta_title is not None and params.meta_title.strip():
        category.category_meta_title = validated_meta_title
    if params.meta_description is not None and params.meta_description.strip():
        category.category_meta_description = validated_meta_description
    if params.featured is not None:
        category.featured_category = params.featured
    if params.show_in_menu is not None:
        category.show_in_menu = params.show_in_menu


async def _handle_file_upload_by_slug(
    category: Category, file: UploadFile, final_slug: str
) -> Optional[JSONResponse]:
    """Handle file upload for category."""
    if not file or not file.filename:
        return None

    if not is_valid_filename(file.filename):
        return api_response(status.HTTP_400_BAD_REQUEST, "Invalid file name.")

    sub_path = settings.CATEGORY_IMAGE_PATH.format(slug_name=final_slug)
    try:
        uploaded_url = await save_uploaded_file(file, sub_path)
        category.category_img_thumbnail = uploaded_url
        return None
    except ValueError as ve:
        return api_response(status.HTTP_400_BAD_REQUEST, str(ve))
    except Exception as e:
        return api_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to save uploaded file: {str(e)}",
            log_error=True,
        )


@router.get("/slug/{slug}")
@exception_handler
async def get_category_by_slug(
    slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_slug=slug)
    )
    category = result.scalars().first()

    if not category:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Category not found",
        )

    data = {
        "category_id": category.category_id,
        "category_name": category.category_name.title(),
        "category_description": category.category_description,
        "category_slug": category.category_slug,
        "category_meta_title": category.category_meta_title,
        "category_meta_description": category.category_meta_description,
        "category_img_thumbnail": get_media_url(
            category.category_img_thumbnail
        ),
        "featured_category": category.featured_category,
        "show_in_menu": category.show_in_menu,
        "category_status": category.category_status,
        "category_tstamp": (
            cast(datetime, category.category_tstamp).isoformat()
            if category.category_tstamp
            else None
        ),
        "subcategories": [
            {
                "subcategory_id": sub.subcategory_id,
                "subcategory_name": sub.subcategory_name.title(),
                "subcategory_description": (sub.subcategory_description),
                "subcategory_slug": sub.subcategory_slug,
                "subcategory_meta_title": sub.subcategory_meta_title,
                "subcategory_meta_description": (
                    sub.subcategory_meta_description
                ),
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
            }
            for sub in category.subcategories
        ],
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Category fetched successfully",
        data=data,
    )


def get_basic_form_data_by_slug(
    name: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Get basic form data."""
    return name, slug, description


def get_meta_form_data_by_slug(
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
) -> tuple[Optional[str], Optional[str]]:
    """Get meta form data."""
    return meta_title, meta_description


def get_feature_form_data_by_slug(
    featured: Optional[bool] = Form(None),
    show_in_menu: Optional[bool] = Form(None),
) -> tuple[Optional[bool], Optional[bool]]:
    """Get feature form data."""
    return featured, show_in_menu


async def get_update_form_data_by_slug(
    basic_data: tuple[Optional[str], Optional[str], Optional[str]] = Depends(
        get_basic_form_data_by_slug
    ),
    meta_data: tuple[Optional[str], Optional[str]] = Depends(
        get_meta_form_data_by_slug
    ),
    feature_data: tuple[Optional[bool], Optional[bool]] = Depends(
        get_feature_form_data_by_slug
    ),
    file: UploadFile = File(None),
) -> UpdateCategoryBySlugParams:
    """Dependency to collect form data into UpdateCategoryBySlugParams."""
    name, slug, description = basic_data
    meta_title, meta_description = meta_data
    featured, show_in_menu = feature_data

    return UpdateCategoryBySlugParams(
        name=name,
        slug=slug,
        description=description,
        meta_title=meta_title,
        meta_description=meta_description,
        featured=featured,
        show_in_menu=show_in_menu,
        file=file,
    )


@router.put("/slug/{category_slug}")
@exception_handler
async def update_category_by_slug(
    category_slug: str,
    name: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    featured: Optional[bool] = Form(None),
    show_in_menu: Optional[bool] = Form(None),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # === Fetch category ===
    result = await db.execute(
        select(Category).filter_by(category_slug=category_slug)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    # === Create params object ===
    params = UpdateCategoryBySlugParams()
    params.name = name
    params.slug = slug
    params.description = description
    params.meta_title = meta_title
    params.meta_description = meta_description
    params.featured = featured
    params.show_in_menu = show_in_menu
    params.file = file

    # === Check if there's no change at all ===
    if _check_no_changes_by_slug(params, category):
        return api_response(status.HTTP_400_BAD_REQUEST, "No changes detected.")

    # === Prepare inputs with fallback ===
    input_values = _prepare_input_values_by_slug(params, category)
    
    # Check if sanitization failed
    if isinstance(input_values, JSONResponse):
        return input_values

    # === Validate format if changed ===
    if _has_field_changes_by_slug(params):
        category_data = CategoryData(
            name=input_values[0],
            slug=input_values[1],
            description=input_values[2],
            meta_title=input_values[3],
            meta_description=input_values[4],
            is_subcategory=False,
        )

        validated_values = validate_category_data(category_data)
        final_slug = slugify(validated_values[1])

        # === Conflict validation ===
        if validated_values[0] is None:
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Category Name is required."
            )

        conflict_data = ConflictCheckData(
            name=validated_values[0],
            slug=final_slug,
            description=validated_values[2],
            meta_title=validated_values[3],
            meta_description=validated_values[4],
            category_id_to_exclude=category.category_id,
        )

        conflict_error = await validate_category_conflicts(db, conflict_data)
        if conflict_error:
            return api_response(status.HTTP_400_BAD_REQUEST, conflict_error)
    else:
        validated_values = input_values
        final_slug = slugify(input_values[1])

    # === Apply updates ===
    await _apply_category_updates_by_slug(category, params, validated_values)

    # === Handle file upload ===
    file_error = await _handle_file_upload_by_slug(
        category, params.file, final_slug
    )
    if file_error:
        return file_error

    await db.commit()
    await db.refresh(category)

    return api_response(
        status.HTTP_200_OK,
        "Category updated successfully",
        data={
            "category_id": category.category_id,
            "category_slug": category.category_slug,
        },
    )


@router.delete("/slug/{category_slug}/soft")
@exception_handler
async def soft_delete_category_by_slug(
    category_slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_slug=category_slug)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    category.category_status = True
    for subcategory in category.subcategories:
        subcategory.subcategory_status = True

    await db.commit()
    return api_response(
        status.HTTP_200_OK,
        "Category and subcategories soft deleted successfully",
    )


@router.put("/slug/{category_slug}/restore")
@exception_handler
async def restore_category_by_slug(
    category_slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_slug=category_slug)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    category.category_status = False
    for subcategory in category.subcategories:
        subcategory.subcategory_status = False

    await db.commit()
    return api_response(
        status.HTTP_200_OK,
        "Category and subcategories restored successfully",
    )


@router.delete("/slug/{category_slug}/hard")
@exception_handler
async def hard_delete_category_by_slug(
    category_slug: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_slug=category_slug)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    await db.delete(category)
    await db.commit()

    return api_response(
        status.HTTP_200_OK,
        "Category and its subcategories permanently deleted",
    )
