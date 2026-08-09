from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Inventory(Base):
    """Inventory state for a single product."""

    __tablename__ = "inventory"

    __table_args__ = (
        CheckConstraint(
            "quantity_available >= 0",
            name="ck_inventory_quantity_non_negative",
        ),
    )

    # Technical identifier for the inventory record
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # Foreign key linking this inventory record to exactly on product
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id"),
        unique=True,
        nullable=False,
    )

    # Current number of units that can be purchased,
    quantity_available: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ORM-level relationship back to the Project object
    product: Mapped["Product"] = relationship(
        back_populates="inventory"
    )