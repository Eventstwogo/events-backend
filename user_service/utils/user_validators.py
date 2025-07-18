from shared.db.models import User


def is_password_expired(user: User) -> bool:
    """
    Check if a user's password has expired based on the login status.

    Args:
        user (AdminUser): The user to check.

    Returns:
        bool: True if the password has expired, False otherwise.

    Use cases:
        - Password rotation enforcement
        - Security compliance
        - User session validation

    Example:
        >>> is_password_expired(user)
        False
    """
    if not user:
        return False  # Or raise ValueError("User cannot be None")

    return user.login_status == 2


def is_using_initial_password(user: User) -> bool:
    """
    Check if a user is still using their initial/default password.

    Args:
        user (AdminUser): The user to check.

    Returns:
        bool: True if the user is using their initial password, False otherwise.

    Use cases:
        - First-time login flows
        - Password change enforcement
        - Security policy compliance

    Example:
        >>> is_using_initial_password(user)
        True
    """
    if not user:
        return False  # or raise ValueError("User cannot be None") depending on your design

    # Assume login_status == -1 means user has never changed their password
    return user.login_status == -1


def is_account_locked(user: User) -> bool:
    """
    Check if a user's account is locked due to failed login attempts.

    Args:
        user (AdminUser): The user to check.

    Returns:
        bool: True if the account is locked, False otherwise.

    Use cases:
        - Login attempt validation
        - Account security enforcement
        - User status reporting

    Example:
        >>> is_account_locked(user)
        False
    """
    if not user:
        return False  # Or raise ValueError("User cannot be None")

    return user.login_status == 1


def is_active_user(user: User) -> bool:
    """
    Check if the user account is active.

    Returns:
        bool: True if login_status is 0.
    """
    if not user:
        return False
    return user.login_status == 0


def requires_password_reset(user: User) -> bool:
    """
    Determine if the user must reset their password.

    Returns:
        bool: True if the user is using initial/default password or if the password has expired.
    """
    if not user:
        return False
    return user.login_status in (-1, 2)


def get_user_status_label(user: User) -> str:
    """
    Return a human-readable label for the user's login status.

    Returns:
        str: Description of the user's account status.
    """
    if not user:
        return "Unknown"

    status_map = {
        -1: "Initial Login",
        0: "Active",
        1: "Locked",
        2: "Password Expired",
    }
    return status_map.get(user.login_status, "Unknown")


def is_email_verified(user: User) -> bool:
    """
    Check if a user's email is verified.

    Args:
        user: User object to check

    Returns:
        True if email is verified, False otherwise
    """
    if not user.verification:
        return False
    return user.verification.email_verified


def is_phone_verified(user: User) -> bool:
    """
    Check if a user's phone number is verified.

    Args:
        user: User object to check

    Returns:
        True if phone is verified, False otherwise
    """
    if not user.verification:
        return False
    return user.verification.phone_verified
