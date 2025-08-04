from typing import Dict, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from category_service.services.category_service import (
    check_subcategory_conflicts,
    check_subcategory_vs_category_conflicts,
    validate_subcategory_fields,
)
from lifespan import settings
from shared.core.api_response import api_response
from shared.db.models import SubCategory
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url, save_uploaded_file
from shared.utils.format_validators import is_valid_filename

router = APIRouter()


@router.get("/{subcategory_id}")
@exception_handler
async def get_subcategory_by_id(
    subcategory_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Load subcategory with related parent category
    result = await db.execute(
        select(SubCategory)
        .options(
            selectinload(SubCategory.category)
        )  # Eager load parent category
        .filter_by(subcategory_id=subcategory_id)
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
            sub.subcategory_tstamp.isoformat()
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
        status_code=status.HTTP_200_OK,
        message="Subcategory fetched successfully",
        data=data,
    )


@router.put("/{subcategory_id}")
@exception_handler
async def update_subcategory(
    subcategory_id: str,
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
    """Update a subcategory by ID."""
    # Get subcategory from database
    subcategory = await get_subcategory_by_id_from_db(db, subcategory_id)
    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    # Check if there are any changes
    if not has_changes(
        subcategory,
        name,
        slug,
        description,
        meta_title,
        meta_description,
        featured,
        show_in_menu,
        file,
    ):
        return api_response(status.HTTP_400_BAD_REQUEST, "No changes detected.")

    # Prepare input values with fallbacks
    input_values = prepare_input_values(
        subcategory, name, slug, description, meta_title, meta_description
    )

    # Validate fields and check for conflicts
    validation_result = await validate_and_check_conflicts(
        db, subcategory_id, input_values
    )
    if isinstance(validation_result, JSONResponse):
        return validation_result

    final_slug = validation_result

    # Apply changes to subcategory
    update_subcategory_fields(
        subcategory, input_values, final_slug, featured, show_in_menu
    )

    # Handle file upload if provided
    if file and file.filename:
        file_upload_result = await handle_file_upload(
            file, subcategory, final_slug
        )
        if isinstance(file_upload_result, JSONResponse):
            return file_upload_result

    # Save changes
    await db.commit()
    await db.refresh(subcategory)

    return api_response(
        status.HTTP_200_OK,
        "Subcategory updated successfully",
        data={"subcategory_id": subcategory.subcategory_id},
    )


async def get_subcategory_by_id_from_db(
    db: AsyncSession, subcategory_id: str
) -> Optional[SubCategory]:
    """Get subcategory by ID from database."""
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=subcategory_id)
    )
    return result.scalars().first()


def has_changes(
    subcategory: SubCategory,
    name: Optional[str],
    slug: Optional[str],
    description: Optional[str],
    meta_title: Optional[str],
    meta_description: Optional[str],
    featured: Optional[bool],
    show_in_menu: Optional[bool],
    file: Optional[UploadFile],
) -> bool:
    """Check if there are any changes to apply."""
    return not (
        (name is None or name.strip() == "")
        and (slug is None or slug.strip() == "")
        and (description is None or description.strip() == "")
        and (meta_title is None or meta_title.strip() == "")
        and (meta_description is None or meta_description.strip() == "")
        and (featured is None or featured == subcategory.featured_subcategory)
        and (show_in_menu is None or show_in_menu == subcategory.show_in_menu)
        and not (file and file.filename)
    )


def prepare_input_values(
    subcategory: SubCategory,
    name: Optional[str],
    slug: Optional[str],
    description: Optional[str],
    meta_title: Optional[str],
    meta_description: Optional[str],
) -> Dict[str, str]:
    """Prepare input values with fallbacks from existing subcategory."""
    return {
        "name": (
            subcategory.subcategory_name or ""
            if (name is None or name.strip() == "")
            else name
        ),
        "slug": (
            subcategory.subcategory_slug or ""
            if (slug is None or slug.strip() == "")
            else slug
        ),
        "description": (
            subcategory.subcategory_description or ""
            if (description is None or description.strip() == "")
            else description
        ),
        "meta_title": (
            subcategory.subcategory_meta_title or ""
            if (meta_title is None or meta_title.strip() == "")
            else meta_title
        ),
        "meta_description": (
            subcategory.subcategory_meta_description or ""
            if (meta_description is None or meta_description.strip() == "")
            else meta_description
        ),
    }


