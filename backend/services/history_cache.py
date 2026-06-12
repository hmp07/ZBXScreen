"""
趋势历史数据按需缓存
- 首次请求 → 调 Zabbix history.get / trend.get，结果写入 monitor_cache
- 后续 30s 内相同请求 → 直接从缓存返回
- TTL 过期后 → 重新调 Zabbix API 并更新缓存
"""
import json
import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models.monitor_cache import MonitorCache
from models.datasource import Datasource
from utils.crypto import decrypt_password
from services.zabbix_client import ZabbixClient

HISTORY_CACHE_TTL = 30  # 秒


def _cache_key(datasource_id: int, hostid: str, item_key: str, start_ts: int, end_ts: int) -> str:
    """生成缓存 key，含时间窗口哈希以区分不同范围"""
    window_hash = hashlib.md5(f"{start_ts}:{end_ts}".encode()).hexdigest()[:8]
    return f"history:{datasource_id}:{hostid}:{item_key}:{window_hash}"


async def get_or_fetch_history(
    datasource_id: int,
    hostid: str,
    item_key: str,
    start_ts: int,
    end_ts: int,
) -> list:
    """
    获取历史/趋势数据（带缓存）。
    优先从 monitor_cache 读取，未命中则调 Zabbix API 并缓存结果。
    """
    key = _cache_key(datasource_id, hostid, item_key, start_ts, end_ts)

    # ── 查缓存 ──
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(MonitorCache).where(
                MonitorCache.cache_key == key,
                MonitorCache.expires_at > datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        row = result.scalar_one_or_none()
        if row:
            return json.loads(row.data_json)

        # ── 缓存未命中：查数据源并调 Zabbix ──
        ds_result = await db.execute(select(Datasource).where(Datasource.id == datasource_id))
        ds = ds_result.scalar_one_or_none()
        if not ds:
            return []

        password = decrypt_password(ds.password_encrypted)
        client = ZabbixClient(ds.url, ds.username, password)

        # 根据时间跨度选择 history 或 trends
        if (end_ts - start_ts) <= 86400:
            data = await client.get_history([hostid], item_key, start_ts, end_ts)
        else:
            data = await client.get_trends([hostid], item_key, start_ts, end_ts)

        # ── 写入缓存 ──
        expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=HISTORY_CACHE_TTL)
        data_json = json.dumps(data, default=str)

        existing = await db.execute(
            select(MonitorCache).where(MonitorCache.cache_key == key)
        )
        cache_row = existing.scalar_one_or_none()
        if cache_row:
            cache_row.data_json = data_json
            cache_row.expires_at = expires
            cache_row.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            db.add(MonitorCache(
                cache_key=key,
                cache_type="history",
                datasource_id=datasource_id,
                data_json=data_json,
                expires_at=expires,
            ))
        await db.commit()

        return data
