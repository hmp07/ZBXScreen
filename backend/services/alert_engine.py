"""
告警检测引擎
- 轮询 Zabbix 触发器
- 对比告警规则
- event_id 去重 + 告警风暴抑制
- 触发 Webhook 推送
"""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from database import AsyncSessionLocal
from models.datasource import Datasource
from models.alert_rule import AlertRule
from models.alert_record import AlertRecord
from utils.crypto import decrypt_password
from services.zabbix_client import ZabbixClient, ZabbixAPIError


# 告警风暴聚合窗口（秒）
ALERT_AGGREGATION_WINDOW = 60
ALERT_BATCH_THRESHOLD = 5  # 窗口内 ≥5 条告警触发批量推送


async def check_alerts():
    """告警检测：每 60 秒由调度器调用"""
    print("[ALERT] Checking alerts...")

    async with AsyncSessionLocal() as db:
        # 获取所有启用的数据源
        result = await db.execute(
            select(Datasource).where(Datasource.enabled == True)
        )
        datasources = result.scalars().all()

        all_triggers = []
        for ds in datasources:
            try:
                client = ZabbixClient(ds.url, ds.username, decrypt_password(ds.password_encrypted))
                triggers = await client.get_triggers(active_only=True, min_severity=1)
                # 附加数据源信息
                for t in triggers:
                    t["_datasource_id"] = ds.id
                    t["_datasource_name"] = ds.name
                all_triggers.extend(triggers)
            except ZabbixAPIError as e:
                print(f"[ALERT] Error fetching triggers from '{ds.name}': {e}")
            except Exception as e:
                print(f"[ALERT] Unexpected error for '{ds.name}': {e}")

        # 获取启用的告警规则
        rules_result = await db.execute(
            select(AlertRule).where(AlertRule.enabled == True)
        )
        rules = rules_result.scalars().all()

        # 处理触发器（使用 no_autoflush 避免 SELECT 触发待 INSERT 的 flush）
        new_alerts = []
        existing_active_ids = set()
        # 先批量查询所有已存在的 active event_id
        existing_result = await db.execute(
            select(AlertRecord.event_id).where(AlertRecord.status == "active")
        )
        for row in existing_result:
            existing_active_ids.add(row[0])

        for trigger in all_triggers:
            event_id = trigger.get("triggerid")  # 使用 triggerid 作为 event_id
            if not event_id:
                continue

            # 去重：检查是否已存在 active 状态的记录（批量查询 + set 查找）
            if event_id in existing_active_ids:
                continue

            # 匹配规则
            severity = int(trigger.get("priority", 0))
            if not _match_rules(trigger, rules):
                continue

            # 映射级别
            level_map = {1: "INFO", 2: "WARNING", 3: "AVERAGE", 4: "HIGH", 5: "DISASTER"}
            level = level_map.get(severity, "INFO")

            # 提取主机信息
            hosts = trigger.get("hosts", [])
            host_name = hosts[0].get("host", "unknown") if hosts else "unknown"
            host_id = hosts[0].get("hostid", "") if hosts else ""

            record = AlertRecord(
                event_id=event_id,
                host_id=host_id,
                host_name=host_name,
                trigger_name=trigger.get("description", ""),
                level=level,
                status="active",
                value=str(trigger.get("value", "")),
                first_occurred=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(record)
            existing_active_ids.add(event_id)
            new_alerts.append(record)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            print(f"[ALERT] IntegrityError on commit (duplicate event_id), skipped")

        # 告警风暴检测
        if len(new_alerts) >= ALERT_BATCH_THRESHOLD:
            print(f"[ALERT] Alert storm detected: {len(new_alerts)} new alerts in window, triggering batch webhook")
            # 标记为批量告警批次
            try:
                from services.webhook_sender import send_batched_webhook
                await send_batched_webhook(new_alerts)
            except Exception as e:
                print(f"[ALERT] Batch webhook error: {e}")
        elif new_alerts:
            # 逐条推送
            try:
                from services.webhook_sender import send_single_webhook
                for alert in new_alerts:
                    await send_single_webhook(alert)
            except Exception as e:
                print(f"[ALERT] Webhook error: {e}")

        # 检测告警恢复
        await _check_recoveries(db, datasources, all_triggers)

    print(f"[ALERT] Done: {len(new_alerts)} new alerts from {len(all_triggers)} triggers")


def _match_rules(trigger: dict, rules: list[AlertRule]) -> bool:
    """检查触发器是否匹配任一条告警规则"""
    if not rules:
        return True  # 无规则时默认全部通过

    severity = int(trigger.get("priority", 0))
    trigger_hostgroups = {g.get("groupid") for g in trigger.get("groups", [])}

    for rule in rules:
        # 级别匹配
        level_map = {"INFO": 1, "WARNING": 2, "AVERAGE": 3, "HIGH": 4, "DISASTER": 5}
        min_level = level_map.get(rule.level, 1)
        if severity < min_level:
            continue

        # 主机组匹配
        if rule.hostgroup_id and rule.hostgroup_id not in trigger_hostgroups:
            continue

        return True

    return False


async def _check_recoveries(db, datasources, active_triggers):
    """检测告警恢复：数据库中 active 但 Zabbix 中已不存在的触发器"""
    active_event_ids = {t.get("triggerid") for t in active_triggers}

    result = await db.execute(
        select(AlertRecord).where(AlertRecord.status == "active")
    )
    db_active = result.scalars().all()

    for record in db_active:
        if record.event_id not in active_event_ids:
            record.status = "recovered"
            record.recovered_at = datetime.now(timezone.utc).replace(tzinfo=None)

            # 推送恢复事件
            try:
                from services.webhook_sender import send_recovery_webhook
                await send_recovery_webhook(record)
            except Exception as e:
                print(f"[ALERT] Recovery webhook error: {e}")

    await db.commit()
