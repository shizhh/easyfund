"""Market data service - fetch stock quotes and exchange rates."""

import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Exchange rate cache: {currency: (rate, timestamp, source)}
_rate_cache: dict[str, tuple[float, float, str]] = {}
_CACHE_TTL = 3600  # 1 hour

# Stock price cache: {ticker: (price, currency, timestamp, prev_close)}
_quote_cache: dict[str, tuple[float, str, float, float | None]] = {}
_QUOTE_CACHE_TTL = 1800  # 30 minutes


# Map yfinance ticker suffixes to Stooq suffixes
# yfinance: BIDU, 9988.HK, 600519.SS
# Stooq:    BIDU.US, 9988.HK, 600519.CN
def _ticker_to_stooq(ticker: str) -> str | None:
    """Convert a yfinance-style ticker to Stooq format."""
    if ticker.endswith(".HK"):
        return ticker  # e.g. 9988.HK -> 9988.HK
    elif ticker.endswith(".SS") or ticker.endswith(".SZ"):
        # Shanghai (.SS) or Shenzhen (.SZ) -> .cn
        code = ticker.rsplit(".", 1)[0]
        return f"{code}.cn"
    elif "." in ticker:
        return None  # Unknown exchange format, skip stooq
    # Plain ticker with no suffix — assume US market
    return f"{ticker}.us"


def _fetch_from_stooq(ticker: str) -> dict | None:
    """Fallback: fetch stock price from stooq.com (free, no API key).

    Returns {"price": float, "prev_close": float|None, "currency": str} or None on failure.
    """
    import csv
    import io
    import urllib.request

    stooq_ticker = _ticker_to_stooq(ticker)
    if not stooq_ticker:
        return None

    # f=p adds Prev Close field
    url = f"https://stooq.com/q/l/?s={stooq_ticker.lower()}&f=sd2t2ohlcvp&h&e=csv"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EasyFund/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode()

        reader = csv.DictReader(io.StringIO(data))
        for row in reader:
            close = row.get("Close", "").strip()
            if close and close != "N/D":
                price = float(close)
                prev = row.get("Prev. Close", "").strip() or row.get("Prev", "").strip()
                prev_close = float(prev) if prev and prev != "N/D" else None
                # Determine currency from ticker suffix
                currency = "USD"
                if stooq_ticker.lower().endswith(".hk"):
                    currency = "HKD"
                elif stooq_ticker.lower().endswith(".cn"):
                    currency = "CNY"
                return {"price": price, "prev_close": prev_close, "currency": currency}
        return None
    except Exception as e:
        logger.warning("Stooq failed for %s (%s): %s", ticker, stooq_ticker, e)
        return None


def get_quote(ticker: str, use_cache: bool = True) -> dict:
    """Get current quote for a stock ticker, with 30-min cache.

    Tries yfinance first, falls back to stooq.com.
    Returns cached price if available and not expired.
    On all failures, falls back to stale cache.
    """
    now = time.time()

    # Return cached price if fresh enough
    cached = _quote_cache.get(ticker)
    if use_cache and cached:
        price, currency, ts, prev_close = cached
        if now - ts < _QUOTE_CACHE_TTL:
            return {"ticker": ticker, "price": price, "currency": currency, "prev_close": prev_close, "source": "cache"}

    # Try yfinance first
    try:
        import yfinance as yf
    except ImportError:
        yf = None

    prev_close = None

    if yf:
        try:
            stock = yf.Ticker(ticker)
            info = stock.fast_info
            price = getattr(info, "last_price", None) or getattr(info, "previous_close", None)
            currency = getattr(info, "currency", "USD")
            prev_close = getattr(info, "previous_close", None)
            # If price came from previous_close (fallback), don't also set prev_close to same value
            if price == prev_close and getattr(info, "last_price", None) is None:
                prev_close = None

            if price is not None:
                _quote_cache[ticker] = (price, currency, now, prev_close)
                return {"ticker": ticker, "price": price, "currency": currency, "prev_close": prev_close, "source": "yfinance"}
        except Exception as e:
            logger.warning("yfinance failed for %s: %s", ticker, e)

    # Fallback: try stooq
    stooq_result = _fetch_from_stooq(ticker)
    if stooq_result and stooq_result["price"] is not None:
        price = stooq_result["price"]
        currency = stooq_result["currency"]
        prev_close = stooq_result.get("prev_close")
        _quote_cache[ticker] = (price, currency, now, prev_close)
        return {"ticker": ticker, "price": price, "currency": currency, "prev_close": prev_close, "source": "stooq"}

    # All sources failed — use stale cache if available
    if cached:
        logger.warning("All sources failed for %s, using stale cache", ticker)
        return {"ticker": ticker, "price": cached[0], "currency": cached[1], "prev_close": cached[3], "source": "stale_cache"}

    return {"ticker": ticker, "price": None, "currency": "USD", "prev_close": None}


