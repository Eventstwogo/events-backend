# Database Pool Constants
POOL_SIZE = 10
MAX_OVERFLOW = 20
POOL_TIMEOUT = 30
POOL_RECYCLE = 3600

# Constants for Business Profile approval statuses
ONBOARDING_NOT_STARTED = -2
ONBOARDING_REJECTED = -1
ONBOARDING_SUBMITTED = 0
ONBOARDING_UNDER_REVIEW = 1
ONBOARDING_APPROVED = 2

# Permission and Role Names
PERMISSION_NAMES = ["MANAGE", "EDIT", "VIEW"]
ROLE_NAMES = ["SUPERADMIN", "ADMIN", "EDITOR", "VIEWER", "ORGANIZER"]

# Mapping: Role → List of Permission Names
ROLE_PERMISSION_NAME_MAP = {
    "SUPERADMIN": ["MANAGE", "EDIT", "VIEW"],
    "ADMIN": ["EDIT", "VIEW"],
    "EDITOR": ["EDIT"],
    "VIEWER": ["VIEW"],
    "ORGANIZER": ["MANAGE", "EDIT", "VIEW"],
}


# Permission Names - Granular permissions for event booking platform
PERMISSION_NAMES_NEW = [
    # System Management
    "SYSTEM_MANAGE",
    "SYSTEM_CONFIG",
    "SYSTEM_ANALYTICS",
    # User Management
    "USER_MANAGE",
    "USER_VIEW",
    "USER_SUSPEND",
    # Admin User Management
    "ADMIN_USER_MANAGE",
    "ADMIN_USER_VIEW",
    "ADMIN_USER_CREATE",
    # Event Management
    "EVENT_CREATE",
    "EVENT_EDIT",
    "EVENT_DELETE",
    "EVENT_VIEW",
    "EVENT_PUBLISH",
    "EVENT_APPROVE",
    "EVENT_ANALYTICS",
    # Event Slot Management
    "SLOT_CREATE",
    "SLOT_EDIT",
    "SLOT_DELETE",
    "SLOT_VIEW",
    # Category Management
    "CATEGORY_MANAGE",
    "CATEGORY_VIEW",
    # Booking Management (for future implementation)
    "BOOKING_VIEW",
    "BOOKING_MANAGE",
    "BOOKING_REFUND",
    # Financial Management
    "FINANCE_VIEW",
    "FINANCE_MANAGE",
    "REVENUE_VIEW",
    # Content Management
    "CONTENT_MODERATE",
    "CONTENT_EDIT",
    # Reports and Analytics
    "REPORTS_VIEW",
    "REPORTS_EXPORT",
    # Role and Permission Management
    "RBAC_MANAGE",
    "RBAC_VIEW",
]

# Role Names - Hierarchical roles for event booking platform
ROLE_NAMES_NEW = [
    "PLATFORM_ADMIN",  # Ultimate system administrator
    "OPERATIONS_MANAGER",  # Operations and user management
    "EVENT_MANAGER",  # Event approval and management
    "CONTENT_MODERATOR",  # Content moderation and basic management
    "EVENT_ORGANIZER",  # Create and manage own events
    "VENUE_PARTNER",  # Venue-specific event management
    "FINANCE_MANAGER",  # Financial operations and reports
    "CUSTOMER_SUPPORT",  # Customer service and basic operations
    "ANALYST",  # Analytics and reporting only
    "VIEWER",  # Read-only access
]

