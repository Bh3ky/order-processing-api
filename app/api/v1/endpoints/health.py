from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db_session

# TODO: Implement each feature's own router.
# The main application will later include this router under the "/api/v1" prefix.
router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check(
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> dict[str, str]:
    """
    Temporarily, verify that API process and PostgreSQL connection are healthy.
    """
    await session.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }
