"""网络设备监控大屏 API"""
import json

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.alert_record import AlertRecord
from models.monitor_cache import MonitorCache
from utils.auth import get_current_user
from utils.cache import memory_cache

router = APIRouter(prefix="/api/v1/network", tags=["网络大屏"])


def success(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


@router.get("/dashboard")
async def network_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """网络大屏聚合数据"""

    # ── 1. 网络设备数据（先内存缓存，再 SQLite）──
    net_row = None
    net_data = memory_cache.get("network_devices_all")
    if net_data is None:
        network_cache = await db.execute(
            select(MonitorCache).where(MonitorCache.cache_key == "network_devices_all")
        )
        net_row = network_cache.scalar_one_or_none()
        if net_row:
            net_data = json.loads(net_row.data_json)
            memory_cache.set("network_devices_all", net_data, 30)
    else:
        net_row = True  # 标记缓存命中

    device_categories = []
    vendor_distribution = []
    crc_errors_top10 = []
    port_traffic_top10 = []
    port_util_top10 = []
    summary_data = {"total": 0, "online": 0, "offline": 0, "alert_devices": 0, "total_traffic_mbps": 0.0}

    network_hostnames = set()
    if net_data:
        device_categories = net_data.get("device_categories", [])
        vendor_distribution = net_data.get("vendor_distribution", [])
        crc_errors_top10 = net_data.get("crc_errors_top10", [])
        port_traffic_top10 = net_data.get("port_traffic_top10", [])
        port_util_top10 = net_data.get("port_util_top10", [])

        # 使用网络设备专属汇总
        ns = net_data.get("network_summary", {})
        summary_data["total"] = ns.get("total_devices", 0)
        summary_data["online"] = ns.get("online_devices", 0)
        summary_data["offline"] = ns.get("offline_devices", 0)
        summary_data["total_traffic_mbps"] = ns.get("total_traffic_mbps", 0.0)

        # 收集网络设备主机名（用于过滤告警）
        network_hostnames = set(net_data.get("network_hosts", []))

    # ── 3. 告警严重等级分布（仅网络设备活跃告警）──
    if network_hostnames:
        level_result = await db.execute(
            select(AlertRecord.level, func.count(AlertRecord.id))
            .where(AlertRecord.status == "active", AlertRecord.host_name.in_(network_hostnames))
            .group_by(AlertRecord.level)
        )
    else:
        level_result = await db.execute(
            select(AlertRecord.level, func.count(AlertRecord.id))
            .where(AlertRecord.status == "active")
            .group_by(AlertRecord.level)
        )
    by_severity = {}
    for row_data in level_result.all():
        by_severity[row_data[0]] = row_data[1]
    for lv in ["INFO", "WARNING", "AVERAGE", "HIGH", "DISASTER"]:
        by_severity.setdefault(lv, 0)

    # ── 4. 告警设备数（仅网络设备）──
    if network_hostnames:
        alert_devices_result = await db.execute(
            select(func.count(func.distinct(AlertRecord.host_name)))
            .where(AlertRecord.status == "active", AlertRecord.host_name.in_(network_hostnames))
        )
    else:
        alert_devices_result = await db.execute(
            select(func.count(func.distinct(AlertRecord.host_name)))
            .where(AlertRecord.status == "active")
        )
    summary_data["alert_devices"] = alert_devices_result.scalar() or 0

    # ── 5. 最近活跃告警（仅网络设备）──
    if network_hostnames:
        recent_result = await db.execute(
            select(AlertRecord)
            .where(AlertRecord.status == "active", AlertRecord.host_name.in_(network_hostnames))
            .order_by(AlertRecord.created_at.desc())
            .limit(20)
        )
    else:
        recent_result = await db.execute(
            select(AlertRecord)
            .where(AlertRecord.status == "active")
            .order_by(AlertRecord.created_at.desc())
            .limit(20)
        )
    recent_alerts = []
    for r in recent_result.scalars().all():
        recent_alerts.append({
            "id": r.id,
            "host_name": r.host_name,
            "trigger_name": r.trigger_name,
            "level": r.level,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return success({
        "summary": summary_data,
        "device_categories": device_categories,
        "vendor_distribution": vendor_distribution,
        "by_severity": by_severity,
        "port_traffic_top10": port_traffic_top10,
        "port_util_top10": port_util_top10,
        "crc_errors_top10": crc_errors_top10,
        "recent_alerts": recent_alerts,
    })
