from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    # the client references an existing product
    product_id: UUID
    # orders must contain a positive number of units
    quantity: int = Field(gt=0) 


class OrderCreate(BaseModel):
    # an order must contain at least one item
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime

