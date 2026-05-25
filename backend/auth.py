"""Authentication: user loading, password verification, JWT, FastAPI dependencies."""

import json
import os
import secrets
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import bcrypt

from backend.database import DATA_DIR, ensure_db, _resolve_data_dir

USERS_PATH = DATA_DIR / "users.json"

# JWT secret: prefer env var, otherwise generate at startup
JWT_SECRET = os.environ.get("JWT_SECRET", "")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_hex(32)
    warnings.warn(
        "JWT_SECRET not set in environment. Using auto-generated secret. "
        "Tokens will invalidate on restart. Set JWT_SECRET for persistence.",
        stacklevel=2,
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7


def load_users() -> list[dict]:
    """Load users from data/users.json."""
    if not USERS_PATH.exists():
        return []
    with open(USERS_PATH) as f:
        return json.load(f)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def create_token(username: str, data_dir: str, display_name: str) -> str:
    """Create a JWT token with user claims."""
    payload = {
        "sub": username,
        "data_dir": data_dir,
        "name": display_name,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# --- FastAPI dependencies ---

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """Extract and validate JWT from Authorization header.
    Returns user payload dict or None (for backward compatibility)."""
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


async def get_user_data_dir(user: dict | None = Depends(get_current_user)) -> str:
    """Return the data_dir string for the authenticated user."""
    if user is None:
        return _resolve_data_dir()
    return user.get("data_dir", "")


async def get_db(data_dir: str = Depends(get_user_data_dir)) -> str:
    """FastAPI dependency: ensure correct DB is connected, return data_dir."""
    await ensure_db(data_dir)
    return data_dir


