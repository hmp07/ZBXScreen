"""
Webhook 推送服务
- 标准化 JSON Schema v1.0
- alert / recovery 两种事件类型
- 指数退避重试
- 批量推送（告警风暴场景）
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from sqlalchemy import select

import httpx
from database import AsyncSessionLocal
from models.webhook_config import WebhookConfig
from models.webhook_log import WebhookLog
from models.alert_record import AlertRecord
from config import settings

# 告警风暴聚合窗口（秒），与 alert_engine 保持一致
ALERT_AGGREGATION_WINDOW = 60


def build_alert_payload(alert: AlertRecord) -> dict:
    """构建新告警事件的标准化 payload"""
    return {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "event_type": "alert",
        "event_time": datetime.now(timezone.utc).isoformat() + "Z",
        "source": {
            "system": "ZBXScreen",
            "version": "1.2.0",
            "instance_url": "",
        },
        "host": {
            "id": alert.host_id,
            "name": alert.host_name,
            "visible_name": alert.host_name,
            "ip": "",
        },
        "alert": {
            "trigger_id": alert.event_id,
            "trigger_name": alert.trigger_name,
            "level": alert.level,
            "level_code": _level_to_code(alert.level),
            "current_value": alert.value or "",
            "threshold": "",
            "duration_seconds": 0,
            "first_occurred": alert.first_occurred.isoformat() if alert.first_occurred else "",
        },
        "context": {
            "data_points_interval_seconds": settings.alert_check_interval,
            "active_alerts_count": 0,
        },
    }


def build_recovery_payload(alert: AlertRecord) -> dict:
    """构建告警恢复事件的标准化 payload"""
    return {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "event_type": "recovery",
        "event_time": datetime.now(timezone.utc).isoformat() + "Z",
        "source": {
            "system": "ZBXScreen",
            "version": "1.2.0",
            "instance_url": "",
        },
        "host": {
            "id": alert.host_id,
            "name": alert.host_name,
            "visible_name": alert.host_name,
            "ip": "",
        },
        "alert": {
            "trigger_id": alert.event_id,
            "trigger_name": alert.trigger_name,
            "level": alert.level,
            "level_code": _level_to_code(alert.level),
            "recovered": True,
            "first_occurred": alert.first_occurred.isoformat() if alert.first_occurred else "",
            "recovered_at": alert.recovered_at.isoformat() if alert.recovered_at else "",
            "duration_seconds": 0,
        },
    }


def _level_to_code(level: str) -> int:
    return {"INFO": 1, "WARNING": 2, "AVERAGE": 3, "HIGH": 4, "DISASTER": 5}.get(level, 1)


async def _get_matching_webhooks(alert: AlertRecord) -> list[WebhookConfig]:
    """获取匹配该告警的 Webhook 端点"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WebhookConfig).where(WebhookConfig.enabled == True)
        )
        configs = result.scalars().all()

        matching = []
        for cfg in configs:
            # 按级别过滤
            if cfg.trigger_levels:
                allowed_levels = cfg.trigger_levels.split(",")
                if alert.level not in allowed_levels:
                    continue
            matching.append(cfg)

        return matching


async def _do_post(url: str, method: str, payload: dict, headers: dict, timeout: int) -> tuple[int, int]:
    """执行 HTTP 请求，返回 (http_status_code, response_ms)"""
    start = time.time()
    async with httpx.AsyncClient(timeout=timeout) as client:
        if method.upper() == "PUT":
            resp = await client.put(url, json=payload, headers=headers)
        else:
            resp = await client.post(url, json=payload, headers=headers)
        elapsed_ms = int((time.time() - start) * 1000)
        return resp.status_code, elapsed_ms


async def _retry_with_backoff(url: str, method: str, payload: dict, headers: dict,
                             timeout: int, max_retries: int, retry_interval: int) -> tuple[int, int, int, str | None]:
    """指数退避重试，返回 (status_code, retry_count, response_ms, error_message)"""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            status_code, response_ms = await _do_post(url, method, payload, headers, timeout)
            if 200 <= status_code < 300:
                return status_code, attempt, response_ms, None
            last_error = f"HTTP {status_code}"
        except Exception as e:
            last_error = str(e)

        if attempt < max_retries:
            wait = retry_interval * (2 ** attempt)  # 指数退避：10s, 20s, 40s
            await asyncio.sleep(wait)

    return 0, max_retries, 0, last_error


