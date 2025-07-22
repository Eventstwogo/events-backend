import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import Category, SubCategory
from shared.utils.security_validators import (
    contains_sql_injection,
    contains_xss,
    sanitize_input,
)
from shared.utils.validators import (
    is_single_reserved_word,
    is_valid_cat_subcat_name,
    normalize_whitespace,
    validate_length,
)


@dataclass
class CategoryData:
    """Data class for category validation parameters."""

    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    is_subcategory: bool = False


@dataclass
class ConflictCheckData:
    """Data class for conflict checking parameters."""

    name: str
    slug: str
    description: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    category_id_to_exclude: Optional[str] = None


@dataclass
class SubcategoryConflictData:
    """Data class for subcategory conflict checking parameters."""

    name: str
    slug: str
    description: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


def _validate_name(name: str, is_subcategory: bool) -> str:
    """Validate and sanitize category/subcategory name."""
    sanitized = sanitize_input(name)
    if not isinstance(sanitized, str):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid input detected."
        )
    name = sanitized
    name = normalize_whitespace(name)
    if is_subcategory:
        if not is_valid_cat_subcat_name(name):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Invalid subcategory name."
            )
        error_msg = (
            "Python reserved words are not allowed in subcategory names."
        )
    else:
        if not is_valid_cat_subcat_name(name):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Invalid category name."
            )
        error_msg = "Python reserved words are not allowed in category names."
    if is_single_reserved_word(name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_msg)
    return name


def _validate_slug(slug: str) -> str:
    """Validate and sanitize slug."""
    sanitized = sanitize_input(slug)
    if not isinstance(sanitized, str):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid input detected."
        )
    slug = sanitized
    if contains_xss(slug) or contains_sql_injection(slug):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid slug.")
    if is_single_reserved_word(slug):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Python reserved words are not allowed in slugs.",
        )
    return slug


def _validate_text_field(text: str, field_name: str, max_length: int) -> str:
    """
    Validate and sanitize text fields such as description, meta_title, meta_description.

    - Allows letters, numbers, spaces, and common punctuation
    - Disallows HTML tags, Python keywords, and dangerous symbols
    - Enforces length and formatting rules
    """
    sanitized = sanitize_input(text)
    if not isinstance(sanitized, str):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid input detected."
        )

    text = normalize_whitespace(sanitized)

    # Normalize unicode for international characters (e.g., é, ñ)
    text = unicodedata.normalize("NFC", text)

    # Disallow HTML tags
    if re.search(r"<[^>]+>", text):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} contains disallowed HTML tags.",
        )

    # Accept realistic metadata content (letters, numbers, basic punctuation, accents)
    if not re.fullmatch(r"[A-Za-z0-9À-ÿ\s.,:;!?()&%#@+\-\"'\/–—|]*", text):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} contains unsupported characters.",
        )

    # Disallow single Python reserved words
    if is_single_reserved_word(text):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Python reserved words are not allowed in {field_name.lower()}s.",
        )

    # Length validation
    if not validate_length(text, 0, max_length):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} too long. Max {max_length} characters allowed.",
        )

    return text


def validate_category_data(
    data: CategoryData,
) -> tuple[str, str, Optional[str], Optional[str], Optional[str]]:
    """
    Validate and normalize category data.
    Ensures valid name, slug, description, and metadata fields.
    """
    # Required fields
    name = _validate_name(data.name, data.is_subcategory)
    slug = _validate_slug(data.slug or data.name)

    # Optional metadata
    description = (
        _validate_text_field(data.description, "Description", 500)
        if data.description
        else None
    )
    meta_title = (
        _validate_text_field(data.meta_title, "Meta title", 70)
        if data.meta_title
        else None
    )
    meta_description = (
        _validate_text_field(data.meta_description, "Meta description", 160)
        if data.meta_description
        else None
    )

    # Optional: log SEO warnings (not raise)
    if meta_title and len(meta_title) > 60:
        print("SEO tip: Meta title exceeds 60 characters.")
    if meta_description and len(meta_description) > 150:
        print("SEO tip: Meta description exceeds 150 characters.")

    return name.upper(), slug.lower(), description, meta_title, meta_description


