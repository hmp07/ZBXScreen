"""认证接口测试"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User
from utils.crypto import hash_password


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_db: AsyncSession):
    """登录成功"""
    # 创建测试用户
    test_db.add(User(username="testadmin", password_hash=hash_password("test123")))
    await test_db.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "test123",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["token_type"] == "Bearer"
    assert data["data"]["expires_in"] == 1800


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_db: AsyncSession):
    """密码错误"""
    test_db.add(User(username="testadmin", password_hash=hash_password("test123")))
    await test_db.commit()

    resp = await client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "wrongpassword",
    })

    assert resp.status_code == 401
    data = resp.json()
    assert data["detail"]["code"] == 1002


@pytest.mark.asyncio
async def test_login_user_not_found(client: AsyncClient):
    """用户不存在"""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "nonexistent",
        "password": "test123",
    })

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_db: AsyncSession):
    """刷新 Token"""
    test_db.add(User(username="testadmin", password_hash=hash_password("test123")))
    await test_db.commit()

    # 先登录获取 token
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "test123",
    })
    refresh_token = login_resp.json()["data"]["refresh_token"]

    # 用 refresh_token 刷新
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "access_token" in data["data"]


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, test_db: AsyncSession):
    """修改密码"""
    test_db.add(User(username="testadmin", password_hash=hash_password("test123")))
    await test_db.commit()

    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "test123",
    })
    token = login_resp.json()["data"]["access_token"]

    # 修改密码
    resp = await client.post(
        "/api/v1/auth/password",
        json={"old_password": "test123", "new_password": "newpass456"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    # 用旧密码应该登录失败
    resp2 = await client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "test123",
    })
    assert resp2.status_code == 401

    # 用新密码应该登录成功
    resp3 = await client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "newpass456",
    })
    assert resp3.status_code == 200


@pytest.mark.asyncio
async def test_protected_route_without_token(client: AsyncClient):
    """无 Token 访问受保护接口"""
    resp = await client.post(
        "/api/v1/auth/password",
        json={"old_password": "x", "new_password": "y"},
    )
    assert resp.status_code == 403  # FastAPI HTTPBearer 返回 403
