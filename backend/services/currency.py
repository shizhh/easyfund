"""Currency exchange rate service."""

from datetime import date

from backend.models import ExchangeRate, Holding, Transaction, FundFlow


async def get_rate_to_cny(currency: str) -> float:
    """Get the latest exchange rate to CNY."""
    if currency == "CNY":
        return 1.0
    rate = await ExchangeRate.get_or_none(currency=currency)
    if rate:
        return rate.rate_to_cny
    return 1.0


async def convert_to_cny(amount: float, currency: str) -> float:
    rate = await get_rate_to_cny(currency)
    return amount * rate


async def get_all_rates() -> dict[str, float]:
    """Get all exchange rates to CNY as a dict, e.g. {"CNY": 1.0, "USD": 7.25}."""
    rates = {"CNY": 1.0}
    for r in await ExchangeRate.all():
        rates[r.currency] = r.rate_to_cny
    return rates


async def update_rate(currency: str, rate: float):
    """Update exchange rate."""
    existing = await ExchangeRate.get_or_none(currency=currency)
    if existing:
        existing.rate_to_cny = rate
        existing.date = date.today().isoformat()
        existing.source = "manual"
        await existing.save()
    else:
        await ExchangeRate.create(
            currency=currency,
            rate_to_cny=rate,
            date=date.today().isoformat(),
            source="manual",
        )


async def refresh_rates_from_yfinance() -> list[dict]:
    """Fetch live rates and merge into stored rates.

    Returns the updated rates list.
    """
    from backend.services.market import fetch_exchange_rates

    # Only fetch rates for currencies that are registered in the DB
    registered = [r.currency for r in await ExchangeRate.all()]
    live = fetch_exchange_rates(registered if registered else None)
    if not live:
        return [r.to_dict() for r in await ExchangeRate.all()]

    today = date.today().isoformat()

    # Batch-load existing records, then bulk-update/create
    existing_map = {r.currency: r for r in await ExchangeRate.filter(currency__in=list(live.keys()))}
    to_update = []
    to_create = []

    for currency, (rate, source) in live.items():
        existing = existing_map.get(currency)
        if existing:
            existing.rate_to_cny = rate
            existing.date = today
            existing.source = source
            to_update.append(existing)
        else:
            to_create.append(ExchangeRate(
                currency=currency,
                rate_to_cny=rate,
                date=today,
                source=source,
            ))

    if to_update:
        await ExchangeRate.bulk_update(to_update, fields=["rate_to_cny", "date", "source"])
    if to_create:
        await ExchangeRate.bulk_create(to_create)

    return [r.to_dict() for r in await ExchangeRate.all()]


async def get_supported_currencies() -> list[dict]:
    """Return list of supported currencies with their rates.

    Always includes CNY (base currency, rate=1.0).
    """
    rates = await ExchangeRate.all()
    result = [{"currency": "CNY", "rate_to_cny": 1.0}]
    for r in rates:
        result.append({"currency": r.currency, "rate_to_cny": r.rate_to_cny,
                       "date": r.date, "source": r.source})
    return result


async def register_currency(currency: str, rate: float) -> dict:
    """Register a new currency by creating an ExchangeRate record."""
    import re
    if not re.match(r'^[A-Z]{3}$', currency):
        raise ValueError(f"Invalid currency code: {currency}. Must be 3 uppercase letters.")
    if currency == "CNY":
        raise ValueError("CNY is the base currency and cannot be registered.")
    existing = await ExchangeRate.get_or_none(currency=currency)
    if existing:
        existing.rate_to_cny = rate
        existing.date = date.today().isoformat()
        existing.source = "manual"
        await existing.save()
        return existing.to_dict()
    record = await ExchangeRate.create(
        currency=currency,
        rate_to_cny=rate,
        date=date.today().isoformat(),
        source="manual",
    )
    return record.to_dict()


async def unregister_currency(currency: str) -> bool:
    """Remove a currency. Fails if any holdings/transactions/fund_flows use it."""
    if currency == "CNY":
        raise ValueError("Cannot unregister base currency CNY.")
    # Check for usage in holdings, transactions, fund_flows
    if await Holding.filter(currency=currency).exists():
        raise ValueError(f"Cannot unregister {currency}: still used by holdings.")
    if await Transaction.filter(currency=currency).exists():
        raise ValueError(f"Cannot unregister {currency}: still used by transactions.")
    if await FundFlow.filter(currency=currency).exists():
        raise ValueError(f"Cannot unregister {currency}: still used by fund flows.")
    deleted = await ExchangeRate.filter(currency=currency).delete()
    return deleted > 0
