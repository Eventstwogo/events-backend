from typing import Annotated, List

from fastapi import APIRouter, Depends, File, Path, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from event_service.services.events import fetch_event_by_id
from event_service.services.response_builder import event_not_found_response
from shared.core.api_response import api_response
from shared.core.config import settings
from shared.db.sessions.database import get_db
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import (
    get_media_url,
    remove_file_if_exists,
    save_uploaded_file,
)

router = APIRouter()


@router.patch("/{event_id}/card-image", summary="Update event card image")
@exception_handler
async def update_event_card_image(
    user_id: str,
    event_id: Annotated[str, Path(..., description="Event ID")],
    card_image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update the event's card image.

    Args:
        event_id: The ID of the event
        card_image: The new card image file

    Returns:
        JSONResponse: Success message with updated card image URL
    """
    # Validate file type
    if card_image.content_type not in settings.ALLOWED_MEDIA_TYPES:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid file type for card image.",
            log_error=True,
        )

    # Fetch the event and verify ownership
    event = await fetch_event_by_id(db, event_id)

    if not event:
        return event_not_found_response()

    # Check if current user is the organizer
    if event.organizer_id != user_id:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You are not authorized to update this event's images.",
            log_error=True,
        )

    # Upload new card image
    uploaded_url = await save_uploaded_file(
        card_image,
        settings.EVENT_CARD_IMAGE_UPLOAD_PATH.format(event_id=event_id),
    )

    # Delete previous card image
    if event.card_image:
        await remove_file_if_exists(event.card_image)

    # Update and save
    event.card_image = uploaded_url
    await db.commit()
    await db.refresh(event)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event card image updated successfully.",
        data={"card_image": get_media_url(event.card_image)},
    )


@router.patch("/{event_id}/banner-image", summary="Update event banner image")
@exception_handler
async def update_event_banner_image(
    user_id: str,
    event_id: Annotated[str, Path(..., description="Event ID")],
    banner_image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update the event's banner image.

    Args:
        event_id: The ID of the event
        banner_image: The new banner image file

    Returns:
        JSONResponse: Success message with updated banner image URL
    """
    # Validate file type
    if banner_image.content_type not in settings.ALLOWED_MEDIA_TYPES:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid file type for banner image.",
            log_error=True,
        )

    # Fetch the event and verify ownership
    event = await fetch_event_by_id(db, event_id)

    if not event:
        return event_not_found_response()

    # Check if current user is the organizer
    if event.organizer_id != user_id:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You are not authorized to update this event's images.",
            log_error=True,
        )

    # Upload new banner image
    uploaded_url = await save_uploaded_file(
        banner_image,
        settings.EVENT_BANNER_IMAGE_UPLOAD_PATH.format(event_id=event_id),
    )

    # Delete previous banner image
    if event.banner_image:
        await remove_file_if_exists(event.banner_image)

    # Update and save
    event.banner_image = uploaded_url
    await db.commit()
    await db.refresh(event)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event banner image updated successfully.",
        data={"banner_image": get_media_url(event.banner_image)},
    )


