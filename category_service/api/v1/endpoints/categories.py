from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, cast

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
from slugify import slugify
from sqlalchemy import and_, any_, case, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse

from category_service.schemas.categories import CategoryOut, CategoryOutDropDown
from category_service.services.category_service import (
    CategoryData,
    ConflictCheckData,
    SubcategoryConflictData,
    validate_category_conflicts,
    validate_category_data,
    validate_subcategory_conflicts,
)
from shared.core.api_response import api_response
from shared.db.models import Category, SubCategory
from shared.db.models.new_events import EventStatus, NewEvent
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url, save_uploaded_file
from shared.utils.id_generators import (
    generate_digits_lowercase,
    generate_digits_uppercase,
    generate_lower_uppercase,
)

router = APIRouter()


@dataclass
class ContentFields:
    """Data class for content-related form fields."""

    name: str
    slug: Optional[str]
    description: Optional[str]
    meta_title: Optional[str]
    meta_description: Optional[str]


@dataclass
class FormData:
    """Data class for form input parameters."""

    content_fields: ContentFields
    category_id: Optional[str]
    featured: bool
    show_in_menu: bool


@dataclass
class ValidatedContent:
    """Data class for validated content fields."""

    name: str
    slug: str
    description: Optional[str]
    meta_title: Optional[str]
    meta_description: Optional[str]


@dataclass
class CreateSubcategoryData:
    """Data class for subcategory creation parameters."""

    category_id: str
    content: ValidatedContent
    featured: bool
    show_in_menu: bool
    file: UploadFile


@dataclass
class CreateCategoryData:
    """Data class for category creation parameters."""

    content: ValidatedContent
    featured: bool
    show_in_menu: bool
    file: UploadFile


async def _create_subcategory(
    db: AsyncSession, data: CreateSubcategoryData
) -> JSONResponse:
    """Helper function to create a subcategory."""
    # Validate parent category exists
    result = await db.execute(
        select(Category).where(Category.category_id == data.category_id)
    )
    if not result.scalars().first():
        return api_response(
            status.HTTP_404_NOT_FOUND, "Parent category not found"
        )

    # Check for conflicts
    subcategory_data = SubcategoryConflictData(
        name=data.content.name,
        slug=data.content.slug,
        description=data.content.description,
        meta_title=data.content.meta_title,
        meta_description=data.content.meta_description,
    )
    conflict_error = await validate_subcategory_conflicts(db, subcategory_data)
    if conflict_error:
        return api_response(
            status.HTTP_400_BAD_REQUEST, conflict_error, log_error=True
        )

    # Create and save subcategory
    new_subcategory = SubCategory(
        id=generate_lower_uppercase(6),
        subcategory_id=generate_digits_lowercase(6),
        category_id=data.category_id,
        subcategory_name=data.content.name,
        subcategory_slug=data.content.slug,
        subcategory_description=data.content.description,
        subcategory_meta_title=data.content.meta_title,
        subcategory_meta_description=data.content.meta_description,
        featured_subcategory=data.featured,
        show_in_menu=data.show_in_menu,
    )

    # Handle file upload
    sub_path = f"subcategories/{data.category_id}/{data.content.slug}"
    uploaded_url = await save_uploaded_file(data.file, sub_path)
    if uploaded_url:
        new_subcategory.subcategory_img_thumbnail = uploaded_url

    db.add(new_subcategory)
    await db.commit()
    await db.refresh(new_subcategory)

    return api_response(
        status.HTTP_201_CREATED,
        "Subcategory created successfully",
        data={"subcategory_id": new_subcategory.subcategory_id},
    )


def _process_form_data(form_data: FormData) -> tuple[ValidatedContent, bool]:
    """Process and validate form data."""
    category_data = CategoryData(
        name=form_data.content_fields.name,
        slug=form_data.content_fields.slug,
        description=form_data.content_fields.description,
        meta_title=form_data.content_fields.meta_title,
        meta_description=form_data.content_fields.meta_description,
        is_subcategory=bool(form_data.category_id),
    )

    validated_data = validate_category_data(category_data)
    final_slug = slugify(validated_data[1])

    content = ValidatedContent(
        name=validated_data[0],
        slug=final_slug,
        description=validated_data[2],
        meta_title=validated_data[3],
        meta_description=validated_data[4],
    )

    return content, bool(form_data.category_id)


