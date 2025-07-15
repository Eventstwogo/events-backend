from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.models.base import EventsBase


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
    show_in_menu: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    category_status: Mapped[bool] = mapped_column(Boolean, default=False)
    category_tstamp: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    # Relationship to SubCategory
    subcategories: Mapped[list["SubCategory"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
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
    show_in_menu: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    subcategory_status: Mapped[bool] = mapped_column(Boolean, default=False)
    subcategory_tstamp: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    # Relationship to Category
    category: Mapped["Category"] = relationship(back_populates="subcategories")
