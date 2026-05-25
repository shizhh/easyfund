"""FastAPI application."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth import get_db
from backend.routers import accounts, auth, chat, dashboard, deposits, fund_flows, import_export, investments, stock_tracker, transactions
from backend.services.market import get_quote, get_quote_history


def _load_dotenv():
    """Load .env file into os.environ. Does NOT override existing env vars."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


@asynccontextmanager
async def lifespan(app):
    # Load .env before anything else
    _load_dotenv()

    # Startup: migrate JSON → SQLite
    from backend.auth import load_users
    from backend.database import ensure_db, close_db
    from backend.migrate import migrate_json_to_sqlite

    await migrate_json_to_sqlite("")
    users = load_users()
    seen = {""}
    for u in users:
        d = u.get("data_dir", "")
        if d not in seen:
            await migrate_json_to_sqlite(d)
            seen.add(d)
    await ensure_db("")

    yield

    await close_db()


app = FastAPI(title="EasyFund", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(investments.router)
app.include_router(transactions.router)
app.include_router(deposits.router)
app.include_router(dashboard.router)
app.include_router(fund_flows.router)
app.include_router(import_export.router)
app.include_router(stock_tracker.router)
app.include_router(chat.router)


@app.get("/api/market/quote/{ticker}")
def market_quote(ticker: str):
    return get_quote(ticker)


@app.get("/api/market/history/{ticker}")
def market_history(ticker: str, days: int = 30):
    return get_quote_history(ticker, days)


@app.get("/api/exchange-rates")
async def exchange_rates(data_dir: str = Depends(get_db)):
    from backend.services.currency import get_supported_currencies
    return await get_supported_currencies()


@app.post("/api/exchange-rates/refresh")
async def refresh_exchange_rates(data_dir: str = Depends(get_db)):
    from backend.services.currency import refresh_rates_from_yfinance
    return await refresh_rates_from_yfinance()


@app.post("/api/exchange-rates")
async def update_exchange_rate(currency: str, rate: float, data_dir: str = Depends(get_db)):
    from backend.services.currency import update_rate
    await update_rate(currency, rate)
    from backend.routers.dashboard import invalidate_dashboard_cache
    invalidate_dashboard_cache()
    return {"ok": True}


@app.post("/api/exchange-rates/refresh")
async def refresh_exchange_rates(data_dir: str = Depends(get_db)):
    """Force refresh exchange rates from yfinance (bypass cache)."""
    from backend.services.market import _rate_cache
    _rate_cache.clear()
    from backend.services.currency import refresh_rates_from_yfinance
    result = await refresh_rates_from_yfinance()
    from backend.routers.dashboard import invalidate_dashboard_cache
    invalidate_dashboard_cache()
    return result


@app.get("/api/currencies")
async def list_currencies(data_dir: str = Depends(get_db)):
    from backend.services.currency import get_supported_currencies
    return await get_supported_currencies()


@app.post("/api/currencies")
async def add_currency(currency: str, rate: float, data_dir: str = Depends(get_db)):
    from fastapi import HTTPException
    from backend.services.currency import register_currency
    try:
        result = await register_currency(currency, rate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    from backend.routers.dashboard import invalidate_dashboard_cache
    invalidate_dashboard_cache()
    return result


@app.delete("/api/currencies/{currency}")
async def remove_currency(currency: str, data_dir: str = Depends(get_db)):
    from fastapi import HTTPException
    from backend.services.currency import unregister_currency
    try:
        deleted = await unregister_currency(currency)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Currency {currency} not found")
    from backend.routers.dashboard import invalidate_dashboard_cache
    invalidate_dashboard_cache()
    return {"ok": True}


# Serve Vue frontend in production
try:
    from pathlib import Path
    from fastapi.responses import FileResponse

    dist = Path(__file__).parent.parent / "frontend" / "dist"
    if dist.exists():
        # SPA catch-all: serve static files if they exist, otherwise index.html
        # so that client-side routing works on browser refresh.
        # Registered last so API routes take precedence.
        @app.get("/{path:path}")
        async def spa_fallback(path: str):
            file = dist / path
            if file.is_file():
                return FileResponse(file)
            return FileResponse(dist / "index.html")
except Exception:
    pass
