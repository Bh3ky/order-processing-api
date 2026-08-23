"""
SQLAlchemy model registry.

Importing all models here ensures that SQLAlchemy knows about every
mapped class before the ORM mapper configuration or Alembic runs.
"""

from app.models.inventory import Inventory
from app.models.order import Order, OrderItem
from app.models.product import Product

__all__ = [
    "Inventory",
    "Order",
    "OrderItem",
    "Product",
]
