"""
监控大屏数据接口
- 从 monitor_cache 表读取聚合数据（由调度器预写入）
- 前端轮询这些接口，不直接调 Zabbix API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from database import get_db
from models.monitor_cache import MonitorCache
from models.alert_record import AlertRecord
from utils.auth import get_current_user
from utils.cache import memory_cache

router = APIRouter(prefix="/api/v1/monitor", tags=["监控大屏"])


def success(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


async def get_cached(db: AsyncSession, cache_type: str, datasource_id: int | None = None) -> dict | list | None:
    """从缓存表读取数据（先内存缓存，再 SQLite 缓存表）"""
    cache_key = f"{cache_type}_{datasource_id or 'all'}"
    mem = memory_cache.get(cache_key)
    if mem is not None:
        return mem

    result = await db.execute(
        select(MonitorCache).where(
            MonitorCache.cache_key == cache_key,
            MonitorCache.expires_at > datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    row = result.scalar_one_or_none()
    if row:
        import json
        data = json.loads(row.data_json)
        # 回填内存缓存
        memory_cache.set(cache_key, data, 30)
        return data
    return None


# ── 汇总 ──

@router.get("/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """大屏汇总数据：主机总数/在线/离线/告警数"""
    data = await get_cached(db, "summary")
    if data is None:
        data = {"total_hosts": 0, "online_hosts": 0, "offline_hosts": 0, "alert_count": 0}
    return success(data)


# ── 主机 ──

@router.get("/hosts")
async def get_monitor_hosts(
    datasource_id: int = Query(None),
    hostgroup_id: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """主机最新数据列表"""
    hosts = await get_cached(db, "hosts", datasource_id) or []
    if hostgroup_id:
        hosts = [h for h in hosts if any(
            g.get("groupid") == hostgroup_id for g in h.get("groups", [])
        )]
    return success(hosts[:limit])


# ── TOP N 排行（从聚合缓存直接返回）──

@router.get("/top-cpu")
async def get_top_cpu(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """CPU 使用率 TOP N"""
    data = await get_cached(db, "top_cpu") or []
    return success(data[:limit])


@router.get("/top-memory")
async def get_top_memory(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """内存使用率 TOP N"""
    data = await get_cached(db, "top_memory") or []
    return success(data[:limit])


@router.get("/top-disk")
async def get_top_disk(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """磁盘使用率 TOP N"""
    data = await get_cached(db, "top_disk") or []
    return success(data[:limit])


@router.get("/top-network-in")
async def get_top_network_in(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """网络入流量 TOP N"""
    data = await get_cached(db, "top_network_in") or []
    return success(data[:limit])


@router.get("/top-network-out")
async def get_top_network_out(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """网络出流量 TOP N"""
    data = await get_cached(db, "top_network_out") or []
    return success(data[:limit])


# ── 告警 ──

@router.get("/alerts")
async def get_recent_alerts(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """最近活跃告警列表"""
    result = await db.execute(
        select(AlertRecord)
        .where(AlertRecord.status == "active")
        .order_by(AlertRecord.first_occurred.desc())
        .limit(limit)
    )
    records = result.scalars().all()
    return success([{
        "id": r.id,
        "host_name": r.host_name,
        "trigger_name": r.trigger_name,
        "level": r.level,
        "status": r.status,
        "value": r.value,
        "first_occurred": r.first_occurred.isoformat() if r.first_occurred else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in records])
