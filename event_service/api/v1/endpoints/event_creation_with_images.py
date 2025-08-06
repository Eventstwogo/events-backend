import json
from datetime import date
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Path,
    UploadFile,
    status,
)
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from admin_service.services.user_service import (
    get_user_by_id,
    get_user_role_name,
)
from event_service.services.events import (
    check_category_and_subcategory_exists_using_joins,
    check_category_exists,
    check_event_exists_with_slug,
    check_event_exists_with_title,
    check_event_slug_unique_for_update,
    check_event_title_unique_for_update,
    check_organizer_exists,
    check_subcategory_exists,
    fetch_category_by_id,
    fetch_event_by_id,
    update_event,
)
from event_service.services.response_builder import (
    category_and_subcategory_not_found_response,
    category_not_found_response,
    event_already_exists_with_slug_response,
    event_not_found_response,
    event_slug_cannot_be_empty_response,
    event_title_already_exists_response,
    event_title_cannot_be_empty_response,
    invalid_file_type_for_banner_image_response,
    invalid_file_type_for_card_image_response,
    invalid_json_format_response,
    organizer_not_found_response,
    subcategory_not_found_response,
    unauthorized_to_update_event_response,
)
from event_service.utils.location_validator import validate_location_input
from shared.core.api_response import api_response
from shared.core.config import settings
from shared.db.models import Event
from shared.db.sessions.database import get_db
from shared.utils.email_utils.admin_emails import send_event_creation_email
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import (
    get_media_url,
    remove_file_if_exists,
    save_uploaded_file,
)
from shared.utils.id_generators import generate_digits_upper_lower_case

router = APIRouter()


def process_location_input(location, allow_empty=False):
    """Process and validate location input consistently"""
    if location is None:
        return None

    # For updates, allow empty string to clear the location
    if allow_empty and location.strip() == "":
        return None

    cleaned_location = validate_location_input(location)
    return cleaned_location if cleaned_location else None


def safe_json_parse(json_string, field_name, default_value=None):
    """Safely parse JSON string with better error handling"""
    if not json_string or json_string.strip() == "":
        return default_value

    # Handle common cases where Swagger might send malformed data
    json_string = json_string.strip()

    # Handle cases where Swagger might double-quote the JSON string
    if json_string.startswith('"') and json_string.endswith('"'):
        json_string = json_string[1:-1]
        # Unescape any escaped quotes
        json_string = json_string.replace('\\"', '"')

    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in {field_name}: {str(e)}. Received: '{json_string[:50]}"
            f"{'...' if len(json_string) > 50 else ''}'",
            json_string,
            e.pos,
        )


