from collections.abc import AsyncGenerator

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.database.dependencies import get_db_session
from app.main import app

test_engine = create_async_engine(
    settings.test_database_url,
    echo=False,
)

TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    # Open one database connection for this test.
    async with test_engine.connect() as connection:
        # Start an outer transaction controlled by the test fixture
        transaction = await connection.begin()

        # Bind the session to that connection.
        # `create_savepoint` lets application code call commit()
        # without committing the outer test transaction.
        session = TestSessionFactory(
            bind=connection,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[TestClient]:
    async def override_get_db_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
