from dataclasses import dataclass
from typing import Optional, Union

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from category_service.services.category_service import (
    ConflictCheckData,
    _validate_name,
    _validate_slug,
    _validate_subcategory_name,
    _validate_subcategory_optional_field,
    _validate_subcategory_slug,
    _validate_text_field,
    check_subcategory_conflicts,
    check_subcategory_vs_category_conflicts,
    validate_category_conflicts,
)
from shared.core.api_response import api_response
from shared.core.config import settings
from shared.db.models import Category, SubCategory
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url, save_uploaded_file
from shared.utils.format_validators import is_valid_filename

router = APIRouter()


@dataclass
class UpdateFormData:
    """Data class for update form parameters."""

    name: Optional[str]
    slug: Optional[str]
    description: Optional[str]
    meta_title: Optional[str]
    meta_description: Optional[str]
    featured: Optional[bool]
    show_in_menu: Optional[bool]
    file: Optional[UploadFile] = None


@dataclass
class FieldMappings:
    """Data class for database field mappings."""

    # pylint: disable=too-many-instance-attributes
    id_field: str
    slug_field: str
    name_field: str
    desc_field: str
    meta_title_field: str
    meta_desc_field: str
    featured_field: str
    img_field: str


@dataclass
class ItemMetadata:
    """Data class for item metadata."""

    item: Union[Category, SubCategory]
    model_type: str
    fields: FieldMappings
    path_template: str


@dataclass
class ValidatedItemData:
    """Validated item data for updates."""

    name: str
    slug: str
    description: Optional[str]
    meta_title: Optional[str]
    meta_description: Optional[str]


async def _get_item_metadata(
    db: AsyncSession, item_id: str
) -> Optional[ItemMetadata]:
    """Get item and its metadata for update operations."""
    # Try fetching as Category
    result = await db.execute(select(Category).filter_by(category_id=item_id))
    category = result.scalars().first()

    if category:
        return ItemMetadata(
            item=category,
            model_type="category",
            fields=FieldMappings(
                id_field="category_id",
                slug_field="category_slug",
                name_field="category_name",
                desc_field="category_description",
                meta_title_field="category_meta_title",
                meta_desc_field="category_meta_description",
                featured_field="featured_category",
                img_field="category_img_thumbnail",
            ),
            path_template=settings.CATEGORY_IMAGE_PATH,
        )

    # Try SubCategory
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=item_id)
    )
    subcategory = result.scalars().first()

    if subcategory:
        return ItemMetadata(
            item=subcategory,
            model_type="subcategory",
            fields=FieldMappings(
                id_field="subcategory_id",
                slug_field="subcategory_slug",
                name_field="subcategory_name",
                desc_field="subcategory_description",
                meta_title_field="subcategory_meta_title",
                meta_desc_field="subcategory_meta_description",
                featured_field="featured_subcategory",
                img_field="subcategory_img_thumbnail",
            ),
            path_template=settings.SUBCATEGORY_IMAGE_PATH,
        )

    return None


def _check_no_changes(
    form_data: UpdateFormData, metadata: ItemMetadata
) -> bool:
    """Check if there are no changes to be made."""
    return (
        (form_data.name is None or form_data.name.strip() == "")
        and (form_data.slug is None or form_data.slug.strip() == "")
        and (
            form_data.description is None or form_data.description.strip() == ""
        )
        and (form_data.meta_title is None or form_data.meta_title.strip() == "")
        and (
            form_data.meta_description is None
            or form_data.meta_description.strip() == ""
        )
        and (
            form_data.featured is None
            or form_data.featured
            == getattr(metadata.item, metadata.fields.featured_field)
        )
        and (
            form_data.show_in_menu is None
            or form_data.show_in_menu == metadata.item.show_in_menu
        )
        and not (form_data.file and form_data.file.filename)
    )


