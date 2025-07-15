import html
import re
from typing import Any, Optional

from fastapi import status
from fastapi.responses import JSONResponse

from shared.core.api_response import api_response
from shared.utils.validators import has_excessive_repetition

# =============================================================================
# SECURITY VALIDATORS
# =============================================================================


def escape_html(content: str) -> str:
    """
    Escapes HTML tags from user input to prevent XSS attacks.

    Args:
        content (str): The input string to escape

    Returns:
        str: HTML-escaped string

    Use cases:
        - Sanitizing user input before displaying in web pages
        - Preventing XSS attacks in form submissions
        - Safe rendering of user-generated content

    Example:
        >>> escape_html('<script>alert("xss")</script>')
        '&lt;script&gt;alert("xss")&lt;/script&gt;'
    """
    return html.escape(s=content)


def contains_xss(content: str) -> bool:
    """
    Detects potential XSS (Cross-Site Scripting) attempts in content.

    Args:
        content (str): The content to check for XSS patterns

    Returns:
        bool: True if XSS-like script tags are found, False otherwise

    Use cases:
        - Pre-validation of user input before processing
        - Content filtering in forums and comment systems
        - Security auditing of user-submitted data

    Example:
        >>> contains_xss('<script>alert("hack")</script>')
        True
        >>> contains_xss('Hello world')
        False
    """
    content_lower: str = content.lower()
    return bool(re.search(r"<\s*script[^>]*>", content_lower))


def contains_sql_injection(content: str) -> bool:
    """
    Detects potential SQL injection patterns in content.

    Args:
        content (str): The content to check for SQL injection patterns

    Returns:
        bool: True if SQL injection keywords are detected, False otherwise

    Use cases:
        - Input validation for database queries
        - Security filtering for search forms
        - Preventing SQL injection attacks

    Example:
        >>> contains_sql_injection("'; DROP TABLE users; --")
        True
        >>> contains_sql_injection('normal search term')
        False
    """
    # More specific patterns to avoid false positives with legitimate words
    sql_injection_patterns: list[str] = [
        r"\b(select|insert|delete|drop|truncate|exec|union)\s+",  # SQL keywords followed by space
        r"--",  # SQL comments
        r";",  # Statement terminators
        r"or\s+1\s*=\s*1",  # Classic injection pattern
        r"'\s*or\s+",  # Quote-based injection
        r'"\s*or\s+',  # Double quote-based injection
        r"\bunion\s+select\b",  # Union-based injection
        r"\bdrop\s+table\b",  # Table dropping
    ]
    content_lower: str = content.lower()
    return any(
        re.search(pattern, content_lower) for pattern in sql_injection_patterns
    )


def sanitize_input(content: Optional[str]) -> str | JSONResponse:
    """
    Validates user input:
    - Rejects if any HTML tags are present
    - Rejects if dangerous SQL patterns
    (quotes, semicolons, comments, or combined keywords) are present

    Allows safe natural words like "drop", "select" in non-malicious contexts.

    Args:
        content (Optional[str]): Raw user input

    Returns:
        str: Trimmed valid string, raises HTTPException if invalid
    """
    if not content:
        return ""

    content = content.strip()

    # Check for HTML tags
    if re.search(r"<.*?>", content):
        return api_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Input must not contain HTML tags.",
            log_error=False,
        )

    # Check for common SQL injection characters and patterns
    forbidden_patterns = [
        r"--",  # SQL comment
        r";",  # SQL statement separator
        r"'",
        r'"',
        r"`",
        (
            r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC|TRUNCATE)\b"
            r".*\b(FROM|TABLE|INTO|WHERE)\b"
        ),
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Input contains forbidden SQL-related patterns.",
                log_error=False,
            )

    return content


def validate_strict_input(field_name: str, value: Any) -> None:
    """
    Performs strict validation with exception raising for invalid inputs.

    Args:
        field_name (str): Name of the field being validated (for error messages)
        value (Any): The value to validate

    Raises:
        ValueError: If validation fails with specific error message

    Use cases:
        - Form validation with detailed error reporting
        - API input validation
        - Strict data integrity checks

    Example:
        >>> validate_strict_input('username', '<script>alert("xss")</script>')
        ValueError: username contains potentially malicious content.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    if contains_xss(value):
        raise ValueError(
            f"{field_name} contains potentially malicious content."
        )
    if contains_sql_injection(value):
        raise ValueError(f"{field_name} contains SQL injection patterns.")
    if has_excessive_repetition(value):
        raise ValueError(
            f"{field_name} contains excessive or too many repeated characters."
        )
