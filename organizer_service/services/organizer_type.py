from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from organizer_service.schemas.organizer_type import OrganizerTypeCreateRequest
from shared.db.models.organizer import OrganizerType
from shared.utils.id_generators import generate_lower_uppercase


async def create_organizer_type_service(
    db: AsyncSession, request: OrganizerTypeCreateRequest
) -> OrganizerType:
    """Create a new organizer type if unique."""
    existing = await db.execute(
        select(OrganizerType).where(
            func.upper(OrganizerType.organizer_type) == request.organizer_type
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(
            f"Organizer type '{request.organizer_type}' already exists"
        )

    new_type = OrganizerType(
        type_id=generate_lower_uppercase(6),
        organizer_type=request.organizer_type,
    )
    db.add(new_type)
    await db.commit()
    await db.refresh(new_type)
    return new_type


async def list_organizer_types_service(db: AsyncSession):
    result = await db.execute(select(OrganizerType))
    return list(result.scalars().all())


async def list_active_organizer_types_service(db: AsyncSession):
    result = await db.execute(
        select(OrganizerType).where(OrganizerType.type_status == True)
    )
    return result.scalars().all()


async def update_organizer_type_service(
    db: AsyncSession, type_id: str, new_name: str
) -> OrganizerType:
    """Update organizer_type field for a given type_id."""
    result = await db.execute(
        select(OrganizerType).where(OrganizerType.type_id == type_id)
    )
    organizer_type = result.scalar_one_or_none()

    if not organizer_type:
        raise ValueError(f"Organizer type with id '{type_id}' not found")

    # Duplicate name check
    existing = await db.execute(
        select(OrganizerType).where(
            OrganizerType.organizer_type == new_name,
            OrganizerType.type_id != type_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Organizer type '{new_name}' already exists")

    organizer_type.organizer_type = new_name
    db.add(organizer_type)
    await db.commit()
    await db.refresh(organizer_type)
    return organizer_type


async def update_organizer_type_status_service(
    db: AsyncSession, type_id: str, new_status: bool
) -> OrganizerType:
    result = await db.execute(
        select(OrganizerType).where(OrganizerType.type_id == type_id)
    )
    organizer_type = result.scalar_one_or_none()

    if not organizer_type:
        raise ValueError(f"Organizer type with id '{type_id}' not found")

    organizer_type.type_status = new_status
    db.add(organizer_type)
    await db.commit()
    await db.refresh(organizer_type)
    return organizer_type
