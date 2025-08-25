from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from category_service.schemas.custom_sub_category import (
    CustomSubCategoryCreate,
    CustomSubCategoryStatusUpdate,
    CustomSubCategoryUpdate,
)
from shared.db.models.categories import Category, SubCategory
from shared.db.models.custom_sub_category import CustomSubCategory
from shared.db.models.new_events import NewEvent
from shared.utils.id_generators import generate_digits_lowercase


async def create_custom_subcategory(
    db: AsyncSession, obj_in: CustomSubCategoryCreate
):
    # # 1. Check if category exists
    # category_result = await db.execute(
    #     select(Category).where(Category.category_id == obj_in.category_ref_id)
    # )
    # category = category_result.scalar_one_or_none()
    # if not category:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=f"Category with id '{obj_in.category_ref_id}' does not exist.",
    #     )

    # # 2. Check if subcategory exists (if provided)
    # if obj_in.subcategory_ref_id:
    #     subcategory_result = await db.execute(
    #         select(SubCategory).where(SubCategory.subcategory_id == obj_in.subcategory_ref_id)
    #     )
    #     subcategory = subcategory_result.scalar_one_or_none()
    #     if not subcategory:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail=f"SubCategory with id '{obj_in.subcategory_ref_id}' does not exist.",
    #         )

    # # 3. Check if event exists (if provided)
    # if obj_in.event_ref_id:
    #     event_result = await db.execute(
    #         select(NewEvent).where(NewEvent.event_id == obj_in.event_ref_id)
    #     )
    #     event = event_result.scalar_one_or_none()
    #     if not event:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail=f"Event with id '{obj_in.event_ref_id}' does not exist.",
    #         )

    # 4. Prepare object (force uppercase name)
    db_obj = CustomSubCategory(
        custom_subcategory_id=generate_digits_lowercase(6),
        category_ref_id=obj_in.category_ref_id,
        subcategory_ref_id=obj_in.subcategory_ref_id,
        event_ref_id=obj_in.event_ref_id,
        custom_subcategory_name=obj_in.custom_subcategory_name.upper(),
    )

    # 5. Save
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_custom_subcategory(db: AsyncSession, custom_subcategory_id: str):
    """Get a single custom subcategory by ID, with 404 handling."""
    result = await db.execute(
        select(CustomSubCategory).where(
            CustomSubCategory.custom_subcategory_id == custom_subcategory_id
        )
    )
    db_obj = result.scalar_one_or_none()
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CustomSubCategory with id '{custom_subcategory_id}' not found",
        )
    return db_obj


async def get_all_custom_subcategories(
    db: AsyncSession, skip: int = 0, limit: int = 100
):
    """Get all custom subcategories with pagination."""
    result = await db.execute(
        select(CustomSubCategory).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def update_custom_subcategory(
    db: AsyncSession,
    custom_subcategory_id: str,
    obj_in: CustomSubCategoryUpdate,
):
    """Update an existing custom subcategory with validation and uppercase conversion."""
    db_obj = await get_custom_subcategory(db, custom_subcategory_id)

    update_data = obj_in.model_dump(exclude_unset=True)

    # Validate category exists (if updating)
    if "category_ref_id" in update_data:
        category_result = await db.execute(
            select(Category).where(
                Category.category_id == update_data["category_ref_id"]
            )
        )
        if not category_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with id '{update_data['category_ref_id']}' does not exist.",
            )

    # Validate subcategory exists (if updating)
    if (
        "subcategory_ref_id" in update_data
        and update_data["subcategory_ref_id"]
    ):
        subcategory_result = await db.execute(
            select(SubCategory).where(
                SubCategory.subcategory_id == update_data["subcategory_ref_id"]
            )
        )
        if not subcategory_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SubCategory with id '{update_data['subcategory_ref_id']}' does not exist.",
            )

    # Validate event exists (if updating)
    if "event_ref_id" in update_data and update_data["event_ref_id"]:
        event_result = await db.execute(
            select(NewEvent).where(
                NewEvent.event_id == update_data["event_ref_id"]
            )
        )
        if not event_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Event with id '{update_data['event_ref_id']}' does not exist.",
            )

    # Ensure uppercase name if updated
    if (
        "custom_subcategory_name" in update_data
        and update_data["custom_subcategory_name"]
    ):
        update_data["custom_subcategory_name"] = update_data[
            "custom_subcategory_name"
        ].upper()

    # Apply updates
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update_custom_subcategory_status(
    db: AsyncSession,
    custom_subcategory_id: str,
    obj_in: CustomSubCategoryStatusUpdate,
):
    """Patch the status of a custom subcategory only."""
    db_obj = await get_custom_subcategory(db, custom_subcategory_id)

    db_obj.custom_subcategory_status = obj_in.custom_subcategory_status

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj
