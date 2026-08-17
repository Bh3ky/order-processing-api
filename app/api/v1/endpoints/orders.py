from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db_session
from app.models.order import Order
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
    new_order = Order(
        status="pending",
        total_amount=Decimal("0.00"),
    )

    session.add(new_order)
    await session.commit()
    await session.refresh(new_order)

    return new_order