def _prepare_input_values(
    form_data: UpdateFormData, metadata: ItemMetadata
) -> tuple[str, str, Optional[str], Optional[str], Optional[str]]:
    """Prepare input values with fallback to existing item values."""
    input_name = (
        getattr(metadata.item, metadata.fields.name_field)
        if (form_data.name is None or form_data.name.strip() == "")
        else form_data.name
    )

    # Auto-generate slug from name if name is provided but slug is not
    if (
        form_data.name is not None
        and form_data.name.strip() != ""
        and (form_data.slug is None or form_data.slug.strip() == "")
    ):
        input_slug = slugify(form_data.name)
    else:
        input_slug = (
            getattr(metadata.item, metadata.fields.slug_field)
            if (form_data.slug is None or form_data.slug.strip() == "")
            else form_data.slug
        )
    input_description = (
        getattr(metadata.item, metadata.fields.desc_field)
        if (
            form_data.description is None or form_data.description.strip() == ""
        )
        else form_data.description
    )
    input_meta_title = (
        getattr(metadata.item, metadata.fields.meta_title_field)
        if (form_data.meta_title is None or form_data.meta_title.strip() == "")
        else form_data.meta_title
    )
    input_meta_description = (
        getattr(metadata.item, metadata.fields.meta_desc_field)
        if (
            form_data.meta_description is None
            or form_data.meta_description.strip() == ""
        )
        else form_data.meta_description
    )
    return (
        input_name,
        input_slug,
        input_description,
        input_meta_title,
        input_meta_description,
    )


def _has_field_changes(form_data: UpdateFormData) -> bool:
    """Check if any text fields are being changed."""
    return any(
        [
            form_data.name is not None and form_data.name.strip(),
            form_data.slug is not None and form_data.slug.strip(),
            form_data.description is not None and form_data.description.strip(),
            form_data.meta_title is not None and form_data.meta_title.strip(),
            form_data.meta_description is not None
            and form_data.meta_description.strip(),
        ]
    )


def _validate_individual_field(
    field_value: str, field_type: str, metadata: ItemMetadata
) -> str:
    """Validate individual field based on type."""
    if metadata.model_type == "category":
        if field_type == "name":
            return _validate_name(field_value, False)
        elif field_type == "slug":
            return _validate_slug(field_value)
        elif field_type in ["description", "meta_title", "meta_description"]:
            max_lengths = {
                "description": 500,
                "meta_title": 70,
                "meta_description": 160,
            }
            return _validate_text_field(
                field_value,
                field_type.replace("_", " ").title(),
                max_lengths[field_type],
            )
    else:  # subcategory
        if field_type == "name":

            _validate_subcategory_name(field_value)
            return field_value.upper()
        elif field_type == "slug":
            _validate_subcategory_slug(field_value)
            return field_value.lower()
        elif field_type in ["description", "meta_title", "meta_description"]:

            max_lengths = {
                "description": 500,
                "meta_title": 70,
                "meta_description": 160,
            }
            _validate_subcategory_optional_field(
                field_value,
                field_type.replace("_", " ").title(),
                max_lengths[field_type],
            )
            return field_value

    return field_value


