from dataclasses import dataclass
from typing import Optional

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

from category_service.services.category_service import (
    CategoryData,
    ConflictCheckData,
    validate_category_conflicts,
    validate_category_data,
)
from shared.core.api_response import api_response
from shared.core.config import settings
from shared.db.models import Category
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url, save_uploaded_file

router = APIRouter()


@dataclass
class UpdateCategoryParams:  # pylint: disable=too-many-instance-attributes
    """Parameters for category update operation."""

    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    featured: Optional[bool] = None
    show_in_menu: Optional[bool] = None
    file: Optional[UploadFile] = None


@router.get("/{category_id}")
@exception_handler
async def get_category_details(
    category_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    #  Fetch category by ID
    result = await db.execute(
        select(Category)
        .options(
            selectinload(Category.subcategories)
        )  # optional: load subcategories
        .filter_by(category_id=category_id)
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
        "category_tstamp": category.category_tstamp,
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Category fetched successfully",
        data=data,
    )


def _validate_update_inputs(
    params: UpdateCategoryParams,
) -> Optional[JSONResponse]:
    """Validate update inputs and return error response if invalid."""
    if params.name is not None and params.name.strip() == "":
        return api_response(
            status.HTTP_400_BAD_REQUEST, "Invalid category name."
        )
    return None


def _check_no_changes(params: UpdateCategoryParams, category: Category) -> bool:
    """Check if there are no changes to be made."""
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


def _prepare_input_values(
    params: UpdateCategoryParams, category: Category
) -> tuple[str, str, Optional[str], Optional[str], Optional[str]]:
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
    return (
        input_name,
        input_slug,
        input_description,
        input_meta_title,
        input_meta_description,
    )


def _has_field_changes(params: UpdateCategoryParams) -> bool:
    """Check if any text fields are being changed."""
    return any(
        [
            params.name is not None and params.name.strip(),
            params.slug is not None and params.slug.strip(),
            params.description is not None and params.description.strip(),
            params.meta_title is not None and params.meta_title.strip(),
            params.meta_description is not None
            and params.meta_description.strip(),
        ]
    )


@dataclass
class ValidatedCategoryData:
    """Validated category data for updates."""

    name: str
    slug: str
    description: Optional[str]
    meta_title: Optional[str]
    meta_description: Optional[str]


async def _apply_category_updates(
    category: Category,
    params: UpdateCategoryParams,
    validated_data: ValidatedCategoryData,
) -> None:
    """Apply updates to the category object."""
    if params.name is not None and params.name.strip():
        category.category_name = validated_data.name.upper()
    if params.slug is not None and params.slug.strip():
        category.category_slug = validated_data.slug
    if params.description is not None and params.description.strip():
        category.category_description = validated_data.description
    if params.meta_title is not None and params.meta_title.strip():
        category.category_meta_title = validated_data.meta_title
    if params.meta_description is not None and params.meta_description.strip():
        category.category_meta_description = validated_data.meta_description

    if params.featured is not None:
        category.featured_category = params.featured

    if params.show_in_menu is not None:
        category.show_in_menu = params.show_in_menu

    if params.file and params.file.filename:
        sub_path = settings.CATEGORY_IMAGE_PATH.format(
            slug_name=validated_data.slug
        )
        uploaded_url = await save_uploaded_file(params.file, sub_path)
        category.category_img_thumbnail = uploaded_url


async def _validate_and_prepare_data(
    params: UpdateCategoryParams, category: Category
) -> tuple[
    CategoryData, tuple[str, str, Optional[str], Optional[str], Optional[str]]
]:
    """Validate inputs and prepare category data."""
    input_values = _prepare_input_values(params, category)

    category_data = CategoryData(
        name=input_values[0],
        slug=input_values[1],
        description=input_values[2],
        meta_title=input_values[3],
        meta_description=input_values[4],
        is_subcategory=False,
    )

    validated_values = validate_category_data(category_data)
    return category_data, validated_values


async def _check_conflicts(
    db: AsyncSession,
    validated_values: tuple[
        str, str, Optional[str], Optional[str], Optional[str]
    ],
    category_id: str,
) -> Optional[str]:
    """Check for category conflicts."""
    (
        validated_name,
        validated_slug,
        validated_description,
        validated_meta_title,
        validated_meta_description,
    ) = validated_values
    final_slug = slugify(validated_slug)

    if validated_name is None:
        return "Category name is required."

    conflict_data = ConflictCheckData(
        name=validated_name,
        slug=final_slug,
        description=validated_description,
        meta_title=validated_meta_title,
        meta_description=validated_meta_description,
        category_id_to_exclude=category_id,
    )

    return await validate_category_conflicts(db, conflict_data)


async def _process_category_update(
    category: Category,
    params: UpdateCategoryParams,
    category_id: str,
    db: AsyncSession,
) -> JSONResponse:
    """Process the category update logic."""
    # === Validate inputs ===
    validation_error = _validate_update_inputs(params)
    if validation_error:
        return validation_error

    # === Check if there's no change at all ===
    if _check_no_changes(params, category):
        return api_response(
            status.HTTP_200_OK,
            "Category updated successfully",
            data={
                "category_id": category.category_id,
                "category_slug": category.category_slug,
            },
        )

    # === Validate and prepare data ===
    _, validated_values = await _validate_and_prepare_data(params, category)
    (
        validated_name,
        validated_slug,
        validated_description,
        validated_meta_title,
        validated_meta_description,
    ) = validated_values
    final_slug = slugify(validated_slug)

    # === Conflict validation only for fields being changed ===
    if _has_field_changes(params):
        conflict_error = await _check_conflicts(
            db, validated_values, category_id
        )
        if conflict_error:
            return api_response(status.HTTP_400_BAD_REQUEST, conflict_error)

    # === Apply updates ===
    validated_data = ValidatedCategoryData(
        name=validated_name,
        slug=final_slug,
        description=validated_description,
        meta_title=validated_meta_title,
        meta_description=validated_meta_description,
    )

    await _apply_category_updates(category, params, validated_data)

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


def get_basic_form_data(
    name: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Get basic form data."""
    return name, slug, description


def get_meta_form_data(
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
) -> tuple[Optional[str], Optional[str]]:
    """Get meta form data."""
    return meta_title, meta_description


def get_feature_form_data(
    featured: Optional[bool] = Form(None),
    show_in_menu: Optional[bool] = Form(None),
) -> tuple[Optional[bool], Optional[bool]]:
    """Get feature form data."""
    return featured, show_in_menu


async def get_update_form_data(
    basic_data: tuple[Optional[str], Optional[str], Optional[str]] = Depends(
        get_basic_form_data
    ),
    meta_data: tuple[Optional[str], Optional[str]] = Depends(
        get_meta_form_data
    ),
    feature_data: tuple[Optional[bool], Optional[bool]] = Depends(
        get_feature_form_data
    ),
    file: UploadFile = File(None),
) -> UpdateCategoryParams:
    """Dependency to collect form data into UpdateCategoryParams."""
    name, slug, description = basic_data
    meta_title, meta_description = meta_data
    featured, show_in_menu = feature_data

    return UpdateCategoryParams(
        name=name,
        slug=slug,
        description=description,
        meta_title=meta_title,
        meta_description=meta_description,
        featured=featured,
        show_in_menu=show_in_menu,
        file=file,
    )


async def _fetch_category(
    category_id: str, db: AsyncSession
) -> Optional[Category]:
    """Fetch category by ID."""
    result = await db.execute(
        select(Category).filter_by(category_id=category_id)
    )
    return result.scalars().first()


@router.put("/{category_id}")
@exception_handler
async def update_category(
    category_id: str,
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
    category = await _fetch_category(category_id, db)
    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    # === Create params object ===
    params = UpdateCategoryParams()
    params.name = name
    params.slug = slug
    params.description = description
    params.meta_title = meta_title
    params.meta_description = meta_description
    params.featured = featured
    params.show_in_menu = show_in_menu
    params.file = file

    # === Process the update ===
    return await _process_category_update(category, params, category_id, db)


@router.delete("/{category_id}/soft")
@exception_handler
async def soft_delete_category(
    category_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Fetch category by ID with subcategories (for optional subcategory soft-delete)
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_id=category_id)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    if category.category_status:
        return api_response(
            status.HTTP_400_BAD_REQUEST, "Category already inactive"
        )

    # Soft-delete the category
    category.category_status = True

    # OPTIONAL: Soft-delete all subcategories (uncomment to activate this behavior)
    # for sub in category.subcategories:
    #     sub.subcategory_status = True

    await db.commit()

    return api_response(
        status.HTTP_200_OK,
        "Category soft deleted successfully",
        # "Category and its subcategories soft deleted successfully",
    )


@router.put("/{category_id}/restore")
@exception_handler
async def restore_category(
    category_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Fetch the category (with subcategories loaded, in case you want to restore them too)
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_id=category_id)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    if not category.category_status:
        return api_response(
            status.HTTP_400_BAD_REQUEST, "Category is already active"
        )

    # Restore the category
    category.category_status = False

    # OPTIONAL: Restore all subcategories (uncomment to activate)
    # for sub in category.subcategories:
    #     sub.subcategory_status = False

    await db.commit()

    return api_response(
        status.HTTP_200_OK,
        "Category restored successfully",
        # "Category and its subcategories restored successfully",
    )


@router.delete("/{category_id}/hard")
@exception_handler
async def hard_delete_category(
    category_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Load category along with its subcategories
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_id=category_id)
    )
    category = result.scalars().first()

    if not category:
        return api_response(status.HTTP_404_NOT_FOUND, "Category not found")

    # This will now delete subcategories too due to
    # cascade="all, delete-orphan"
    await db.delete(category)
    await db.commit()

    return api_response(
        status.HTTP_200_OK,
        "Category and its subcategories permanently deleted",
    )
