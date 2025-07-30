"""
Data processing utilities for handling encrypted and serialized data.

This module provides utility functions for safely handling data that might be
stored as JSON strings or dictionaries, with proper type checking and error handling.
"""

import json
from typing import Any, Dict, Union

from shared.core.security import decrypt_dict_values


def safe_decrypt_profile_details(
    profile_details: Union[str, Dict[str, Any], None],
) -> Dict[str, Any]:
    """
    Safely decrypt profile_details that might be stored as a JSON string or dict.

    Args:
        profile_details: The profile details data that might be a JSON string,
                        dict, or None

    Returns:
        Dict[str, Any]: Decrypted profile details dictionary

    Raises:
        ValueError: If decryption fails or data is invalid
    """
    if not profile_details:
        return {}

    try:
        # Check if profile_details is already a dict or needs JSON parsing
        if isinstance(profile_details, str):
            encrypted_profile_dict = json.loads(profile_details)
        else:
            encrypted_profile_dict = profile_details

        return decrypt_dict_values(encrypted_profile_dict)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in profile_details: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to decrypt profile details: {str(e)}")


def safe_parse_json_field(
    field_data: Union[str, Any, None], field_name: str = "field"
) -> Any:
    """
    Safely parse a field that might be stored as a JSON string or already parsed.

    Args:
        field_data: The field data that might be a JSON string or already parsed
        field_name: Name of the field for error messages (optional)

    Returns:
        Any: Parsed data (could be dict, list, or original value)
    """
    if not field_data:
        return {}

    if isinstance(field_data, str):
        try:
            return json.loads(field_data)
        except json.JSONDecodeError:
            # If JSON parsing fails, return the original string as fallback
            return field_data
    else:
        # Already parsed, return as-is
        return field_data


def safe_decrypt_profile_details_with_fallback(
    profile_details: Union[str, Dict[str, Any], None],
) -> Dict[str, Any]:
    """
    Safely decrypt profile_details with error fallback (for non-critical operations).

    This version returns an error dict instead of raising exceptions,
    useful for endpoints that should continue working even if decryption fails.

    Args:
        profile_details: The profile details data that might be a JSON string,
                        dict, or None

    Returns:
        Dict[str, Any]: Decrypted profile details dictionary or error dict
    """
    if not profile_details:
        return {}

    try:
        return safe_decrypt_profile_details(profile_details)
    except Exception as e:
        return {"error": f"Decryption failed: {str(e)}"}


# Convenience function that combines both operations
def process_business_profile_data(
    profile_details: Union[str, Dict[str, Any], None],
    purpose: Union[str, Any, None],
    use_fallback: bool = False,
) -> tuple[Dict[str, Any], Any]:
    """
    Process both profile_details and purpose fields in one call.

    Args:
        profile_details: The profile details data
        purpose: The purpose field data
        use_fallback: If True, use fallback error handling for profile_details

    Returns:
        tuple: (decrypted_profile_details, parsed_purpose)

    Raises:
        ValueError: If decryption fails and use_fallback is False
    """
    if use_fallback:
        decrypted_profile = safe_decrypt_profile_details_with_fallback(
            profile_details
        )
    else:
        decrypted_profile = safe_decrypt_profile_details(profile_details)

    parsed_purpose = safe_parse_json_field(purpose, "purpose")

    return decrypted_profile, parsed_purpose