@router.patch(
    "/{event_id}/extra-images", summary="Update extra images for event"
)
@exception_handler
async def add_event_extra_images(
    user_id: str,
    event_id: Annotated[str, Path(..., description="Event ID")],
    extra_images: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update extra images for the event. Replaces all existing extra images.
    Maximum 5 extra images allowed.

    Args:
        event_id: The ID of the event
        extra_images: List of extra image files (max 5)

    Returns:
        JSONResponse: Success message with uploaded extra image URLs
    """
    # Validate file types
    for image in extra_images:
        if image.content_type not in settings.ALLOWED_MEDIA_TYPES:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid file type for image: {image.filename}",
                log_error=True,
            )

    # Limit number of extra images
    if len(extra_images) > 5:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Maximum 5 extra images allowed",
            log_error=True,
        )

    # Fetch the event and verify ownership
    event = await fetch_event_by_id(db, event_id)

    if not event:
        return event_not_found_response()

    # Check if current user is the organizer
    if event.organizer_id != user_id:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You are not authorized to update this event's images.",
            log_error=True,
        )

    # Validate extra images limit considering existing images
    existing_count = (
        len(event.event_extra_images) if event.event_extra_images else 0
    )
    new_count = len(extra_images)

    # Check if the final count would exceed 5
    # (existing - deleted + new) should not exceed 5
    remaining_after_deletion = max(0, existing_count - new_count)
    final_count = remaining_after_deletion + new_count

    if final_count > 5:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Total extra images cannot exceed 5",
            log_error=True,
        )

    # Update extra images (delete first N existing images and add new ones at the end)
    existing_images = event.event_extra_images or []
    num_new_images = len(extra_images)

    # Delete the first N existing images (where N = number of new images)
    images_to_delete = existing_images[:num_new_images]
    for old_image_url in images_to_delete:
        await remove_file_if_exists(old_image_url)

    # Keep the remaining existing images
    remaining_images = existing_images[num_new_images:]

    # Upload new extra images
    uploaded_urls = []
    existing_count = len(remaining_images)
    for i, image in enumerate(extra_images):
        upload_path = (
            f"{settings.EVENT_EXTRA_IMAGES_UPLOAD_PATH.format(event_id=event_id)}"
            f"/image_{existing_count + i + 1}"
        )
        uploaded_url = await save_uploaded_file(image, upload_path)
        uploaded_urls.append(uploaded_url)

    # Combine remaining existing images with new images
    event.event_extra_images = remaining_images + uploaded_urls

    await db.commit()
    await db.refresh(event)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Extra images updated successfully.",
        data={
            "extra_images": [
                get_media_url(url) for url in (event.event_extra_images or [])
            ],
            "total_extra_images": (
                len(event.event_extra_images or [])
                if event.event_extra_images is not None
                else 0
            ),
        },
    )


@router.delete(
    "/{event_id}/extra-images/{image_index}",
    summary="Remove extra image from event",
)
@exception_handler
async def remove_event_extra_image(
    user_id: str,
    event_id: Annotated[str, Path(..., description="Event ID")],
    image_index: Annotated[
        int, Path(..., description="Index of the image to remove (0-based)")
    ],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Remove an extra image from the event by index.

    Args:
        event_id: The ID of the event
        image_index: Index of the image to remove (0-based)

    Returns:
        JSONResponse: Success message
    """
    # Fetch the event and verify ownership
    event = await fetch_event_by_id(db, event_id)

    if not event:
        return event_not_found_response()

    # Check if current user is the organizer
    if event.organizer_id != user_id:
        return api_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You are not authorized to update this event's images.",
            log_error=True,
        )

    # Check if extra images exist and index is valid
    if (
        not event.event_extra_images
        or image_index >= len(event.event_extra_images)
        or image_index < 0
    ):
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid image index.",
            log_error=True,
        )

    # Remove the image file and update the list
    image_to_remove = event.event_extra_images[image_index]
    await remove_file_if_exists(image_to_remove)

    # Create a new list without the image at the specified index
    updated_images = event.event_extra_images.copy()
    updated_images.pop(image_index)
    event.event_extra_images = updated_images

    await db.commit()
    await db.refresh(event)

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Extra image removed successfully.",
        data={
            "remaining_extra_images": (
                len(event.event_extra_images or [])
                if event.event_extra_images
                else 0
            ),
        },
    )


@router.get("/{event_id}/images", summary="Get all event images")
@exception_handler
async def get_event_images(
    event_id: Annotated[str, Path(..., description="Event ID")],
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Get all images for an event.

    Args:
        event_id: The ID of the event

    Returns:
        JSONResponse: Event images data
    """
    # Fetch the event and verify ownership
    event = await fetch_event_by_id(db, event_id)

    if not event:
        return event_not_found_response()

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event images retrieved successfully.",
        data={
            "event_id": event.event_id,
            "card_image": (
                get_media_url(event.card_image) if event.card_image else None
            ),
            "banner_image": (
                get_media_url(event.banner_image)
                if event.banner_image
                else None
            ),
            "extra_images": (
                [get_media_url(url) for url in event.event_extra_images]
                if event.event_extra_images
                else []
            ),
            "total_extra_images": (
                len(event.event_extra_images) if event.event_extra_images else 0
            ),
        },
    )
