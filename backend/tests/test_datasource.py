"""数据源管理接口测试"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from utils.crypto import hash_password, encrypt_password
from models.datasource import Datasource


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _login(client: AsyncClient) -> str:
    """登录并返回 access_token"""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "test123",
    })
    return resp.json()["data"]["access_token"]


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, test_db: AsyncSession):
    """创建 admin 用户并返回 token"""
    test_db.add(User(username="admin", password_hash=hash_password("test123")))
    await test_db.commit()
    return await _login(client)


@pytest.mark.asyncio
async def test_create_datasource(client: AsyncClient, test_db: AsyncSession, admin_token: str):
    """添加数据源"""
    resp = await client.post(
        "/api/v1/datasources",
        json={
            "name": "测试Zabbix",
            "url": "http://zabbix.example.com",
            "username": "Admin",
            "password": "zabbix123",
        },
        headers=_auth_header(admin_token),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "测试Zabbix"
    assert data["data"]["username"] == "Admin"
    # 密码不应出现在响应中
    assert "password" not in data["data"]
    assert data["data"]["enabled"] is True


@pytest.mark.asyncio
async def test_list_datasources(client: AsyncClient, test_db: AsyncSession, admin_token: str):
    """获取数据源列表"""
    # 先创建一个数据源
    test_db.add(Datasource(
        name="Zabbix1",
        url="http://zbx1.example.com",
        username="admin",
        password_encrypted=encrypt_password("pass1"),
    ))
    await test_db.commit()

    resp = await client.get("/api/v1/datasources", headers=_auth_header(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_update_datasource(client: AsyncClient, test_db: AsyncSession, admin_token: str):
    """修改数据源"""
    ds = Datasource(
        name="OldName",
        url="http://old.example.com",
        username="admin",
        password_encrypted=encrypt_password("oldpass"),
    )
    test_db.add(ds)
    await test_db.commit()
    await test_db.refresh(ds)

    resp = await client.post(
        f"/api/v1/datasources/{ds.id}/update",
        json={"name": "NewName", "password": "newpass"},
        headers=_auth_header(admin_token),
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "NewName"


@pytest.mark.asyncio
async def test_delete_datasource(client: AsyncClient, test_db: AsyncSession, admin_token: str):
    """删除数据源"""
    ds = Datasource(
        name="ToDelete",
        url="http://del.example.com",
        username="admin",
        password_encrypted=encrypt_password("pass"),
    )
    test_db.add(ds)
    await test_db.commit()
    await test_db.refresh(ds)

    resp = await client.post(
        f"/api/v1/datasources/{ds.id}/delete",
        headers=_auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    # 确认已删除
    resp2 = await client.get("/api/v1/datasources", headers=_auth_header(admin_token))
    ids = [d["id"] for d in resp2.json()["data"]]
    assert ds.id not in ids


@pytest.mark.asyncio
async def test_toggle_datasource(client: AsyncClient, test_db: AsyncSession, admin_token: str):
    """启用/禁用数据源"""
    ds = Datasource(
        name="ToggleTest",
        url="http://toggle.example.com",
        username="admin",
        password_encrypted=encrypt_password("pass"),
        enabled=True,
    )
    test_db.add(ds)
    await test_db.commit()
    await test_db.refresh(ds)

    # 禁用
    resp = await client.post(
        f"/api/v1/datasources/{ds.id}/toggle",
        headers=_auth_header(admin_token),
    )
    assert resp.json()["data"]["enabled"] is False

    # 再次切换：启用
    resp2 = await client.put(
        f"/api/v1/datasources/{ds.id}/toggle",
        headers=_auth_header(admin_token),
    )
    assert resp2.json()["data"]["enabled"] is True


@pytest.mark.asyncio
async def test_datasource_not_found(client: AsyncClient, admin_token: str):
    """访问不存在的数据源"""
    resp = await client.get(
        "/api/v1/datasources/99999/hostgroups",
        headers=_auth_header(admin_token),
    )
    # 数据库中没有该数据源，API 返回 404
    assert resp.status_code in (404, 400)
