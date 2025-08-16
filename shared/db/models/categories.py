from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.models.base import EventsBase
from shared.db.models.new_events import NewEvent

if TYPE_CHECKING:
    from shared.db.models.events import Event


class Category(EventsBase):
    __tablename__ = "e2gcategories"

    category_id: Mapped[str] = mapped_column(
        String, primary_key=True, unique=True
    )
    category_name: Mapped[str] = mapped_column(String, nullable=False)
    category_description: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    category_slug: Mapped[str] = mapped_column(
        String, nullable=False, unique=True
    )
    category_meta_title: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    category_meta_description: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    category_img_thumbnail: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    featured_category: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    promotion_category: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    show_in_menu: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    category_status: Mapped[bool] = mapped_column(Boolean, default=False)
    category_tstamp: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    # Relationships
    subcategories: Mapped[List["SubCategory"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )
    events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="category",
        lazy="dynamic",
    )
    new_events: Mapped[List["NewEvent"]] = relationship(
        "NewEvent",
        back_populates="new_category",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SubCategory(EventsBase):
    __tablename__ = "e2gsubcategories"

    id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    subcategory_id: Mapped[str] = mapped_column(String, unique=True)
    category_id: Mapped[str] = mapped_column(
        ForeignKey(column="e2gcategories.category_id"), nullable=False
    )
    subcategory_name: Mapped[str] = mapped_column(String, nullable=False)
    subcategory_description: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    subcategory_slug: Mapped[str] = mapped_column(
        String, nullable=False, unique=True
    )
    subcategory_meta_title: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    subcategory_meta_description: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    subcategory_img_thumbnail: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    featured_subcategory: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    promotion_subcategory: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    show_in_menu: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    subcategory_status: Mapped[bool] = mapped_column(Boolean, default=False)
    subcategory_tstamp: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    # Relationships
    category: Mapped["Category"] = relationship(back_populates="subcategories")
    events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="subcategory",
        lazy="dynamic",
    )
    new_events: Mapped[List["NewEvent"]] = relationship(
        "NewEvent",
        back_populates="new_subcategory",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
