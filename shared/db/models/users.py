from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    select,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql.selectable import Select

from shared.core.security import generate_searchable_hash
from shared.db.models.base import EventsBase
from shared.db.types import EncryptedString

if TYPE_CHECKING:
    from shared.db.models.events import EventBooking


# User Table
class User(EventsBase):
    __tablename__ = "e2gusers"

    user_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, unique=True, nullable=False
    )
    # Encrypted fields using custom type
    username_encrypted: Mapped[str] = mapped_column(
        EncryptedString(255), nullable=False
    )
    first_name_encrypted: Mapped[Optional[str]] = mapped_column(
        EncryptedString(255), nullable=True
    )
    last_name_encrypted: Mapped[Optional[str]] = mapped_column(
        EncryptedString(255), nullable=True
    )
    email_encrypted: Mapped[str] = mapped_column(
        EncryptedString(255), nullable=False
    )
    phone_number_encrypted: Mapped[Optional[str]] = mapped_column(
        EncryptedString(255), nullable=True, default="0"
    )

    # Hash fields for efficient querying
    username_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    first_name_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    last_name_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    email_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    phone_number_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_picture: Mapped[Optional[str]] = mapped_column(
        String(255), default=None
    )

    days_180_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    days_180_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )

    login_status: Mapped[int] = mapped_column(
        Integer, default=-1, nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )
    account_locked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_login_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    successful_login_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships
    verification: Mapped[Optional["UserVerification"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    password_reset: Mapped[Optional["UserPasswordReset"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    device_sessions: Mapped[List["UserDeviceSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    event_bookings: Mapped[List["EventBooking"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    # Properties for username, first_name, last_name, email, and phone_number.
    @property
    def username(self) -> str:
        """Get the decrypted username."""
        return self.username_encrypted

    @username.setter
    def username(self, value: str) -> None:
        """Set the username and update its hash."""
        self.username_encrypted = value
        self.username_hash = generate_searchable_hash(value)

    @property
    def first_name(self) -> Optional[str]:
        """Get the decrypted first name."""
        return self.first_name_encrypted

    @first_name.setter
    def first_name(self, value: Optional[str]) -> None:
        """Set the first name and update its hash."""
        self.first_name_encrypted = value
        self.first_name_hash = (
            generate_searchable_hash(value) if value else None
        )

    @property
    def last_name(self) -> Optional[str]:
        """Get the decrypted last name."""
        return self.last_name_encrypted

    @last_name.setter
    def last_name(self, value: Optional[str]) -> None:
        """Set the last name and update its hash."""
        self.last_name_encrypted = value
        self.last_name_hash = generate_searchable_hash(value) if value else None

    @property
    def email(self) -> str:
        """Get the decrypted email."""
        return self.email_encrypted

    @email.setter
    def email(self, value: str) -> None:
        """Set the email and update its hash."""
        self.email_encrypted = value
        self.email_hash = generate_searchable_hash(value)

    @property
    def phone_number(self) -> Optional[str]:
        """Get the decrypted phone number."""
        return self.phone_number_encrypted

    @phone_number.setter
    def phone_number(self, value: Optional[str]) -> None:
        """Set the phone number and update its hash."""
        self.phone_number_encrypted = value
        self.phone_number_hash = (
            generate_searchable_hash(value) if value else None
        )

    @staticmethod
    def by_username_query(username: str):
        """
        Create a query to find a user by username using the hash for efficient querying.

        Args:
            username: The username to search for

        Returns:
            A SQLAlchemy select statement that can be executed with a database session
        """
        username_hash = generate_searchable_hash(username)
        return select(User).where(User.username_hash == username_hash)

    @staticmethod
    def by_email_query(email: str):
        """
        Create a query to find a user by email using the hash for efficient querying.

        Args:
            email: The email to search for

        Returns:
            A SQLAlchemy select statement that can be executed with a database session
        """

        email_hash = generate_searchable_hash(email)
        return select(User).where(User.email_hash == email_hash)

    @staticmethod
    def by_phone_number_query(phone_number: str):
        """
        Create a query to find a user by phone number using the hash for efficient querying.

        Args:
            phone_number: The phone number to search for

        Returns:
                A SQLAlchemy select statement that can be executed with a database session
        """

        phone_number_hash = generate_searchable_hash(phone_number)
        return select(User).where(User.phone_number_hash == phone_number_hash)


# UserVerification Table
class UserVerification(EventsBase):
    __tablename__ = "e2guserverifications"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("e2gusers.user_id"), primary_key=True
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    phone_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255), default=None
    )
    email_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )

    phone_verification_code: Mapped[Optional[str]] = mapped_column(
        String(6), default=None
    )
    phone_code_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )

    user: Mapped["User"] = relationship(back_populates="verification")


# PasswordReset Table
class UserPasswordReset(EventsBase):
    __tablename__ = "e2guserpasswordresets"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("e2gusers.user_id"), primary_key=True
    )

    reset_password_token: Mapped[Optional[str]] = mapped_column(
        String(255), default=None
    )
    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )
    last_reset_done_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )

    user: Mapped["User"] = relationship(back_populates="password_reset")


# AdminUserDeviceSession Table
class UserDeviceSession(EventsBase):
    __tablename__ = "e2guserdevicesessions"

    session_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("e2gusers.user_id"), nullable=False
    )

    # Basic device information
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45)
    )  # IPv4 or IPv6
    device_name: Mapped[Optional[str]] = mapped_column(String(255))
    user_agent: Mapped[Optional[str]] = mapped_column(String(1024))

    # Enhanced device information
    device_fingerprint: Mapped[Optional[str]] = mapped_column(String(64))
    device_family: Mapped[Optional[str]] = mapped_column(String(100))
    device_brand: Mapped[Optional[str]] = mapped_column(String(100))
    device_model: Mapped[Optional[str]] = mapped_column(String(100))
    device_type: Mapped[Optional[str]] = mapped_column(String(50))

    # Browser information
    browser_family: Mapped[Optional[str]] = mapped_column(String(100))
    browser_version: Mapped[Optional[str]] = mapped_column(String(100))

    # Operating system information
    os_family: Mapped[Optional[str]] = mapped_column(String(100))
    os_version: Mapped[Optional[str]] = mapped_column(String(100))

    # Location information
    location: Mapped[Optional[str]] = mapped_column(String(255))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    country_code: Mapped[Optional[str]] = mapped_column(String(10))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    latitude: Mapped[Optional[str]] = mapped_column(String(20))
    longitude: Mapped[Optional[str]] = mapped_column(String(20))
    timezone: Mapped[Optional[str]] = mapped_column(String(50))
    isp: Mapped[Optional[str]] = mapped_column(String(255))

    # Additional metadata
    language: Mapped[Optional[str]] = mapped_column(String(20))
    is_mobile: Mapped[bool] = mapped_column(Boolean, default=False)
    is_tablet: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pc: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)

    # Session status
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    logged_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    logged_out_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=None
    )

    user: Mapped["User"] = relationship(back_populates="device_sessions")
