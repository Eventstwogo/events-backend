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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from shared.core.security import generate_searchable_hash
from shared.db.models.base import EventsBase
from shared.db.types import EncryptedString

if TYPE_CHECKING:
    from shared.db.models.events import Event
    from shared.db.models.organizer import BusinessProfile
    from shared.db.models.rbac import Role


# AdminUser Table
class AdminUser(EventsBase):
    __tablename__ = "e2gadminusers"

    user_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, unique=True, nullable=False
    )
    role_id: Mapped[str] = mapped_column(
        ForeignKey("e2groles.role_id"), nullable=False
    )

    # Encrypted fields using custom type
    username_encrypted: Mapped[str] = mapped_column(
        EncryptedString(255), nullable=False
    )
    email_encrypted: Mapped[str] = mapped_column(
        EncryptedString(255), nullable=False
    )

    # Hash fields for efficient querying
    username_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    email_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
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
    is_verified: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    profile_id: Mapped[str] = mapped_column(
        String(6), nullable=False, unique=True
    )
    business_id: Mapped[str] = mapped_column(
        String(6), nullable=False, unique=True
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
    role: Mapped["Role"] = relationship(back_populates="users")
    # Relationships
    verification: Mapped[Optional["AdminUserVerification"]] = relationship(
        back_populates="admin_user", uselist=False, cascade="all, delete-orphan"
    )
    password_reset: Mapped[Optional["PasswordReset"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    device_sessions: Mapped[list["AdminUserDeviceSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    organized_events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="organizer",
        lazy="dynamic",
    )
    business_profile: Mapped[Optional["BusinessProfile"]] = relationship(
        "BusinessProfile",
        back_populates="organizer_login",
        uselist=False,
        cascade="all, delete-orphan",
    )
    user_profile: Mapped[Optional["AdminUserProfile"]] = relationship(
        "AdminUserProfile",
        back_populates="admin_user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Properties for username and email
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
    def email(self) -> str:
        """Get the decrypted email."""
        return self.email_encrypted

    @email.setter
    def email(self, value: str) -> None:
        """Set the email and update its hash."""
        self.email_encrypted = value
        self.email_hash = generate_searchable_hash(value)

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
        return select(AdminUser).where(AdminUser.username_hash == username_hash)

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
        return select(AdminUser).where(AdminUser.email_hash == email_hash)


# UserVerification Table
class AdminUserVerification(EventsBase):
    __tablename__ = "e2gadminuserverifications"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("e2gadminusers.user_id"), primary_key=True
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

    admin_user: Mapped["AdminUser"] = relationship(
        back_populates="verification"
    )


# PasswordReset Table
class PasswordReset(EventsBase):
    __tablename__ = "e2gpasswordresets"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("e2gadminusers.user_id"), primary_key=True
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

    user: Mapped["AdminUser"] = relationship(back_populates="password_reset")


# AdminUserDeviceSession Table
class AdminUserDeviceSession(EventsBase):
    __tablename__ = "e2gadminuserdevicesessions"

    session_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("e2gadminusers.user_id"), nullable=False
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

    user: Mapped["AdminUser"] = relationship(back_populates="device_sessions")


class AdminUserProfile(EventsBase):
    __tablename__ = "e2gadminuserprofiles"

    profile_id: Mapped[str] = mapped_column(
        String(6), ForeignKey("e2gadminusers.profile_id"), primary_key=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(15), unique=True, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    social_links: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    preferences: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    profile_bio: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationship to AdminUser
    admin_user: Mapped["AdminUser"] = relationship(
        "AdminUser", back_populates="user_profile", uselist=False, lazy="joined"
    )


class AboutUs(EventsBase):
    __tablename__ = "e2gaboutus"

    about_us_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, unique=True, nullable=False
    )
    about_us_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    about_us_status: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Partners(EventsBase):
    __tablename__ = "e2gpartners"

    partner_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, unique=True, nullable=False
    )
    logo: Mapped[str] = mapped_column(String(255), nullable=False)
    website_url: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_status: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Advertisement(EventsBase):
    __tablename__ = "e2gadvertisement"

    ad_id: Mapped[str] = mapped_column(
        String(6), primary_key=True, unique=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    banner: Mapped[str] = mapped_column(String(255), nullable=False)
    target_url: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    ad_status: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
