from uuid import UUID

from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    # the client references an existing product
    product_id: UUID
    # orders must contain a positive number of units
    quantity: int = Field(gt=0) 


class OrderCreate(BaseModel):
    # an order must contain at least one item
    items: list[OrderItemCreate] = Field(min_length=1)
