"""
认证接口：登录、刷新 Token、修改密码
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from utils.crypto import hash_password, verify_password
from utils.auth import create_access_token, create_refresh_token, decode_token, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


# ── 请求/响应模型 ──

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(...)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(...)
    new_password: str = Field(..., min_length=6, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


# ── 统一响应格式 ──

def success(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


# ── 接口 ──

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail={"code": 1002, "message": "用户名或密码错误"})

    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id, user.username)

    # 检查是否为默认密码
    from config import settings
    is_default = verify_password(settings.default_admin_password, user.password_hash)

    return success({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 1800,  # 30 分钟
        "token_type": "Bearer",
        "is_default_password": is_default,
    })


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    """刷新 Token"""
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail={"code": 1002, "message": "请使用 refresh_token"})

    user_id = int(payload["sub"])
    username = payload["username"]

    access_token = create_access_token(user_id, username)
    refresh_token = create_refresh_token(user_id, username)

    return success({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 1800,
        "token_type": "Bearer",
    })


@router.post("/password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    result = await db.execute(select(User).where(User.id == int(current_user["sub"])))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail={"code": 1001, "message": "旧密码错误"})

    user.password_hash = hash_password(req.new_password)
    await db.commit()

    return success(message="密码修改成功")
