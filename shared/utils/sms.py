import secrets
import string
from datetime import datetime, timedelta, timezone

from shared.core.logging_config import get_logger

logger = get_logger(__name__)


def generate_otp(length: int = 6) -> str:
    """
    Generate a numeric OTP (One-Time Password).

    Args:
        length: Length of the OTP to generate (default: 6)

    Returns:
        str: A random string of digits
    """
    return "".join(secrets.choice(string.digits) for _ in range(length))


def send_sms_otp(phone_number: str, otp_code: str) -> bool:
    """
    Send SMS OTP to the provided phone number.

    This is a placeholder implementation. In production, you would integrate
    with an SMS service provider like Twilio, AWS SNS, or similar.

    Args:
        phone_number: The phone number to send OTP to
        otp_code: The OTP code to send

    Returns:
        bool: True if SMS was sent successfully, False otherwise
    """
    try:
        # TODO: Implement actual SMS sending logic here
        # For now, we'll just log the OTP (for development/testing)
        logger.info(f"SMS OTP sent to {phone_number}: {otp_code}")

        # In production, replace this with actual SMS service integration:
        # Example with Twilio:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # message = client.messages.create(
        #     body=f"Your Events2Go verification code is: {otp_code}. Valid for 10 minutes.",
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=phone_number
        # )
        # return message.sid is not None

        # For development, always return True
        return True

    except Exception as e:
        logger.error(f"Failed to send SMS OTP to {phone_number}: {e}")
        return False


def is_otp_expired(created_at: datetime, expiry_minutes: int = 10) -> bool:
    """
    Check if an OTP has expired.

    Args:
        created_at: When the OTP was created
        expiry_minutes: OTP validity in minutes (default: 10)

    Returns:
        bool: True if OTP has expired, False otherwise
    """
    if not created_at:
        return True

    expiry_time = created_at + timedelta(minutes=expiry_minutes)
    return datetime.now(timezone.utc) > expiry_time


def format_phone_number(phone_number: str) -> str:
    """
    Format phone number for display (mask middle digits).

    Args:
        phone_number: The phone number to format

    Returns:
        str: Formatted phone number with masked digits
    """
    if not phone_number or len(phone_number) < 8:
        return phone_number

    # For phone numbers like +1234567890, show +123****890
    if phone_number.startswith("+"):
        if len(phone_number) <= 7:
            return phone_number
        return f"{phone_number[:4]}{'*' * (len(phone_number) - 7)}{phone_number[-3:]}"
    else:
        # For numbers without +, show first 3 and last 3 digits
        if len(phone_number) <= 6:
            return phone_number
        return f"{phone_number[:3]}{'*' * (len(phone_number) - 6)}{phone_number[-3:]}"


class SMSService:
    """
    SMS service class for handling OTP operations.
    """

    def __init__(self, otp_length: int = 6, expiry_minutes: int = 10):
        self.otp_length = otp_length
        self.expiry_minutes = expiry_minutes

    def send_verification_otp(self, phone_number: str) -> tuple[str, bool]:
        """
        Generate and send verification OTP to phone number.

        Args:
            phone_number: The phone number to send OTP to

        Returns:
            tuple: (otp_code, success_status)
        """
        otp_code = generate_otp(self.otp_length)
        success = send_sms_otp(phone_number, otp_code)
        return otp_code, success

    def verify_otp(
        self, provided_otp: str, stored_otp: str, created_at: datetime
    ) -> bool:
        """
        Verify if the provided OTP matches the stored OTP and is not expired.

        Args:
            provided_otp: OTP provided by user
            stored_otp: OTP stored in database
            created_at: When the OTP was created

        Returns:
            bool: True if OTP is valid, False otherwise
        """
        if not provided_otp or not stored_otp:
            return False

        if provided_otp != stored_otp:
            return False

        return not is_otp_expired(created_at, self.expiry_minutes)


# Default SMS service instance
sms_service = SMSService()