async def _validate_and_prepare_data(
    form_data: UpdateFormData, metadata: ItemMetadata
) -> tuple[str, str, Optional[str], Optional[str], Optional[str]]:
    """Validate inputs and prepare data using service layer."""
    # Get current values from the item
    current_name = getattr(metadata.item, metadata.fields.name_field)
    current_slug = getattr(metadata.item, metadata.fields.slug_field)
    current_description = getattr(metadata.item, metadata.fields.desc_field)
    current_meta_title = getattr(
        metadata.item, metadata.fields.meta_title_field
    )
    current_meta_description = getattr(
        metadata.item, metadata.fields.meta_desc_field
    )

    # Prepare values - use new values if provided, otherwise use current values
    name_value = (
        form_data.name
        if (form_data.name is not None and form_data.name.strip())
        else current_name
    )

    # Handle slug generation
    if (
        form_data.name is not None
        and form_data.name.strip()
        and (form_data.slug is None or form_data.slug.strip() == "")
    ):
        slug_value = slugify(form_data.name)
    elif form_data.slug is not None and form_data.slug.strip():
        slug_value = form_data.slug
    else:
        slug_value = current_slug

    description_value = (
        form_data.description
        if (form_data.description is not None and form_data.description.strip())
        else current_description
    )
    meta_title_value = (
        form_data.meta_title
        if (form_data.meta_title is not None and form_data.meta_title.strip())
        else current_meta_title
    )
    meta_description_value = (
        form_data.meta_description
        if (
            form_data.meta_description is not None
            and form_data.meta_description.strip()
        )
        else current_meta_description
    )

    # Validate only the fields that are being changed
    validated_name = name_value
    validated_slug = slug_value
    validated_description = description_value
    validated_meta_title = meta_title_value
    validated_meta_description = meta_description_value

    if form_data.name is not None and form_data.name.strip():
        validated_name = _validate_individual_field(
            name_value, "name", metadata
        )

    if (form_data.slug is not None and form_data.slug.strip()) or (
        form_data.name is not None and form_data.name.strip()
    ):
        validated_slug = _validate_individual_field(
            slug_value, "slug", metadata
        )

    if form_data.description is not None and form_data.description.strip():
        validated_description = _validate_individual_field(
            description_value, "description", metadata
        )

    if form_data.meta_title is not None and form_data.meta_title.strip():
        validated_meta_title = _validate_individual_field(
            meta_title_value, "meta_title", metadata
        )

    if (
        form_data.meta_description is not None
        and form_data.meta_description.strip()
    ):
        validated_meta_description = _validate_individual_field(
            meta_description_value, "meta_description", metadata
        )

    return (
        validated_name,
        validated_slug,
        validated_description,
        validated_meta_title,
        validated_meta_description,
    )


async def _check_conflicts(
    db: AsyncSession,
    validated_values: tuple[
        str, str, Optional[str], Optional[str], Optional[str]
    ],
    metadata: ItemMetadata,
    item_id: str,
) -> Optional[str]:
    """Check for conflicts using service layer."""
    (
        validated_name,
        validated_slug,
        validated_description,
        validated_meta_title,
        validated_meta_description,
    ) = validated_values
    final_slug = slugify(validated_slug)

    if metadata.model_type == "category":
        conflict_data = ConflictCheckData(
            name=validated_name,
            slug=final_slug,
            description=validated_description,
            meta_title=validated_meta_title,
            meta_description=validated_meta_description,
            category_id_to_exclude=item_id,
        )
        return await validate_category_conflicts(db, conflict_data)
    else:
        # For subcategory - check both subcategory and category conflicts
        subcategory_conflict = await check_subcategory_conflicts(
            db=db,
            name=validated_name,
            slug=final_slug,
            description=validated_description,
            meta_title=validated_meta_title,
            meta_description=validated_meta_description,
            subcategory_id_to_exclude=item_id,
        )
        if subcategory_conflict:
            return subcategory_conflict

        return await check_subcategory_vs_category_conflicts(
            db=db,
            name=validated_name,
            slug=final_slug,
            description=validated_description,
            meta_title=validated_meta_title,
            meta_description=validated_meta_description,
        )


async def _apply_item_updates(
    metadata: ItemMetadata,
    form_data: UpdateFormData,
    validated_data: Optional[ValidatedItemData],
) -> None:
    """Apply updates to the item object."""
    # Update text fields only if validated_data is available
    if validated_data:
        if form_data.name is not None and form_data.name.strip():
            setattr(
                metadata.item,
                metadata.fields.name_field,
                validated_data.name.upper(),
            )
        if form_data.slug is not None and form_data.slug.strip():
            setattr(
                metadata.item, metadata.fields.slug_field, validated_data.slug
            )
        if form_data.description is not None and form_data.description.strip():
            setattr(
                metadata.item,
                metadata.fields.desc_field,
                validated_data.description,
            )
        if form_data.meta_title is not None and form_data.meta_title.strip():
            setattr(
                metadata.item,
                metadata.fields.meta_title_field,
                validated_data.meta_title,
            )
        if (
            form_data.meta_description is not None
            and form_data.meta_description.strip()
        ):
            setattr(
                metadata.item,
                metadata.fields.meta_desc_field,
                validated_data.meta_description,
            )

    # Update boolean fields (these don't need validation)
    if form_data.featured is not None:
        setattr(
            metadata.item, metadata.fields.featured_field, form_data.featured
        )
    if form_data.show_in_menu is not None:
        metadata.item.show_in_menu = form_data.show_in_menu


