# Third-Party Library Imports
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.models.base import EventsBase

if TYPE_CHECKING:
    from shared.db.models.admin_users import AdminUser


class Role(EventsBase):
    __tablename__ = "e2groles"

    role_id: Mapped[str] = mapped_column(
        String(length=6), primary_key=True, unique=True
    )
    role_name: Mapped[str] = mapped_column(String(length=100), nullable=False)
    role_status: Mapped[bool] = mapped_column(Boolean, default=False)
    role_tstamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    users: Mapped[list["AdminUser"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class Permission(EventsBase):
    __tablename__ = "e2gpermissions"

    permission_id: Mapped[str] = mapped_column(
        String(length=6), primary_key=True, unique=True
    )
    permission_name: Mapped[str] = mapped_column(
        String(length=100), nullable=False
    )
    permission_status: Mapped[bool] = mapped_column(Boolean, default=False)
    permission_tstamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    roles: Mapped[list["RolePermission"]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )


class RolePermission(EventsBase):
    __tablename__ = "e2grolepermissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role_id: Mapped[str] = mapped_column(
        ForeignKey(column="e2groles.role_id"), nullable=False
    )
    permission_id: Mapped[str] = mapped_column(
        ForeignKey(column="e2gpermissions.permission_id"), nullable=False
    )
    rp_status: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    role: Mapped["Role"] = relationship(back_populates="permissions")
    permission: Mapped["Permission"] = relationship(back_populates="roles")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
