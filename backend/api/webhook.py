"""Webhook 管理 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.webhook_config import WebhookConfig
from models.webhook_log import WebhookLog
from utils.auth import get_current_user

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhook"])


def success(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


class WebhookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=1000)
    method: str = Field("POST")
    headers_json: str | None = None
    trigger_levels: str | None = None
    hostgroup_ids: str | None = None
    enabled: bool = True
    retry_count: int = Field(3)
    retry_interval: int = Field(10)
    timeout: int = Field(10)


@router.get("")
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(WebhookConfig).order_by(WebhookConfig.created_at.desc()))
    configs = result.scalars().all()
    return success([{
        "id": c.id, "name": c.name, "url": c.url, "method": c.method,
        "headers_json": c.headers_json, "trigger_levels": c.trigger_levels,
        "hostgroup_ids": c.hostgroup_ids, "enabled": c.enabled,
        "retry_count": c.retry_count, "retry_interval": c.retry_interval, "timeout": c.timeout,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    } for c in configs])


@router.post("")
async def create_webhook(
    req: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    cfg = WebhookConfig(**req.model_dump())
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return success({"id": cfg.id}, "Webhook 端点创建成功")


@router.post("/{webhook_id}/update")
async def update_webhook(
    webhook_id: int,
    req: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(WebhookConfig).where(WebhookConfig.id == webhook_id))
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "Webhook 不存在"})
    for key, value in req.model_dump().items():
        setattr(cfg, key, value)
    await db.commit()
    return success(message="Webhook 修改成功")


@router.post("/{webhook_id}/delete")
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(WebhookConfig).where(WebhookConfig.id == webhook_id))
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "Webhook 不存在"})
    await db.delete(cfg)
    await db.commit()
    return success(message="Webhook 已删除")


@router.post("/{webhook_id}/toggle")
async def toggle_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(WebhookConfig).where(WebhookConfig.id == webhook_id))
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "Webhook 不存在"})
    cfg.enabled = not cfg.enabled
    await db.commit()
    return success({"enabled": cfg.enabled})


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """发送测试推送"""
    result = await db.execute(select(WebhookConfig).where(WebhookConfig.id == webhook_id))
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail={"code": 1003, "message": "Webhook 不存在"})

    import httpx, json, uuid
    test_payload = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "event_type": "test",
        "event_time": "2026-06-01T10:00:00Z",
        "source": {"system": "ZBXScreen", "version": "1.2.0"},
        "message": "This is a test webhook from ZabbixScreen",
    }
    headers = {"Content-Type": "application/json"}
    if cfg.headers_json:
        try:
            headers.update(json.loads(cfg.headers_json))
        except json.JSONDecodeError:
            pass

    try:
        async with httpx.AsyncClient(timeout=cfg.timeout) as client:
            if cfg.method.upper() == "PUT":
                resp = await client.put(cfg.url, json=test_payload, headers=headers)
            else:
                resp = await client.post(cfg.url, json=test_payload, headers=headers)

        return success({
            "success": 200 <= resp.status_code < 300,
            "http_status": resp.status_code,
        }, "测试推送完成")
    except Exception as e:
        return success({
            "success": False,
            "error": str(e),
        }, "测试推送失败")


@router.get("/{webhook_id}/logs")
async def webhook_logs(
    webhook_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = select(WebhookLog).where(WebhookLog.webhook_id == webhook_id)
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(WebhookLog.pushed_at.desc()).offset(offset).limit(page_size)
    )
    logs = result.scalars().all()
    return success({
        "items": [{
            "id": l.id, "event_id": l.event_id, "status": l.status,
            "http_status_code": l.http_status_code, "retry_count": l.retry_count,
            "response_ms": l.response_ms, "error_message": l.error_message,
            "pushed_at": l.pushed_at.isoformat() if l.pushed_at else None,
        } for l in logs],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    })
