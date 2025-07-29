import re
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import BusinessProfile
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler

router = APIRouter()


# Schema for store name availability check
class StoreNameCheckResponse(BaseModel):
    status_code: int
    message: str


class StoreNameAvailabilityResponse(BaseModel):
    available: bool
    message: str
    suggestions: Optional[List[str]] = None


def validate_store_name(store_name: str) -> str:
    """Validate and clean store name according to business rules."""
    if not store_name or not store_name.strip():
        raise ValueError("Store name cannot be empty")

    # Clean the store name - remove extra spaces
    cleaned_name = " ".join(store_name.strip().split())

    # Check minimum length after cleaning
    if len(cleaned_name) < 2:
        raise ValueError("Store name must be at least 2 characters long")

    # Check maximum length
    if len(cleaned_name) > 50:
        raise ValueError("Store name cannot exceed 50 characters")

    # Check for valid characters (letters, numbers, spaces, hyphens, underscores)
    if not re.match(r"^[a-zA-Z0-9\s\-_]+$", cleaned_name):
        raise ValueError(
            "Store name can only contain letters, numbers, spaces, hyphens, and underscores"
        )

    # Check if it starts or ends with special characters
    if cleaned_name.startswith(("-", "_")) or cleaned_name.endswith(("-", "_")):
        raise ValueError(
            "Store name cannot start or end with hyphens or underscores"
        )

    # Check for reserved names
    reserved_names = {
        "admin",
        "api",
        "www",
        "mail",
        "support",
        "help",
        "info",
        "test",
        "demo",
        "shop",
        "store",
        "events2go",
        "e2g",
    }
    if cleaned_name.lower() in reserved_names:
        raise ValueError(
            "Store name contains reserved words. Please choose a different name"
        )

    return cleaned_name


async def generate_store_name_suggestions(
    original_name: str, db: AsyncSession, max_suggestions: int = 5
) -> List[str]:
    """Generate alternative store name suggestions when the original is taken."""
    suggestions = []
    base_name = original_name.strip()

    # Generate different variations
    variations = [
        f"{base_name} Shop",
        f"{base_name} Store",
        f"The {base_name}",
        f"{base_name} Co",
        f"{base_name} Hub",
        f"New {base_name}",
        f"{base_name} Plus",
        f"{base_name} Pro",
        f"{base_name} Express",
        f"{base_name} Central",
    ]

    # Add numbered variations
    for i in range(2, 10):
        variations.append(f"{base_name} {i}")

    # Check each variation for availability
    for variation in variations:
        if len(suggestions) >= max_suggestions:
            break

        try:
            # Validate the suggestion first
            cleaned_variation = validate_store_name(variation)

            # Check if this variation is available
            stmt = select(BusinessProfile).where(
                BusinessProfile.store_name.ilike(cleaned_variation)
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                suggestions.append(cleaned_variation)
        except ValueError:
            # Skip invalid suggestions
            continue

    return suggestions


@router.get("/check-store-name/{store_name}")
@exception_handler
async def check_store_name_availability_get(
    store_name: str,
    db: AsyncSession = Depends(get_db),
) -> StoreNameAvailabilityResponse:
    """
    Check if store name is available for use (GET endpoint).

    This endpoint validates the store name format and checks if it's already
    taken by another business profile. If unavailable, it provides suggestions.

    Args:
        store_name: Store name to check (URL path parameter)
        db: Database session dependency

    Returns:
        StoreNameAvailabilityResponse: Contains availability status, message, and suggestions

    Raises:
        HTTPException: For validation errors or server issues
    """
    # Validate and clean the store name
    cleaned_store_name = validate_store_name(store_name)

    # Check if store name already exists (case-insensitive)
    stmt = select(BusinessProfile).where(
        BusinessProfile.store_name.ilike(cleaned_store_name)
    )
    result = await db.execute(stmt)
    existing_store = result.scalar_one_or_none()

    if existing_store:
        # Generate suggestions for alternative names
        suggestions = await generate_store_name_suggestions(
            cleaned_store_name, db
        )

        return StoreNameAvailabilityResponse(
            available=False,
            message=f"Store name '{cleaned_store_name}' is already taken",
            suggestions=suggestions if suggestions else None,
        )

    return StoreNameAvailabilityResponse(
        available=True,
        message=f"Store name '{cleaned_store_name}' is available",
    )
