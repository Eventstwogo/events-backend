import re

from shared.utils.security_validators import contains_xss
from shared.utils.validators import (
    has_excessive_repetition,
    normalize_whitespace,
    validate_length_range,
)


def validate_location_input(
    location: str, min_len: int = 5, max_len: int = 255
) -> str:
    """
    Validates and sanitizes a user-provided address/location input.

    Returns:
        A cleaned and validated location string.

    Raises:
        ValueError: If input fails any validation rule.
    """
    if location is None:
        raise ValueError("Location must not be null.")

    # Normalize and trim whitespace
    location = normalize_whitespace(location)

    if location.strip() == "":
        raise ValueError("Location must not be empty or only whitespace.")

    # Length check
    validate_length_range(location, min_len, max_len)

    # Reject XSS
    if contains_xss(location):
        raise ValueError("Location contains potentially dangerous content.")

    # Reject excessive character repetition
    if has_excessive_repetition(location):
        raise ValueError("Location contains excessive repetition.")

    # Reject purely numeric inputs
    if location.isdigit():
        raise ValueError("Location cannot be only numbers.")

    # Require at least one alphabetic character (to avoid inputs like "1234")
    if not re.search(r"[A-Za-z]", location):
        raise ValueError("Location must contain at least one letter.")

    # Optional: Ensure at least 2 alphabetic characters (stricter)
    if len(re.findall(r"[A-Za-z]", location)) < 2:
        raise ValueError("Location must contain at least two letters.")

    # Address character pattern: letters, digits, space, comma, slash, dash, dot,
    # hash, colon, parens
    address_pattern = re.compile(r"^[\w\s.,#/\-():]+$", re.UNICODE)
    if not address_pattern.match(location):
        raise ValueError("Location contains invalid characters.")

    return location


def process_location_input(location, allow_empty=False):
    """Process and validate location input consistently"""
    if location is None:
        return None

    # For updates, allow empty string to clear the location
    if allow_empty and location.strip() == "":
        return None

    cleaned_location = validate_location_input(location)
    return cleaned_location if cleaned_location else None
