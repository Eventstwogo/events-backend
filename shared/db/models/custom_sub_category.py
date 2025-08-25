from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.models.base import EventsBase

if TYPE_CHECKING:
    from shared.db.models.categories import Category, SubCategory
    from shared.db.models.new_events import NewEvent


class CustomSubCategory(EventsBase):
    __tablename__ = "e2gcustom_subcategories"

    custom_subcategory_id: Mapped[str] = mapped_column(
        String, primary_key=True, unique=True
    )

    # References
    category_ref_id: Mapped[str] = mapped_column(
        ForeignKey("e2gcategories.category_id", ondelete="CASCADE"),
        nullable=False,
    )
    subcategory_ref_id: Mapped[str] = mapped_column(
        ForeignKey("e2gsubcategories.subcategory_id", ondelete="CASCADE"),
        nullable=True,
    )
    event_ref_id: Mapped[str] = mapped_column(
        ForeignKey("e2gevents_new.event_id", ondelete="CASCADE"),
        nullable=True,
    )

    # Data fields
    custom_subcategory_name: Mapped[str] = mapped_column(
        String, nullable=False, unique=True
    )
    custom_subcategory_status: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    custom_subcategory_tstamp: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    custom_category: Mapped["Category"] = relationship(
        "Category", back_populates="custom_subcategories"
    )
    custom_subcategory: Mapped["SubCategory"] = relationship(
        "SubCategory", back_populates="custom_subcategories"
    )
    custom_event: Mapped["NewEvent"] = relationship(
        "NewEvent", back_populates="custom_subcategories"
    )