async def _create_category(
    db: AsyncSession, data: CreateCategoryData
) -> JSONResponse:
    """Helper function to create a category."""
    # Check for conflicts
    category_conflict_data = ConflictCheckData(
        name=data.content.name,
        slug=data.content.slug,
        description=data.content.description,
        meta_title=data.content.meta_title,
        meta_description=data.content.meta_description,
    )
    conflict_error = await validate_category_conflicts(
        db, category_conflict_data
    )
    if conflict_error:
        return api_response(
            status.HTTP_400_BAD_REQUEST, conflict_error, log_error=True
        )

    # Create and save category
    new_category = Category(
        category_id=generate_digits_uppercase(6),
        category_name=data.content.name,
        category_slug=data.content.slug,
        category_description=data.content.description,
        category_meta_title=data.content.meta_title,
        category_meta_description=data.content.meta_description,
        featured_category=data.featured,
        show_in_menu=data.show_in_menu,
    )

    # Handle file upload
    cat_path = f"categories/{data.content.slug}"
    uploaded_url = await save_uploaded_file(data.file, cat_path)
    if uploaded_url:
        new_category.category_img_thumbnail = uploaded_url

    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)

    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Category created successfully",
        data={"category_id": new_category.category_id},
    )


@router.post(
    "",
    summary="Integrated in Admin frontend at Categories/AddCategory page",
    description="Creates a new category or subcategory based on the provided form data.",
)
@exception_handler
async def create_category_or_subcategory(  # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    category_id: Optional[str] = Form(None),
    name: str = Form(...),
    slug: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    meta_title: Optional[str] = Form(None),
    meta_description: Optional[str] = Form(None),
    featured: bool = Form(False),
    show_in_menu: bool = Form(True),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Process form data
    content_fields = ContentFields(
        name=name,
        slug=slug,
        description=description,
        meta_title=meta_title,
        meta_description=meta_description,
    )

    form_data = FormData(
        content_fields=content_fields,
        category_id=category_id,
        featured=featured,
        show_in_menu=show_in_menu,
    )

    content, is_subcategory = _process_form_data(form_data)

    # Route to appropriate creation function
    if is_subcategory:
        if category_id is None:
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                "Category ID is required for subcategory creation.",
            )
        # At this point, category_id is guaranteed to be str (not None)

        return await _create_subcategory(
            db,
            CreateSubcategoryData(
                category_id=category_id,
                content=content,
                featured=featured,
                show_in_menu=show_in_menu,
                file=file,
            ),
        )

    return await _create_category(
        db,
        CreateCategoryData(
            content=content,
            featured=featured,
            show_in_menu=show_in_menu,
            file=file,
        ),
    )


