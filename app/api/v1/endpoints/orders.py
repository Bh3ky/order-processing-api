from fastapi import APIRouter

from app.schemas.order import OrderCreate

router = APIRouter()


@router.post("/orders", status_code=201)
async def create_order(order: OrderCreate):
    # TODO: temporarily return the validated request
    return order