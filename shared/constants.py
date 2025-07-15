# Database Pool Constants
POOL_SIZE = 10
MAX_OVERFLOW = 20
POOL_TIMEOUT = 30
POOL_RECYCLE = 3600

# Permission and Role Names
PERMISSION_NAMES = ["MANAGE", "EDIT", "VIEW"]
ROLE_NAMES = ["SUPERADMIN", "ADMIN", "EDITOR", "VIEWER"]

# Mapping: Role → List of Permission Names
ROLE_PERMISSION_NAME_MAP = {
    "SUPERADMIN": ["MANAGE", "EDIT", "VIEW"],
    "ADMIN": ["EDIT", "VIEW"],
    "EDITOR": ["EDIT"],
    "VIEWER": ["VIEW"],
}
