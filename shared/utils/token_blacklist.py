"""
Token blacklist implementation for JWT token revocation.
"""

import time
from datetime import datetime
from typing import Dict

from shared.core.logging_config import get_logger

logger = get_logger(__name__)

# In-memory blacklist storage
# Structure: {token_jti: expiration_timestamp}
_token_blacklist: Dict[str, float] = {}

# Cleanup interval in seconds
_CLEANUP_INTERVAL = 3600  # 1 hour


def add_to_blacklist(jti: str, exp_timestamp: datetime) -> None:
    """
    Add a token to the blacklist.

    Args:
        jti: The token's unique identifier (jti claim)
        exp_timestamp: The token's expiration time
    """
    # Convert datetime to Unix timestamp
    exp_unix_time = exp_timestamp.timestamp()
    _token_blacklist[jti] = exp_unix_time
    logger.info(
        f"Token {jti[:8]}... added to blacklist until {exp_timestamp.isoformat()}"
    )

    # Perform cleanup if needed
    _cleanup_expired()


def is_blacklisted(jti: str) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        jti: The token's unique identifier (jti claim)

    Returns:
        bool: True if token is blacklisted, False otherwise
    """
    # If token is not in blacklist, it's not blacklisted
    if jti not in _token_blacklist:
        return False

    # If token is in blacklist but expired, remove it and return False
    current_time = time.time()
    if _token_blacklist[jti] < current_time:
        del _token_blacklist[jti]
        return False

    # Token is in blacklist and not expired
    return True


def _cleanup_expired() -> None:
    """
    Remove expired tokens from the blacklist.
    This is called periodically to prevent memory leaks.
    """
    # Get current time as Unix timestamp
    current_time = time.time()

    # Find expired tokens
    expired_jtis = [
        jti
        for jti, exp_time in _token_blacklist.items()
        if exp_time < current_time
    ]

    # Remove expired tokens
    for jti in expired_jtis:
        del _token_blacklist[jti]

    if expired_jtis:
        logger.info(
            f"Cleaned up {len(expired_jtis)} expired tokens from blacklist"
        )


def get_blacklist_size() -> int:
    """
    Get the current size of the blacklist.

    Returns:
        int: Number of tokens in the blacklist
    """
    return len(_token_blacklist)