@router.post("/create-with-images", status_code=status.HTTP_201_CREATED)
@exception_handler
async def create_event_with_images(
    # Text/JSON data as form fields
    user_id: str = Form(..., description="User ID of the organizer"),
    event_title: str = Form(..., description="Event title"),
    event_slug: str = Form(..., description="Event slug"),
    category_id: str = Form(..., description="Category ID"),
    subcategory_id: Optional[str] = Form(None, description="Subcategory ID"),
    location: Optional[str] = Form(
        None, description="Event location (optional)"
    ),
    extra_data: str = Form(
        "{}", description="Additional event data as JSON string"
    ),
    hash_tags: str = Form("[]", description="List of hashtags as JSON string"),
    # Image files (optional)
    card_image: Optional[UploadFile] = File(
        None, description="Event card image"
    ),
    banner_image: Optional[UploadFile] = File(
        None, description="Event banner image"
    ),
    extra_images: List[UploadFile] = File(
        default=[], description="List of extra event images"
    ),
    # Dependencies
    # current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Create a new event with optional image uploads.

    This endpoint combines event creation with image uploading to handle
    text data, JSON data, and file uploads simultaneously.

    Args:
        event_title: The title of the event
        event_slug: SEO-friendly slug for the event
        category_id: ID of the event category
        subcategory_id: ID of the event subcategory
        extra_data: Additional event data as JSON string
        hash_tags: List of hashtags as JSON string
        card_image: Optional card image file
        banner_image: Optional banner image file
        extra_images: List of optional extra image files
        current_user: Current authenticated user (organizer)
        db: Database session

    Returns:
        JSONResponse: Success message with created event data
    """

    # Parse JSON fields
    try:
        extra_data_dict = safe_json_parse(extra_data, "extra_data", {})
        hash_tags_list = safe_json_parse(hash_tags, "hash_tags", [])
    except json.JSONDecodeError as e:
        return invalid_json_format_response(e)

    # Validate basic required fields
    if not event_title or not event_title.strip():
        return event_title_cannot_be_empty_response()

    if not event_slug or not event_slug.strip():
        return event_slug_cannot_be_empty_response()

    # Validate location
    cleaned_location = process_location_input(location)

    # Validate image file types if provided
    if (
        card_image
        and card_image.content_type not in settings.ALLOWED_MEDIA_TYPES
    ):
        return invalid_file_type_for_card_image_response()

    if (
        banner_image
        and banner_image.content_type not in settings.ALLOWED_MEDIA_TYPES
    ):
        return invalid_file_type_for_banner_image_response()

    for i, image in enumerate(extra_images):
        if image.content_type not in settings.ALLOWED_MEDIA_TYPES:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid file type for extra image {i+1}: {image.filename}",
                log_error=True,
            )

    # Limit number of extra images
    if len(extra_images) > 5:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Maximum 5 extra images allowed",
            log_error=True,
        )

    # Normalize and slugify the event slug first
    event_slug = slugify(event_slug.lower() or event_title.lower())

    # Check if event title is unique
    existing_title = await check_event_exists_with_title(
        db, event_title.strip()
    )
    if existing_title:
        return event_title_already_exists_response()

    # Check if an event with the same slug already exists
    existing_event = await check_event_exists_with_slug(db, event_slug)
    if existing_event:
        return event_already_exists_with_slug_response()

    # Check if the organizer exists (should always pass since we have current_user)
    organizer = await check_organizer_exists(db, user_id)
    if not organizer:
        return organizer_not_found_response()

    # Check if the category and subcategory exist
    category = await check_category_exists(db, category_id)
    if not category:
        return category_not_found_response()

    # Convert empty string to None for subcategory_id
    if subcategory_id == "":
        subcategory_id = None

    if subcategory_id:
        subcategory = await check_subcategory_exists(db, subcategory_id)
        if not subcategory:
            return subcategory_not_found_response()

        existing_category_subcategory = (
            await check_category_and_subcategory_exists_using_joins(
                db, category_id, subcategory_id
            )
        )
        if not existing_category_subcategory:
            return category_and_subcategory_not_found_response()

    # Generate a new event ID
    new_event_id = generate_digits_upper_lower_case(length=6)

    # Upload images if provided
    card_image_url = None
    banner_image_url = None
    extra_image_urls = []
    uploaded_files = []  # Track uploaded files for cleanup

    try:
        # Upload card image
        if card_image:
            card_image_url = await save_uploaded_file(
                card_image,
                settings.EVENT_CARD_IMAGE_UPLOAD_PATH.format(
                    event_id=new_event_id
                ),
            )
            uploaded_files.append(card_image_url)

        # Upload banner image
        if banner_image:
            banner_image_url = await save_uploaded_file(
                banner_image,
                settings.EVENT_BANNER_IMAGE_UPLOAD_PATH.format(
                    event_id=new_event_id
                ),
            )
            uploaded_files.append(banner_image_url)

        # Upload extra images
        for i, image in enumerate(extra_images):
            upload_path = (
                f"{settings.EVENT_EXTRA_IMAGES_UPLOAD_PATH.format(event_id=new_event_id)}"
                f"/image_{i+1}"
            )
            uploaded_url = await save_uploaded_file(image, upload_path)
            extra_image_urls.append(uploaded_url)
            uploaded_files.append(uploaded_url)

    except Exception as e:
        # Clean up any uploaded files on failure
        for file_url in uploaded_files:
            await remove_file_if_exists(file_url)
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to upload images: {str(e)}",
            log_error=True,
        )

    # Create new event
    new_event = Event(
        event_id=new_event_id,
        event_title=event_title.title(),
        event_slug=event_slug.lower(),
        category_id=category_id,
        subcategory_id=subcategory_id,
        location=cleaned_location if location else None,
        organizer_id=user_id,
        card_image=card_image_url,
        banner_image=banner_image_url,
        event_extra_images=extra_image_urls if extra_image_urls else None,
        extra_data=extra_data_dict,
        hash_tags=hash_tags_list if hash_tags_list else None,
        slot_id=generate_digits_upper_lower_case(length=8),
    )

    # Add to database
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)

    # Prepare response data
    response_data = {
        "event_id": new_event.event_id,
        "slot_id": new_event.slot_id,
        "event_title": new_event.event_title,
        "event_slug": new_event.event_slug,
        "organizer_id": new_event.organizer_id,
        "images": {
            "card_image": (
                get_media_url(card_image_url) if card_image_url else None
            ),
            "banner_image": (
                get_media_url(banner_image_url) if banner_image_url else None
            ),
            "extra_images": (
                [get_media_url(url) for url in extra_image_urls]
                if extra_image_urls
                else []
            ),
            "total_extra_images": len(extra_image_urls),
        },
    }

    # Return success response
    return api_response(
        status_code=status.HTTP_201_CREATED,
        message="Event created successfully with images",
        data=response_data,
    )


@router.patch(
    "/{event_id}/update-with-images", summary="Update event with images"
)
@exception_handler
async def update_event_with_images(
    user_id: str = Form(..., description="User ID of the organizer"),
    event_id: str = Path(..., description="Event ID"),
    # Optional text/JSON data as form fields
    event_title: Optional[str] = Form(None, description="Event title"),
    event_slug: Optional[str] = Form(None, description="Event slug"),
    category_id: Optional[str] = Form(None, description="Category ID"),
    subcategory_id: Optional[str] = Form(None, description="Subcategory ID"),
    location: Optional[str] = Form(
        None, description="Event location (optional)"
    ),
    extra_data: Optional[str] = Form(
        None, description="Additional event data as JSON string"
    ),
    hash_tags: Optional[str] = Form(
        None, description="List of hashtags as JSON string"
    ),
    # Optional image files
    card_image: Optional[UploadFile] = File(
        None, description="New event card image"
    ),
    banner_image: Optional[UploadFile] = File(
        None, description="New event banner image"
    ),
    extra_images: List[UploadFile] = File(
        default=[], description="Additional extra event images"
    ),
    # Dependencies
    # current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update an existing event with optional image uploads.

    This endpoint allows updating event data and images simultaneously.
    Only provided fields will be updated.

    Args:
        event_id: ID of the event to update
        event_title: Optional new title
        event_slug: Optional new slug
        category_id: Optional new category ID
        subcategory_id: Optional new subcategory ID
        extra_data: Optional additional data as JSON string
        hash_tags: Optional hashtags as JSON string
        card_image: Optional new card image
        banner_image: Optional new banner image
        extra_images: Optional additional extra images (will be appended)
        current_user: Current authenticated user
        db: Database session

    Returns:
        JSONResponse: Success message with updated event data
    """
    # Fetch the event and verify ownership
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return event_not_found_response()

    # Check if current user is the organizer
    if event.organizer_id != user_id:
        return unauthorized_to_update_event_response()

    # Parse JSON fields if provided
    extra_data_dict = None
    hash_tags_list = None

    try:
        if extra_data is not None:
            extra_data_dict = safe_json_parse(extra_data, "extra_data", {})
        if hash_tags is not None:
            hash_tags_list = safe_json_parse(hash_tags, "hash_tags", [])
    except json.JSONDecodeError as e:
        return invalid_json_format_response(e)

    # Validate image file types if provided
    if (
        card_image
        and card_image.content_type not in settings.ALLOWED_MEDIA_TYPES
    ):
        return invalid_file_type_for_card_image_response()

    if (
        banner_image
        and banner_image.content_type not in settings.ALLOWED_MEDIA_TYPES
    ):
        return invalid_file_type_for_banner_image_response()

    for i, image in enumerate(extra_images):
        if image.content_type not in settings.ALLOWED_MEDIA_TYPES:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid file type for extra image {i+1}: {image.filename}",
                log_error=True,
            )

    # Validate extra images limit considering existing images
    if extra_images:
        existing_count = (
            len(event.event_extra_images) if event.event_extra_images else 0
        )
        new_count = len(extra_images)

        # Check if we're trying to add more than 5 images at once
        if new_count > 5:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Maximum 5 extra images allowed per request",
                log_error=True,
            )

        # Check if the final count would exceed 5
        # We'll keep existing images and add new ones, removing oldest if needed
        total_after_adding = existing_count + new_count
        if total_after_adding > 5:
            # This is acceptable - we'll handle it by removing oldest images
            pass

    # Prepare update data
    update_data = {}

    # Validate location
    if location is not None:
        cleaned_location = process_location_input(location, allow_empty=True)
        update_data["location"] = cleaned_location
    # Validate and prepare title update
    if event_title is not None:
        if not await check_event_title_unique_for_update(
            db, event_id, event_title.strip()
        ):
            return event_title_already_exists_response()
        update_data["event_title"] = event_title.title()

    if event_slug is None and event_title is not None:
        event_slug = event_title.lower()

    # Validate and prepare slug update
    if event_slug is not None:
        event_slug = slugify(event_slug.lower())
        if not await check_event_slug_unique_for_update(
            db, event_id, event_slug
        ):
            return event_already_exists_with_slug_response()
        update_data["event_slug"] = event_slug

    # Validate category if provided
    if category_id is not None:
        category = await check_category_exists(db, category_id)
        if not category:
            return category_not_found_response()
        update_data["category_id"] = category_id

    # Validate subcategory if provided
    if subcategory_id is not None:
        # Convert empty string to None for subcategory_id
        if subcategory_id == "":
            subcategory_id = None

        if subcategory_id:
            subcategory = await check_subcategory_exists(db, subcategory_id)
            if not subcategory:
                return subcategory_not_found_response()

        update_data["subcategory_id"] = subcategory_id

    # Validate category-subcategory relationship if both are being updated
    final_category_id = update_data.get("category_id", event.category_id)
    final_subcategory_id = update_data.get(
        "subcategory_id", event.subcategory_id
    )

    if final_category_id and final_subcategory_id:
        existing_category_subcategory = (
            await check_category_and_subcategory_exists_using_joins(
                db, final_category_id, final_subcategory_id
            )
        )
        if not existing_category_subcategory:
            return category_and_subcategory_not_found_response()

    # Add other fields
    if extra_data_dict is not None:
        update_data["extra_data"] = extra_data_dict

    if hash_tags_list is not None:
        update_data["hash_tags"] = hash_tags_list

    # Upload new images if provided
    try:
        # Upload new card image
        if card_image:
            # Delete previous card image
            if event.card_image:
                await remove_file_if_exists(event.card_image)

            card_image_url = await save_uploaded_file(
                card_image,
                settings.EVENT_CARD_IMAGE_UPLOAD_PATH.format(event_id=event_id),
            )
            update_data["card_image"] = card_image_url

        # Upload new banner image
        if banner_image:
            # Delete previous banner image
            if event.banner_image:
                await remove_file_if_exists(event.banner_image)

            banner_image_url = await save_uploaded_file(
                banner_image,
                settings.EVENT_BANNER_IMAGE_UPLOAD_PATH.format(
                    event_id=event_id
                ),
            )
            update_data["banner_image"] = banner_image_url

        if extra_images:
            existing_images = event.event_extra_images or []
            num_existing = len(existing_images)
            num_new_images = len(extra_images)
            total_after_adding = num_existing + num_new_images

            # Determine how many existing images to keep/delete
            if total_after_adding <= 5:
                # Case 1: Total ≤ 5, keep all existing images and add new ones
                images_to_delete = []
                remaining_images = existing_images.copy()
            else:
                # Case 2: Total > 5, delete oldest images to make room
                num_to_delete = total_after_adding - 5
                images_to_delete = existing_images[:num_to_delete]
                remaining_images = existing_images[num_to_delete:]

            # Delete the determined images
            for old_image_url in images_to_delete:
                await remove_file_if_exists(old_image_url)

            # Upload new extra images
            new_extra_urls = []
            existing_count = len(remaining_images)
            for i, image in enumerate(extra_images):
                upload_path = (
                    f"{settings.EVENT_EXTRA_IMAGES_UPLOAD_PATH.format(event_id=event_id)}"
                    f"/image_{existing_count + i + 1}"
                )
                uploaded_url = await save_uploaded_file(image, upload_path)
                new_extra_urls.append(uploaded_url)

            # Combine remaining existing images with new images
            update_data["event_extra_images"] = (
                remaining_images + new_extra_urls
            )

    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to upload images: {str(e)}",
            log_error=True,
        )

    # Update the event if there's any data to update
    if update_data:
        try:
            updated_event = await update_event(db, event_id, update_data)
            if not updated_event:
                return api_response(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Failed to update event",
                    log_error=True,
                )
        except Exception as e:
            await db.rollback()
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to update event: {str(e)}",
                log_error=True,
            )
    else:
        updated_event = event

    # Prepare response data
    response_data = {
        "event_id": updated_event.event_id,
        "slot_id": updated_event.slot_id,
        "updated_fields": list(update_data.keys()),
        "images": {
            "card_image": (
                get_media_url(updated_event.card_image)
                if updated_event.card_image
                else None
            ),
            "banner_image": (
                get_media_url(updated_event.banner_image)
                if updated_event.banner_image
                else None
            ),
            "extra_images": (
                [get_media_url(url) for url in updated_event.event_extra_images]
                if updated_event.event_extra_images
                else []
            ),
            "total_extra_images": (
                len(updated_event.event_extra_images)
                if updated_event.event_extra_images
                else 0
            ),
        },
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event updated successfully with images",
        data=response_data,
    )


