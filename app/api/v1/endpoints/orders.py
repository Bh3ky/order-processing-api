from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db_session
from app.models.order import Order
from app.models.product import Product
from app.schemas.order import OrderCreate

router = APIRouter()

SessionDependency = Annotated[
    AsyncSession,
    Depends(get_db_session),
]


@router.post("/orders", status_code=201)
async def create_order(
    order: OrderCreate,
    session: SessionDependency,
):
    # product-validation logic
    requested_ids = [item.product_id for item in order.items]

    statement = select(Product.id).where(Product.id.in_(requested_ids))

    result = await session.execute(statement)

    found_ids = set(result.scalars().all())

    missing_ids = set(requested_ids) - found_ids

    if missing_ids:
        raise HTTPException(
            status_code=404, detail="One or more products were not found."
        )

    new_order = Order(
        status="pending",
        total_amount=Decimal("0.00"),
    )

    session.add(new_order)
    await session.commit()
    await session.refresh(new_order)

    return new_order
