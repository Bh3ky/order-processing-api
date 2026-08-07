from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Product(Base):
    """Product available for purchase."""

    __tablename__ = "products"

    __table_args__ = (
        CheckConstraint(
            "price > 0",
            name="ck_products_price_non_negative",
        ),
    )

    # Technical identifier used internally by the application
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4
    )

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
