"""
Secure string generators using Python's secrets module.
Includes combinations of digits, uppercase, lowercase characters,
and verification tokens.
"""

import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone

from typing_extensions import LiteralString


def generate_digits_uppercase(length: int = 6) -> str:
    """
    Generate a secure random string with digits and uppercase letters.

    Args:
        length (int): Length of the string to generate. Default is 6.

    Returns:
        str: A secure random string.
    """
    chars: LiteralString = string.digits + string.ascii_uppercase
    return "".join(secrets.choice(seq=chars) for _ in range(length))


# for snos and ids


def generate_lower_uppercase(length: int = 6) -> str:
    """
    Generate a secure random string with lowercase and uppercase letters.

    Args:
        length (int): Length of the string to generate. Default is 6.

    Returns:
        str: A secure random string.
    """
    chars: LiteralString = string.ascii_lowercase + string.ascii_uppercase
    return "".join(secrets.choice(seq=chars) for _ in range(length))


def generate_digits_lowercase(length: int = 6) -> str:
    """
    Generate a secure random string with digits and lowercase letters.

    Args:
        length (int): Length of the string to generate. Default is 6.

    Returns:
        str: A secure random string.
    """
    chars: LiteralString = string.digits + string.ascii_lowercase
    return "".join(secrets.choice(seq=chars) for _ in range(length))


# Event IDS
def generate_digits_upper_lower_case(length: int = 6) -> str:
    """
    Generate a secure random string with digits, uppercase and lowercase letters.

    Args:
        length (int): Length of the string to generate. Default is 6.

    Returns:
        str: A secure random string.
    """
    chars: LiteralString = (
        string.digits + string.ascii_lowercase + string.ascii_uppercase
    )
    return "".join(secrets.choice(seq=chars) for _ in range(length))


def generate_verification_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure verification token.

    Args:
        length: Byte length of the token to generate (default: 32)
               The resulting string will be longer due to base64 encoding

    Returns:
        str: A secure random token
    """
    return secrets.token_urlsafe(length)


def get_token_expiry(hours: int = 24) -> datetime:
    """
    Get a datetime representing token expiry.

    Args:
        hours: Number of hours until expiry (default: 24)

    Returns:
        datetime: A datetime representing token expiry
    """
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def generate_uuid() -> str:
    """
    Generate a random UUID.

    Returns:
        str: A random UUID string
    """
    return str(uuid.uuid4())


# # Optional: Sample usage when run as a script
# if __name__ == "__main__":
#     print("Digits + Uppercase: ", generate_digits_uppercase())
#     print("Lowercase + Uppercase: ", generate_lower_uppercase())
#     print("Digits + Lowercase: ", generate_digits_lowercase())
#     print("Verification Token: ", generate_verification_token())
#     print("OTP: ", generate_otp())
#     print("UUID: ", generate_uuid())
