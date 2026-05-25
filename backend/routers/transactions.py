"""Transactions router."""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth import get_db
from backend.models import Transaction
from backend.schemas import TransactionCreate, TransactionUpdate

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("")
async def list_transactions(
    data_dir: str = Depends(get_db),
    account_id: str | None = Query(None),
    year: int | None = Query(None),
    type: str | None = Query(None),
):
    qs = Transaction.all()
    if account_id:
        qs = qs.filter(account_id=account_id)
    if year:
        qs = qs.filter(date__startswith=str(year))
    if type:
        qs = qs.filter(type=type)
    items = await qs
    return [t.to_dict() for t in items]


@router.get("/pnl/annual")
async def annual_pnl(data_dir: str = Depends(get_db)):
    """Annual P&L summary grouped by account and year."""
    transactions = await Transaction.filter(type="pnl").all()
    result: dict[str, dict[int, float]] = {}
    for t in transactions:
        acct = t.account_id or "unknown"
        yr = int(t.date[:4]) if t.date and len(t.date) >= 4 else 0
        result.setdefault(acct, {})
        result[acct][yr] = result[acct].get(yr, 0) + t.amount
    return result


@router.post("", status_code=201)
async def create_transaction(data: TransactionCreate, data_dir: str = Depends(get_db)):
    if await Transaction.get_or_none(id=data.id):
        raise HTTPException(400, "Transaction id already exists")
    txn = await Transaction.create(**data.model_dump())
    return txn.to_dict()


@router.put("/{transaction_id}")
async def update_transaction(transaction_id: str, data: TransactionUpdate, data_dir: str = Depends(get_db)):
    txn = await Transaction.get_or_none(id=transaction_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(txn, key, value)
    await txn.save()
    return txn.to_dict()


@router.delete("/{transaction_id}")
async def delete_transaction(transaction_id: str, data_dir: str = Depends(get_db)):
    txn = await Transaction.get_or_none(id=transaction_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")
    await txn.delete()
    return {"ok": True}
