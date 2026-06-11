"""
数据清理服务
- 每日凌晨 3:00 清理过期告警记录和 Webhook 日志
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from database import AsyncSessionLocal
from models.alert_record import AlertRecord
from models.webhook_log import WebhookLog
from config import settings


async def cleanup_old_records():
    """清理超过保留天数的数据"""
    retention_days = settings.data_retention_days
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=retention_days)

    async with AsyncSessionLocal() as db:
        # 清理告警记录
        result1 = await db.execute(
            delete(AlertRecord).where(AlertRecord.created_at < cutoff)
        )
        deleted_alerts = result1.rowcount

        # 清理 Webhook 日志
        result2 = await db.execute(
            delete(WebhookLog).where(WebhookLog.pushed_at < cutoff)
        )
        deleted_logs = result2.rowcount

        await db.commit()

        print(f"[CLEANUP] Deleted {deleted_alerts} alert records and {deleted_logs} webhook logs (older than {retention_days} days)")
