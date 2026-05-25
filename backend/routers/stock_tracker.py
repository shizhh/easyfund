"""Stock tracker router — watchlist CRUD + tracker overview."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth import get_db
from backend.models import Holding, PriceSnapshot, WatchlistItem
from backend.schemas import WatchlistItemCreate, WatchlistItemUpdate
from backend.services.currency import get_all_rates, get_rate_to_cny

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stock-tracker", tags=["stock-tracker"])


# ── Watchlist CRUD ──────────────────────────────────────────

@router.get("/watchlist")
async def list_watchlist(data_dir: str = Depends(get_db)):
    items = await WatchlistItem.all()
    return [w.to_dict() for w in items]


@router.post("/watchlist", status_code=201)
async def create_watchlist_item(data: WatchlistItemCreate, data_dir: str = Depends(get_db)):
    if await WatchlistItem.get_or_none(id=data.id):
        raise HTTPException(400, "Watchlist item id already exists")
    item = await WatchlistItem.create(**data.model_dump())
    return item.to_dict()


@router.put("/watchlist/{item_id}")
async def update_watchlist_item(item_id: str, data: WatchlistItemUpdate, data_dir: str = Depends(get_db)):
    item = await WatchlistItem.get_or_none(id=item_id)
    if not item:
        raise HTTPException(404, "Watchlist item not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    await item.save()
    return item.to_dict()


@router.delete("/watchlist/{item_id}")
async def delete_watchlist_item(item_id: str, data_dir: str = Depends(get_db)):
    item = await WatchlistItem.get_or_none(id=item_id)
    if not item:
        raise HTTPException(404, "Watchlist item not found")
    await item.delete()
    return {"ok": True}


# ── Tracker Overview ────────────────────────────────────────

@router.get("/overview")
async def tracker_overview(data_dir: str = Depends(get_db)):
    """Aggregate all tracker data in one call.

    Returns stored prices immediately (fast). Use refresh=true to fetch live prices.
    """
    holdings = await Holding.all()
    watchlist = await WatchlistItem.all()
    rates = await get_all_rates()

    # ── Build merged stock list using stored prices (fast, no API calls) ──
    stocks = []
    seen_tickers: set[str] = set()

    # Process holdings individually (one entry per holding, not aggregated by ticker)
    for h in holdings:
        ticker = h.ticker
        if not ticker:
            continue
        seen_tickers.add(ticker)

        shares = h.shares
        avg_cost = h.avg_cost_price
        stored_price = h.current_price
        currency = h.currency
        price = stored_price if stored_price else None

        rate = await get_rate_to_cny(currency)
        market_value_cny = (shares * price * rate) if price else 0
        cost_cny = shares * avg_cost * rate
        pnl_cny = market_value_cny - cost_cny

        stocks.append({
            "holding_id": h.id,
            "account_id": h.account_id,
            "ticker": ticker,
            "name": h.name,
            "price": price,
            "currency": currency,
            "prev_close": None,
            "change_pct": None,
            "shares": shares,
            "avg_cost_price": round(avg_cost, 2),
            "market_value_cny": round(market_value_cny, 2),
            "pnl_cny": round(pnl_cny, 2),
            "source": "holding",
        })

    # Process watchlist items — try cache only (no live fetch)
    for w in watchlist:
        ticker = w.ticker
        if not ticker or ticker in seen_tickers:
            continue
        seen_tickers.add(ticker)

        # Try in-memory cache only (instant, no API call)
        from backend.services.market import _quote_cache, _QUOTE_CACHE_TTL
        import time
        cached = _quote_cache.get(ticker)
        price = None
        currency = "USD"
        prev_close = None
        if cached:
            c_price, c_currency, c_ts, c_prev = cached
            if time.time() - c_ts < _QUOTE_CACHE_TTL:
                price = c_price
                currency = c_currency
                prev_close = c_prev

        change_pct = None
        if price and prev_close and prev_close > 0:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        stocks.append({
            "ticker": ticker,
            "name": w.name,
            "price": price,
            "currency": currency,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "shares": 0,
            "avg_cost_price": 0,
            "market_value_cny": 0,
            "pnl_cny": 0,
            "source": "watchlist",
        })

    # ── Sparkline data (7-day from price snapshots) ──
    snapshots = await PriceSnapshot.all()
    snap_map: dict[str, list[dict]] = {}
    for s in snapshots:
        snap_map.setdefault(s.ticker, []).append(s.to_dict())

    for stock in stocks:
        ticker = stock["ticker"]
        ticker_snaps = snap_map.get(ticker, [])
        ticker_snaps.sort(key=lambda x: x.get("date", ""))
        recent = ticker_snaps[-7:] if len(ticker_snaps) >= 7 else ticker_snaps
        stock["sparkline"] = [s.get("price") for s in recent if s.get("price")]

    # ── Summary ──
    total_pnl_cny = sum(s["pnl_cny"] for s in stocks if s["source"] == "holding")
    today_change_cny = 0.0

    # Count unique tickers for holding_count
    holding_tickers = set(s["ticker"] for s in stocks if s["source"] == "holding")

    exchange_rates_list = [{"currency": c, "rate_to_cny": r} for c, r in rates.items()]

    summary = {
        "total_pnl_cny": round(total_pnl_cny, 2),
        "today_change_cny": round(today_change_cny, 2),
        "holding_count": len(holding_tickers),
        "watchlist_count": len(watchlist),
        "exchange_rates": exchange_rates_list,
    }

    # ── 30-day trend (from price snapshots) ──
    trend = _build_portfolio_trend([s.to_dict() for s in snapshots], [h.to_dict() for h in holdings], rates)

    return {"summary": summary, "stocks": stocks, "trend": trend}


@router.get("/refresh-prices")
async def refresh_tracker_prices(data_dir: str = Depends(get_db)):
    """Fetch live prices for all tracked stocks (holdings + watchlist).

    Returns updated stock list with live prices, change_pct, etc.
    """
    from backend.services.market import fetch_quotes_parallel, update_holding_prices

    holdings = await Holding.all()
    watchlist = await WatchlistItem.all()
    rates = await get_all_rates()

    # Collect unique tickers from both holdings and watchlist
    tickers = list({h.ticker for h in holdings if h.ticker} | {w.ticker for w in watchlist if w.ticker})

    quotes = await fetch_quotes_parallel(tickers)
    await update_holding_prices(quotes)

    # Build stock list with live data
    stocks = []
    seen_tickers: set[str] = set()

    for h in holdings:
        ticker = h.ticker
        if not ticker:
            continue
        seen_tickers.add(ticker)

        shares = h.shares
        avg_cost = h.avg_cost_price
        currency = h.currency

        quote = quotes.get(ticker, {})
        price = quote.get("price") or h.current_price
        currency = quote.get("currency", currency)
        prev_close = quote.get("prev_close")

        change_pct = None
        if price and prev_close and prev_close > 0:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        rate = await get_rate_to_cny(currency)
        market_value_cny = (shares * price * rate) if price else 0
        cost_cny = shares * avg_cost * rate
        pnl_cny = market_value_cny - cost_cny

        today_change_cny = 0.0
        if price and prev_close and shares:
            today_change_cny = shares * (price - prev_close) * rate

        stocks.append({
            "holding_id": h.id,
            "account_id": h.account_id,
            "ticker": ticker,
            "name": h.name,
            "price": price,
            "currency": currency,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "shares": shares,
            "avg_cost_price": round(avg_cost, 2),
            "market_value_cny": round(market_value_cny, 2),
            "pnl_cny": round(pnl_cny, 2),
            "today_change_cny": round(today_change_cny, 2),
            "source": "holding",
        })

    for w in watchlist:
        ticker = w.ticker
        if not ticker or ticker in seen_tickers:
            continue
        seen_tickers.add(ticker)

        quote = quotes.get(ticker, {})
        price = quote.get("price")
        currency = quote.get("currency", "USD")
        prev_close = quote.get("prev_close")

        change_pct = None
        if price and prev_close and prev_close > 0:
            change_pct = round((price - prev_close) / prev_close * 100, 2)

        stocks.append({
            "ticker": ticker,
            "name": w.name,
            "price": price,
            "currency": currency,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "shares": 0,
            "avg_cost_price": 0,
            "market_value_cny": 0,
            "pnl_cny": 0,
            "today_change_cny": 0,
            "source": "watchlist",
        })

    # Sparkline data
    snapshots = await PriceSnapshot.all()
    snap_map: dict[str, list[dict]] = {}
    for s in snapshots:
        snap_map.setdefault(s.ticker, []).append(s.to_dict())

    for stock in stocks:
        ticker = stock["ticker"]
        ticker_snaps = snap_map.get(ticker, [])
        ticker_snaps.sort(key=lambda x: x.get("date", ""))
        recent = ticker_snaps[-7:] if len(ticker_snaps) >= 7 else ticker_snaps
        stock["sparkline"] = [s.get("price") for s in recent if s.get("price")]

    # Summary
    total_pnl_cny = sum(s["pnl_cny"] for s in stocks if s["source"] == "holding")
    today_change_cny = sum(s.get("today_change_cny", 0) for s in stocks if s["source"] == "holding")
    exchange_rates_list = [{"currency": c, "rate_to_cny": r} for c, r in rates.items()]

    holding_tickers = set(s["ticker"] for s in stocks if s["source"] == "holding")

    summary = {
        "total_pnl_cny": round(total_pnl_cny, 2),
        "today_change_cny": round(today_change_cny, 2),
        "holding_count": len(holding_tickers),
        "watchlist_count": len(watchlist),
        "exchange_rates": exchange_rates_list,
    }

    return {"summary": summary, "stocks": stocks}


def _build_portfolio_trend(
    snapshots: list[dict],
    holdings: list[dict],
    rates: dict[str, float],
) -> list[dict]:
    """Build 30-day portfolio value trend from price snapshots."""
    if not snapshots or not holdings:
        return []

    # Group snapshots by date -> {ticker: price}
    by_date: dict[str, dict[str, float]] = {}
    for s in snapshots:
        d = s.get("date", "")
        t = s.get("ticker", "")
        p = s.get("price")
        if d and t and p:
            by_date.setdefault(d, {})[t] = p

    if not by_date:
        return []

    # Aggregate shares per ticker
    ticker_shares: dict[str, dict] = {}
    for h in holdings:
        t = h.get("ticker", "")
        if not t:
            continue
        if t not in ticker_shares:
            ticker_shares[t] = {"shares": 0, "currency": h.get("currency", "USD")}
        ticker_shares[t]["shares"] += h.get("shares", 0)

    # Calculate portfolio value for each date
    trend = []
    for date in sorted(by_date.keys()):
        value = 0.0
        for ticker, info in ticker_shares.items():
            price = by_date[date].get(ticker)
            if price:
                rate = rates.get(info["currency"], 1.0)
                value += info["shares"] * price * rate
        trend.append({"date": date, "value_cny": round(value, 2)})

    # Keep last 30 entries
    return trend[-30:]


# ── Price Snapshots ─────────────────────────────────────────

@router.post("/snapshot")
async def save_price_snapshot(data_dir: str = Depends(get_db)):
    """Save current prices as a snapshot for historical tracking."""
    from datetime import date

    from backend.services.market import fetch_quotes_parallel

    holdings = await Holding.all()
    watchlist = await WatchlistItem.all()
    today = date.today().isoformat()

    # Collect unique tickers
    tickers = list({h.ticker for h in holdings if h.ticker} | {w.ticker for w in watchlist if w.ticker})

    quotes = await fetch_quotes_parallel(tickers)

    # Delete existing snapshots for today, then create new ones
    await PriceSnapshot.filter(date=today).delete()

    for ticker, quote in quotes.items():
        if quote.get("price") is not None:
            await PriceSnapshot.create(
                ticker=ticker,
                price=quote["price"],
                currency=quote.get("currency", "USD"),
                date=today,
            )

    return {"ok": True, "date": today, "tickers": tickers}