@router.patch(
    "/{event_id}/update-event-details", summary="Update event details"
)
@exception_handler
async def update_event_details(
    background_tasks: BackgroundTasks,
    user_id: str = Form(..., description="User ID of the organizer"),
    event_id: str = Path(..., description="Event ID"),
    # Event details fields
    start_date: Optional[date] = Form(
        None, description="Event start date in ISO format (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Form(
        None, description="Event end date in ISO format (YYYY-MM-DD)"
    ),
    location: Optional[str] = Form(
        None, description="Event location (optional)"
    ),
    is_online: Optional[bool] = Form(
        default=False, description="Is the event online?"
    ),
    # Dependencies
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Update event details including dates, location, online status.

    This endpoint allows updating specific event details without handling images.
    Only provided fields will be updated.

    Args:
        user_id: User ID of the organizer
        event_id: ID of the event to update
        start_date: Optional new start date in ISO date format (YYYY-MM-DD)
        end_date: Optional new end date in ISO date format (YYYY-MM-DD)
        location: Optional new location
        is_online: Optional online status
        db: Database session

    Returns:
        JSONResponse: Success message with updated event data
    """
    # Get user information for the email
    user = await get_user_by_id(db, user_id)
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            log_error=True,
        )

    # Fetch the event and verify ownership
    event = await fetch_event_by_id(db, event_id)
    if not event:
        return event_not_found_response()

    # Check if current user is the organizer
    if event.organizer_id != user_id:
        return unauthorized_to_update_event_response()

    # Prepare update data
    update_data = {}

    # Validation
    if start_date is not None:
        update_data["start_date"] = start_date

    if end_date is not None:
        update_data["end_date"] = end_date

    # Validate both dates if provided
    if start_date and end_date:
        if end_date < start_date:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="End date must be after start date.",
                log_error=True,
            )

    # Validate start_date against existing end_date
    elif start_date and event.end_date:
        if start_date >= event.end_date:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Start date must be before the existing end date.",
                log_error=True,
            )

    # Validate end_date against existing start_date
    elif end_date and event.start_date:
        if end_date <= event.start_date:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="End date must be after the existing start date.",
                log_error=True,
            )

    # Validate location
    if location is not None:
        cleaned_location = process_location_input(location, allow_empty=True)
        update_data["location"] = cleaned_location

    # Validate is_online
    if is_online is not None:
        update_data["is_online"] = is_online

    # Check if there's any data to update
    if not update_data:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="No valid fields provided for update.",
            log_error=True,
        )

    # Update the event
    try:
        updated_event = await update_event(db, event_id, update_data)
        if not updated_event:
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to update event",
                log_error=True,
            )
    except Exception as e:
        await db.rollback()
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to update event: {str(e)}",
            log_error=True,
        )

    # Send event creation email only if the event originally had no start_date and end_date
    # and now both dates are being added for the first time
    should_send_email = False

    # Check if event originally had no dates and now has both dates after update
    if (
        updated_event.start_date
        and updated_event.end_date
        and ("start_date" in update_data or "end_date" in update_data)
    ):

        # Only send email if the event originally had no start_date AND no end_date
        # This means dates are being added for the first time, not just updated
        original_had_no_start_date = event.start_date is None
        original_had_no_end_date = event.end_date is None

        # Send email only if both dates were originally missing
        should_send_email = (
            original_had_no_start_date and original_had_no_end_date
        )

    if should_send_email:

        try:
            # Get user role to determine if admin or organizer
            user_role_name = await get_user_role_name(db, user_id)
            created_by_role = (
                "organizer"
                if user_role_name and user_role_name.lower() == "organizer"
                else "admin"
            )

            organizer_email = user.email
            organizer_name = user.username

            # Get category information
            event_category = "General"
            if updated_event.category_id:
                category = await fetch_category_by_id(
                    db, updated_event.category_id
                )
                if category:
                    event_category = category.category_name

            # Format dates and times for email
            event_start_date = updated_event.start_date.strftime("%B %d, %Y")
            event_end_date = updated_event.end_date.strftime("%B %d, %Y")

            # Add background task to send email
            background_tasks.add_task(
                send_event_creation_email,
                email=organizer_email,
                organizer_name=organizer_name,
                event_title=updated_event.event_title,
                event_id=updated_event.event_id,
                event_start_date=event_start_date,
                event_end_date=event_end_date,
                event_location=updated_event.location,
                event_category=event_category,
                created_by_role=created_by_role,
            )

        except Exception as email_error:
            # Log the error but don't fail the update operation
            print(f"Failed to queue event creation email: {str(email_error)}")

    # Prepare response data
    response_data = {
        "event_id": updated_event.event_id,
        "slot_id": updated_event.slot_id,
        "event_title": updated_event.event_title,
        "updated_fields": list(update_data.keys()),
        "event_details": {
            "start_date": (
                updated_event.start_date.isoformat()
                if updated_event.start_date
                else None
            ),
            "end_date": (
                updated_event.end_date.isoformat()
                if updated_event.end_date
                else None
            ),
            "location": updated_event.location,
            "is_online": updated_event.is_online,
        },
    }

    return api_response(
        status_code=status.HTTP_200_OK,
        message="Event details updated successfully",
        data=response_data,
    )