# History cache: {ticker: (history_list, timestamp)}
_history_cache: dict[str, tuple[list[dict], float]] = {}
_HISTORY_CACHE_TTL = 3600  # 1 hour


def _fetch_history_from_stooq(ticker: str, days: int) -> list[dict] | None:
    """Fallback: fetch historical daily close prices from stooq.com.

    Returns list of {"date": str, "price": float} or None on failure.
    """
    import csv
    import io
    import urllib.request

    stooq_ticker = _ticker_to_stooq(ticker)
    if not stooq_ticker:
        return None

    # Stooq historical data URL: d1=20230101&d2=20231231 format
    from datetime import datetime, timedelta
    end = datetime.now()
    start = end - timedelta(days=days + 10)  # extra buffer for non-trading days
    d1 = start.strftime("%Y%m%d")
    d2 = end.strftime("%Y%m%d")
    url = f"https://stooq.com/q/d/l/?s={stooq_ticker.lower()}&d1={d1}&d2={d2}&i=d"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EasyFund/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode()

        reader = csv.DictReader(io.StringIO(data))
        result = []
        for row in reader:
            date_str = row.get("Date", "").strip()
            close = row.get("Close", "").strip()
            if date_str and close:
                try:
                    result.append({"date": date_str, "price": round(float(close), 4)})
                except ValueError:
                    continue
        return result[-days:] if result else None
    except Exception as e:
        logger.warning("Stooq history failed for %s (%s): %s", ticker, stooq_ticker, e)
        return None


def get_quote_history(ticker: str, days: int = 30) -> dict:
    """Get historical daily close prices for a ticker, with 1-hour cache.

    Tries yfinance first, falls back to stooq.com.
    Returns {"ticker": str, "history": [{"date": str, "price": float}, ...], "source": str}.
    """
    now = time.time()
    cache_key = f"{ticker}_{days}"

    # Return cached if fresh
    cached = _history_cache.get(cache_key)
    if cached and (now - cached[1]) < _HISTORY_CACHE_TTL:
        return {"ticker": ticker, "history": cached[0], "source": "cache"}

    # Try yfinance
    try:
        import yfinance as yf
    except ImportError:
        yf = None

    if yf:
        try:
            stock = yf.Ticker(ticker)
            period_map = {7: "5d", 14: "1mo", 30: "1mo", 90: "3mo"}
            period = period_map.get(days, "1mo")
            hist = stock.history(period=period)
            if hist is not None and not hist.empty:
                result = []
                for idx, row in hist.iterrows():
                    result.append({
                        "date": idx.strftime("%Y-%m-%d"),
                        "price": round(float(row["Close"]), 4),
                    })
                if result:
                    result = result[-days:]
                    _history_cache[cache_key] = (result, now)
                    return {"ticker": ticker, "history": result, "source": "yfinance"}
        except Exception as e:
            logger.warning("yfinance history failed for %s: %s", ticker, e)

    # Fallback: try stooq history
    stooq_result = _fetch_history_from_stooq(ticker, days)
    if stooq_result:
        _history_cache[cache_key] = (stooq_result, now)
        return {"ticker": ticker, "history": stooq_result, "source": "stooq"}

    # Stale cache
    if cached:
        logger.warning("All history sources failed for %s, using stale cache", ticker)
        return {"ticker": ticker, "history": cached[0], "source": "stale_cache"}

    return {"ticker": ticker, "history": [], "source": "none"}


def _fetch_from_yfinance(currency: str, ticker: str) -> float | None:
    """Try to fetch a single FX rate from yfinance."""
    import yfinance as yf
    t = yf.Ticker(ticker)
    price = getattr(t.fast_info, "last_price", None)
    if price and price > 0:
        return round(price, 4)
    return None


def _fetch_from_frankfurter(currencies: list[str]) -> dict[str, float]:
    """Fallback: fetch FX rates from frankfurter.app (free, no key, EU central bank).

    Returns rates like {"USD": 0.11, "HKD": 0.85} — these are CNY->foreign,
    so we invert to get foreign->CNY.
    """
    import urllib.request
    import json

    url = f"https://api.frankfurter.app/latest?from=CNY&to={','.join(currencies)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EasyFund/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        # frankfurter returns {base: 1, "USD": 0.14, "HKD": 1.09}
        # meaning 1 CNY = 0.14 USD, so USD/CNY = 1/0.14
        result = {}
        for c in currencies:
            if c in data.get("rates", {}):
                rate = data["rates"][c]
                if rate > 0:
                    result[c] = round(1 / rate, 4)
        return result
    except Exception as e:
        logger.warning("Frankfurter API failed: %s", e)
        return {}


# FX rate sources — yfinance tickers
# Only currencies present in the ExchangeRate table are fetched at runtime.
# This mapping is a lookup table for known yfinance ticker formats.
_FX_TICKERS = {
    "USD": "CNY=X",
    "HKD": "HKDCNY=X",
    "EUR": "EURCNY=X",
    "JPY": "JPYCNY=X",
    "GBP": "GBPCNY=X",
    "SGD": "SGDCNY=X",
    "AUD": "AUDCNY=X",
    "CAD": "CAD=CNY",
    "CHF": "CHFCNY=X",
}