@router.get(
    "",
    summary="Integrated in Admin frontend at Categories/AddCategory page",
    description="Returns a list of all categories with their subcategories, optionally filtered by status.",
)
@exception_handler
async def get_all_categories(
    status_filter: Optional[bool] = Query(
        None,
        description="Filter by category status: true, false, or omit for all",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Load categories with subcategories
    stmt = select(Category).options(selectinload(Category.subcategories))

    if status_filter is not None:
        stmt = stmt.where(Category.category_status == status_filter)

    result = await db.execute(stmt)
    categories = result.scalars().unique().all()

    data = []

    for cat in categories:
        # Filter subcategories by status_filter
        if status_filter is not None:
            subcats = [
                s
                for s in cat.subcategories
                if s.subcategory_status == status_filter
            ]
        else:
            subcats = cat.subcategories

        data.append(
            {
                "category_id": cat.category_id,
                "category_name": cat.category_name.title(),
                "category_description": cat.category_description,
                "category_slug": cat.category_slug,
                "category_meta_title": cat.category_meta_title,
                "category_meta_description": cat.category_meta_description,
                "category_img_thumbnail": get_media_url(
                    cat.category_img_thumbnail
                ),
                "featured_category": cat.featured_category,
                "show_in_menu": cat.show_in_menu,
                "category_status": cat.category_status,
                "category_tstamp": (
                    cast(datetime, cat.category_tstamp).isoformat()
                    if cat.category_tstamp
                    else None
                ),
                "has_subcategories": len(subcats) > 0,
                "subcategory_count": len(subcats),
            }
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Categories fetched successfully",
        data=data,
    )


@router.get(
    "/analytics",
    summary="Not Integrated in any frontend",
    description="Returns aggregated statistics about categories and subcategories.",
)
@exception_handler
async def category_analytics(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Optimized Aggregation Query
    stats_query = await db.execute(
        select(
            func.count().label("total"),
            func.count(case((Category.category_status.is_(False), 1))).label(
                "active"
            ),
            func.count(case((Category.category_status.is_(True), 1))).label(
                "inactive"
            ),
            func.count(case((Category.featured_category.is_(True), 1))).label(
                "featured"
            ),
            func.count(case((Category.show_in_menu.is_(True), 1))).label(
                "show_in_menu"
            ),
            func.count(case((Category.show_in_menu.is_(False), 1))).label(
                "hidden_from_menu"
            ),
        )
    )
    stats = stats_query.first()

    # Subcategory Stats in One ORM Query
    result = await db.execute(
        select(Category).options(selectinload(Category.subcategories))
    )
    categories = result.scalars().all()

    total_subcategories = 0
    categories_with_subs = 0
    subcategory_distribution = []

    for category in categories:
        sub_count = len(category.subcategories)
        total_subcategories += sub_count
        if sub_count > 0:
            categories_with_subs += 1
        subcategory_distribution.append(
            {
                "category_name": category.category_name,
                "subcategory_count": sub_count,
            }
        )

    total_categories = getattr(stats, "total", 0) if stats else 0
    avg_subcategories_per_category = (
        total_subcategories / total_categories if total_categories else 0
    )

    top_categories_by_subs = sorted(
        subcategory_distribution,
        key=lambda x: x["subcategory_count"],
        reverse=True,
    )[:5]

    return api_response(
        status.HTTP_200_OK,
        "Category analytics fetched successfully",
        data={
            "totals": {
                "total_categories": getattr(stats, "total", 0),
                "active_categories": getattr(stats, "active", 0),
                "inactive_categories": getattr(stats, "inactive", 0),
                "featured_categories": getattr(stats, "featured", 0),
                "show_in_menu": getattr(stats, "show_in_menu", 0),
                "hidden_from_menu": getattr(stats, "hidden_from_menu", 0),
            },
            "subcategory_stats": {
                "total_subcategories": total_subcategories,
                "categories_with_subcategories": (categories_with_subs),
                "avg_subcategories_per_category": round(
                    avg_subcategories_per_category, 2
                ),
                "top_categories_by_subcategory_count": top_categories_by_subs,
            },
        },
    )


@router.get(
    "/list",
    response_model=List[CategoryOut],
    summary=(
        "Integrated in Admin Categories, Events/BasicInfo pages, Organizer Events/BasicInfo page "
        "and Application ZunstanStore/Categories Store frontend"
    ),
    description=(
        "Returns all categories and their subcategories, "
        "optionally filtered by category status."
    ),
)
@exception_handler
async def get_categories_and_subcategories_by_status(
    status_value: Optional[bool] = Query(
        None, description="Filter by category status: true / false / none"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    stmt = select(Category).options(selectinload(Category.subcategories))

    # Apply category status filter if provided
    if status_value is not None:
        stmt = stmt.where(Category.category_status.is_(status_value))

    result = await db.execute(stmt)
    categories = result.scalars().unique().all()

    for category in categories:
        category.category_name = category.category_name.title()
        category.category_img_thumbnail = get_media_url(
            category.category_img_thumbnail
        )

        if category.category_status:
            # If category is active, override subcategory status to True in response
            for sub in category.subcategories:
                sub.subcategory_status = True

        for sub in category.subcategories:
            sub.subcategory_name = sub.subcategory_name.title()
            sub.subcategory_img_thumbnail = get_media_url(
                sub.subcategory_img_thumbnail
            )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Categories fetched successfully",
        data=[CategoryOut.model_validate(cat) for cat in categories],
    )


@router.get(
    "/count",
    summary="Not Integrated in any frontend",
    description="Returns total, active, inactive counts of categories and subcategories.",
)
@exception_handler
async def total_categories_count(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # Category aggregation
    category_query = await db.execute(
        select(
            func.count().label("total"),
            func.count(case((Category.category_status.is_(False), 1))).label(
                "active"
            ),
            func.count(case((Category.category_status.is_(True), 1))).label(
                "inactive"
            ),
        )
    )
    category_stats = category_query.first()

    # Subcategory aggregation
    subcategory_query = await db.execute(
        select(
            func.count().label("total"),
            func.count(
                case((SubCategory.subcategory_status.is_(False), 1))
            ).label("active"),
            func.count(
                case((SubCategory.subcategory_status.is_(True), 1))
            ).label("inactive"),
        )
    )
    subcategory_stats = subcategory_query.first()

    # Load category names with subcategory stats
    result = await db.execute(
        select(Category).options(selectinload(Category.subcategories))
    )
    categories = result.scalars().all()

    category_distribution = []
    for cat in categories:
        total = len(cat.subcategories)
        active = sum(
            1 for s in cat.subcategories if s.subcategory_status is False
        )
        inactive = sum(
            1 for s in cat.subcategories if s.subcategory_status is True
        )

        category_distribution.append(
            {
                "category_name": cat.category_name,
                "total_subcategories": total,
                "active_subcategories": active,
                "inactive_subcategories": inactive,
            }
        )

    return api_response(
        status.HTTP_200_OK,
        "Category total count fetched successfully",
        data={
            "totals": {
                "total_categories": getattr(category_stats, "total", 0),
                "active_categories": getattr(category_stats, "active", 0),
                "inactive_categories": getattr(category_stats, "inactive", 0),
            },
            "subcategory_stats": {
                "total_subcategories": getattr(subcategory_stats, "total", 0),
                "active_subcategories": getattr(subcategory_stats, "active", 0),
                "inactive_subcategories": getattr(
                    subcategory_stats, "inactive", 0
                ),
                "category_distribution": category_distribution,
            },
        },
    )


@router.get(
    "/list/event-categories",
    response_model=List[CategoryOut],
    summary=(
        "Integrated in Application ZunstanStore/Categories Store frontend"
    ),
    description=(
        "Returns all categories and their subcategories, "
        "optionally filtered by category status. "
        "Also ensures categories have at least one active event with valid upcoming event_dates."
    ),
)
@exception_handler
async def get_categories_and_subcategories_by_status_event_categories(
    status_value: Optional[bool] = Query(
        None, description="Filter by category status: true / false / none"
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:

    current_date = date.today()

    # Base query: categories joined with events
    stmt = (
        select(Category)
        .options(selectinload(Category.subcategories))
        .join(NewEvent, NewEvent.category_id == Category.category_id)
        .where(
            and_(
                NewEvent.event_status == EventStatus.ACTIVE,
                any_(NewEvent.event_dates) > current_date,
            )
        )
        .distinct()
    )

    # Apply category status filter if provided
    if status_value is not None:
        stmt = stmt.where(Category.category_status.is_(status_value))

    result = await db.execute(stmt)
    categories = result.scalars().unique().all()

    # Process categories for response
    for category in categories:
        category.category_name = category.category_name.title()
        category.category_img_thumbnail = get_media_url(
            category.category_img_thumbnail
        )

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Categories with upcoming active events fetched successfully",
        data=[CategoryOutDropDown.model_validate(cat) for cat in categories],
    )
