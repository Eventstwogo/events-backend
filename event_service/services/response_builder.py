# response_builders.py

from fastapi import status
from starlette.responses import JSONResponse

from shared.core.api_response import api_response


def event_already_exists_with_slug_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message="Event with this slug already exists",
        log_error=True,
    )


def event_title_already_exists_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message="Event title already existed",
        log_error=True,
    )


def organizer_not_found_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Organizer not found",
        log_error=True,
    )


def category_not_found_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Category not found",
        log_error=True,
    )


def subcategory_not_found_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Subcategory not found",
        log_error=True,
    )


def category_and_subcategory_not_found_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Category or Subcategory are not related",
        log_error=True,
    )


def event_not_found_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Event not found",
        log_error=True,
    )


def unauthorized_to_update_event_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_403_FORBIDDEN,
        message="You are not authorized to update this event.",
        log_error=True,
    )


def event_slug_already_exists_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message="Event with this slug already exists",
        log_error=True,
    )


def invalid_event_data_response(
    message: str = "Invalid event data",
) -> JSONResponse:
    return api_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message,
        log_error=True,
    )


def event_deleted_successfully_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event deleted successfully",
    )


def event_updated_successfully_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event updated successfully",
    )


def event_status_updated_successfully_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event status updated successfully",
    )


# Slot-related response builders
def slot_not_found_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Slot not found",
        log_error=True,
    )


def slot_already_exists_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message="Slot already exists for this event",
        log_error=True,
    )


def invalid_slot_data_response(
    message: str = "Invalid slot data",
) -> JSONResponse:
    return api_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message,
        log_error=True,
    )


def slot_created_successfully_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Slot created successfully",
    )


def slot_updated_successfully_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot updated successfully",
    )


def slot_status_updated_successfully_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot status updated successfully",
    )


def slot_deleted_successfully_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_200_OK,
        message="Slot deleted successfully",
    )


def invalid_json_format_response(e: Exception) -> JSONResponse:
    return api_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=f"Invalid JSON format: {str(e)}",
        log_error=True,
    )


def event_title_cannot_be_empty_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message="Event title cannot be empty",
        log_error=True,
    )


def event_slug_cannot_be_empty_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message="Event slug cannot be empty",
        log_error=True,
    )


def invalid_file_type_for_card_image_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message="Invalid file type for card image.",
        log_error=True,
    )


def invalid_file_type_for_banner_image_response() -> JSONResponse:
    return api_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message="Invalid file type for banner image.",
        log_error=True,
    )