# Mapping: Role → List of Permission Names
ROLE_PERMISSION_NAME_MAP_NEW = {
    # Platform Administrator - Full system access
    "PLATFORM_ADMIN": [
        "SYSTEM_MANAGE",
        "SYSTEM_CONFIG",
        "SYSTEM_ANALYTICS",
        "USER_MANAGE",
        "USER_VIEW",
        "USER_SUSPEND",
        "ADMIN_USER_MANAGE",
        "ADMIN_USER_VIEW",
        "ADMIN_USER_CREATE",
        "EVENT_CREATE",
        "EVENT_EDIT",
        "EVENT_DELETE",
        "EVENT_VIEW",
        "EVENT_PUBLISH",
        "EVENT_APPROVE",
        "EVENT_ANALYTICS",
        "SLOT_CREATE",
        "SLOT_EDIT",
        "SLOT_DELETE",
        "SLOT_VIEW",
        "CATEGORY_MANAGE",
        "CATEGORY_VIEW",
        "BOOKING_VIEW",
        "BOOKING_MANAGE",
        "BOOKING_REFUND",
        "FINANCE_VIEW",
        "FINANCE_MANAGE",
        "REVENUE_VIEW",
        "CONTENT_MODERATE",
        "CONTENT_EDIT",
        "REPORTS_VIEW",
        "REPORTS_EXPORT",
        "RBAC_MANAGE",
        "RBAC_VIEW",
    ],
    # Operations Manager - User and system operations
    "OPERATIONS_MANAGER": [
        "SYSTEM_ANALYTICS",
        "USER_MANAGE",
        "USER_VIEW",
        "USER_SUSPEND",
        "ADMIN_USER_VIEW",
        "ADMIN_USER_CREATE",
        "EVENT_VIEW",
        "EVENT_APPROVE",
        "EVENT_ANALYTICS",
        "SLOT_VIEW",
        "CATEGORY_VIEW",
        "BOOKING_VIEW",
        "BOOKING_MANAGE",
        "CONTENT_MODERATE",
        "CONTENT_EDIT",
        "REPORTS_VIEW",
        "REPORTS_EXPORT",
        "RBAC_VIEW",
    ],
    # Event Manager - Event approval and oversight
    "EVENT_MANAGER": [
        "EVENT_CREATE",
        "EVENT_EDIT",
        "EVENT_VIEW",
        "EVENT_PUBLISH",
        "EVENT_APPROVE",
        "EVENT_ANALYTICS",
        "SLOT_CREATE",
        "SLOT_EDIT",
        "SLOT_VIEW",
        "CATEGORY_VIEW",
        "BOOKING_VIEW",
        "CONTENT_MODERATE",
        "REPORTS_VIEW",
    ],
    # Content Moderator - Content and basic event management
    "CONTENT_MODERATOR": [
        "EVENT_VIEW",
        "EVENT_EDIT",
        "SLOT_VIEW",
        "SLOT_EDIT",
        "CATEGORY_VIEW",
        "CONTENT_MODERATE",
        "CONTENT_EDIT",
        "USER_VIEW",
        "REPORTS_VIEW",
    ],
    # Event Organizer - Create and manage own events
    "EVENT_ORGANIZER": [
        "EVENT_CREATE",
        "EVENT_EDIT",
        "EVENT_VIEW",
        "EVENT_PUBLISH",
        "SLOT_CREATE",
        "SLOT_EDIT",
        "SLOT_DELETE",
        "SLOT_VIEW",
        "CATEGORY_VIEW",
        "BOOKING_VIEW",
        "REVENUE_VIEW",  # Own events only
        "REPORTS_VIEW",  # Own events only
    ],
    # Venue Partner - Venue-specific event management
    "VENUE_PARTNER": [
        "EVENT_CREATE",
        "EVENT_EDIT",
        "EVENT_VIEW",
        "SLOT_CREATE",
        "SLOT_EDIT",
        "SLOT_VIEW",
        "CATEGORY_VIEW",
        "BOOKING_VIEW",  # Venue events only
        "REPORTS_VIEW",  # Venue events only
    ],
    # Finance Manager - Financial operations
    "FINANCE_MANAGER": [
        "EVENT_VIEW",
        "BOOKING_VIEW",
        "BOOKING_MANAGE",
        "BOOKING_REFUND",
        "FINANCE_VIEW",
        "FINANCE_MANAGE",
        "REVENUE_VIEW",
        "REPORTS_VIEW",
        "REPORTS_EXPORT",
        "USER_VIEW",
    ],
    # Customer Support - Customer service operations
    "CUSTOMER_SUPPORT": [
        "USER_VIEW",
        "EVENT_VIEW",
        "SLOT_VIEW",
        "BOOKING_VIEW",
        "BOOKING_MANAGE",
        "REPORTS_VIEW",
    ],
    # Analyst - Analytics and reporting
    "ANALYST": [
        "SYSTEM_ANALYTICS",
        "EVENT_VIEW",
        "EVENT_ANALYTICS",
        "USER_VIEW",
        "BOOKING_VIEW",
        "REVENUE_VIEW",
        "REPORTS_VIEW",
        "REPORTS_EXPORT",
    ],
    # Viewer - Read-only access
    "VIEWER": [
        "EVENT_VIEW",
        "SLOT_VIEW",
        "CATEGORY_VIEW",
        "USER_VIEW",
        "REPORTS_VIEW",
    ],
}

# Permission Categories for UI grouping and better organization
PERMISSION_CATEGORIES = {
    "System": ["SYSTEM_MANAGE", "SYSTEM_CONFIG", "SYSTEM_ANALYTICS"],
    "User Management": [
        "USER_MANAGE",
        "USER_VIEW",
        "USER_SUSPEND",
        "ADMIN_USER_MANAGE",
        "ADMIN_USER_VIEW",
        "ADMIN_USER_CREATE",
    ],
    "Event Management": [
        "EVENT_CREATE",
        "EVENT_EDIT",
        "EVENT_DELETE",
        "EVENT_VIEW",
        "EVENT_PUBLISH",
        "EVENT_APPROVE",
        "EVENT_ANALYTICS",
    ],
    "Slot Management": ["SLOT_CREATE", "SLOT_EDIT", "SLOT_DELETE", "SLOT_VIEW"],
    "Category Management": ["CATEGORY_MANAGE", "CATEGORY_VIEW"],
    "Booking Management": ["BOOKING_VIEW", "BOOKING_MANAGE", "BOOKING_REFUND"],
    "Financial": ["FINANCE_VIEW", "FINANCE_MANAGE", "REVENUE_VIEW"],
    "Content": ["CONTENT_MODERATE", "CONTENT_EDIT"],
    "Reports & Analytics": ["REPORTS_VIEW", "REPORTS_EXPORT"],
    "Access Control": ["RBAC_MANAGE", "RBAC_VIEW"],
}

# Role Hierarchy - Higher number means higher privilege level
ROLE_HIERARCHY = {
    "PLATFORM_ADMIN": 10,
    "OPERATIONS_MANAGER": 9,
    "EVENT_MANAGER": 8,
    "FINANCE_MANAGER": 7,
    "CONTENT_MODERATOR": 6,
    "EVENT_ORGANIZER": 5,
    "VENUE_PARTNER": 4,
    "CUSTOMER_SUPPORT": 3,
    "ANALYST": 2,
    "VIEWER": 1,
}

# Default role for new organizers
DEFAULT_ORGANIZER_ROLE = "EVENT_ORGANIZER"

# Roles that can create events
EVENT_CREATOR_ROLES = [
    "PLATFORM_ADMIN",
    "OPERATIONS_MANAGER",
    "EVENT_MANAGER",
    "EVENT_ORGANIZER",
    "VENUE_PARTNER",
]

# Roles that require approval for event publishing
APPROVAL_REQUIRED_ROLES = ["EVENT_ORGANIZER", "VENUE_PARTNER"]
