"""
数据源管理 API
- CRUD + 测试连接 + 启用/禁用
- 主机组 + 主机列表查询
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from database import get_db
from models.datasource import Datasource
from utils.auth import get_current_user
from utils.crypto import encrypt_password, decrypt_password
from services.zabbix_client import ZabbixClient, ZabbixAPIError

router = APIRouter(prefix="/api/v1/datasources", tags=["数据源"])


# ── 请求/响应模型 ──

class DatasourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)


class DatasourceUpdate(BaseModel):
    name: str = Field(None, min_length=1, max_length=100)
    url: str = Field(None, min_length=1, max_length=500)
    username: str = Field(None, min_length=1, max_length=100)
    password: str = Field(None, min_length=1)


class DatasourceResponse(BaseModel):
    id: int
    name: str
    url: str
    username: str
    enabled: bool
    last_connected_at: datetime | None
    zabbix_version: str | None
    created_at: datetime


# ── 辅助函数 ──

def success(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


def datasource_to_dict(ds: Datasource) -> dict:
    return {
        "id": ds.id,
        "name": ds.name,
        "url": ds.url,
        "username": ds.username,
        "enabled": ds.enabled,
        "last_connected_at": ds.last_connected_at.isoformat() if ds.last_connected_at else None,
        "zabbix_version": ds.zabbix_version,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
    }


def create_zabbix_client(ds: Datasource) -> ZabbixClient:
    """从数据源配置创建 ZabbixClient 实例"""
    password = decrypt_password(ds.password_encrypted)
    return ZabbixClient(ds.url, ds.username, password)


# ── 接口 ──

@router.get("")
async def list_datasources(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取所有数据源"""
    result = await db.execute(select(Datasource).order_by(Datasource.created_at.desc()))
    datasources = result.scalars().all()
    return success([datasource_to_dict(ds) for ds in datasources])


@router.post("")
async def create_datasource(
    req: DatasourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """添加数据源"""
    ds = Datasource(
        name=req.name,
        url=req.url,
        username=req.username,
        password_encrypted=encrypt_password(req.password),
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return success(datasource_to_dict(ds), "数据源添加成功")


@router.post("/{ds_id}/update")
async def update_datasource(
    ds_id: int,
    req: DatasourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """修改数据源"""
    result = await db.execute(select(Datasource).where(Datasource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "数据源不存在"})

    if req.name is not None:
        ds.name = req.name
    if req.url is not None:
        ds.url = req.url
    if req.username is not None:
        ds.username = req.username
    if req.password is not None:
        ds.password_encrypted = encrypt_password(req.password)

    ds.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(ds)
    return success(datasource_to_dict(ds), "数据源修改成功")


@router.post("/{ds_id}/delete")
async def delete_datasource(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """删除数据源"""
    result = await db.execute(select(Datasource).where(Datasource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "数据源不存在"})

    await db.delete(ds)
    await db.commit()
    return success(message="数据源已删除")


@router.post("/{ds_id}/test")
async def test_connection(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """测试 Zabbix 连接"""
    result = await db.execute(select(Datasource).where(Datasource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "数据源不存在"})

    try:
        client = create_zabbix_client(ds)
        info = await client.test_connection()

        # 更新连接状态
        ds.last_connected_at = datetime.now(timezone.utc).replace(tzinfo=None)
        ds.zabbix_version = info["version"]
        await db.commit()

        return success({
            "connected": True,
            "version": info["version"],
        }, "连接成功")
    except ZabbixAPIError as e:
        return success({
            "connected": False,
            "error": e.message,
        }, "连接失败")


@router.post("/{ds_id}/toggle")
async def toggle_datasource(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """启用/禁用数据源"""
    result = await db.execute(select(Datasource).where(Datasource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "数据源不存在"})

    ds.enabled = not ds.enabled
    await db.commit()
    return success({"enabled": ds.enabled}, f"数据源已{'启用' if ds.enabled else '禁用'}")


@router.get("/{ds_id}/hostgroups")
async def get_hostgroups(
    ds_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取主机组列表"""
    result = await db.execute(select(Datasource).where(Datasource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "数据源不存在"})

    try:
        client = create_zabbix_client(ds)
        groups = await client.get_hostgroups()
        return success(groups)
    except ZabbixAPIError as e:
        raise HTTPException(status_code=400, detail={"code": 2002, "message": e.message})


@router.get("/{ds_id}/hosts")
async def get_hosts(
    ds_id: int,
    groupid: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取主机列表"""
    result = await db.execute(select(Datasource).where(Datasource.id == ds_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "数据源不存在"})

    try:
        client = create_zabbix_client(ds)
        hosts = await client.get_hosts(groupids=[groupid] if groupid else None)
        return success(hosts)
    except ZabbixAPIError as e:
        raise HTTPException(status_code=400, detail={"code": 2002, "message": e.message})