# === Category Checking ===
async def check_category_name_exists(db: AsyncSession, name: str) -> bool:
    result = await db.execute(
        select(Category).where(
            func.lower(Category.category_name) == name.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Category name cannot be same as an existing category name.",
        )
    return False


async def check_category_slug_exists(db: AsyncSession, slug: str) -> bool:
    result = await db.execute(
        select(Category).where(
            func.lower(Category.category_slug) == slug.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Category slug cannot be same as an existing category slug.",
        )
    return False


async def check_category_description_exists(
    db: AsyncSession, description: str
) -> bool:
    result = await db.execute(
        select(Category).where(
            func.lower(Category.category_description)
            == description.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Category description cannot be same as an existing category description.",
        )
    return False


async def check_category_meta_title_exists(
    db: AsyncSession, meta_title: str
) -> bool:
    result = await db.execute(
        select(Category).where(
            func.lower(Category.category_meta_title)
            == meta_title.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Category meta title cannot be same as an existing category meta title.",
        )
    return False


async def check_category_meta_description_exists(
    db: AsyncSession, meta_description: str
) -> bool:
    result = await db.execute(
        select(Category).where(
            func.lower(Category.category_meta_description)
            == meta_description.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                "Category meta description cannot be same as an "
                "existing category meta description."
            ),
        )
    return False


# === Subcategory Checking ===
async def check_subcategory_name_exists(db: AsyncSession, name: str) -> bool:
    result = await db.execute(
        select(SubCategory).where(
            func.lower(SubCategory.subcategory_name) == name.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Subcategory name cannot be same as an existing subcategory name.",
        )
    return False


async def check_subcategory_slug_exists(db: AsyncSession, slug: str) -> bool:
    result = await db.execute(
        select(SubCategory).where(
            func.lower(SubCategory.subcategory_slug) == slug.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Subcategory slug cannot be same as an existing subcategory slug.",
        )
    return False


async def check_subcategory_description_exists(
    db: AsyncSession, description: str
) -> bool:
    result = await db.execute(
        select(SubCategory).where(
            func.lower(SubCategory.subcategory_description)
            == description.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Subcategory description cannot be same as an existing subcategory description.",
        )
    return False


async def check_subcategory_meta_title_exists(
    db: AsyncSession, meta_title: str
) -> bool:
    result = await db.execute(
        select(SubCategory).where(
            func.lower(SubCategory.subcategory_meta_title)
            == meta_title.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Subcategory meta title cannot be same as an existing subcategory meta title.",
        )
    return False


async def check_subcategory_meta_description_exists(
    db: AsyncSession, meta_description: str
) -> bool:
    result = await db.execute(
        select(SubCategory).where(
            func.lower(SubCategory.subcategory_meta_description)
            == meta_description.strip().lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                "Subcategory meta description cannot be same as"
                "an existing subcategory meta description."
            ),
        )
    return False


def _check_category_field_conflict(
    category: Category, field_name: str, value: Optional[str], field_type: str
) -> Optional[str]:
    """Check if a specific field conflicts with existing category."""
    if not value:
        return None
    category_field = getattr(category, f"category_{field_name}", None)
    if (
        category_field
        and category_field.strip().lower() == value.strip().lower()
    ):
        return f"Category {field_type} already exists."
    return None


def _check_subcategory_field_conflict(
    subcategory: SubCategory,
    field_name: str,
    value: Optional[str],
    field_type: str,
) -> Optional[str]:
    """Check if a specific field conflicts with existing subcategory."""
    if not value:
        return None
    subcategory_field = getattr(subcategory, f"subcategory_{field_name}", None)
    if (
        subcategory_field
        and subcategory_field.strip().lower() == value.strip().lower()
    ):
        return (
            f"Category {field_type} cannot be same as an existing "
            f"subcategory {field_type}."
        )
    return None


async def validate_category_conflicts(
    db: AsyncSession, data: ConflictCheckData
) -> str | None:
    """Validate category conflicts with reduced complexity."""
    # Check against existing categories
    result = await db.execute(select(Category))
    categories = result.scalars().all()

    for cat in categories:
        # Skip the current category (important for update scenarios)
        if data.category_id_to_exclude and str(cat.category_id) == str(
            data.category_id_to_exclude
        ):
            continue

        # Check each field for conflicts
        conflicts = [
            _check_category_field_conflict(cat, "name", data.name, "name"),
            _check_category_field_conflict(cat, "slug", data.slug, "slug"),
            _check_category_field_conflict(
                cat, "description", data.description, "description"
            ),
            _check_category_field_conflict(
                cat, "meta_title", data.meta_title, "meta title"
            ),
            _check_category_field_conflict(
                cat,
                "meta_description",
                data.meta_description,
                "meta description",
            ),
        ]
        for conflict in conflicts:
            if conflict:
                return conflict

    # Check against subcategories
    result = await db.execute(select(SubCategory))
    subcategories = result.scalars().all()

    for sub in subcategories:
        conflicts = [
            _check_subcategory_field_conflict(sub, "name", data.name, "name"),
            _check_subcategory_field_conflict(sub, "slug", data.slug, "slug"),
            _check_subcategory_field_conflict(
                sub, "description", data.description, "description"
            ),
            _check_subcategory_field_conflict(
                sub, "meta_title", data.meta_title, "meta title"
            ),
            _check_subcategory_field_conflict(
                sub,
                "meta_description",
                data.meta_description,
                "meta description",
            ),
        ]
        for conflict in conflicts:
            if conflict:
                return conflict
    return None


def _check_category_subcategory_conflict(
    category: Category, field_name: str, value: Optional[str], field_type: str
) -> Optional[str]:
    """Check if subcategory field conflicts with existing category."""
    if not value:
        return None
    category_field = getattr(category, f"category_{field_name}", None)
    if category_field:
        # Normalize both values by replacing underscores with spaces and comparing in lowercase
        normalized_category = category_field.strip().lower().replace("_", " ")
        normalized_value = value.strip().lower().replace("_", " ")
        if normalized_category == normalized_value:
            return (
                f"Subcategory {field_type} cannot be same as an existing "
                f"category {field_type}."
            )
    return None


async def validate_subcategory_conflicts(
    db: AsyncSession, data: SubcategoryConflictData
) -> str | None:
    """Validate subcategory conflicts with reduced complexity."""
    # Check against existing categories
    result = await db.execute(select(Category))
    categories = result.scalars().all()
    for cat in categories:
        conflicts = [
            _check_category_subcategory_conflict(
                cat, "name", data.name, "name"
            ),
            _check_category_subcategory_conflict(
                cat, "slug", data.slug, "slug"
            ),
            _check_category_subcategory_conflict(
                cat, "description", data.description, "description"
            ),
            _check_category_subcategory_conflict(
                cat, "meta_title", data.meta_title, "meta title"
            ),
            _check_category_subcategory_conflict(
                cat,
                "meta_description",
                data.meta_description,
                "meta description",
            ),
        ]
        for conflict in conflicts:
            if conflict:
                return conflict
    # Check against existing subcategories using existing functions
    return await _check_subcategory_existence(db, data)


async def _check_subcategory_existence(
    db: AsyncSession, data: SubcategoryConflictData
) -> str | None:
    """Helper function to check subcategory existence and reduce branches."""
    try:
        await check_subcategory_name_exists(db, data.name)
        await check_subcategory_slug_exists(db, data.slug)
        if data.description:
            await check_subcategory_description_exists(db, data.description)
        if data.meta_title:
            await check_subcategory_meta_title_exists(db, data.meta_title)
        if data.meta_description:
            await check_subcategory_meta_description_exists(
                db, data.meta_description
            )
    except HTTPException:
        # These functions raise HTTPException on conflict, so we catch and return None
        return None

    return None


def _validate_subcategory_name(name: str) -> None:
    """Validate subcategory name."""
    if not is_valid_cat_subcat_name(name):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid subcategory name."
        )
    if is_single_reserved_word(name):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Python reserved words are not allowed in subcategory names.",
        )


def _validate_subcategory_slug(slug: str) -> None:
    """Validate subcategory slug."""
    if contains_xss(slug) or contains_sql_injection(slug):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Invalid slug provided."
        )
    if is_single_reserved_word(slug):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Python reserved words are not allowed in slugs.",
        )


def _validate_subcategory_optional_field(
    field_value: str, field_name: str, max_length: int
) -> None:
    """Validate optional subcategory fields."""
    if not field_value:
        return
    if not validate_length(field_value, 0, max_length):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} too long. Max {max_length} characters.",
        )
    if not re.fullmatch(r"[A-Za-z\s]+", field_value):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must contain only letters and spaces.",
        )
    if is_single_reserved_word(field_value):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Python reserved words are not allowed in {field_name.lower()}s.",
        )


