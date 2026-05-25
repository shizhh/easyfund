"""Database lifecycle management — SQLite via Tortoise ORM."""

import asyncio
import os
from pathlib import Path

from tortoise import Tortoise

DATA_DIR = Path(__file__).parent.parent / "data"

_current_data_dir: str | None = None
_db_lock = asyncio.Lock()


def db_path_for_data_dir(data_dir: str) -> Path:
    """Map data_dir string to a SQLite file path."""
    if not data_dir:
        return DATA_DIR / "easyfund.db"
    return DATA_DIR / f"{data_dir}.db"


def _resolve_data_dir() -> str:
    """Resolve data_dir from EASYFUND_MOCK env var."""
    if os.environ.get("EASYFUND_MOCK", "").lower() in ("1", "true", "yes"):
        return "mock"
    return ""


async def ensure_db(data_dir: str = "") -> None:
    """Ensure the correct DB is connected for this data_dir.

    Uses an asyncio Lock + double-check pattern so that concurrent
    requests for the same data_dir share a single Tortoise.init() call
    instead of colliding and corrupting the global context.
    """
    global _current_data_dir

    # Fast path: already connected to the right DB
    if data_dir == _current_data_dir and _current_data_dir is not None:
        return

    async with _db_lock:
        # Double-check after acquiring lock — another request may have
        # already completed the init while we waited.
        if data_dir == _current_data_dir and _current_data_dir is not None:
            return

        await Tortoise.close_connections()

        db_path = db_path_for_data_dir(data_dir)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite://{db_path}"

        await Tortoise.init(
            db_url=db_url,
            modules={"models": ["backend.models"]},
            _enable_global_fallback=True,
        )
        await Tortoise.generate_schemas(safe=True)

        # Performance pragmas for SQLite
        conn = Tortoise.get_connection("default")
        await conn.execute_query("PRAGMA journal_mode=WAL")
        await conn.execute_query("PRAGMA synchronous=NORMAL")
        await conn.execute_query("PRAGMA cache_size=-8000")
        await conn.execute_query("PRAGMA mmap_size=268435456")
        await conn.execute_query("PRAGMA busy_timeout=5000")

        _current_data_dir = data_dir


async def close_db() -> None:
    """Close all DB connections."""
    global _current_data_dir
    await Tortoise.close_connections()
    _current_data_dir = None
