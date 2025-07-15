"""
Custom SQLAlchemy types for the Events2Go application.
"""

from typing import Any, Optional

from sqlalchemy.types import String, TypeDecorator

from shared.core.security import decrypt_data, encrypt_data


class EncryptedString(TypeDecorator):
    """
    Custom SQLAlchemy type that automatically encrypts data before storing
    and decrypts it when loading from the database.
    """

    impl = String
    cache_ok = True  # Required in SQLAlchemy 2.0+ to ensure safe caching of custom types

    def process_bind_param(
        self, value: Optional[str], dialect: Any
    ) -> Optional[str]:
        """Encrypt data before storing in the database."""
        if value is None:
            return None
        return encrypt_data(value)

    def process_result_value(
        self, value: Optional[str], dialect: Any
    ) -> Optional[str]:
        """Decrypt data after retrieving from the database."""
        if value is None:
            return None
        return decrypt_data(value)