def fetch_exchange_rates(currencies: list[str] | None = None) -> dict[str, tuple[float, str]]:
    """Fetch live exchange rates to CNY, with 1-hour cache.

    Args:
        currencies: List of currency codes to fetch. If None, fetches all
                    currencies in _FX_TICKERS (backward compatible default).

    Tries yfinance first, falls back to frankfurter.app.
    Returns dict like {"USD": (7.25, "yfinance"), "HKD": (0.93, "frankfurter")}.
    Falls back to stale cache or empty dict on failure.
    """
    now = time.time()
    result: dict[str, tuple[float, str]] = {}
    need_fetch: list[str] = []  # currencies that need a live fetch

    if currencies is None:
        currencies = list(_FX_TICKERS.keys())

    for currency in currencies:
        cached = _rate_cache.get(currency)
        if cached and (now - cached[1]) < _CACHE_TTL:
            result[currency] = (cached[0], cached[2])
        else:
            need_fetch.append(currency)

    if not need_fetch:
        return result

    # Try yfinance in parallel for currencies with known tickers
    yfinance_failed = []
    yfinance_tasks = {}  # future -> currency
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for currency in need_fetch:
            ticker = _FX_TICKERS.get(currency)
            if ticker:
                futures[executor.submit(_fetch_from_yfinance, currency, ticker)] = currency
            else:
                yfinance_failed.append(currency)

        for future in as_completed(futures):
            currency = futures[future]
            try:
                rate = future.result()
                if rate:
                    _rate_cache[currency] = (rate, now, "yfinance")
                    result[currency] = (rate, "yfinance")
                    logger.info("Fetched %s/CNY = %s (yfinance)", currency, rate)
                else:
                    yfinance_failed.append(currency)
            except Exception as e:
                logger.warning("yfinance failed for %s: %s", currency, e)
                yfinance_failed.append(currency)

    # Fallback to frankfurter for currencies yfinance couldn't fetch
    if yfinance_failed:
        fb_rates = _fetch_from_frankfurter(yfinance_failed)
        for currency, rate in fb_rates.items():
            _rate_cache[currency] = (rate, now, "frankfurter")
            result[currency] = (rate, "frankfurter")
            logger.info("Fetched %s/CNY = %s (frankfurter)", currency, rate)

        # For any still missing, use stale cache
        for currency in yfinance_failed:
            if currency not in result and currency not in fb_rates:
                cached = _rate_cache.get(currency)
                if cached:
                    result[currency] = (cached[0], cached[2])
                    logger.warning("Using stale cache for %s/CNY", currency)

    return result


async def get_quote_async(ticker: str, use_cache: bool = True) -> dict:
    """Async wrapper for get_quote — runs sync yfinance in a thread."""
    import asyncio
    return await asyncio.to_thread(get_quote, ticker, use_cache)


async def fetch_exchange_rates_async() -> dict[str, tuple[float, str]]:
    """Async wrapper for fetch_exchange_rates — runs sync calls in a thread."""
    import asyncio
    return await asyncio.to_thread(fetch_exchange_rates)


async def fetch_quotes_parallel(tickers: list[str], concurrency: int = 3) -> dict[str, dict]:
    """Fetch quotes for multiple tickers in parallel with concurrency limit.

    Returns dict mapping ticker -> quote dict.
    Failed fetches return {"ticker": ticker, "price": None, "currency": "USD"}.
    """
    import asyncio

    sem = asyncio.Semaphore(concurrency)

    async def fetch_one(ticker: str) -> tuple[str, dict]:
        async with sem:
            try:
                quote = await get_quote_async(ticker)
                return ticker, quote
            except Exception as e:
                logger.warning("Failed to fetch %s: %s", ticker, e)
                return ticker, {"ticker": ticker, "price": None, "currency": "USD"}

    results = await asyncio.gather(*[fetch_one(t) for t in tickers])
    return dict(results)


async def update_holding_prices(quotes: dict[str, dict]) -> list[dict]:
    """Update Holding current_price from fetched quotes. Returns updated list."""
    from backend.models import Holding

    holdings = await Holding.all()
    ticker_map: dict[str, list[Holding]] = {}
    for h in holdings:
        if h.ticker:
            ticker_map.setdefault(h.ticker, []).append(h)

    updated = []
    errors = []

    for ticker, hlds in ticker_map.items():
        quote = quotes.get(ticker, {})
        price = quote.get("price")
        if price is not None:
            for h in hlds:
                if h.current_price != price:
                    h.current_price = price
                    await h.save()
            updated.append({"ticker": ticker, "price": price, "source": quote.get("source", "yfinance")})
        else:
            errors.append({"ticker": ticker, "error": "no price returned"})

    return updated, errors
