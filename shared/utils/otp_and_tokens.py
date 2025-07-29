import secrets
import string
from datetime import datetime, timedelta, timezone


def generate_verification_tokens(
    length: int = 32, expires_in_minutes: int = 30
) -> tuple[str, datetime]:
    """
    Generate a cryptographically secure verification token with expiration time.

    Args:
        length: Byte length of the token to generate (default: 32)
               The resulting string will be longer due to base64 encoding
        expires_in_minutes: Number of minutes until the token expires (default: 30)

    Returns:
        tuple[str, datetime]: A secure random token and its expiration time
    """
    token = secrets.token_urlsafe(length)
    expiration_time = datetime.now(timezone.utc) + timedelta(
        minutes=expires_in_minutes
    )
    return token, expiration_time


def generate_otps(
    length: int = 6, expires_in_minutes: int = 10
) -> tuple[str, datetime]:
    """
    Generate a numeric OTP (One-Time Password) with expiration time.

    Args:
        length: Length of the OTP to generate (default: 6)
        expires_in_minutes: Number of minutes until the OTP expires (default: 10)

    Returns:
        tuple[str, datetime]: A random string of digits and its expiration time
    """
    otp = "".join(secrets.choice(string.digits) for _ in range(length))
    expiration_time = datetime.now(timezone.utc) + timedelta(
        minutes=expires_in_minutes
    )
    return otp, expiration_time
