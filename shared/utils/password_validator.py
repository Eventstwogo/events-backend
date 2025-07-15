"""
Password validation utilities for ensuring strong password requirements.
"""

import re
import string
from typing import Dict, Union

from fastapi import status


class PasswordValidator:
    """
    A utility class for validating passwords based on security criteria.
    """

    SPECIAL_CHARACTERS = set(string.punctuation)
    MIN_LENGTH = 8
    MAX_LENGTH = 14

    @staticmethod
    def is_strong_password(password: str) -> bool:
        """
        Quick boolean validation using regex.

        Requirements:
            - At least 8 characters
            - At least 1 uppercase letter
            - At least 1 lowercase letter
            - At least 1 number
            - At least 1 special character
        """
        pattern = (
            r"^(?=.*[a-z])"  # at least one lowercase letter
            r"(?=.*[A-Z])"  # at least one uppercase letter
            r"(?=.*\d)"  # at least one digit
            r"(?=.*[@$!%*?&#])"  # at least one special character
            r"[A-Za-z\d@$!%*?&#]{8,14}$"  # 8-14 total characters
        )
        return bool(re.fullmatch(pattern, password))

    @classmethod
    def validate(cls, password: str) -> Dict[str, Union[int, str]]:
        """
        Full validation with error messages.

        :param password: Password to validate
        :return: Dictionary with status_code and message
        """
        if not cls.MIN_LENGTH <= len(password) <= cls.MAX_LENGTH:
            return {
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": (
                    f"Password length must be between {cls.MIN_LENGTH} and "
                    f"{cls.MAX_LENGTH} characters."
                ),
            }

        conditions = {
            "uppercase": any(c.isupper() for c in password),
            "lowercase": any(c.islower() for c in password),
            "digit": any(c.isdigit() for c in password),
            "special_character": any(
                c in cls.SPECIAL_CHARACTERS for c in password
            ),
        }

        if all(conditions.values()):
            return {
                "status_code": status.HTTP_200_OK,
                "message": "Password is valid.",
            }

        missing = [
            k.replace("_", " ").capitalize()
            for k, v in conditions.items()
            if not v
        ]

        return {
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": (
                "Password must contain at least one: " f"{', '.join(missing)}."
            ),
        }
