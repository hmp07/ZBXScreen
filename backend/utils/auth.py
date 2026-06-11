"""
JWT 认证工具
- Token 生成（access_token + refresh_token）
- Token 验证
- 当前用户依赖注入
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings

security = HTTPBearer()


def _now() -> datetime:
    """返回当前 UTC 时间（naive datetime，兼容 PyJWT）"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_access_token(user_id: int, username: str) -> str:
    """生成 access_token（有效期 30 分钟）"""
    now = _now()
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def create_refresh_token(user_id: int, username: str) -> str:
    """生成 refresh_token（有效期 7 天）"""
    now = _now()
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    """解码 JWT token，验证签名和过期时间"""
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"code": 1002, "message": "Token 已过期"})
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail={"code": 1002, "message": "Token 无效"})


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """从请求头提取并验证 JWT，返回当前用户信息"""
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail={"code": 1002, "message": "请使用 access_token"})
    return payload
