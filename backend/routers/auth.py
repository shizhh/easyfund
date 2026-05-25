"""Auth router: login and current user endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import load_users, verify_password, create_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    display_name: str


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """Authenticate user and return JWT token."""
    users = load_users()
    user = next((u for u in users if u["username"] == req.username), None)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(user["username"], user.get("data_dir", ""), user.get("display_name", ""))
    return LoginResponse(
        token=token,
        username=user["username"],
        display_name=user.get("display_name", ""),
    )


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    """Return current user info (validates token)."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "username": user["sub"],
        "display_name": user.get("name", ""),
        "data_dir": user.get("data_dir", ""),
    }
