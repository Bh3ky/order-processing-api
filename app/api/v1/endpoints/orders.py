from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db_session
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem
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

    statement = select(Product).where(Product.id.in_(requested_ids))

    result = await session.execute(statement)

    products = result.scalars().all()
    found_ids = {product.id for product in products}

    missing_ids = set(requested_ids) - found_ids

    if missing_ids:
        raise HTTPException(
            status_code=404, detail="One or more products were not found."
        )

    products_by_id = {product.id: product for product in products}

    inventory_statement = select(Inventory).where(
        Inventory.product_id.in_(requested_ids)
    )
    inventory_result = await session.execute(inventory_statement)
    inventories = inventory_result.scalars().all()

    inventories_by_product_id = {
        inventory.product_id: inventory for inventory in inventories
    }

    # validate sufficient inventory before modifying any stock
    for item in order.items:
        inventory = inventories_by_product_id.get(item.product_id)

        if inventory is None or inventory.quantity_available < item.quantity:
            # choice: 409 rather than 404; tells us the product exists,
            # but its current inventory state conflicts with the requested
            # operation.
            raise HTTPException(
                status_code=409,
                detail="Insufficient inventory for one or more products.",
            )

    for item in order.items:
        inventory = inventories_by_product_id[item.product_id]
        inventory.quantity_available -= item.quantity

    new_order = Order(
        status="pending",
        total_amount=Decimal("0.00"),
    )

    order_total = Decimal("0.00")

    for item in order.items:
        product = products_by_id[item.product_id]

        unit_price = product.price
        line_total = unit_price * item.quantity

        order_total += line_total

        order_item = OrderItem(
            product_id=product.id,
            quantity=item.quantity,
            unit_price=unit_price,
            line_total=line_total,
        )

        new_order.items.append(order_item)

    new_order.total_amount = order_total

    session.add(new_order)
    await session.commit()
    await session.refresh(new_order)

    return new_order
