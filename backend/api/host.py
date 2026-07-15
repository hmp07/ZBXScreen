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
from models.monitor_cache import MonitorCache
from utils.auth import get_current_user
from utils.crypto import decrypt_password
from utils.cache import memory_cache
from services.zabbix_client import ZabbixClient, ZabbixAPIError

router = APIRouter(prefix="/api/v1/hosts", tags=["主机监控"])


def _enrich_host_status(h: dict) -> dict:
    """补充计算字段：zbx_status（原始Zabbix状态）+ online_status（在线状态）"""
    zbx_status = str(h.get("status", "0"))
    online_status = "disabled"
    if zbx_status != "1":
        # 主机未停用，检查接口可用性
        interfaces = h.get("interfaces", [])
        if interfaces:
            main_iface = None
            for iface in interfaces:
                if iface.get("main") == "1" or iface.get("main") == 1:
                    main_iface = iface
                    break
            if main_iface is None:
                main_iface = interfaces[0]
            avail = main_iface.get("available", "0")
            try:
                avail = int(avail) if isinstance(avail, str) else avail
            except (ValueError, TypeError):
                avail = 0
            online_status = "offline" if avail == 2 else "online"
        else:
            online_status = "online"  # 无接口信息默认在线
    h["zbx_status"] = zbx_status
    h["online_status"] = online_status
    return h


async def _get_cached_hosts(db: AsyncSession):
    """从缓存读取全量主机列表（scheduler 预聚合）。未命中返回 None。"""
    cache_key = "hosts_all"
    mem = memory_cache.get(cache_key)
    if mem is not None:
        return mem

    import json
    from datetime import datetime, timezone
    result = await db.execute(
        select(MonitorCache).where(
            MonitorCache.cache_key == cache_key,
            MonitorCache.expires_at > datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    row = result.scalar_one_or_none()
    if row:
        data = json.loads(row.data_json)
        memory_cache.set(cache_key, data, 30)
        return data
    return None


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
    # ── 优先从缓存读取（scheduler 每 30s 预聚合）──
    cached = await _get_cached_hosts(db)
    if cached:
        hosts = cached
        # datasource 筛选
        if datasource_id:
            hosts = [h for h in hosts if h.get("_datasource_id") == datasource_id]
        # hostgroup 筛选
        if hostgroup_id:
            hosts = [h for h in hosts if any(
                g.get("groupid") == hostgroup_id for g in h.get("groups", [])
            )]
        # 搜索
        if search:
            search_lower = search.lower()
            hosts = [h for h in hosts if search_lower in (h.get("host", "") + h.get("name", "")).lower()]
        # 分页
        total = len(hosts)
        start = (page - 1) * page_size
        hosts_page = hosts[start:start + page_size]
        # 补充计算字段
        enriched = [_enrich_host_status(h) for h in hosts_page]
        return success({
            "items": enriched,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
        })

    # ── 缓存未命中：实时查询 Zabbix（兜底）──
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
    import json
    from datetime import datetime, timezone

    result = await db.execute(select(Datasource).where(Datasource.id == datasource_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "数据源不存在"})

    # ── 优先从缓存读取指标 ──
    cache_key = "host_metrics_all"
    mem = memory_cache.get(cache_key)
    if mem is None:
        row = await db.execute(
            select(MonitorCache).where(
                MonitorCache.cache_key == cache_key,
                MonitorCache.expires_at > datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        row = row.scalar_one_or_none()
        if row:
            mem = json.loads(row.data_json)
            memory_cache.set(cache_key, mem, 30)

    if mem:
        entry = mem.get(f"{datasource_id}:{hostid}")
        if entry:
            # 从 hosts 缓存取主机对象
            hosts_cached = await _get_cached_hosts(db)
            host_obj = None
            if hosts_cached:
                for h in hosts_cached:
                    if h.get("hostid") == hostid and h.get("_datasource_id") == datasource_id:
                        host_obj = h
                        break
            if host_obj is None:
                host_obj = {"hostid": hostid, "host": entry["host"], "name": entry["hostname"]}

            metrics = {k: v for k, v in entry.items()
                       if k in ("cpu_usage", "memory_usage", "disk_usage", "network_in", "network_out")}
            return success({"host": host_obj, "metrics": metrics})

    # ── 缓存未命中：实时查询 Zabbix（兜底）──

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
                metrics["network_in"] = round(val / 1_000_000, 2)  # bps → Mbps
            elif "net.if.out" in key and "lo" not in key:
                metrics["network_out"] = round(val / 1_000_000, 2)  # bps → Mbps

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
    from services.history_cache import get_or_fetch_history

    result = await db.execute(select(Datasource).where(Datasource.id == datasource_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "数据源不存在"})

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # 将时间对齐到 30s 边界，确保同一时间窗口内请求命中缓存
    now_aligned = now.replace(second=(now.second // 30) * 30, microsecond=0)
    if start_time:
        start = datetime.fromisoformat(start_time)
        start_aligned = start.replace(second=(start.second // 30) * 30, microsecond=0)
    else:
        start_aligned = now_aligned - timedelta(hours=1)
    if end_time:
        end = datetime.fromisoformat(end_time)
        end_aligned = end.replace(second=(end.second // 30) * 30, microsecond=0)
    else:
        end_aligned = now_aligned
    start_ts = int(start_aligned.timestamp())
    end_ts = int(end_aligned.timestamp())

    try:
        # 缓存优先（内部自动回退到实时 Zabbix API）
        data = await get_or_fetch_history(datasource_id, hostid, item_key, start_ts, end_ts)

        return success({
            "hostid": hostid, "item_key": item_key,
            "start_time": start.isoformat(), "end_time": end.isoformat(),
            "data": data,
        })
    except ZabbixAPIError as e:
        raise HTTPException(status_code=400, detail={"code": 2002, "message": e.message})
