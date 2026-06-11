"""
APScheduler 定时任务配置
- 由 scheduler_main.py 独立进程启动
- 不在 FastAPI worker 内运行（避免多 worker 重复执行）
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


def start_scheduler():
    """启动调度器（注册所有定时任务）"""
    # 延迟导入避免循环引用
    from services.data_aggregator import aggregate_all_datasources
    from services.alert_engine import check_alerts
    from services.data_cleanup import cleanup_old_records

    # 数据聚合：每 30 秒
    scheduler.add_job(
        aggregate_all_datasources,
        "interval",
        seconds=30,
        id="data_aggregation",
        replace_existing=True,
    )

    # 告警检测：每 60 秒
    scheduler.add_job(
        check_alerts,
        "interval",
        seconds=60,
        id="alert_check",
        replace_existing=True,
    )

    # 数据清理：每日凌晨 3:00
    scheduler.add_job(
        cleanup_old_records,
        "cron",
        hour=3,
        minute=0,
        id="data_cleanup",
        replace_existing=True,
    )

    scheduler.start()
    print("[scheduler] APScheduler started: aggregation(30s), alert(60s), cleanup(daily 03:00)")
