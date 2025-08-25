from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from category_service.schemas.custom_sub_category import (
    CustomSubCategoryOut,
)
from category_service.services.custom_sub_category import (
    get_all_custom_subcategories,
    get_custom_subcategory,
)
from shared.core.api_response import api_response
from shared.db.models.custom_sub_category import CustomSubCategory
from shared.db.models.new_events import NewEvent
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


# @router.post("/", response_model=CustomSubCategoryOut)
# async def create_item(obj_in: CustomSubCategoryCreate, db: AsyncSession = Depends(get_db)):
#     return await create_custom_subcategory(db, obj_in)


@router.get("/", response_model=List[CustomSubCategoryOut])
@exception_handler
async def get_all(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    custom_subcategories_data = await get_all_custom_subcategories(
        db, skip=skip, limit=limit
    )
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Custom subcategories retrieved successfully",
        data=custom_subcategories_data,
    )


# @router.put("/{custom_subcategory_id}", response_model=CustomSubCategoryOut)
# async def update_item(
#     custom_subcategory_id: str,
#     obj_in: CustomSubCategoryUpdate,
#     db: AsyncSession = Depends(get_db),
# ):
#     return await update_custom_subcategory(db, custom_subcategory_id, obj_in)


@router.get("/summary")
@exception_handler
async def custom_subcategories_summary(
    db: AsyncSession = Depends(get_db),
    days: int = Query(
        30, ge=1, le=365, description="Optional time window for trending data"
    ),
    top_limit: int = Query(
        10, ge=1, le=50, description="Top N results for organizers/names"
    ),
) -> JSONResponse:
    """
    Unified analytics for custom subcategories:
    - Total rows
    - Active vs inactive
    - Unique subcategory names
    - Duplicate names with frequency
    - Top organizers creating subcategories
    - Trending names (within last N days)
    """

    analytics: Dict[str, Any] = {}

    # 1. Total rows + active/inactive count
    stmt_status = select(
        func.count(CustomSubCategory.custom_subcategory_id).label("total"),
        func.sum(
            case(
                (CustomSubCategory.custom_subcategory_status == True, 1),
                else_=0,
            )
        ).label("inactive"),
        func.sum(
            case(
                (CustomSubCategory.custom_subcategory_status == False, 1),
                else_=0,
            )
        ).label("active"),
    )
    res = await db.execute(stmt_status)
    row = res.first()
    if row:
        analytics["overview"] = {
            "total": row.total or 0,
            "active": row.active or 0,
            "inactive": row.inactive or 0,
        }
    else:
        analytics["overview"] = {"total": 0, "active": 0, "inactive": 0}

    # 2. Unique subcategory names & duplicate frequency
    stmt_names = (
        select(
            CustomSubCategory.custom_subcategory_name,
            func.count(CustomSubCategory.custom_subcategory_id).label(
                "usage_count"
            ),
            func.count(func.distinct(NewEvent.organizer_id)).label(
                "organizer_count"
            ),
        )
        .join(
            NewEvent,
            CustomSubCategory.event_ref_id == NewEvent.event_id,
            isouter=True,
        )
        .group_by(CustomSubCategory.custom_subcategory_name)
        .order_by(desc(func.count(CustomSubCategory.custom_subcategory_id)))
    )
    res = await db.execute(stmt_names)
    all_names = res.all()
    analytics["name_stats"] = {
        "unique_names": len(all_names),
        "duplicates": [
            {
                "name": r.custom_subcategory_name,
                "usage_count": r.usage_count,
                "organizer_count": r.organizer_count,
            }
            for r in all_names
            if r.usage_count > 1
        ][:top_limit],
    }

    # 3. Top organizers (who create more frequently)
    stmt_orgs = (
        select(
            NewEvent.organizer_id,
            func.count(CustomSubCategory.custom_subcategory_id).label(
                "total_created"
            ),
            func.count(
                func.distinct(CustomSubCategory.custom_subcategory_name)
            ).label("unique_names"),
        )
        .join(NewEvent, CustomSubCategory.event_ref_id == NewEvent.event_id)
        .group_by(NewEvent.organizer_id)
        .order_by(desc(func.count(CustomSubCategory.custom_subcategory_id)))
        .limit(top_limit)
    )
    res = await db.execute(stmt_orgs)
    analytics["top_organizers"] = [
        {
            "organizer_id": r.organizer_id,
            "total_created": r.total_created,
            "unique_names": r.unique_names,
        }
        for r in res.all()
    ]

    # 4. Trending names (last N days)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    stmt_trending = (
        select(
            CustomSubCategory.custom_subcategory_name,
            func.count(CustomSubCategory.custom_subcategory_id).label(
                "usage_count"
            ),
            func.count(func.distinct(NewEvent.organizer_id)).label(
                "unique_organizers"
            ),
        )
        .join(
            NewEvent,
            CustomSubCategory.event_ref_id == NewEvent.event_id,
            isouter=True,
        )
        .where(CustomSubCategory.custom_subcategory_tstamp >= cutoff_date)
        .group_by(CustomSubCategory.custom_subcategory_name)
        .order_by(desc(func.count(CustomSubCategory.custom_subcategory_id)))
        .limit(top_limit)
    )
    res = await db.execute(stmt_trending)
    analytics["trending_names"] = [
        {
            "name": r.custom_subcategory_name,
            "usage_count": r.usage_count,
            "unique_organizers": r.unique_organizers,
        }
        for r in res.all()
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Custom subcategory analytics retrieved successfully",
        data=analytics,
    )


@router.get("/{custom_subcategory_id}", response_model=CustomSubCategoryOut)
@exception_handler
async def get_item(
    custom_subcategory_id: str, db: AsyncSession = Depends(get_db)
):
    custm_sub_category = await get_custom_subcategory(db, custom_subcategory_id)
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Custom subcategory retrieved successfully",
        data=custm_sub_category,
    )
