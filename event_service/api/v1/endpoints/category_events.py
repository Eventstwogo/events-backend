from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from event_service.schemas.category_events import (
    CategoryEventsResponse,
    CategoryInfoResponse,
    CategoryWithEventsResponse,
    PaginatedEventResponse,
    PaginationMeta,
    SlugEventsResponse,
    SubCategoryInfoResponse,
    SubCategoryWithEventsResponse,
)
from event_service.services.category_events import (
    fetch_categories_with_latest_events,
    fetch_events_by_category_or_subcategory_slug,
    fetch_subcategories_with_latest_events,
)
from shared.core.api_response import api_response
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


@router.get(
    "/categories-with-events",
    status_code=status.HTTP_200_OK,
    response_model=CategoryEventsResponse,
)
@exception_handler
async def get_categories_with_latest_events(
    db: AsyncSession = Depends(get_db),
):
    """Get all categories and subcategories with their latest 5 events each"""

    # Fetch categories with their latest events
    categories_data = await fetch_categories_with_latest_events(db)

    # Fetch subcategories with their latest events
    subcategories_data = await fetch_subcategories_with_latest_events(db)

    # Convert to response format
    categories_response = [
        CategoryWithEventsResponse.model_validate(category_data)
        for category_data in categories_data
    ]

    subcategories_response = [
        SubCategoryWithEventsResponse.model_validate(subcategory_data)
        for subcategory_data in subcategories_data
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Categories and subcategories with latest events retrieved successfully",
        data={
            "categories": [cat.model_dump() for cat in categories_response],
            "subcategories": [
                subcat.model_dump() for subcat in subcategories_response
            ],
            "total_categories": len(categories_response),
            "total_subcategories": len(subcategories_response),
        },
    )


@router.get(
    "/events-by-slug/{slug}",
    status_code=status.HTTP_200_OK,
    response_model=SlugEventsResponse,
)
@exception_handler
async def get_events_by_category_or_subcategory_slug(
    slug: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(
        10, ge=1, le=100, description="Number of events per page (max 100)"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated events by category slug or subcategory slug in descending order of creation time

    This endpoint accepts either a category slug or subcategory slug and returns:
    - Paginated events in descending order of created_at timestamp
    - Information about the category or subcategory found
    - Pagination metadata

    Args:
        slug: Category slug or subcategory slug
        page: Page number (default: 1)
        limit: Number of events per page (default: 10, max: 100)
        db: Database session

    Returns:
        SlugEventsResponse with events, pagination info, and category/subcategory details

    Raises:
        HTTPException: If slug is not found or no events exist for the slug
    """

    # Fetch events and metadata
    events_data, total_count, category_data, subcategory_data = (
        await fetch_events_by_category_or_subcategory_slug(
            db=db,
            slug=slug,
            page=page,
            limit=limit,
        )
    )

    # Check if slug was found
    if not category_data and not subcategory_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No category or subcategory found with slug: {slug}",
        )

    # Check if any events exist
    if total_count == 0:
        slug_type = "category" if category_data else "subcategory"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No published events found for {slug_type}: {slug}",
        )

    # Calculate pagination metadata
    total_count = total_count or 0
    total_pages = (total_count + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_prev = page > 1

    # Convert events to response format
    events_response = [
        PaginatedEventResponse.model_validate(event_data)
        for event_data in events_data
    ]

    # Create pagination metadata
    pagination = PaginationMeta(
        current_page=page,
        per_page=limit,
        total_items=total_count,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
    )

    # Determine slug type and prepare response data
    if category_data:
        slug_type = "category"
        category_response = CategoryInfoResponse.model_validate(category_data)
        subcategory_response = None
    else:
        slug_type = "subcategory"
        category_response = None
        subcategory_response = SubCategoryInfoResponse.model_validate(
            subcategory_data
        )

    # Create response
    response_data = SlugEventsResponse(
        events=events_response,
        pagination=pagination,
        category=category_response,
        subcategory=subcategory_response,
        slug=slug,
        slug_type=slug_type,
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        message=f"Events for {slug_type} '{slug}' retrieved successfully",
        data=response_data.model_dump(),
    )
