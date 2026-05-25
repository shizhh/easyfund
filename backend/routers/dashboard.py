"""Dashboard aggregation router."""

from datetime import date

from fastapi import APIRouter, Depends

from backend.auth import get_current_user, get_db
from backend.models import Account, Holding, ExchangeRate
from backend.services.currency import get_all_rates

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# In-memory cache for dashboard aggregation results.
# Invalidated when underlying data changes (accounts, holdings, rates).
_dashboard_cache: dict[str, dict] = {}


def invalidate_dashboard_cache():
    """Clear the dashboard cache. Call from mutation endpoints."""
    _dashboard_cache.clear()


def _to_cny(amount: float, currency: str, rates: dict) -> float:
    return amount * rates.get(currency, 1.0)


@router.get("/overview")
async def overview(data_dir: str = Depends(get_db), include_account_totals: bool = False):
    """Asset overview: total, by category, exchange rates."""
    cached = _dashboard_cache.get(f"{data_dir}:overview")
    # Don't serve cached result when caller needs account_totals (snapshot path)
    if cached is not None and not include_account_totals:
        return cached

    rates = await get_all_rates()
    accounts = await Account.all()
    holdings = await Holding.all()

    category_totals: dict[str, float] = {}
    total = 0.0

    excluded_ids = {acct.id for acct in accounts if acct.exclude_from_total}

    for acct in accounts:
        if acct.id in excluded_ids:
            continue
        cat = acct.category
        cat_cny = 0.0
        for b in (acct.balances or []):
            cat_cny += _to_cny(b["amount"], b["currency"], rates)
        if cat == "insurance" and cat_cny == 0:
            cat_cny = (acct.ins_premium or 0) * (acct.ins_paid_periods or 0)
        if cat == "future_cash" and cat_cny == 0:
            cat_cny = sum(sa.get("amount", 0) for sa in (acct.sub_accounts or []))
        category_totals[cat] = category_totals.get(cat, 0) + cat_cny
        total += cat_cny

    for h in holdings:
        if h.account_id in excluded_ids:
            continue
        mv = h.shares * h.current_price
        mv_cny = _to_cny(mv, h.currency, rates)
        category_totals["investment"] = category_totals.get("investment", 0) + mv_cny
        total += mv_cny

    category_pcts = {
        cat: round(v / total * 100, 1) if total else 0
        for cat, v in category_totals.items()
    }

    result = {
        "total_cny": round(total, 2),
        "category_totals": category_totals,
        "category_pcts": category_pcts,
        "rates": rates,
        "account_count": len(accounts),
        "holding_count": len(holdings),
    }
    if include_account_totals:
        # Build per-account totals in a single pass alongside the category aggregation above.
        account_totals = {}
        for acct in accounts:
            if acct.id in excluded_ids:
                continue
            acct_cny = 0.0
            for b in (acct.balances or []):
                acct_cny += _to_cny(b["amount"], b["currency"], rates)
            if acct.category == "insurance" and acct_cny == 0:
                acct_cny = (acct.ins_premium or 0) * (acct.ins_paid_periods or 0)
            if acct.category == "future_cash" and acct_cny == 0:
                acct_cny = sum(sa.get("amount", 0) for sa in (acct.sub_accounts or []))
            for h in holdings:
                if h.account_id == acct.id:
                    acct_cny += _to_cny(h.shares * h.current_price, h.currency, rates)
            account_totals[acct.id] = {"name": acct.name, "value_cny": round(acct_cny, 2)}
        result["account_totals"] = account_totals

    _dashboard_cache[f"{data_dir}:overview"] = result
    return result


