"""
FastAPI 应用入口
挂载路由，配置 CORS，不初始化 Scheduler（Scheduler 由独立进程管理）
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

app = FastAPI(
    title="ZabbixScreen",
    version="1.3.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health_check():
    """健康检查接口（无需认证）"""
    return {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "version": "1.3.0",
        "services": {
            "database": "ok",
        },
    }


@app.get("/api/v1/scheduler-status")
async def scheduler_status():
    """
    Scheduler 健康检查（无需认证）。
    读取 monitor_cache 表最新时间戳，超过 90 秒未更新则标记 degraded。
    """
    from datetime import datetime, timezone, timedelta
    from database import AsyncSessionLocal
    from sqlalchemy import select, func
    from models.monitor_cache import MonitorCache

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.max(MonitorCache.created_at))
            )
            latest = result.scalar()
    except Exception as e:
        import traceback
        print(f"[scheduler-status] Error: {e}\n{traceback.format_exc()}")
        return {
            "status": "error",
            "message": "Unable to check scheduler status",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    fresh = latest is not None and (now - latest.replace(tzinfo=None)).total_seconds() < 90

    return {
        "status": "healthy" if fresh else "degraded",
        "last_cache_at": latest.isoformat() if latest else None,
        "max_age_seconds": (now - latest.replace(tzinfo=None)).total_seconds() if latest else None,
        "threshold_seconds": 90,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# 注册路由
from api.auth import router as auth_router
from api.datasource import router as datasource_router
from api.monitor import router as monitor_router
from api.host import router as host_router
from api.alert import router as alert_router
from api.webhook import router as webhook_router
from api.settings import router as settings_router
from api.network import router as network_router
from api.integrations import router as integrations_router

app.include_router(network_router)
app.include_router(integrations_router)
app.include_router(auth_router)
app.include_router(datasource_router)
app.include_router(monitor_router)
app.include_router(host_router)
app.include_router(alert_router)
app.include_router(webhook_router)
app.include_router(settings_router)