def _extract_subcategory_inputs(
    data: Optional[SubcategoryConflictData],
    name: Optional[str],
    slug: Optional[str],
    description: Optional[str],
    meta_title: Optional[str],
    meta_description: Optional[str],
) -> tuple[
    Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]
]:
    """Extract and return subcategory inputs from either dataclass or keyword args."""
    if data is not None:
        return (
            data.name,
            data.slug,
            data.description,
            data.meta_title,
            data.meta_description,
        )
    return name, slug, description, meta_title, meta_description


def _clean_subcategory_inputs(
    raw_name: Optional[str],
    raw_slug: Optional[str],
    raw_description: Optional[str],
    raw_meta_title: Optional[str],
    raw_meta_description: Optional[str],
) -> tuple[str, str, str, str, str]:
    """Clean and sanitize subcategory inputs."""
    if not raw_name or not raw_slug:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Name and slug are required."
        )

    def ensure_str(value, field_name):
        if not isinstance(value, str):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input detected for {field_name}.",
            )
        return value

    return (
        normalize_whitespace(ensure_str(sanitize_input(raw_name), "name")),
        normalize_whitespace(ensure_str(sanitize_input(raw_slug), "slug")),
        (
            normalize_whitespace(
                ensure_str(sanitize_input(raw_description), "description")
            )
            if raw_description
            else ""
        ),
        (
            normalize_whitespace(
                ensure_str(sanitize_input(raw_meta_title), "meta_title")
            )
            if raw_meta_title
            else ""
        ),
        (
            normalize_whitespace(
                ensure_str(
                    sanitize_input(raw_meta_description), "meta_description"
                )
            )
            if raw_meta_description
            else ""
        ),
    )


