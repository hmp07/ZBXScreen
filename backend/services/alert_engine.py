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
        failed_datasource_ids = set()  # 记录不可达的数据源，跳过恢复检测
        for ds in datasources:
            try:
                client = ZabbixClient(ds.url, ds.username, decrypt_password(ds.password_encrypted))
                triggers = await client.get_triggers(active_only=True, min_severity=1)
                for t in triggers:
                    t["_datasource_id"] = ds.id
                    t["_datasource_name"] = ds.name
                all_triggers.extend(triggers)
            except ZabbixAPIError as e:
                print(f"[ALERT] Error fetching triggers from '{ds.name}': {e}")
                failed_datasource_ids.add(ds.id)
            except Exception as e:
                print(f"[ALERT] Unexpected error for '{ds.name}': {e}")
                failed_datasource_ids.add(ds.id)

        # 获取启用的告警规则
        rules_result = await db.execute(
            select(AlertRule).where(AlertRule.enabled == True)
        )
        rules = rules_result.scalars().all()

        # 处理触发器
        # event_id = {triggerid}_{lastchange} —— Zabbix 的 lastchange 在触发器
        # 状态变更时更新，持续 PROBLEM 期间不变，天然保证同一问题不重复创建
        new_alerts = []
        existing_active_ids = set()
        # 先批量查询所有已存在的 active event_id
        existing_result = await db.execute(
            select(AlertRecord.event_id).where(AlertRecord.status == "active")
        )
        for row in existing_result:
            existing_active_ids.add(row[0])

        for trigger in all_triggers:
            trigger_id = trigger.get("triggerid")
            if not trigger_id:
                continue

            # 使用 Zabbix 的 lastchange 作为时间戳标识
            lastchange = trigger.get("lastchange", "0")
            if not lastchange or lastchange == "0":
                lastchange = str(int(datetime.now(timezone.utc).timestamp()))

            event_id = f"{trigger_id}_{lastchange}"
            if event_id in existing_active_ids:
                continue

            # 匹配规则
            severity = int(trigger.get("priority", 0))
            if not _match_rules(trigger, rules):
                continue

            level_map = {1: "INFO", 2: "WARNING", 3: "AVERAGE", 4: "HIGH", 5: "DISASTER"}
            level = level_map.get(severity, "INFO")

            hosts = trigger.get("hosts", [])
            host_name = hosts[0].get("host", "unknown") if hosts else "unknown"
            host_id = hosts[0].get("hostid", "") if hosts else ""

            # first_occurred 使用 Zabbix 中问题实际发生时间
            try:
                first_ts = int(lastchange)
                first_occurred = datetime.fromtimestamp(first_ts, tz=timezone.utc).replace(tzinfo=None)
            except (ValueError, OSError):
                first_occurred = datetime.now(timezone.utc).replace(tzinfo=None)

            record = AlertRecord(
                event_id=event_id,
                host_id=host_id,
                host_name=host_name,
                trigger_name=trigger.get("description", ""),
                level=level,
                status="active",
                value=str(trigger.get("value", "")),
                first_occurred=first_occurred,
                datasource_id=trigger.get("_datasource_id"),
            )
            db.add(record)
            existing_active_ids.add(event_id)
            new_alerts.append(record)

        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            print(f"[ALERT] IntegrityError on commit, rolling back batch: {e}")
            # 逐个重试，只跳过冲突记录
            saved = []
            for alert in new_alerts:
                try:
                    db.add(alert)
                    await db.commit()
                    saved.append(alert)
                except IntegrityError:
                    await db.rollback()
                    print(f"[ALERT] Skipped duplicate: {alert.event_id}")
            new_alerts = saved

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

        # 检测告警恢复（跳过不可达数据源的告警）
        await _check_recoveries(db, datasources, all_triggers, failed_datasource_ids)

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


async def _check_recoveries(db, datasources, active_triggers, failed_datasource_ids: set = None):
    """检测告警恢复：数据库中 active 但 Zabbix 中已不存在的触发器。
    排除不可达数据源的告警，避免误恢复。"""
    if failed_datasource_ids is None:
        failed_datasource_ids = set()

    # event_id = {triggerid}_{lastchange}，构建完整的 active event_id 集合
    active_event_ids = set()
    for t in active_triggers:
        tid = t.get("triggerid", "")
        lc = t.get("lastchange", "0")
        if tid and lc and lc != "0":
            active_event_ids.add(f"{tid}_{lc}")

    result = await db.execute(
        select(AlertRecord).where(AlertRecord.status == "active")
    )
    db_active = result.scalars().all()

    # 构建 host_id → datasource_id 映射（用于跳过不可达数据源的恢复）
    if failed_datasource_ids:
        print(f"[ALERT] Skipping recovery check for {len(failed_datasource_ids)} unreachable datasource(s)")

    for record in db_active:
        # 跳过仍在 active 的
        if record.event_id in active_event_ids:
            continue

        # 跳过不可达数据源的告警（数据源离线不应触发恢复）
        if record.host_id:
            # 检查此记录是否属于不可达的数据源
            host_in_failed_ds = False
            for t in active_triggers:
                hosts = t.get("hosts", [])
                for h in hosts:
                    if h.get("hostid") == record.host_id:
                        host_in_failed_ds = True
                        break
                if host_in_failed_ds:
                    break
            if not host_in_failed_ds and failed_datasource_ids:
                # 无法确认主机属于哪个数据源，安全起见：只要有不可达数据源，跳过恢复
                # 避免批量误恢复
                continue

        record.status = "recovered"
        record.recovered_at = datetime.now(timezone.utc).replace(tzinfo=None)

        try:
            from services.webhook_sender import send_recovery_webhook
            await send_recovery_webhook(record)
        except Exception as e:
            print(f"[ALERT] Recovery webhook error: {e}")

    await db.commit()
