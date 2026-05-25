"""Investment holdings router."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_db
from backend.models import Holding
from backend.routers.dashboard import invalidate_dashboard_cache
from backend.schemas import HoldingCreate, HoldingUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


@router.post("/refresh-prices")
async def refresh_prices(data_dir: str = Depends(get_db)):
    """Fetch live prices for all holdings and update current_price."""
    from backend.services.market import fetch_quotes_parallel, update_holding_prices

    holdings = await Holding.all()
    tickers = list({h.ticker for h in holdings if h.ticker})

    quotes = await fetch_quotes_parallel(tickers)
    updated, errors = await update_holding_prices(quotes)

    invalidate_dashboard_cache()
    return {"updated": updated, "errors": errors}


@router.get("")
async def list_holdings(data_dir: str = Depends(get_db)):
    holdings = await Holding.all()
    return [h.to_dict() for h in holdings]


@router.get("/{holding_id}")
async def get_holding(holding_id: str, data_dir: str = Depends(get_db)):
    holding = await Holding.get_or_none(id=holding_id)
    if not holding:
        raise HTTPException(404, "Holding not found")
    return holding.to_dict()


@router.get("/{holding_id}/pnl")
async def holding_pnl(holding_id: str, data_dir: str = Depends(get_db)):
    item = await Holding.get_or_none(id=holding_id)
    if not item:
        raise HTTPException(404, "Holding not found")
    cost = item.shares * item.avg_cost_price
    market = item.shares * item.current_price
    pnl = market - cost
    pnl_pct = (pnl / cost * 100) if cost else 0
    return {
        "id": holding_id,
        "ticker": item.ticker,
        "shares": item.shares,
        "cost": cost,
        "market_value": market,
        "pnl": pnl,
        "pnl_pct": round(pnl_pct, 2),
        "currency": item.currency,
    }


@router.post("", status_code=201)
async def create_holding(data: HoldingCreate, data_dir: str = Depends(get_db)):
    if await Holding.get_or_none(id=data.id):
        raise HTTPException(400, "Holding id already exists")
    holding = await Holding.create(**data.model_dump())
    invalidate_dashboard_cache()
    return holding.to_dict()


@router.put("/{holding_id}")
async def update_holding(holding_id: str, data: HoldingUpdate, data_dir: str = Depends(get_db)):
    holding = await Holding.get_or_none(id=holding_id)
    if not holding:
        raise HTTPException(404, "Holding not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(holding, key, value)
    await holding.save()
    invalidate_dashboard_cache()
    return holding.to_dict()


@router.delete("/{holding_id}")
async def delete_holding(holding_id: str, data_dir: str = Depends(get_db)):
    holding = await Holding.get_or_none(id=holding_id)
    if not holding:
        raise HTTPException(404, "Holding not found")
    await holding.delete()
    invalidate_dashboard_cache()
    return {"ok": True}
