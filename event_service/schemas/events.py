import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from shared.utils.file_uploads import get_media_url
from shared.utils.security_validators import contains_xss
from shared.utils.validators import (
    has_excessive_repetition,
    normalize_whitespace,
    validate_length_range,
)


class EventCreateRequest(BaseModel):
    event_title: str = Field(
        ..., min_length=1, max_length=500, description="Event title"
    )
    event_slug: str = Field(
        ..., min_length=1, max_length=100, description="Event slug"
    )
    category_id: str = Field(
        ..., min_length=1, max_length=6, description="Category ID"
    )
    subcategory_id: str = Field(
        ..., min_length=1, max_length=6, description="Subcategory ID"
    )
    organizer_id: str = Field(
        ..., min_length=1, max_length=6, description="Organizer ID"
    )
    card_image: Optional[str] = Field(None, description="Card image URL")
    banner_image: Optional[str] = Field(None, description="Banner image URL")
    event_extra_images: Optional[List[str]] = Field(
        None, description="List of additional event images"
    )
    extra_data: Optional[dict] = Field(
        default_factory=dict, description="Additional event data"
    )
    hash_tags: Optional[List[str]] = Field(
        None, description="List of hashtags for the event"
    )

    @field_validator("event_title")
    @classmethod
    def validate_event_title(cls, v: str) -> str:
        """Validate event title for security and quality"""
        if not v or not v.strip():
            raise ValueError("Event title cannot be empty")

        # Normalize whitespace
        v = normalize_whitespace(v)

        # Security checks
        if contains_xss(v):
            raise ValueError(
                "Event title contains potentially malicious content"
            )

        # Quality checks
        if has_excessive_repetition(v):
            raise ValueError(
                "Event title contains excessive repeated characters"
            )

        # Length validation after normalization
        if not validate_length_range(v, 1, 500):
            raise ValueError("Event title must be between 1 and 500 characters")

        return v.title()

    @field_validator("event_slug")
    @classmethod
    def validate_event_slug(cls, v: str) -> str:
        """Validate event slug for format, security, and uniqueness"""
        if not v or not v.strip():
            raise ValueError("Event slug cannot be empty")

        v = v.strip().lower()

        # Security checks
        if contains_xss(v):
            raise ValueError(
                "Event slug contains potentially malicious content"
            )

        # Format validation - only allow alphanumeric and hyphens
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError(
                "Event slug must contain only lowercase letters, numbers, and hyphens"
            )

        # No consecutive hyphens
        if "--" in v:
            raise ValueError("Event slug cannot contain consecutive hyphens")

        # Cannot start or end with hyphen
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Event slug cannot start or end with a hyphen")

        # Length validation
        if not validate_length_range(v, 1, 100):
            raise ValueError("Event slug must be between 1 and 100 characters")

        return v

    @field_validator("category_id")
    @classmethod
    def validate_category_id(cls, v: str) -> str:
        """Validate category ID format and security"""
        if not v or not v.strip():
            raise ValueError("Category ID cannot be empty")

        v = v.strip()

        # Security checks
        if contains_xss(v):
            raise ValueError(
                "Category ID contains potentially malicious content"
            )

        # Length validation
        if not validate_length_range(v, 1, 6):
            raise ValueError("Category ID must be between 1 and 6 characters")

        return v

    @field_validator("subcategory_id")
    @classmethod
    def validate_subcategory_id(cls, v: str) -> str:
        """Validate subcategory ID format and security"""
        if not v or not v.strip():
            raise ValueError("Subcategory ID cannot be empty")

        v = v.strip()

        # Security checks
        if contains_xss(v):
            raise ValueError(
                "Subcategory ID contains potentially malicious content"
            )

        # Length validation
        if not validate_length_range(v, 1, 6):
            raise ValueError(
                "Subcategory ID must be between 1 and 6 characters"
            )

        return v

    @field_validator("organizer_id")
    @classmethod
    def validate_organizer_id(cls, v: str) -> str:
        """Validate organizer ID format and security"""
        if not v or not v.strip():
            raise ValueError("Organizer ID cannot be empty")

        v = v.strip()

        # Security checks
        if contains_xss(v):
            raise ValueError(
                "Organizer ID contains potentially malicious content"
            )

        # Length validation - must match user_id format (6 characters)
        if not validate_length_range(v, 6, 6):
            raise ValueError("Organizer ID must be exactly 6 characters")

        return v

    @field_validator("card_image", "banner_image")
    @classmethod
    def validate_image_urls(cls, v: Optional[str]) -> Optional[str]:
        """Validate image URLs for security"""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Security checks
        if contains_xss(v):
            raise ValueError("Image URL contains potentially malicious content")

        # Basic URL format validation
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Image URL must start with http:// or https://")

        # Length validation
        if len(v) > 2000:
            raise ValueError("Image URL is too long (max 2000 characters)")

        return v

    @field_validator("event_extra_images")
    @classmethod
    def validate_event_extra_images(
        cls, v: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Validate list of extra event images"""
        if v is None:
            return v

        if not isinstance(v, list):
            raise ValueError("event_extra_images must be a list")

        # Limit the number of extra images
        if len(v) > 10:
            raise ValueError("Maximum 10 extra images allowed")

        validated_images = []
        for i, image_url in enumerate(v):
            if not isinstance(image_url, str):
                raise ValueError(f"Image URL at index {i} must be a string")

            image_url = image_url.strip()
            if not image_url:
                continue  # Skip empty URLs

            # Security checks
            if contains_xss(image_url):
                raise ValueError(
                    f"Image URL at index {i} contains potentially malicious content"
                )

            # Basic URL format validation
            if not (
                image_url.startswith("http://")
                or image_url.startswith("https://")
            ):
                raise ValueError(
                    f"Image URL at index {i} must start with http:// or https://"
                )

            # Length validation
            if len(image_url) > 2000:
                raise ValueError(
                    f"Image URL at index {i} is too long (max 2000 characters)"
                )

            validated_images.append(image_url)

        return validated_images if validated_images else None

    @field_validator("hash_tags")
    @classmethod
    def validate_hash_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate hash tags for security and format"""
        if v is None:
            return v

        if not isinstance(v, list):
            raise ValueError("hash_tags must be a list")

        if len(v) > 20:
            raise ValueError("Maximum 20 hashtags allowed")

        validated_tags = []
        for i, tag in enumerate(v):
            if not isinstance(tag, str):
                raise ValueError(f"Hashtag at index {i} must be a string")

            tag = tag.strip()
            if not tag:
                continue  # Skip empty tags

            # Security checks
            if contains_xss(tag):
                raise ValueError(
                    f"Hashtag '{tag}' contains potentially malicious content"
                )

            # Format validation
            if not tag.startswith("#"):
                tag = f"#{tag}"

            # Remove multiple # symbols
            tag = tag.replace("##", "#")

            # Length validation
            if len(tag) > 50:
                raise ValueError(
                    f"Hashtag '{tag}' is too long (max 50 characters)"
                )

            if len(tag) < 2:  # At least # + 1 character
                raise ValueError(f"Hashtag '{tag}' is too short")

            validated_tags.append(tag)

        return validated_tags if validated_tags else None

    @field_validator("extra_data")
    @classmethod
    def validate_extra_data(cls, v: Optional[dict]) -> dict:
        """Validate extra_data dictionary for security and structure"""
        if v is None:
            return {}

        if not isinstance(v, dict):
            raise ValueError("extra_data must be a dictionary")

        # Validate each key-value pair in extra_data
        validated_data = {}
        for key, value in v.items():
            # Validate keys
            if not isinstance(key, str):
                raise ValueError(
                    f"extra_data keys must be strings, got {type(key)}"
                )

            if contains_xss(key):
                raise ValueError(
                    f"extra_data key '{key}' contains potentially malicious content"
                )

            if len(key) > 100:
                raise ValueError(
                    f"extra_data key '{key}' is too long (max 100 characters)"
                )

            # Validate values (only allow strings, numbers, booleans, lists, and nested dicts)
            if value is not None:
                validated_value = cls._validate_extra_data_value(key, value)
                validated_data[key] = validated_value

        return validated_data

    @staticmethod
    def _validate_extra_data_value(key: str, value: Any) -> Any:
        """Recursively validate extra_data values"""
        if isinstance(value, str):
            if contains_xss(value):
                raise ValueError(
                    f"extra_data value for key '{key}' contains potentially malicious content"
                )
            if len(value) > 5000:
                raise ValueError(
                    f"extra_data string value for key '{key}' is too long (max 5000 characters)"
                )
            return normalize_whitespace(value)

        elif isinstance(value, (int, float, bool)):
            return value

        elif isinstance(value, list):
            if len(value) > 100:
                raise ValueError(
                    f"extra_data list for key '{key}' is too long (max 100 items)"
                )
            return [
                EventCreateRequest._validate_extra_data_value(
                    f"{key}[{i}]", item
                )
                for i, item in enumerate(value)
            ]

        elif isinstance(value, dict):
            if len(value) > 50:
                raise ValueError(
                    f"extra_data nested dict for key '{key}' has too many keys (max 50)"
                )
            return {
                k: EventCreateRequest._validate_extra_data_value(
                    f"{key}.{k}", v
                )
                for k, v in value.items()
            }

        else:
            raise ValueError(
                f"extra_data value for key '{key}' has unsupported type: {type(value)}"
            )

    @model_validator(mode="after")
    def validate_model(self) -> "EventCreateRequest":
        """Final model validation"""
        # Additional cross-field validations can be added here
        return self


class EventUpdateRequest(BaseModel):
    event_title: Optional[str] = Field(
        None, min_length=1, max_length=500, description="Event title"
    )
    event_slug: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Event slug"
    )
    category_id: Optional[str] = Field(
        None, min_length=1, max_length=6, description="Category ID"
    )
    subcategory_id: Optional[str] = Field(
        None, min_length=1, max_length=6, description="Subcategory ID"
    )
    card_image: Optional[str] = Field(None, description="Card image URL")
    banner_image: Optional[str] = Field(None, description="Banner image URL")
    event_extra_images: Optional[List[str]] = Field(
        None, description="List of additional event images"
    )
    extra_data: Optional[dict] = Field(
        default_factory=dict, description="Additional event data"
    )
    hash_tags: Optional[List[str]] = Field(
        None, description="List of hashtags for the event"
    )

    @field_validator("event_title")
    @classmethod
    def validate_event_title(cls, v: Optional[str]) -> Optional[str]:
        """Validate event title for security and quality"""
        if v is None:
            return v

        if not v.strip():
            raise ValueError("Event title cannot be empty if provided")

        # Normalize whitespace
        v = normalize_whitespace(v)

        # Security checks
        if contains_xss(v):
            raise ValueError(
                "Event title contains potentially malicious content"
            )

        # Quality checks
        if has_excessive_repetition(v):
            raise ValueError(
                "Event title contains excessive repeated characters"
            )

        # Length validation after normalization
        if not validate_length_range(v, 1, 500):
            raise ValueError("Event title must be between 1 and 500 characters")

        return v

    @field_validator("event_slug")
    @classmethod
    def validate_event_slug(cls, v: Optional[str]) -> Optional[str]:
        """Validate event slug for format, security, and uniqueness"""
        if v is None:
            return v

        if not v.strip():
            raise ValueError("Event slug cannot be empty if provided")

        v = v.strip().lower()

        # Security checks
        if contains_xss(v):
            raise ValueError(
                "Event slug contains potentially malicious content"
            )

        # Format validation - only allow alphanumeric and hyphens
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError(
                "Event slug must contain only lowercase letters, numbers, and hyphens"
            )

        # No consecutive hyphens
        if "--" in v:
            raise ValueError("Event slug cannot contain consecutive hyphens")

        # Cannot start or end with hyphen
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Event slug cannot start or end with a hyphen")

        # Length validation
        if not validate_length_range(v, 1, 100):
            raise ValueError("Event slug must be between 1 and 100 characters")

        return v

    @field_validator("category_id")
    @classmethod
    def validate_category_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate category ID format and security"""
        if v is None:
            return v

        if not v.strip():
            raise ValueError("Category ID cannot be empty if provided")

        v = v.strip()

        # Security checks
        if contains_xss(v):
            raise ValueError(
                "Category ID contains potentially malicious content"
            )

        # Length validation
        if not validate_length_range(v, 1, 6):
            raise ValueError("Category ID must be between 1 and 6 characters")

        return v

    @field_validator("subcategory_id")
    @classmethod
    def validate_subcategory_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate subcategory ID format and security"""
        if v is None:
            return v

        # Convert empty string to None
        if not v.strip():
            return None

        v = v.strip()

        # Security checks
        if contains_xss(v):
            raise ValueError(
                "Subcategory ID contains potentially malicious content"
            )

        # Length validation
        if not validate_length_range(v, 1, 6):
            raise ValueError(
                "Subcategory ID must be between 1 and 6 characters"
            )

        return v

    @field_validator("card_image", "banner_image")
    @classmethod
    def validate_image_urls(cls, v: Optional[str]) -> Optional[str]:
        """Validate image URLs for security"""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Security checks
        if contains_xss(v):
            raise ValueError("Image URL contains potentially malicious content")

        # Basic URL format validation
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Image URL must start with http:// or https://")

        # Length validation
        if len(v) > 2000:
            raise ValueError("Image URL is too long (max 2000 characters)")

        return v

    @field_validator("event_extra_images")
    @classmethod
    def validate_event_extra_images(
        cls, v: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Validate list of extra event images"""
        if v is None:
            return v

        if not isinstance(v, list):
            raise ValueError("event_extra_images must be a list")

        # Limit the number of extra images
        if len(v) > 10:
            raise ValueError("Maximum 10 extra images allowed")

        validated_images = []
        for i, image_url in enumerate(v):
            if not isinstance(image_url, str):
                raise ValueError(f"Image URL at index {i} must be a string")

            image_url = image_url.strip()
            if not image_url:
                continue  # Skip empty URLs

            # Security checks
            if contains_xss(image_url):
                raise ValueError(
                    f"Image URL at index {i} contains potentially malicious content"
                )

            # Basic URL format validation
            if not (
                image_url.startswith("http://")
                or image_url.startswith("https://")
            ):
                raise ValueError(
                    f"Image URL at index {i} must start with http:// or https://"
                )

            # Length validation
            if len(image_url) > 2000:
                raise ValueError(
                    f"Image URL at index {i} is too long (max 2000 characters)"
                )

            validated_images.append(image_url)

        return validated_images if validated_images else None

    @field_validator("hash_tags")
    @classmethod
    def validate_hash_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate hash tags for security and format"""
        if v is None:
            return v

        if not isinstance(v, list):
            raise ValueError("hash_tags must be a list")

        if len(v) > 20:
            raise ValueError("Maximum 20 hashtags allowed")

        validated_tags = []
        for i, tag in enumerate(v):
            if not isinstance(tag, str):
                raise ValueError(f"Hashtag at index {i} must be a string")

            tag = tag.strip()
            if not tag:
                continue  # Skip empty tags

            # Security checks
            if contains_xss(tag):
                raise ValueError(
                    f"Hashtag '{tag}' contains potentially malicious content"
                )

            # Format validation
            if not tag.startswith("#"):
                tag = f"#{tag}"

            # Remove multiple # symbols
            tag = tag.replace("##", "#")

            # Length validation
            if len(tag) > 50:
                raise ValueError(
                    f"Hashtag '{tag}' is too long (max 50 characters)"
                )

            if len(tag) < 2:  # At least # + 1 character
                raise ValueError(f"Hashtag '{tag}' is too short")

            validated_tags.append(tag)

        return validated_tags if validated_tags else None

    @field_validator("extra_data")
    @classmethod
    def validate_extra_data(cls, v: Optional[dict]) -> dict:
        """Validate extra_data dictionary for security and structure"""
        if v is None:
            return {}

        if not isinstance(v, dict):
            raise ValueError("extra_data must be a dictionary")

        # Validate each key-value pair in extra_data
        validated_data = {}
        for key, value in v.items():
            # Validate keys
            if not isinstance(key, str):
                raise ValueError(
                    f"extra_data keys must be strings, got {type(key)}"
                )

            if contains_xss(key):
                raise ValueError(
                    f"extra_data key '{key}' contains potentially malicious content"
                )

            if len(key) > 100:
                raise ValueError(
                    f"extra_data key '{key}' is too long (max 100 characters)"
                )

            # Validate values (only allow strings, numbers, booleans, lists, and nested dicts)
            if value is not None:
                validated_value = cls._validate_extra_data_value(key, value)
                validated_data[key] = validated_value

        return validated_data

    @staticmethod
    def _validate_extra_data_value(key: str, value: Any) -> Any:
        """Recursively validate extra_data values"""
        if isinstance(value, str):
            if contains_xss(value):
                raise ValueError(
                    f"extra_data value for key '{key}' contains potentially malicious content"
                )
            if len(value) > 5000:
                raise ValueError(
                    f"extra_data string value for key '{key}' is too long (max 5000 characters)"
                )
            return normalize_whitespace(value)

        elif isinstance(value, (int, float, bool)):
            return value

        elif isinstance(value, list):
            if len(value) > 100:
                raise ValueError(
                    f"extra_data list for key '{key}' is too long (max 100 items)"
                )
            return [
                EventUpdateRequest._validate_extra_data_value(
                    f"{key}[{i}]", item
                )
                for i, item in enumerate(value)
            ]

        elif isinstance(value, dict):
            if len(value) > 50:
                raise ValueError(
                    f"extra_data nested dict for key '{key}' has too many keys (max 50)"
                )
            return {
                k: EventUpdateRequest._validate_extra_data_value(
                    f"{key}.{k}", v
                )
                for k, v in value.items()
            }

        else:
            raise ValueError(
                f"extra_data value for key '{key}' has unsupported type: {type(value)}"
            )

    @model_validator(mode="after")
    def validate_model(self) -> "EventUpdateRequest":
        """Final model validation"""
        # Ensure at least one field is being updated (besides event_id)
        update_fields = [
            self.event_title,
            self.card_image,
            self.banner_image,
            self.extra_data,
        ]
        if all(
            field is None or (isinstance(field, dict) and not field)
            for field in update_fields
        ):
            raise ValueError("At least one field must be provided for update")

        return self


# Related entity schemas
class CategoryInfo(BaseModel):
    """Schema for category information in event response"""

    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    category_slug: str = Field(..., description="Category slug")
    category_img_thumbnail: Optional[str] = Field(
        None, description="Category thumbnail image"
    )

    @field_serializer("category_img_thumbnail")
    def serialize_category_img_thumbnail(
        self, value: Optional[str]
    ) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    class Config:
        from_attributes = True


class SubCategoryInfo(BaseModel):
    """Schema for subcategory information in event response"""

    subcategory_id: str = Field(..., description="Subcategory ID")
    subcategory_name: str = Field(..., description="Subcategory name")
    subcategory_slug: str = Field(..., description="Subcategory slug")
    subcategory_img_thumbnail: Optional[str] = Field(
        None, description="Subcategory thumbnail image"
    )

    @field_serializer("subcategory_img_thumbnail")
    def serialize_subcategory_img_thumbnail(
        self, value: Optional[str]
    ) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    class Config:
        from_attributes = True


class OrganizerInfo(BaseModel):
    """Schema for organizer information in event response"""

    user_id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    profile_picture: Optional[str] = Field(
        None, description="Profile picture URL"
    )

    @field_serializer("profile_picture")
    def serialize_profile_picture(self, value: Optional[str]) -> Optional[str]:
        """Convert relative path to full media URL"""
        return get_media_url(value)

    class Config:
        from_attributes = True