async def validate_and_check_conflicts(
    db: AsyncSession, subcategory_id: str, input_values: Dict[str, str]
) -> str | JSONResponse:
    """Validate fields and check for conflicts."""
    # Validate fields
    try:
        (
            input_name,
            input_slug,
            input_description,
            input_meta_title,
            input_meta_description,
        ) = validate_subcategory_fields(
            name=input_values["name"],
            slug=input_values["slug"],
            description=input_values["description"],
            meta_title=input_values["meta_title"],
            meta_description=input_values["meta_description"],
        )
    except HTTPException as e:
        return api_response(e.status_code, e.detail)

    final_slug = slugify(input_slug)

    # Check for conflicts (subcategory vs subcategory)
    conflict_error = await check_subcategory_conflicts(
        db=db,
        name=input_name,
        slug=final_slug,
        description=input_description,
        meta_title=input_meta_title,
        meta_description=input_meta_description,
        subcategory_id_to_exclude=subcategory_id,
    )
    if conflict_error:
        return api_response(status.HTTP_400_BAD_REQUEST, conflict_error)

    # Check for conflicts (subcategory vs category)
    conflict_error = await check_subcategory_vs_category_conflicts(
        db=db,
        name=input_name,
        slug=final_slug,
        description=input_description,
        meta_title=input_meta_title,
        meta_description=input_meta_description,
    )
    if conflict_error:
        return api_response(status.HTTP_400_BAD_REQUEST, conflict_error)

    return final_slug


def update_subcategory_fields(
    subcategory: SubCategory,
    input_values: Dict[str, str],
    final_slug: str,
    featured: Optional[bool],
    show_in_menu: Optional[bool],
) -> None:
    """Update subcategory fields with new values."""
    name = input_values["name"]
    slug = input_values["slug"]
    description = input_values["description"]
    meta_title = input_values["meta_title"]
    meta_description = input_values["meta_description"]

    if name is not None and name.strip():
        subcategory.subcategory_name = name.upper()
    if slug is not None and slug.strip():
        subcategory.subcategory_slug = final_slug
    if description is not None and description.strip():
        subcategory.subcategory_description = description
    if meta_title is not None and meta_title.strip():
        subcategory.subcategory_meta_title = meta_title
    if meta_description is not None and meta_description.strip():
        subcategory.subcategory_meta_description = meta_description
    if featured is not None:
        subcategory.featured_subcategory = featured
    if show_in_menu is not None:
        subcategory.show_in_menu = show_in_menu


async def handle_file_upload(
    file: UploadFile, subcategory: SubCategory, final_slug: str
) -> None | JSONResponse:
    """Handle file upload for subcategory thumbnail."""
    if file.filename is None:
        return api_response(status.HTTP_400_BAD_REQUEST, "Missing filename.")

    if not is_valid_filename(file.filename):
        return api_response(status.HTTP_400_BAD_REQUEST, "Invalid file name.")

    sub_path = settings.SUBCATEGORY_IMAGE_PATH.format(
        category_id=subcategory.category_id, slug_name=final_slug
    )

    uploaded_url = await save_uploaded_file(file, sub_path)
    subcategory.subcategory_img_thumbnail = uploaded_url

    return None


@router.delete("/{subcategory_id}/soft")
@exception_handler
async def soft_delete_subcategory(
    subcategory_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=subcategory_id)
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


@router.put("/{subcategory_id}/restore")
@exception_handler
async def restore_subcategory(
    subcategory_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=subcategory_id)
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


@router.delete("/{subcategory_id}/hard")
@exception_handler
async def hard_delete_subcategory(
    subcategory_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=subcategory_id)
    )
    subcategory = result.scalars().first()

    if not subcategory:
        return api_response(status.HTTP_404_NOT_FOUND, "Subcategory not found")

    await db.delete(subcategory)
    await db.commit()

    return api_response(status.HTTP_200_OK, "Subcategory permanently deleted")
