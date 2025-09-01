import json
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
from category_service.schemas.custom_sub_category import CustomSubCategoryCreate
from category_service.services.custom_sub_category import (
    create_custom_subcategory,
)
from new_event_service.services.events import (
    check_category_and_subcategory_exists_using_joins,
    check_category_exists,
    check_event_exists_with_slug,
    check_event_exists_with_title,
    check_event_slug_unique_for_update,
    check_event_title_unique_for_update,
    check_organizer_exists,
    check_subcategory_exists,
    fetch_event_by_id,
    update_event,
)
from new_event_service.services.response_builder import (
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
from new_event_service.utils.utils import normalize_tags, safe_json_parse
from shared.core.api_response import api_response
from shared.core.config import settings
from shared.db.models.new_events import EventStatus, NewEvent
from shared.db.sessions.database import get_db
from shared.utils.email_utils.admin_emails import send_event_creation_email_new
from shared.utils.exception_handlers import exception_handler
from shared.utils.file_uploads import (
    get_media_url,
    remove_file_if_exists,
    save_uploaded_file,
)
from shared.utils.id_generators import generate_digits_upper_lower_case
from shared.utils.location_validator import process_location_input

router = APIRouter()


@router.post("/create-with-images", status_code=status.HTTP_201_CREATED)
@exception_handler
async def create_event_with_images(
    background_tasks: BackgroundTasks,
    user_id: str = Form(..., description="User ID of the organizer"),
    event_title: str = Form(..., description="Event title"),
    event_slug: str = Form(..., description="Event slug"),
    category_id: str = Form(..., description="Category ID"),
    subcategory_id: Optional[str] = Form(None, description="Subcategory ID"),
    custom_subcategory_name: Optional[str] = Form(
        None, description="Custom subcategory name (optional)"
    ),
    event_type: Optional[str] = Form(None, description="Event type (optional)"),
    location: Optional[str] = Form(
        None, description="Event location (optional)"
    ),
    is_online: bool = Form(False, description="Is the event online?"),
    extra_data: str = Form(
        "{}", description="Additional event data as JSON string"
    ),
    hash_tags: str = Form("[]", description="List of hashtags as JSON string"),
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
    # Parse JSON fields
    try:
        extra_data_dict = safe_json_parse(extra_data, "extra_data", {})
        raw_hash_tags_list = safe_json_parse(hash_tags, "hash_tags", [])
        hash_tags_list = normalize_tags(raw_hash_tags_list)
    except json.JSONDecodeError as e:
        return invalid_json_format_response(e)

    # Get user information for the email
    user = await get_user_by_id(db, user_id)
    if not user:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            log_error=True,
        )

    # Validate basic required fields
    if not event_title or not event_title.strip():
        return event_title_cannot_be_empty_response()

    if not event_slug or not event_slug.strip():
        return event_slug_cannot_be_empty_response()

    custom_subcategory_name = (
        custom_subcategory_name.strip() if custom_subcategory_name else None
    )

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

        # If custom_subcategory_name provided → enforce subcategory name must be "Others"
        if (
            custom_subcategory_name
            and subcategory.subcategory_name.lower() != "others"
        ):
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Custom subcategory can only be added when subcategory is 'Others'",
                log_error=True,
            )

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
    new_event = NewEvent(
        event_id=new_event_id,
        event_title=event_title.title(),
        event_slug=event_slug.lower(),
        category_id=category_id,
        subcategory_id=subcategory_id,
        event_type=event_type if event_type else None,
        location=cleaned_location if location else None,
        is_online=is_online,
        organizer_id=user_id,
        card_image=card_image_url,
        banner_image=banner_image_url,
        event_extra_images=extra_image_urls if extra_image_urls else None,
        extra_data=extra_data_dict,
        hash_tags=hash_tags_list if hash_tags_list else None,
        event_status=EventStatus.PENDING,
    )

    # Add to database
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)

    if custom_subcategory_name and not subcategory_id:
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Subcategory ID must be provided when custom subcategory name is given.",
            log_error=True,
        )

    if subcategory_id and custom_subcategory_name:
        custom_data = CustomSubCategoryCreate(
            category_ref_id=category_id,
            subcategory_ref_id=subcategory_id,
            event_ref_id=new_event.event_id,
            custom_subcategory_name=(
                custom_subcategory_name.upper()
                if custom_subcategory_name
                else f"Custom-{new_event.event_id}"
            ),
        )

        custom_sub_category = await create_custom_subcategory(db, custom_data)

    # Get user role to determine if admin or organizer
    user_role_name = await get_user_role_name(db, user_id)
    created_by_role = (
        "organizer"
        if user_role_name and user_role_name.lower() == "organizer"
        else "admin"
    )

    # Add background task to send email
    background_tasks.add_task(
        send_event_creation_email_new,
        email=user.email,
        organizer_name=user.username,
        event_title=new_event.event_title,
        event_id=new_event.event_id,
        event_location=new_event.location or "",
        is_online=new_event.is_online,
        event_category=category.category_name,
        created_by_role=created_by_role,
    )

    # Prepare response data
    response_data = {
        "event_id": new_event.event_id,
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

@router.post("/create/step-1")
async def create_step_one(
    background_tasks: BackgroundTasks,
    user_id: str = Form(..., description="User ID of the organizer"),
    event_title: str = Form(..., description="Event title"),
    event_slug: str = Form(..., description="Event slug"),
    category_id: str = Form(..., description="Category ID"),
    subcategory_id: Optional[str] = Form(None, description="Subcategory ID"),
    custom_subcategory_name: Optional[str] = Form(
        None, description="Custom subcategory name (optional)"
    ),
    event_type: Optional[str] = Form(None, description="Event type (optional)"),
    location: Optional[str] = Form(
        None, description="Event location (optional)"
    ),
    is_online: bool = Form(False, description="Is the event online?"),
    extra_data: str = Form(
        "{}", description="Additional event data as JSON string"
    ),
    hash_tags: str = Form("[]", description="List of hashtags as JSON string"),
    # Dependencies
    # current_user: User = Depends(get_current_active_user),
):
    pass