@router.get("/trend")
async def trend(data_dir: str = Depends(get_db), user: dict | None = Depends(get_current_user)):
    """Asset trend from snapshots (per-user isolated)."""
    username = user.get("sub", "default") if user else "default"
    cache_key = f"{data_dir}:{username}:trend"
    cached = _dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    import json
    from pathlib import Path

    from backend.database import db_path_for_data_dir

    data_path = db_path_for_data_dir(data_dir).parent
    snap_dir = data_path / "snapshots" / username
    if not snap_dir.exists():
        return []

    snapshots = []
    for f in sorted(snap_dir.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
            data["date"] = f.stem
            snapshots.append(data)

    _dashboard_cache[cache_key] = snapshots
    return snapshots


@router.post("/snapshot")
async def save_snapshot(data_dir: str = Depends(get_db), user: dict | None = Depends(get_current_user)):
    """Save current overview as a daily snapshot for trend tracking (per-user isolated)."""
    import json
    from pathlib import Path

    from backend.database import db_path_for_data_dir

    username = user.get("sub", "default") if user else "default"

    # Invalidate overview cache so we get a fresh read with account_totals
    _dashboard_cache.pop(f"{data_dir}:overview", None)
    ov = await overview(data_dir, include_account_totals=True)

    data_path = db_path_for_data_dir(data_dir).parent
    snap_dir = data_path / "snapshots" / username
    snap_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    snap_file = snap_dir / f"{today}.json"

    with open(snap_file, "w") as f:
        json.dump(ov, f, ensure_ascii=False, indent=2)

    # Invalidate caches that depend on snapshots
    cache_key = f"{data_dir}:{username}:trend"
    _dashboard_cache.pop(cache_key, None)

    return {"ok": True, "date": today}


@router.get("/holdings-pnl")
async def holdings_pnl(data_dir: str = Depends(get_db)):
    """P&L for all holdings, sorted by P&L amount in CNY (descending)."""
    rates = await get_all_rates()
    holdings = await Holding.all()
    accounts = {a.id: a for a in await Account.all()}

    result = []
    for h in holdings:
        acct = accounts.get(h.account_id)
        if acct and acct.exclude_from_total:
            continue
        cost = h.shares * h.avg_cost_price
        market = h.shares * h.current_price
        pnl = market - cost
        pnl_pct = (pnl / cost * 100) if cost else 0
        rate = rates.get(h.currency, 1.0)
        result.append({
            "id": h.id,
            "ticker": h.ticker,
            "name": h.name,
            "shares": h.shares,
            "cost": round(cost, 2),
            "market_value": round(market, 2),
            "pnl": round(pnl, 2),
            "pnl_cny": round(pnl * rate, 2),
            "pnl_pct": round(pnl_pct, 2),
            "currency": h.currency,
            "account_name": acct.name if acct else "",
        })

    result.sort(key=lambda x: x["pnl_cny"], reverse=True)
    return result


@router.get("/all")
async def dashboard_all(data_dir: str = Depends(get_db), user: dict | None = Depends(get_current_user)):
    """Aggregated endpoint returning overview, annual P&L, trend, holdings P&L, and rates."""
    import asyncio
    import json
    from pathlib import Path

    from backend.database import db_path_for_data_dir
    from backend.models import Transaction

    # Fetch shared data once
    rates = await get_all_rates()
    accounts = await Account.all()
    holdings = await Holding.all()

    async def _overview():
        category_totals: dict[str, float] = {}
        total = 0.0
        excluded_ids = {acct.id for acct in accounts if acct.exclude_from_total}

        for acct in accounts:
            if acct.id in excluded_ids:
                continue
            cat = acct.category
            cat_cny = 0.0
            for b in (acct.balances or []):
                cat_cny += _to_cny(b["amount"], b["currency"], rates)
            if cat == "insurance" and cat_cny == 0:
                cat_cny = (acct.ins_premium or 0) * (acct.ins_paid_periods or 0)
            if cat == "future_cash" and cat_cny == 0:
                cat_cny = sum(sa.get("amount", 0) for sa in (acct.sub_accounts or []))
            category_totals[cat] = category_totals.get(cat, 0) + cat_cny
            total += cat_cny

        for h in holdings:
            if h.account_id in excluded_ids:
                continue
            mv = h.shares * h.current_price
            mv_cny = _to_cny(mv, h.currency, rates)
            category_totals["investment"] = category_totals.get("investment", 0) + mv_cny
            total += mv_cny

        category_pcts = {
            cat: round(v / total * 100, 1) if total else 0
            for cat, v in category_totals.items()
        }

        return {
            "total_cny": round(total, 2),
            "category_totals": category_totals,
            "category_pcts": category_pcts,
            "rates": rates,
            "account_count": len(accounts),
            "holding_count": len(holdings),
        }

    async def _annual_pnl():
        transactions = await Transaction.filter(type="pnl").all()
        result: dict[str, dict[int, float]] = {}
        for t in transactions:
            acct = t.account_id or "unknown"
            yr = int(t.date[:4]) if t.date and len(t.date) >= 4 else 0
            result.setdefault(acct, {})
            result[acct][yr] = result[acct].get(yr, 0) + t.amount
        return result

    async def _trend():
        username = user.get("sub", "default") if user else "default"
        data_path = db_path_for_data_dir(data_dir).parent
        snap_dir = data_path / "snapshots" / username
        if not snap_dir.exists():
            return []
        snapshots = []
        for f in sorted(snap_dir.glob("*.json")):
            with open(f) as fh:
                data = json.load(fh)
                data["date"] = f.stem
                snapshots.append(data)
        return snapshots

    async def _holdings_pnl():
        acct_map = {a.id: a for a in accounts}
        result = []
        for h in holdings:
            acct = acct_map.get(h.account_id)
            if acct and acct.exclude_from_total:
                continue
            cost = h.shares * h.avg_cost_price
            market = h.shares * h.current_price
            pnl = market - cost
            pnl_pct = (pnl / cost * 100) if cost else 0
            rate = rates.get(h.currency, 1.0)
            result.append({
                "id": h.id, "ticker": h.ticker, "name": h.name,
                "shares": h.shares, "cost": round(cost, 2),
                "market_value": round(market, 2), "pnl": round(pnl, 2),
                "pnl_cny": round(pnl * rate, 2), "pnl_pct": round(pnl_pct, 2),
                "currency": h.currency,
                "account_name": acct.name if acct else "",
            })
        result.sort(key=lambda x: x["pnl_cny"], reverse=True)
        return result

    async def _rates_data():
        return [r.to_dict() for r in await ExchangeRate.all()]

    results = await asyncio.gather(
        _overview(), _annual_pnl(), _trend(), _holdings_pnl(), _rates_data(),
        return_exceptions=True,
    )

    keys = ["overview", "annualPnl", "trendData", "holdingsPnl", "ratesData"]
    response = {}
    for key, result in zip(keys, results):
        if isinstance(result, Exception):
            import logging
            logging.getLogger(__name__).warning("dashboard/all sub-query '%s' failed: %s", key, result)
            response[key] = None
        else:
            response[key] = result

    return response
