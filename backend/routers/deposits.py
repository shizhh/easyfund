"""Deposits router."""

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_db
from backend.models import Deposit
from backend.routers.dashboard import invalidate_dashboard_cache
from backend.schemas import DepositCreate, DepositUpdate

router = APIRouter(prefix="/api/deposits", tags=["deposits"])


@router.get("")
async def list_deposits(data_dir: str = Depends(get_db)):
    items = await Deposit.all()
    return [d.to_dict() for d in items]


@router.post("", status_code=201)
async def create_deposit(data: DepositCreate, data_dir: str = Depends(get_db)):
    if await Deposit.get_or_none(id=data.id):
        raise HTTPException(400, "Deposit id already exists")
    deposit = await Deposit.create(**data.model_dump())
    invalidate_dashboard_cache()
    return deposit.to_dict()


@router.put("/{deposit_id}")
async def update_deposit(deposit_id: str, data: DepositUpdate, data_dir: str = Depends(get_db)):
    deposit = await Deposit.get_or_none(id=deposit_id)
    if not deposit:
        raise HTTPException(404, "Deposit not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(deposit, key, value)
    await deposit.save()
    invalidate_dashboard_cache()
    return deposit.to_dict()


@router.delete("/{deposit_id}")
async def delete_deposit(deposit_id: str, data_dir: str = Depends(get_db)):
    deposit = await Deposit.get_or_none(id=deposit_id)
    if not deposit:
        raise HTTPException(404, "Deposit not found")
    await deposit.delete()
    invalidate_dashboard_cache()
    return {"ok": True}
