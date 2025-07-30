"""
Data processing utilities for handling encrypted and serialized data.

This module provides utility functions for safely handling data that might be
stored as JSON strings or dictionaries, with proper type checking and error handling.
"""

import json
from typing import Any, Dict, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


# Validation functions for organizer data
def validate_organizer_role(role_name: Optional[str]) -> bool:
    """
    Validate if the user has the 'Organizer' role.

    Args:
        role_name: The role name to validate

    Returns:
        bool: True if role is 'Organizer', False otherwise
    """
    return role_name is not None and role_name.lower() == "organizer"


def validate_business_profile_exists(business_profile) -> bool:
    """
    Validate if business profile exists and has required data.

    Args:
        business_profile: The business profile object

    Returns:
        bool: True if business profile exists and is valid, False otherwise
    """
    return business_profile is not None


def create_organizer_validation_error(
    user_id: str, issue: str
) -> Dict[str, Any]:
    """
    Create a standardized error response for organizer validation issues.

    Args:
        user_id: The user ID that failed validation
        issue: Description of the validation issue

    Returns:
        Dict: Error response structure
    """
    return {
        "user_id": user_id,
        "error": f"Validation failed: {issue}",
        "status": "invalid",
    }


async def validate_organizer_with_business_profile(
    db: AsyncSession, user_id: str, business_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive validation for organizer role and business profile.

    Args:
        db: Database session
        user_id: The user ID to validate
        business_id: Optional business ID to validate (if not provided, will get from user)

    Returns:
        Dict containing validation results:
        {
            "is_valid": bool,
            "role_name": str or None,
            "has_business_profile": bool,
            "business_profile_approved": bool or None,
            "error_message": str or None
        }
    """
    from admin_service.services.user_service import get_user_role_name
    from shared.db.models import AdminUser, BusinessProfile

    result = {
        "is_valid": False,
        "role_name": None,
        "has_business_profile": False,
        "business_profile_approved": None,
        "error_message": None,
    }

    try:
        # Get user role name
        role_name = await get_user_role_name(db, user_id)
        result["role_name"] = role_name

        # Check if user has organizer role
        if not validate_organizer_role(role_name):
            current_role = (role_name or "None").upper()
            result["error_message"] = (
                f"Access restricted to organizers only. Your current role '{current_role}' does not have the required permissions."
            )
            return result

        # Get business_id if not provided
        if not business_id:
            user_stmt = select(AdminUser.business_id).where(
                AdminUser.user_id == user_id
            )
            user_result = await db.execute(user_stmt)
            business_id = user_result.scalar_one_or_none()

            if not business_id:
                result["error_message"] = (
                    "No business profile is associated with this organizer account. Please complete your business registration."
                )
                return result

        # Check business profile
        profile_stmt = select(
            BusinessProfile.is_approved,
            BusinessProfile.ref_number,
        ).where(BusinessProfile.business_id == business_id)

        profile_result = await db.execute(profile_stmt)
        profile_data = profile_result.first()

        if profile_data:
            result["has_business_profile"] = True
            result["business_profile_approved"] = profile_data.is_approved
            result["is_valid"] = True
        else:
            result["error_message"] = (
                "Business profile not found. Please complete your business registration to access organizer features."
            )

    except Exception as e:
        result["error_message"] = (
            f"Unable to validate organizer credentials. Please try again or contact support if the issue persists."
        )

    return result
