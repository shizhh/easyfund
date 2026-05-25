"""Excel import service — AI-driven two-phase import: analyze then confirm."""

import io
import os
import time
import uuid
from datetime import date
from pathlib import Path

from backend.models import Account, Deposit, ExchangeRate, Holding, Transaction
from backend.schemas import ImportMappingSchema
from backend.services.excel_analyzer import call_ai_for_mapping, extract_workbook_metadata
from backend.services.excel_mapper import parse_workbook_with_mapping

# Temp file directory for staging uploads between analyze and confirm
_TMP_DIR = Path("data/.import_tmp")
_MAX_TMP_AGE_SECONDS = 3600  # 1 hour


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _cleanup_tmp_files():
    """Remove temp import files older than 1 hour."""
    if not _TMP_DIR.exists():
        return
    now = time.time()
    for f in _TMP_DIR.iterdir():
        if f.is_file() and (now - f.stat().st_mtime) > _MAX_TMP_AGE_SECONDS:
            try:
                f.unlink()
            except OSError:
                pass


async def analyze_excel(content: bytes) -> tuple[str, ImportMappingSchema]:
    """Phase 1: Extract workbook metadata, call AI for mapping, stage file.

    Returns (session_id, mapping_schema).
    Raises ValueError if AI is not configured.
    """
    # Cleanup old temp files
    _cleanup_tmp_files()

    # Extract structural metadata from the workbook
    metadata = extract_workbook_metadata(content)

    # Call AI to generate mapping
    mapping = await call_ai_for_mapping(metadata)

    # Stage the file with a session ID
    session_id = _uid()
    _TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = _TMP_DIR / f"{session_id}.xlsx"
    tmp_path.write_bytes(content)

    return session_id, mapping


async def import_excel_with_mapping(session_id: str, mapping: ImportMappingSchema) -> dict:
    """Phase 2: Apply the confirmed mapping to parse and import data.

    Returns import counts summary.
    """
    # Read staged file
    tmp_path = _TMP_DIR / f"{session_id}.xlsx"
    if not tmp_path.exists():
        raise FileNotFoundError(f"导入会话不存在或已过期，请重新上传文件")

    content = tmp_path.read_bytes()

    # Delete temp file after reading
    try:
        tmp_path.unlink()
    except OSError:
        pass

    # Parse workbook with the mapping
    parsed = parse_workbook_with_mapping(content, mapping)

    # Clear existing data and write all via ORM
    await Account.all().delete()
    await Holding.all().delete()
    await Transaction.all().delete()
    await Deposit.all().delete()
    await ExchangeRate.all().delete()

    accounts = parsed["accounts"]
    holdings = parsed["holdings"]
    transactions = parsed["transactions"]
    deposits = parsed["deposits"]
    rates_data = parsed["rates"]

    # Ensure all holdings reference valid account IDs
    account_ids = {a["id"] for a in accounts}
    for h in holdings:
        if h["account_id"] not in account_ids:
            # Create a placeholder account if the referenced one doesn't exist
            acct = {
                "id": h["account_id"],
                "name": h.get("account_name", h["account_id"]),
                "category": "investment",
                "institution": "",
                "balances": [{"currency": h.get("currency", "USD"), "amount": 0}],
                "notes": "",
            }
            accounts.append(acct)
            account_ids.add(acct["id"])

    # Ensure all transactions reference valid account IDs
    for t in transactions:
        if t["account_id"] not in account_ids:
            acct = {
                "id": t["account_id"],
                "name": t.get("account_name", t["account_id"]),
                "category": "investment",
                "institution": "",
                "balances": [{"currency": "CNY", "amount": 0}],
                "notes": "",
            }
            accounts.append(acct)
            account_ids.add(acct["id"])

    # Ensure all deposits reference valid account IDs
    for d in deposits:
        if d["account_id"] not in account_ids:
            acct = {
                "id": d["account_id"],
                "name": d.get("account_name", d["account_id"]),
                "category": "cash",
                "institution": "",
                "balances": [{"currency": "CNY", "amount": 0}],
                "notes": "",
            }
            accounts.append(acct)
            account_ids.add(acct["id"])

    for acct in accounts:
        await Account.create(**acct)
    for h in holdings:
        await Holding.create(**h)
    for t in transactions:
        await Transaction.create(**t)
    for d in deposits:
        await Deposit.create(**d)

    for k, v in rates_data.items():
        if k != "CNY":
            await ExchangeRate.create(
                currency=k,
                rate_to_cny=v,
                date=date.today().isoformat(),
            )

    return {
        "accounts": len(accounts),
        "holdings": len(holdings),
        "transactions": len(transactions),
        "deposits": len(deposits),
        "rates": len([k for k in rates_data if k != "CNY"]),
    }
