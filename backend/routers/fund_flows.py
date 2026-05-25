"""Fund flow router — track deposits/withdrawals with FX rates."""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth import get_db
from backend.models import Account, FundFlow, Holding
from backend.routers.dashboard import invalidate_dashboard_cache
from backend.schemas import FundFlowCreate, FundFlowUpdate
from backend.services.currency import get_all_rates

router = APIRouter(prefix="/api/fund-flows", tags=["fund-flows"])


@router.get("")
async def list_fund_flows(account_id: str | None = Query(None), data_dir: str = Depends(get_db)):
    qs = FundFlow.all()
    if account_id:
        qs = qs.filter(account_id=account_id)
    items = await qs
    return [f.to_dict() for f in items]


@router.post("", status_code=201)
async def create_fund_flow(data: FundFlowCreate, data_dir: str = Depends(get_db)):
    if await FundFlow.get_or_none(id=data.id):
        raise HTTPException(400, "Fund flow id already exists")
    flow = await FundFlow.create(**data.model_dump())
    invalidate_dashboard_cache()
    return flow.to_dict()


@router.put("/{flow_id}")
async def update_fund_flow(flow_id: str, data: FundFlowUpdate, data_dir: str = Depends(get_db)):
    flow = await FundFlow.get_or_none(id=flow_id)
    if not flow:
        raise HTTPException(404, "Fund flow not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(flow, key, value)
    await flow.save()
    invalidate_dashboard_cache()
    return flow.to_dict()


@router.delete("/{flow_id}")
async def delete_fund_flow(flow_id: str, data_dir: str = Depends(get_db)):
    flow = await FundFlow.get_or_none(id=flow_id)
    if not flow:
        raise HTTPException(404, "Fund flow not found")
    await flow.delete()
    invalidate_dashboard_cache()
    return {"ok": True}


@router.get("/analysis")
async def fund_flow_analysis(account_id: str = Query(...), data_dir: str = Depends(get_db)):
    """Compute fund flow analysis for an investment account."""
    flows = await FundFlow.filter(account_id=account_id).all()

    account = await Account.get_or_none(id=account_id)
    if not account:
        raise HTTPException(404, "Account not found")

    rates = await get_all_rates()

    # Current value: balances + holdings at today's rates
    current_value_cny = 0.0
    for b in (account.balances or []):
        current_value_cny += b["amount"] * rates.get(b["currency"], 1.0)
    holdings = await Holding.filter(account_id=account_id).all()
    for h in holdings:
        mv = h.shares * h.current_price
        current_value_cny += mv * rates.get(h.currency, 1.0)

    # Historical flow calculations
    total_deposited_cny = 0.0
    total_withdrawn_cny = 0.0
    deposits_at_current_rate_cny = 0.0

    for f in flows:
        amount_cny_historical = f.amount * f.rate_at_time
        amount_cny_current = f.amount * rates.get(f.currency, 1.0)

        if f.type == "deposit":
            total_deposited_cny += amount_cny_historical
            deposits_at_current_rate_cny += amount_cny_current
        else:
            total_withdrawn_cny += amount_cny_historical

    net_invested_cny = total_deposited_cny - total_withdrawn_cny
    unrealized_pnl = current_value_cny - net_invested_cny
    unrealized_pnl_pct = (unrealized_pnl / net_invested_cny * 100) if net_invested_cny else 0

    # FX impact: deposits at today's rate vs historical rate
    fx_gain_loss = deposits_at_current_rate_cny - total_deposited_cny
    investment_gain_loss = unrealized_pnl - fx_gain_loss

    return {
        "account_id": account_id,
        "flows": [f.to_dict() for f in flows],
        "total_deposited_cny": round(total_deposited_cny, 2),
        "total_withdrawn_cny": round(total_withdrawn_cny, 2),
        "net_invested_cny": round(net_invested_cny, 2),
        "current_value_cny": round(current_value_cny, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
        "deposits_at_current_rate_cny": round(deposits_at_current_rate_cny, 2),
        "fx_gain_loss": round(fx_gain_loss, 2),
        "investment_gain_loss": round(investment_gain_loss, 2),
    }
