"""告警管理 API"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, extract, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.alert_rule import AlertRule
from models.alert_record import AlertRecord
from utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/alerts", tags=["告警管理"])


def success(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


# ── 规则管理 ──

class RuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    rule_type: str = Field("zabbix_trigger")
    datasource_id: int | None = None
    hostgroup_id: str | None = None
    level: str = Field("WARNING")
    enabled: bool = True
    config_json: str | None = None


@router.get("/rules")
async def list_rules(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(AlertRule).order_by(AlertRule.created_at.desc()))
    rules = result.scalars().all()
    return success([{
        "id": r.id, "name": r.name, "rule_type": r.rule_type,
        "datasource_id": r.datasource_id, "hostgroup_id": r.hostgroup_id,
        "level": r.level, "enabled": r.enabled, "config_json": r.config_json,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rules])


@router.post("/rules")
async def create_rule(
    req: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rule = AlertRule(**req.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return success({"id": rule.id}, "规则创建成功")


@router.post("/rules/{rule_id}/update")
async def update_rule(
    rule_id: int,
    req: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "规则不存在"})
    for key, value in req.model_dump().items():
        setattr(rule, key, value)
    await db.commit()
    return success(message="规则修改成功")


@router.post("/rules/{rule_id}/delete")
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "规则不存在"})
    await db.delete(rule)
    await db.commit()
    return success(message="规则已删除")


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "规则不存在"})
    rule.enabled = not rule.enabled
    await db.commit()
    return success({"enabled": rule.enabled})


# ── 告警记录 ──

@router.get("/records")
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: str = Query(None),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = select(AlertRecord)
    if level:
        query = query.where(AlertRecord.level == level)
    if status:
        query = query.where(AlertRecord.status == status)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(AlertRecord.created_at.desc()).offset(offset).limit(page_size)
    )
    records = result.scalars().all()

    return success({
        "items": [{
            "id": r.id, "event_id": r.event_id, "host_id": r.host_id,
            "host_name": r.host_name, "trigger_name": r.trigger_name,
            "level": r.level, "status": r.status, "value": r.value,
            "first_occurred": r.first_occurred.isoformat() if r.first_occurred else None,
            "recovered_at": r.recovered_at.isoformat() if r.recovered_at else None,
            "webhook_pushed": r.webhook_pushed,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in records],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    })


@router.get("/stats")
async def alert_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """告警统计（按级别分布）"""
    result = await db.execute(
        select(AlertRecord.level, func.count(AlertRecord.id))
        .where(AlertRecord.status == "active")
        .group_by(AlertRecord.level)
    )
    by_level = {row[0]: row[1] for row in result.all()}
    return success({"by_level": by_level})


@router.get("/dashboard")
async def alert_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """告警聚合大屏数据 — 一次返回所有维度的统计分析"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_24h = now - timedelta(hours=24)

    # ── 1. Summary KPIs ──
    # 活跃告警数
    active_result = await db.execute(
        select(func.count(AlertRecord.id)).where(AlertRecord.status == "active")
    )
    active_count = active_result.scalar() or 0

    # 今日新增
    today_new_result = await db.execute(
        select(func.count(AlertRecord.id)).where(AlertRecord.created_at >= today_start)
    )
    today_new = today_new_result.scalar() or 0

    # 今日恢复
    today_recovered_result = await db.execute(
        select(func.count(AlertRecord.id)).where(
            AlertRecord.recovered_at >= today_start,
            AlertRecord.status == "recovered",
        )
    )
    today_recovered = today_recovered_result.scalar() or 0

    # 平均恢复时长（分钟）
    avg_recovery_result = await db.execute(
        select(func.avg(
            func.julianday(AlertRecord.recovered_at) - func.julianday(AlertRecord.first_occurred)
        )).where(
            AlertRecord.status == "recovered",
            AlertRecord.recovered_at.isnot(None),
            AlertRecord.first_occurred.isnot(None),
        )
    )
    avg_days = avg_recovery_result.scalar()
    avg_recovery_minutes = round(avg_days * 24 * 60, 0) if avg_days else 0

    # 未推送数（active 但 webhook_pushed=false）
    unpushed_result = await db.execute(
        select(func.count(AlertRecord.id)).where(
            AlertRecord.status == "active",
            AlertRecord.webhook_pushed == False,
        )
    )
    unpushed_count = unpushed_result.scalar() or 0

    summary = {
        "active_count": active_count,
        "today_new": today_new,
        "today_recovered": today_recovered,
        "avg_recovery_minutes": int(avg_recovery_minutes),
        "unpushed_count": unpushed_count,
    }

    # ── 2. 按级别分布（活跃告警）──
    level_result = await db.execute(
        select(AlertRecord.level, func.count(AlertRecord.id))
        .where(AlertRecord.status == "active")
        .group_by(AlertRecord.level)
    )
    by_level = {}
    for row in level_result.all():
        by_level[row[0]] = row[1]
    # 确保所有级别都有值
    for lv in ["INFO", "WARNING", "AVERAGE", "HIGH", "DISASTER"]:
        by_level.setdefault(lv, 0)

    # ── 3. 近 24h 趋势（按小时 × 级别，排除 INFO）──
    trend_result = await db.execute(
        select(
            func.strftime("%H", AlertRecord.first_occurred).label("hour"),
            AlertRecord.level,
            func.count(AlertRecord.id),
        ).where(
            AlertRecord.first_occurred >= yesterday_24h,
            AlertRecord.level != "INFO",
        ).group_by("hour", AlertRecord.level).order_by("hour")
    )
    trend_map = {}
    for row in trend_result.all():
        hour, level, cnt = row[0], row[1], row[2]
        if hour not in trend_map:
            trend_map[hour] = {"hour": hour, "WARNING": 0, "AVERAGE": 0, "HIGH": 0, "DISASTER": 0}
        trend_map[hour][level] = cnt
    # 填充缺失的小时
    trend_24h = []
    for h in range(24):
        hour_str = f"{h:02d}"
        if hour_str in trend_map:
            trend_24h.append(trend_map[hour_str])
        else:
            trend_24h.append({"hour": f"{h:02d}:00", "WARNING": 0, "AVERAGE": 0, "HIGH": 0, "DISASTER": 0})

    # ── 4. 主机告警 TOP 10 ──
    host_result = await db.execute(
        select(
            AlertRecord.host_name,
            func.count(AlertRecord.id).label("total"),
            func.sum(case((AlertRecord.status == "active", 1), else_=0)).label("active"),
            func.sum(case((AlertRecord.status == "recovered", 1), else_=0)).label("recovered"),
        ).group_by(AlertRecord.host_name).order_by(func.count(AlertRecord.id).desc()).limit(10)
    )
    top_hosts = []
    for row in host_result.all():
        top_hosts.append({
            "host_name": row[0], "total": row[1],
            "active": row[2] or 0, "recovered": row[3] or 0,
        })

    # ── 5. 告警类型 TOP 8 ──
    trigger_result = await db.execute(
        select(
            AlertRecord.trigger_name,
            func.count(AlertRecord.id).label("count"),
        ).group_by(AlertRecord.trigger_name).order_by(func.count(AlertRecord.id).desc()).limit(10)
    )
    top_triggers = [{"trigger_name": row[0], "count": row[1]} for row in trigger_result.all()]

    # ── 6. 最近活跃告警 ──
    recent_result = await db.execute(
        select(AlertRecord)
        .where(AlertRecord.status == "active")
        .order_by(AlertRecord.created_at.desc())
        .limit(20)
    )
    recent_active = []
    for r in recent_result.scalars().all():
        recent_active.append({
            "id": r.id, "host_name": r.host_name, "trigger_name": r.trigger_name,
            "level": r.level, "status": r.status, "value": r.value,
            "first_occurred": r.first_occurred.isoformat() if r.first_occurred else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return success({
        "summary": summary,
        "by_level": by_level,
        "trend_24h": trend_24h,
        "top_hosts": top_hosts,
        "top_triggers": top_triggers,
        "recent_active": recent_active,
    })
