"""
主机监控接口
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from database import get_db
from models.datasource import Datasource
from utils.auth import get_current_user
from utils.crypto import decrypt_password
from services.zabbix_client import ZabbixClient, ZabbixAPIError

router = APIRouter(prefix="/api/v1/hosts", tags=["主机监控"])


def success(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


def create_client(ds: Datasource) -> ZabbixClient:
    return ZabbixClient(ds.url, ds.username, decrypt_password(ds.password_encrypted))


@router.get("")
async def get_host_list(
    datasource_id: int = Query(None),
    hostgroup_id: str = Query(None),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """主机列表（分页 + 搜索 + 筛选）。不指定 datasource_id 时聚合所有数据源。"""
    # 获取数据源列表
    if datasource_id:
        ds_result = await db.execute(select(Datasource).where(Datasource.id == datasource_id))
        ds_list = [ds_result.scalar_one_or_none()]
        if not ds_list[0]:
            raise HTTPException(status_code=404, detail={"code": 1003, "message": "数据源不存在"})
    else:
        result = await db.execute(select(Datasource).where(Datasource.enabled == True))
        ds_list = result.scalars().all()

    # 并发拉取所有数据源的主机
    all_hosts = []
    seen = set()

    async def fetch_from_ds(ds: Datasource):
        try:
            client = create_client(ds)
            groupids = [hostgroup_id] if hostgroup_id else None
            hosts = await client.get_hosts(groupids=groupids, filter_name=search)
            for h in hosts:
                h["_datasource_id"] = ds.id
                h["_datasource_name"] = ds.name
            return hosts
        except ZabbixAPIError:
            return []

    tasks = [fetch_from_ds(ds) for ds in ds_list]
    results = await asyncio.gather(*tasks)

    for hosts in results:
        for h in hosts:
            key = h.get("host") or h.get("name", "")
            if key and key not in seen:
                seen.add(key)
                all_hosts.append(h)

    # 搜索过滤
    if search:
        search_lower = search.lower()
        all_hosts = [h for h in all_hosts if search_lower in (h.get("host", "") + h.get("name", "")).lower()]

    # 分页
    total = len(all_hosts)
    start = (page - 1) * page_size
    hosts_page = all_hosts[start:start + page_size]

    return success({
        "items": hosts_page,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
    })


@router.get("/{hostid}")
async def get_host_detail(
    hostid: str,
    datasource_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """主机详情"""
    result = await db.execute(select(Datasource).where(Datasource.id == datasource_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "数据源不存在"})

    try:
        client = create_client(ds)
        hosts = await client.get_hosts(hostids=[hostid])
        if not hosts:
            raise HTTPException(status_code=404, detail={"code": 1003, "message": "主机不存在"})

        host = hosts[0]
        key_items = await client.get_items(
            hostids=[hostid],
            search_keys=["system.cpu.util[,idle]", "vm.memory.utilization",
                         "vm.memory.size[pused]", "vm.memory.size[pavailable]",
                         "vfs.fs.size[/,pused]", "net.if.in", "net.if.out"],
        )

        metrics = {}
        for item in key_items:
            key = item["key_"]
            lastval = item.get("lastvalue", "0")
            try:
                val = float(lastval)
            except (ValueError, TypeError):
                val = 0.0

            if "cpu" in key and "idle" in key:
                metrics["cpu_usage"] = round(100.0 - val, 1)
            elif "memory" in key and "utilization" in key:
                metrics["memory_usage"] = round(val, 1)
            elif "memory" in key and "pused" in key:
                metrics["memory_usage"] = round(val, 1)
            elif "memory" in key and "pavailable" in key:
                metrics["memory_usage"] = round(100.0 - val, 1)
            elif "vfs.fs" in key:
                metrics["disk_usage"] = round(val, 1)
            elif "net.if.in" in key and "lo" not in key:
                metrics["network_in"] = val
            elif "net.if.out" in key and "lo" not in key:
                metrics["network_out"] = val

        return success({"host": host, "metrics": metrics})
    except ZabbixAPIError as e:
        raise HTTPException(status_code=400, detail={"code": 2002, "message": e.message})


@router.get("/{hostid}/history")
async def get_host_history(
    hostid: str,
    datasource_id: int = Query(...),
    item_key: str = Query(...),
    start_time: str = Query(None),
    end_time: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """主机历史数据"""
    result = await db.execute(select(Datasource).where(Datasource.id == datasource_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "数据源不存在"})

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = datetime.fromisoformat(start_time) if start_time else now - timedelta(hours=1)
    end = datetime.fromisoformat(end_time) if end_time else now
    start_ts = int(start.timestamp())
    end_ts = int(end.timestamp())

    try:
        client = create_client(ds)
        if (end_ts - start_ts) <= 86400:
            data = await client.get_history([hostid], item_key, start_ts, end_ts)
        else:
            data = await client.get_trends([hostid], item_key, start_ts, end_ts)

        return success({
            "hostid": hostid, "item_key": item_key,
            "start_time": start.isoformat(), "end_time": end.isoformat(),
            "data": data,
        })
    except ZabbixAPIError as e:
        raise HTTPException(status_code=400, detail={"code": 2002, "message": e.message})
