from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.inventory import Inventory


class Product(Base):
    """Product available for purchase."""

    __tablename__ = "products"

    __table_args__ = (
        CheckConstraint(
            "price > 0",
            name="ck_products_price_positive",
        ),
    )

    # TODO: add relationship between product and inventory
    # One product has one inventory record.
    # back_populates links this attribute with Inventory.product,
    # allowing navigation in both directions.
    inventory: Mapped["Inventory"] = relationship(
        back_populates="product",
    )

    # Technical identifier used internally by the application
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Business identifier exposed as part of the product catalogue
    sku: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Exact decimal storage is required for monetary values
    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    # Here, let PostgreSQL assign timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
