# response_builders.py
from typing import Optional

from fastapi import status
from starlette.responses import JSONResponse

from shared.core.api_response import api_response
from shared.db.models import AdminUser


def user_not_found_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="User Account not found.",
        log_error=False,
    )


def role_not_found_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Role not found.",
        log_error=True,
    )


def config_not_found_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Configuration not found.",
        log_error=True,
    )


def default_password_not_set_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Default password hash not set in configuration.",
        log_error=True,
    )


def account_deactivated() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_403_FORBIDDEN,
        message="User is inactive. Please contact your administrator to activate your account.",
        log_error=True,
    )


def account_not_approved() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_403_FORBIDDEN,
        message=(
            "This user account is not yet approved by the administration, so you can't "
            "log in until you are verified."
        ),
        log_error=True,
    )


def email_not_verified_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_403_FORBIDDEN,
        message="Email address has not been verified.",
        log_error=True,
    )


def initial_login_response(user: AdminUser) -> JSONResponse:
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Initial login detected. Please reset your password.",
        data={"email": user.email},
    )


def password_expired_response(
    user: AdminUser,
    access_token: str,
    refresh_token: Optional[str] = None,
    organizer_info: Optional[dict] = None,
) -> JSONResponse:
    response_data = {
        "success": False,
        "message": "Password expired. Please update your password.",
        "data": {
            "email": user.email,
        },
        "access_token": access_token,
        "token_type": "bearer",
    }

    if refresh_token:
        response_data["refresh_token"] = refresh_token

    if organizer_info:
        response_data["organizer_info"] = organizer_info

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=response_data,
    )


def login_success_response(
    user: AdminUser,
    access_token: str,
    refresh_token: Optional[str] = None,
    session_id: Optional[int] = None,
    organizer_info: Optional[dict] = None,
) -> JSONResponse:
    response_data = {
        "success": True,
        "message": "Login successful.",
        "data": {
            "email": user.email,
        },
        "access_token": access_token,
        "token_type": "bearer",
    }

    if refresh_token:
        response_data["refresh_token"] = refresh_token
    if session_id:
        response_data["session_id"] = str(session_id)
    if organizer_info:
        response_data["organizer_info"] = organizer_info

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_data,
    )


def organizer_registration_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_403_FORBIDDEN,
        message=(
            "Organizer accounts cannot be created through this endpoint. "
            "Please use the dedicated organizer registration process."
        ),
    )
