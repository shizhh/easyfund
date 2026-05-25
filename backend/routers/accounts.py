"""Accounts CRUD router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import get_db
from backend.models import Account, Deposit
from backend.routers.dashboard import invalidate_dashboard_cache
from backend.schemas import AccountCreate, AccountUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class ReorderItem(BaseModel):
    id: str
    sort_order: int


@router.get("")
async def list_accounts(data_dir: str = Depends(get_db)):
    accounts = await Account.all().order_by("sort_order")
    return [a.to_dict() for a in accounts]


@router.get("/{account_id}")
async def get_account(account_id: str, data_dir: str = Depends(get_db)):
    account = await Account.get_or_none(id=account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    return account.to_dict()


@router.post("", status_code=201)
async def create_account(data: AccountCreate, data_dir: str = Depends(get_db)):
    if await Account.get_or_none(id=data.id):
        raise HTTPException(400, "Account id already exists")
    account = await Account.create(**data.model_dump())
    invalidate_dashboard_cache()
    return account.to_dict()


@router.put("/reorder")
async def reorder_accounts(items: list[ReorderItem], data_dir: str = Depends(get_db)):
    for it in items:
        account = await Account.get_or_none(id=it.id)
        if account:
            account.sort_order = it.sort_order
            await account.save()
    invalidate_dashboard_cache()
    return {"ok": True}


@router.put("/{account_id}")
async def update_account(account_id: str, data: AccountUpdate, data_dir: str = Depends(get_db)):
    account = await Account.get_or_none(id=account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(account, key, value)
    await account.save()
    invalidate_dashboard_cache()
    return account.to_dict()


@router.delete("/{account_id}")
async def delete_account(account_id: str, data_dir: str = Depends(get_db)):
    account = await Account.get_or_none(id=account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    # FK CASCADE handles deposits, transactions, holdings, fund_flows
    await account.delete()
    invalidate_dashboard_cache()
    return {"ok": True}