def validate_subcategory_fields(
    data: Optional[SubcategoryConflictData] = None,
    *,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    meta_title: Optional[str] = None,
    meta_description: Optional[str] = None,
) -> tuple[str, str, str, str, str]:
    """Sanitize and validate subcategory inputs."""
    # Extract inputs from either dataclass or keyword arguments
    inputs = _extract_subcategory_inputs(
        data, name, slug, description, meta_title, meta_description
    )

    # Clean and sanitize inputs
    clean_fields = _clean_subcategory_inputs(*inputs)

    # Validate each field using helper functions
    _validate_subcategory_name(clean_fields[0])
    _validate_subcategory_slug(clean_fields[1])
    _validate_subcategory_optional_field(clean_fields[2], "Description", 500)
    _validate_subcategory_optional_field(clean_fields[3], "Meta title", 70)
    _validate_subcategory_optional_field(
        clean_fields[4], "Meta description", 160
    )

    return clean_fields


def _extract_conflict_check_inputs(
    data: Optional[ConflictCheckData],
    name: Optional[str],
    slug: Optional[str],
    description: Optional[str],
    meta_title: Optional[str],
    meta_description: Optional[str],
    exclude_id: Optional[str],
) -> tuple[
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[str],
]:
    """Extract conflict check inputs from either dataclass or keyword args."""
    if data is not None:
        return (
            data.name,
            data.slug,
            data.description,
            data.meta_title,
            data.meta_description,
            data.category_id_to_exclude,
        )
    return name, slug, description, meta_title, meta_description, exclude_id


