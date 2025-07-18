from fastapi import APIRouter

from category_service.api.v1.endpoints import (
    categories,
    categories_by_id,
    categories_by_slug,
    category_items,
    sub_categories_by_id,
    sub_categories_by_slug,
    subcategories,
)

category_router = APIRouter(prefix="/api/v1")

# Category Endpoints
category_router.include_router(
    categories.router, prefix="/categories", tags=["Categories"]
)
category_router.include_router(
    categories_by_id.router, prefix="/categories", tags=["Categories by ID"]
)
category_router.include_router(
    categories_by_slug.router, prefix="/categories", tags=["Categories by Slug"]
)

# Subcategory Endpoints
category_router.include_router(
    subcategories.router, prefix="/subcategories", tags=["Subcategories"]
)
category_router.include_router(
    sub_categories_by_id.router,
    prefix="/subcategories",
    tags=["Subcategories by ID"],
)
category_router.include_router(
    sub_categories_by_slug.router,
    prefix="/subcategories",
    tags=["Subcategories by Slug"],
)

category_router.include_router(
    category_items.router,
    prefix="/category-items",
    tags=["categories or subcategories by id"],
)
