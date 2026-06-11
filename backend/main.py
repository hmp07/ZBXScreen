"""
FastAPI 应用入口
挂载路由，配置 CORS，不初始化 Scheduler（Scheduler 由独立进程管理）
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

app = FastAPI(
    title="ZabbixScreen",
    version="1.0.0",
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
        "version": "1.0.0",
        "services": {
            "database": "ok",
        },
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

app.include_router(network_router)
app.include_router(auth_router)
app.include_router(datasource_router)
app.include_router(monitor_router)
app.include_router(host_router)
app.include_router(alert_router)
app.include_router(webhook_router)
app.include_router(settings_router)
