"""
Database models package.

This module exposes all ORM models for easy import elsewhere in the application.
It uses a structured approach to avoid circular imports while maintaining
a clean public API for importing models.

Usage:
    # Import all models
    from db.models import *

    # Import specific models
    from db.models import AdminUser, Role

    # Import models by category
    from db.models.user import AdminUser
    from db.models.rbac import Role, Permission
"""

# Version of the models package - update when making significant changes
__version__ = "1.0.0"

from .admin_users import (
    AdminUser,
    AdminUserDeviceSession,
    AdminUserVerification,
    PasswordReset,
)

# First, import the base class which has no dependencies
from .base import EventsBase

# Models with dependencies only on base
from .categories import Category, SubCategory

# Import models in dependency order to avoid circular imports at runtime
# Models with no model dependencies
from .config import Config
from .contact_us import ContactUs, ContactUsStatus
from .coupons import Coupon
from .events import BookingStatus, Event, EventBooking, EventSlot, EventStatus
from .new_events import (
    NewEvent,
    NewEventBooking,
    NewEventSeatCategory,
    NewEventSlot,
)

# Models that depend on Organization Profile
from .organizer import BusinessProfile, OrganizerQuery, QueryStatus

# Models with potential circular dependencies - order matters
# Import RBAC models before user models since user.py imports from rbac.py
from .rbac import Permission, Role, RolePermission

# Models that depend on other models
from .users import User, UserDeviceSession, UserPasswordReset, UserVerification

# Define what's available when using "from db.models import *"
__all__ = [
    # Base
    "EventsBase",
    # Configuration
    "Config",
    # Categories
    "Category",
    "SubCategory",
    # Events
    "Event",
    "EventBooking",
    "EventSlot",
    "BookingStatus",
    "EventStatus",
    # New Events
    "NewEvent",
    "NewEventSlot",
    "NewEventSeatCategory",
    "NewEventBooking",
    # Role-Based Access Control
    "Role",
    "Permission",
    "RolePermission",
    # Admin Users
    "AdminUser",
    "PasswordReset",
    "AdminUserDeviceSession",
    "AdminUserVerification",
    # Organizer
    "BusinessProfile",
    # USers
    "User",
    "UserVerification",
    "UserPasswordReset",
    "UserDeviceSession",
    # ContactUs Form
    "ContactUs",
    "ContactUsStatus",
    # Organizer Queries
    "OrganizerQuery",
    "QueryStatus",
    # coupon
    "Coupon",
]

# Model relationships overview:
# - AdminUser has a many-to-one relationship with Role
# - Role has a one-to-many relationship with RolePermission
# - RolePermission links Role and Permission in a many-to-many relationship
# - Category has a one-to-many relationship with SubCategory