def _check_subcategory_conflicts_for_entity(
    entity: SubCategory,
    fields: tuple[
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
    ],
) -> Optional[str]:
    """Check conflicts for a single subcategory entity."""
    (
        check_name,
        check_slug,
        check_description,
        check_meta_title,
        check_meta_description,
    ) = fields

    conflicts = [
        _check_subcategory_field_conflict(entity, "name", check_name, "name"),
        _check_subcategory_field_conflict(entity, "slug", check_slug, "slug"),
        _check_subcategory_field_conflict(
            entity, "description", check_description, "description"
        ),
        _check_subcategory_field_conflict(
            entity, "meta_title", check_meta_title, "meta title"
        ),
        _check_subcategory_field_conflict(
            entity,
            "meta_description",
            check_meta_description,
            "meta description",
        ),
    ]

    for conflict in conflicts:
        if conflict:
            return conflict.replace(
                "cannot be same as an existing subcategory", "already exists"
            )
    return None


async def check_subcategory_conflicts(
    db: AsyncSession,
    data: Optional[ConflictCheckData] = None,
    *,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    meta_title: Optional[str] = None,
    meta_description: Optional[str] = None,
    subcategory_id_to_exclude: Optional[str] = None,
) -> Optional[str]:
    """Check if subcategory data conflicts with existing subcategories."""
    # Extract inputs from either dataclass or keyword arguments
    inputs = _extract_conflict_check_inputs(
        data,
        name,
        slug,
        description,
        meta_title,
        meta_description,
        subcategory_id_to_exclude,
    )
    check_fields = inputs[:5]  # First 5 are the field values
    exclude_id = inputs[5]  # Last one is the exclude ID

    result = await db.execute(select(SubCategory))
    subcategories = result.scalars().all()

    for sub in subcategories:
        if exclude_id and str(sub.subcategory_id) == str(exclude_id):
            continue

        conflict = _check_subcategory_conflicts_for_entity(sub, check_fields)
        if conflict:
            return conflict

    return None


def _check_category_conflicts_for_entity(
    entity: Category,
    fields: tuple[
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
    ],
) -> Optional[str]:
    """Check conflicts for a single category entity against subcategory fields."""
    (
        check_name,
        check_slug,
        check_description,
        check_meta_title,
        check_meta_description,
    ) = fields

    conflicts = [
        _check_category_subcategory_conflict(
            entity, "name", check_name, "name"
        ),
        _check_category_subcategory_conflict(
            entity, "slug", check_slug, "slug"
        ),
        _check_category_subcategory_conflict(
            entity, "description", check_description, "description"
        ),
        _check_category_subcategory_conflict(
            entity, "meta_title", check_meta_title, "meta title"
        ),
        _check_category_subcategory_conflict(
            entity,
            "meta_description",
            check_meta_description,
            "meta description",
        ),
    ]

    for conflict in conflicts:
        if conflict:
            return conflict
    return None


async def check_subcategory_vs_category_conflicts(
    db: AsyncSession,
    data: Optional[SubcategoryConflictData] = None,
    *,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    meta_title: Optional[str] = None,
    meta_description: Optional[str] = None,
) -> Optional[str]:
    """Ensure subcategory fields don't conflict with category fields."""
    # Extract inputs from either dataclass or keyword arguments
    check_fields = _extract_subcategory_inputs(
        data, name, slug, description, meta_title, meta_description
    )

    result = await db.execute(select(Category))
    categories = result.scalars().all()

    for cat in categories:
        conflict = _check_category_conflicts_for_entity(cat, check_fields)
        if conflict:
            return conflict

    return None