async def _handle_file_upload(
    metadata: ItemMetadata, file: UploadFile, final_slug: str
) -> None:
    """Handle file upload with validation."""
    if not file or not file.filename:
        return

    if not is_valid_filename(file.filename):
        raise ValueError("Invalid file name.")

    if metadata.model_type == "category":
        sub_path = metadata.path_template.format(slug_name=final_slug)
    else:
        sub_path = metadata.path_template.format(
            category_id=metadata.item.category_id, slug_name=final_slug
        )

    uploaded_url = await save_uploaded_file(file, sub_path)
    setattr(metadata.item, metadata.fields.img_field, uploaded_url)


@router.get("/{item_id}")
@exception_handler
async def get_category_or_subcategory_details(
    item_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Try to find category by ID
    category_result = await db.execute(
        select(Category)
        .options(selectinload(Category.subcategories))
        .filter_by(category_id=item_id)
    )
    category = category_result.scalars().first()

    if category:
        data = {
            "type": "category",
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

    # Try to find subcategory by ID
    subcat_result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=item_id)
    )
    sub = subcat_result.scalars().first()

    if sub:
        data = {
            "type": "subcategory",
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
            "subcategory_tstamp": sub.subcategory_tstamp,
            "category_id": sub.category_id,
        }
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Subcategory fetched successfully",
            data=data,
        )

    # Neither category nor subcategory found
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Category or Subcategory not found",
    )


async def _process_item_update(
    metadata: ItemMetadata,
    form_data: UpdateFormData,
    file: UploadFile,
    db: AsyncSession,
    item_id: str,
) -> JSONResponse:
    """Process the item update logic."""
    # Validate inputs
    validation_error = _validate_update_inputs(form_data)
    if validation_error:
        return validation_error

    # Check if there's no change at all
    if _check_no_changes(form_data, metadata):
        return api_response(status.HTTP_400_BAD_REQUEST, "No changes detected.")

    # Handle file upload validation first (before slug validation)
    if file and file.filename:
        if not is_valid_filename(file.filename):
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Invalid file name."
            )

    # Only validate and prepare text data if text fields are being changed
    validated_values = None
    final_slug = None
    validated_data = None

    if _has_field_changes(form_data):
        # Validate and prepare data
        try:
            validated_values = await _validate_and_prepare_data(
                form_data, metadata
            )
        except Exception as e:
            return api_response(status.HTTP_400_BAD_REQUEST, str(e))

        # Check for conflicts only for fields being changed
        conflict_error = await _check_conflicts(
            db, validated_values, metadata, item_id
        )
        if conflict_error:
            return api_response(status.HTTP_400_BAD_REQUEST, conflict_error)

        # Create validated data object
        (
            validated_name,
            validated_slug,
            validated_description,
            validated_meta_title,
            validated_meta_description,
        ) = validated_values
        final_slug = slugify(validated_slug)

        validated_data = ValidatedItemData(
            name=validated_name,
            slug=final_slug,
            description=validated_description,
            meta_title=validated_meta_title,
            meta_description=validated_meta_description,
        )
    else:
        # For non-text field updates, use existing slug for file upload
        final_slug = getattr(metadata.item, metadata.fields.slug_field)

    # Apply updates
    await _apply_item_updates(metadata, form_data, validated_data)

    # Handle file upload
    try:
        await _handle_file_upload(metadata, file, final_slug)
    except ValueError as ve:
        return api_response(status.HTTP_400_BAD_REQUEST, str(ve))
    except Exception as e:
        return api_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to save uploaded file: {str(e)}",
            log_error=True,
        )

    await db.commit()
    await db.refresh(metadata.item)

    return api_response(
        status.HTTP_200_OK,
        f"{metadata.model_type.capitalize()} updated successfully",
        data={
            f"{metadata.model_type}_id": item_id,
            f"{metadata.model_type}_slug": getattr(
                metadata.item, metadata.fields.slug_field
            ),
        },
    )


