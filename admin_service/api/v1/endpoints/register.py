from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.schemas.register import (
    AdminRegisterRequest,
    AdminRegisterResponse,
)
from admin_service.services.response_builders import config_not_found_response
from admin_service.services.user_service import get_config_or_404
from admin_service.services.user_validation import (
    validate_role,
    validate_superadmin_uniqueness,
    validate_unique_user,
)
from shared.core.api_response import api_response
from shared.db.models import AdminUser, Role
from shared.db.sessions.database import get_db
from shared.utils.email import send_welcome_email
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import get_media_url
from shared.utils.id_generators import generate_lower_uppercase

router = APIRouter()


@router.post(
    "/register",
    response_model=AdminRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@exception_handler
async def register_user(
    background_tasks: BackgroundTasks,
    user_data: AdminRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Register a new admin user.

    This endpoint creates a new admin user with the provided information.
    A welcome email with login credentials will be sent to the user's email address.

    Args:
        background_tasks: FastAPI background tasks handler
        user_data: User registration data including first_name, last_name,
            username, email, and role_id
        db: Database session

    Returns:
        JSONResponse: Response with user details and success message
    """
    # Check if user already exists
    unique_user_result = await validate_unique_user(
        db, user_data.username, user_data.email
    )
    if unique_user_result is not None:
        return unique_user_result

    # Validate role
    role_result = await validate_role(db, user_data.role_id)
    if not isinstance(role_result, Role):
        return role_result

    role = role_result

    # Check superadmin uniqueness
    superadmin_result = await validate_superadmin_uniqueness(db, role)
    if superadmin_result is not None:
        return superadmin_result

    # Get system configuration
    config_result = await get_config_or_404(db)
    if not config_result:
        return config_not_found_response()

    config = config_result

    # Create new user
    user_id = generate_lower_uppercase(length=6)
    new_user = AdminUser(
        user_id=user_id,
        role_id=user_data.role_id,
        username=user_data.username.lower(),
        email=user_data.email.lower(),
        password_hash=config.default_password_hash,
        days_180_flag=config.global_180_day_flag,
    )

    # Add to database
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Send welcome email in background
    # Get logo URL, ensuring it's a string
    logo_url = get_media_url(config.logo_url or "")
    if logo_url is None:
        logo_url = ""  # Provide empty string if None

    background_tasks.add_task(
        send_welcome_email,
        email=user_data.email,
        username=user_data.username,
        password=config.default_password,
        logo_url=logo_url,
    )

    # Return success response
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="User registered successfully. Welcome email sent in background.",
        data=AdminRegisterResponse(
            user_id=user_id,
            email=user_data.email,
            username=user_data.username,
        ),
    )
