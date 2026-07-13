"""
数据库初始化脚本
- 创建所有表
- 插入默认 admin 用户
- 插入默认系统设置
"""
import sys
import os

# 将 backend 目录加入路径（兼容本地开发和容器内部署）
# 本地: scripts/../backend/; 容器: /app/scripts/../ 即 /app/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import asyncio
import bcrypt
from sqlalchemy import text
from database import engine, DATABASE_URL
from models import Base

# 导入所有模型以确保注册到 Base
from models.user import User
from models.datasource import Datasource
from models.alert_rule import AlertRule
from models.alert_record import AlertRecord
from models.webhook_config import WebhookConfig
from models.webhook_log import WebhookLog
from models.settings import Settings
from models.monitor_cache import MonitorCache
from config import settings as app_settings


async def init_db():
    print(f"[init_db] Database: {DATABASE_URL}")

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[init_db] All tables created.")

    # 插入默认数据
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select

    async with AsyncSession(engine) as session:
        # 检查是否已有 admin 用户
        result = await session.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none() is None:
            password_hash = bcrypt.hashpw(
                app_settings.default_admin_password.encode(),
                bcrypt.gensalt()
            ).decode()
            session.add(User(username="admin", password_hash=password_hash))

        # 插入默认系统设置
        default_settings = {
            "SYSTEM_TITLE": "ZBXScreen",
            "DEFAULT_REFRESH_INTERVAL": str(app_settings.default_refresh_interval),
            "DATA_RETENTION_DAYS": str(app_settings.data_retention_days),
            "SYSTEM_SUBTITLE": "ZABBIX · VISUALIZATION",
            "SYSTEM_LOGO": "",
            "THEME": "dark",
            "TZ": app_settings.tz,
        }
        for key, value in default_settings.items():
            result = await session.execute(select(Settings).where(Settings.key == key))
            if result.scalar_one_or_none() is None:
                session.add(Settings(key=key, value=value))

        await session.commit()

    print("[init_db] Default data inserted (admin user + settings).")
    print("[init_db] Database initialization complete.")


if __name__ == "__main__":
    asyncio.run(init_db())
