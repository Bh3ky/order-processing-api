import asyncio

import pytest

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, text, select

from app.models.inventory import Inventory
from app.models.product import Product

from tests.conftest import TestSessionFactory


@pytest.mark.asyncio
async def test_concurrent_sessions_use_distinct_connections():
    async def get_connection_id() -> int:
        async with TestSessionFactory() as session:
            result = await session.execute(text("SELECT pg_backend_pid()"))
            connection_id = result.scalar_one()

            # hold both connections open until both have queried
            await barrier.wait()
            return connection_id

    barrier = asyncio.Barrier(2)

    connection_ids = await asyncio.gather(
        get_connection_id(),
        get_connection_id(),
    )

    assert connection_ids[0] != connection_ids[1]


@pytest.mark.asyncio
async def test_second_transaction_waits_for_advisory_lock():
    # use a PostgreSQL transaction-scoped advisory lock to demonstrate
    # blocking behaviour without modifying application data
    lock_key = 123456789

    first_has_lock = asyncio.Event()
    release_first = asyncio.Event()
    second_has_lock = asyncio.Event()
    second_is_asking = asyncio.Event()

    async def first_transaction():
        async with TestSessionFactory() as session:
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": lock_key},
            )

            first_has_lock.set()

            # keep the transaction open until the test releases it
            await release_first.wait()
            await session.commit()

    async def second_transaction():
        await first_has_lock.wait()

        second_is_asking.set()

        async with TestSessionFactory() as session:
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": lock_key},
            )

            second_has_lock.set()
            await session.commit()

    first_task = asyncio.create_task(first_transaction())
    second_task = asyncio.create_task(second_transaction())

    try:
        # wait until the first transaction owns the lock
        await asyncio.wait_for(first_has_lock.wait(), timeout=5)

        # wait until the second transaction has started asking for the lock
        await asyncio.wait_for(second_is_asking.wait(), timeout=5)

        with pytest.raises(TimeoutError):
            await asyncio.wait_for(second_has_lock.wait(), timeout=0.5)

        # the second transaction must not have acquired the lock yet
        assert not second_has_lock.is_set()

        release_first.set()

        await asyncio.wait_for(
            asyncio.gather(first_task, second_task),
            timeout=5,
        )

        assert second_has_lock.is_set()
    finally:
        release_first.set()
        for task in (first_task, second_task):
            if not task.done():
                task.cancel()
        await asyncio.gather(first_task, second_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_second_transaction_waits_for_inventory_row_lock():
    """
    Steps:
    1. create a product with 5 inventory and commit
    2. start tx A, lock row with FOR UPDATE and wait
    3. concurrently start tx B, attempt FOR UPDATE (should block until A commits)
    4. after A commits updated inventory, B should see the updated value
    """

    # arrange: committed product with stock 5, in its own session
    async with TestSessionFactory() as session:
        product = Product(
            sku=f"LOCK-TEST-{uuid4()}",
            name="Lock Test Product",
            price=Decimal("9.99"),
        )
        inventory = Inventory(
            product=product,
            quantity_available=5,
        )
        session.add_all([product, inventory])
        await session.commit()

    product_id = product.id

    try:
        # verify: a NEW session can see the committed row
        async with TestSessionFactory() as session:
            result = await session.execute(
                # get the inventory row for the product we just created
                select(Inventory).where(Inventory.product_id == product_id)
            )
            # verify that the initial quantity is 5
            assert result.scalar_one().quantity_available == 5
    finally:
        # cleanup: delete the product and inventory in a new session
        # delete the inventory first before the product to avoid foreign
        # key constraint errors
        async with TestSessionFactory() as session:
            await session.execute(
                delete(Inventory).where(Inventory.product_id == product_id)
            )
            await session.execute(
                delete(Product).where(Product.id == product_id)
            )
            # commit the changes    
            await session.commit()


