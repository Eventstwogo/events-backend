from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from shared.core.api_response import api_response
from shared.core.config import settings
from shared.core.logging_config import get_logger
from shared.db.sessions.database import get_db
from user_service.schemas.password import (
    ForgotPassword,
    ResetPasswordWithToken,
    UserChangePassword,
)
from user_service.services.password_reset_service import (
    create_password_reset_record,
    generate_password_reset_token,
    mark_password_reset_used,
    validate_reset_token,
)
from user_service.services.response_builders import account_deactivated, user_not_found_response
from user_service.services.user_service import get_user_by_email, get_user_by_id
from user_service.utils.auth import (
    hash_password,
    verify_password,
)
from shared.utils.email import send_password_reset_email
from shared.utils.email_validators import EmailValidator
from shared.utils.exception_handlers import exception_handler

logger = get_logger(__name__)

router = APIRouter()


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@exception_handler
async def forgot_password(
    request: Request,
    data: ForgotPassword = Depends(ForgotPassword.as_form),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Send a password reset link to the user's email if the account exists and is active."""
    try:
        # Get the client's IP address
        client_host = request.client.host if request.client else "unknown"

        # Or check headers (especially if behind a reverse proxy/load balancer)
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = client_host

        # Log or use the IP address
        print(f"Password reset requested by user with IP: {ip_address}")
        
        # Step 1: Validate email format and normalize
        email = data.email.strip().lower()
        EmailValidator.validate(email)

        # Step 2: Check if user exists
        user = await get_user_by_email(db, email)
        if not user:
            return user_not_found_response()

        # Step 3: Check if user is active (False = active in your logic)
        if user.is_deleted:  # True means account is deactivated
            return account_deactivated()

        # Step 4: Generate a secure 32-character reset token with 1 hour expiration
        reset_token, expires_at = generate_password_reset_token(
            expires_in_minutes=60
        )

        # Step 5: Save the token to the database
        await create_password_reset_record(
            db=db,
            user_id=user.user_id,
            token=reset_token,
            expires_at=expires_at,
        )

        # Step 6: Create the reset link
        reset_link = (
            f"{settings.FRONTEND_URL}/reset-password?email={email}&token={reset_token}"
        )

        # Step 7: Send the password reset email
        send_password_reset_email(
            email=user.email,
            username=user.username,
            reset_link=reset_link,
            expiry_minutes=60,  # 1 hour expiry
            ip_address=ip_address,
            request_time=datetime.now(timezone.utc).isoformat(),
        )

        # Return success message (don't include token in response for security)
        return api_response(
            status_code=status.HTTP_200_OK,
            message="Password reset link sent to registered email address.",
        )

    except ValueError as e:
        # Handle validation errors
        logger.error(f"Validation error in password reset request: {str(e)}")
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Invalid input: {str(e)}",
        )


@router.post("/reset-password/token", status_code=status.HTTP_200_OK)
@exception_handler
async def reset_password_with_token(
    data: ResetPasswordWithToken = Depends(ResetPasswordWithToken.as_form),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Reset password using the token received via email"""
    try:
        # Step 1: Validate the reset token
        is_valid, error_message, user = await validate_reset_token(
            db=db, token=data.token, email=data.email
        )

        if not is_valid or user is None:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=error_message or "Invalid or expired reset token.",
            )

        # Step 2: Prevent using the same password
        if verify_password(data.new_password, user.password_hash):
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="New password cannot be the same as old password.",
            )

        # Step 3: Update the password
        user.password_hash = hash_password(data.new_password)
        user.login_status = 0  # Normal login status
        user.failure_login_attempts = 0  # Reset login attempts

        # Step 4: Mark the reset token as used
        await mark_password_reset_used(db=db, user_id=user.user_id)

        await db.commit()
        await db.refresh(user)

        return api_response(
            status_code=status.HTTP_200_OK,
            message="Password has been reset successfully.",
        )

    except Exception as e:
        # Handle any unexpected errors
        logger.error(f"Error in password reset: {str(e)}")
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while resetting the password.",
        )


@router.post("/change-password", status_code=status.HTTP_200_OK)
@exception_handler
async def change_password(
    user_id: str,
    data: UserChangePassword = Depends(UserChangePassword.as_form),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Change password for authenticated user.

    This endpoint allows authenticated users to change their password by providing
    their current password and a new password that meets security requirements.
    """
    try:
        # Retrieve the currently logged-in user based on provided user ID
        current_user = await get_user_by_id(db, user_id)
        if isinstance(current_user, JSONResponse):
            return current_user
        # Step 0: Check if user exists
        if not current_user:
            logger.warning(
                f"Attempted password change for non-existent user: {user_id}"
            )
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="User does not exist.",
                log_error=False,
            )
        # Step 1: Check if user account is active
        if current_user.is_deleted:
            logger.warning(
                f"Password change attempt for deactivated user: {current_user.user_id}"
            )
            return account_deactivated()

        # Step 2: Verify current password
        if not verify_password(
            data.current_password, current_user.password_hash
        ):
            logger.warning(
                f"Invalid current password attempt for user: {current_user.user_id}"
            )
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Current password is incorrect.",
                log_error=False,
            )

        # Step 3: Prevent using the same password
        if verify_password(data.new_password, current_user.password_hash):
            logger.info(
                f"User {current_user.user_id} attempted to use same password"
            )
            return api_response(
                status_code=status.HTTP_409_CONFLICT,
                message="New password cannot be the same as current password.",
                log_error=False,
            )

        # Step 4: Update password and reset security fields
        current_user.password_hash = hash_password(data.new_password)
        current_user.failure_login_attempts = 0  # Reset failed login attempts
        current_user.login_status = 0  # Ensure normal login status
        current_user.updated_at = datetime.now(timezone.utc)  # Update timestamp

        # Step 5: Commit changes to database
        await db.commit()
        await db.refresh(current_user)

        logger.info(
            f"Password successfully changed for user: {current_user.user_id}"
        )

        return api_response(
            status_code=status.HTTP_200_OK,
            message="Password changed successfully.",
        )

    except ValueError as e:
        # Handle validation errors from schema
        logger.error(f"Validation error in password change: {str(e)}")
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Invalid input: {str(e)}",
        )

    except Exception as e:
        # Handle any unexpected errors
        logger.error(
            f"Unexpected error in password change for user {user_id}: {str(e)}"
        )
        await db.rollback()  # Rollback any partial changes
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An error occurred while changing the password.",
        )