@router.put("/{item_id}")
@exception_handler
async def update_category_or_subcategory(  # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    item_id: str,
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
    # Fetch item
    metadata = await _fetch_item(item_id, db)
    if not metadata:
        return api_response(status.HTTP_404_NOT_FOUND, "Item not found")

    # Create form data object
    form_data = UpdateFormData(
        name=name,
        slug=slug,
        description=description,
        meta_title=meta_title,
        meta_description=meta_description,
        featured=featured,
        show_in_menu=show_in_menu,
        file=file,
    )

    # Process the update
    return await _process_item_update(metadata, form_data, file, db, item_id)


async def _fetch_item(item_id: str, db: AsyncSession) -> Optional[ItemMetadata]:
    """Fetch item by ID and return metadata."""
    return await _get_item_metadata(db, item_id)


def _validate_update_inputs(
    form_data: UpdateFormData,
) -> Optional[JSONResponse]:
    """Validate update inputs and return error response if invalid."""
    if form_data.name is not None and form_data.name.strip() == "":
        return api_response(
            status.HTTP_400_BAD_REQUEST, "Invalid name provided."
        )
    return None


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
) -> UpdateFormData:
    """Dependency to collect form data into UpdateFormData."""
    name, slug, description = basic_data
    meta_title, meta_description = meta_data
    featured, show_in_menu = feature_data

    return UpdateFormData(
        name=name,
        slug=slug,
        description=description,
        meta_title=meta_title,
        meta_description=meta_description,
        featured=featured,
        show_in_menu=show_in_menu,
        file=file,
    )


@router.delete("/soft/{item_id}")
@exception_handler
async def soft_delete_category_or_subcategory(
    item_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # Try to find as Category
    result = await db.execute(
        select(Category)
        .options(
            selectinload(Category.subcategories)
        )  # still useful if you later need it
        .filter_by(category_id=item_id)
    )
    category = result.scalars().first()

    if category:
        if category.category_status:
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Category already inactive"
            )

        # Soft-delete category only (no subcategories affected)
        category.category_status = True

        await db.commit()
        return api_response(
            status.HTTP_200_OK,
            "Category soft deleted successfully",  # Updated message
        )

    # Try to find as SubCategory
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=item_id)
    )
    subcategory = result.scalars().first()

    if subcategory:
        if subcategory.subcategory_status:
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Subcategory already inactive"
            )

        # Soft-delete subcategory
        subcategory.subcategory_status = True

        await db.commit()
        return api_response(
            status.HTTP_200_OK,
            "Subcategory soft deleted successfully",
        )

    # Not found
    return api_response(
        status.HTTP_404_NOT_FOUND,
        "Category or Subcategory not found",
    )


@router.put("/restore/{item_id}")
@exception_handler
async def restore_category_or_subcategory(
    item_id: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    # First: Try restoring as Category
    result = await db.execute(
        select(Category)
        .options(
            selectinload(Category.subcategories)
        )  # You can remove this if not used
        .filter_by(category_id=item_id)
    )
    category = result.scalars().first()

    if category:
        if not category.category_status:
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Category is already active"
            )

        # Restore category only (do not touch subcategories)
        category.category_status = False

        await db.commit()
        return api_response(
            status.HTTP_200_OK,
            "Category restored successfully",
        )

    # Next: Try restoring as SubCategory
    result = await db.execute(
        select(SubCategory).filter_by(subcategory_id=item_id)
    )
    subcategory = result.scalars().first()

    if subcategory:
        if not subcategory.subcategory_status:
            return api_response(
                status.HTTP_400_BAD_REQUEST, "Subcategory is already active"
            )

        # Restore subcategory only
        subcategory.subcategory_status = False

        await db.commit()
        return api_response(
            status.HTTP_200_OK,
            "Subcategory restored successfully",
        )

    # If not found
    return api_response(
        status.HTTP_404_NOT_FOUND,
        "Category or Subcategory not found",
    )