async def _log_webhook(webhook_id: int, alert_record_id: int, event_id: str,
                       status: str, http_code: int, retry_count: int, response_ms: int,
                       error_message: str | None):
    """记录 Webhook 推送日志"""
    async with AsyncSessionLocal() as db:
        log = WebhookLog(
            webhook_id=webhook_id,
            alert_record_id=alert_record_id,
            event_id=event_id,
            status=status,
            http_status_code=http_code,
            retry_count=retry_count,
            response_ms=response_ms,
            error_message=error_message,
        )
        db.add(log)
        await db.commit()


async def send_single_webhook(alert: AlertRecord):
    """发送单条告警 Webhook"""
    payload = build_alert_payload(alert)
    configs = await _get_matching_webhooks(alert)

    for cfg in configs:
        headers = {"Content-Type": "application/json"}
        if cfg.headers_json:
            try:
                headers.update(json.loads(cfg.headers_json))
            except json.JSONDecodeError:
                pass

        status_code, retry_count, response_ms, error = await _retry_with_backoff(
            cfg.url, cfg.method, payload, headers,
            cfg.timeout or settings.webhook_request_timeout,
            cfg.retry_count, cfg.retry_interval,
        )

        log_status = "success" if status_code and 200 <= status_code < 300 else "failed"
        await _log_webhook(
            cfg.id, alert.id, payload["event_id"],
            log_status, status_code, retry_count, response_ms, error,
        )

    # 标记告警已推送
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AlertRecord).where(AlertRecord.id == alert.id))
        record = result.scalar_one_or_none()
        if record:
            record.webhook_pushed = True
            await db.commit()


async def send_recovery_webhook(alert: AlertRecord):
    """发送告警恢复 Webhook"""
    payload = build_recovery_payload(alert)
    configs = await _get_matching_webhooks(alert)

    for cfg in configs:
        headers = {"Content-Type": "application/json"}
        if cfg.headers_json:
            try:
                headers.update(json.loads(cfg.headers_json))
            except json.JSONDecodeError:
                pass

        status_code, retry_count, response_ms, error = await _retry_with_backoff(
            cfg.url, cfg.method, payload, headers,
            cfg.timeout or settings.webhook_request_timeout,
            cfg.retry_count, cfg.retry_interval,
        )

        log_status = "success" if status_code and 200 <= status_code < 300 else "failed"
        await _log_webhook(
            cfg.id, alert.id, payload["event_id"],
            log_status, status_code, retry_count, response_ms, error,
        )


async def send_batched_webhook(alerts: list[AlertRecord]):
    """批量推送（告警风暴场景）"""
    if not alerts:
        return

    # 合并为一条批量 payload
    batch_payload = {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "event_type": "batch_alert",
        "event_time": datetime.now(timezone.utc).isoformat() + "Z",
        "source": {"system": "ZBXScreen", "version": "1.2.0", "instance_url": ""},
        "batch": {
            "count": len(alerts),
            "aggregation_window_seconds": ALERT_AGGREGATION_WINDOW,
            "alerts": [
                {
                    "host_name": a.host_name,
                    "trigger_name": a.trigger_name,
                    "level": a.level,
                    "level_code": _level_to_code(a.level),
                    "value": a.value,
                }
                for a in alerts
            ],
        },
    }

    # 获取第一个告警匹配的所有 webhook
    first_alert = alerts[0]
    configs = await _get_matching_webhooks(first_alert)

    for cfg in configs:
        headers = {"Content-Type": "application/json"}
        if cfg.headers_json:
            try:
                headers.update(json.loads(cfg.headers_json))
            except json.JSONDecodeError:
                pass

        status_code, retry_count, response_ms, error = await _retry_with_backoff(
            cfg.url, cfg.method, batch_payload, headers,
            cfg.timeout or settings.webhook_request_timeout,
            cfg.retry_count, cfg.retry_interval,
        )

        log_status = "success" if status_code and 200 <= status_code < 300 else "failed"
        await _log_webhook(
            cfg.id, alerts[0].id, batch_payload["event_id"],
            log_status, status_code, retry_count, response_ms, error,
        )
