"""JSON-to-SQLite migration — auto-runs on first startup."""

import json
import logging
from pathlib import Path

from backend.database import DATA_DIR, ensure_db

logger = logging.getLogger(__name__)

MIGRATION_MARKER = ".migrated_to_sqlite"


def _needs_migration(data_dir: str) -> bool:
    json_dir = DATA_DIR / data_dir if data_dir else DATA_DIR
    if (json_dir / MIGRATION_MARKER).exists():
        return False
    return bool(list(json_dir.glob("*.json")))


def _load_json(data_dir: str, collection: str) -> list:
    json_dir = DATA_DIR / data_dir if data_dir else DATA_DIR
    path = json_dir / f"{collection}.json"
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


async def _safe_create(model_cls, **kwargs):
    """Create only if id doesn't already exist (idempotent migration)."""
    pk = kwargs.get("id") or kwargs.get("currency")
    if pk is not None:
        existing = await model_cls.filter(**{model_cls._meta.pk_attr: pk}).first()
        if existing:
            return
    await model_cls.create(**kwargs)


async def migrate_json_to_sqlite(data_dir: str = "") -> None:
    """Migrate JSON data to SQLite for a given data_dir."""
    if not _needs_migration(data_dir):
        logger.info("data_dir='%s': already migrated", data_dir or "(default)")
        return

    logger.info("Migrating JSON → SQLite for data_dir='%s'...", data_dir or "(default)")
    await ensure_db(data_dir)

    from backend.models import (
        Account, Holding, Transaction, Deposit, FundFlow,
        ExchangeRate, WatchlistItem, PriceSnapshot, Conversation,
    )

    # 1. Accounts first (FK target)
    for a in _load_json(data_dir, "accounts"):
        await _safe_create(Account,
            id=a["id"], name=a["name"], category=a.get("category", "cash"),
            institution=a.get("institution", ""), balances=a.get("balances", []),
            notes=a.get("notes", ""), sub_accounts=a.get("sub_accounts", []),
            annual_rate=a.get("annual_rate", 0), exclude_from_total=a.get("exclude_from_total", False),
            ins_premium=a.get("ins_premium", 0), ins_total_periods=a.get("ins_total_periods", 0),
            ins_paid_periods=a.get("ins_paid_periods", 0), ins_start_year=a.get("ins_start_year", 0),
            ins_rate=a.get("ins_rate", 0), ins_annual_payout=a.get("ins_annual_payout", 0),
            ins_payout_schedule=a.get("ins_payout_schedule", []),
            ins_start_date=a.get("ins_start_date", ""), ins_birth_date=a.get("ins_birth_date", ""),
            ins_end_date=a.get("ins_end_date", ""), sort_order=a.get("sort_order", 0),
        )

    # 2. Holdings, Transactions, Deposits, FundFlows (FK → Account)
    for h in _load_json(data_dir, "holdings"):
        await _safe_create(Holding,
            id=h["id"], account_id=h["account_id"], ticker=h.get("ticker", ""),
            name=h.get("name", ""), shares=h.get("shares", 0),
            avg_cost_price=h.get("avg_cost_price", 0), current_price=h.get("current_price", 0),
            currency=h.get("currency", "USD"), vested_shares=h.get("vested_shares", 0),
            unvested_shares=h.get("unvested_shares", 0), vesting_schedule=h.get("vesting_schedule", []),
        )

    for t in _load_json(data_dir, "transactions"):
        await _safe_create(Transaction,
            id=t["id"], account_id=t["account_id"], type=t["type"], date=t["date"],
            amount=t["amount"], currency=t.get("currency", "CNY"),
            quantity=t.get("quantity"), price=t.get("price"), pnl=t.get("pnl"),
            notes=t.get("notes", ""),
        )

    for d in _load_json(data_dir, "deposits"):
        await _safe_create(Deposit,
            id=d["id"], account_id=d["account_id"], amount=d["amount"], rate=d["rate"],
            start_date=d.get("start_date", ""), maturity_date=d.get("maturity_date", ""),
            interest=d.get("interest", 0),
        )

    for f in _load_json(data_dir, "fund_flows"):
        await _safe_create(FundFlow,
            id=f["id"], account_id=f["account_id"], type=f["type"],
            currency=f["currency"], amount=f["amount"], rate_at_time=f["rate_at_time"],
            date=f["date"], notes=f.get("notes", ""),
        )

    # 3. Independent tables
    for r in _load_json(data_dir, "exchange_rates"):
        await _safe_create(ExchangeRate,
            currency=r["currency"], rate_to_cny=r["rate_to_cny"],
            date=r.get("date", ""), source=r.get("source", ""),
        )

    for w in _load_json(data_dir, "watchlist"):
        await _safe_create(WatchlistItem, id=w["id"], ticker=w["ticker"], name=w.get("name", ""))

    for s in _load_json(data_dir, "price_snapshots"):
        await PriceSnapshot.create(ticker=s["ticker"], price=s["price"],
                                    currency=s.get("currency", "USD"), date=s["date"])

    for c in _load_json(data_dir, "conversations"):
        await _safe_create(Conversation,
            id=c["id"], title=c.get("title", "新对话"), messages=c.get("messages", []),
            created_at=c.get("created_at", ""), updated_at=c.get("updated_at", ""),
        )

    # Write marker
    json_dir = DATA_DIR / data_dir if data_dir else DATA_DIR
    (json_dir / MIGRATION_MARKER).touch()
    logger.info("Migration complete for data_dir='%s'", data_dir or "(default)")
