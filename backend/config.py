"""
ZabbixScreen 配置管理
从环境变量读取配置，提供默认值
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT + 加密
    app_secret_key: str = "change-this-in-production"

    # 刷新间隔
    default_refresh_interval: int = 30
    alert_check_interval: int = 60

    # 数据保留
    data_retention_days: int = 30

    # 超时配置
    zabbix_request_timeout: int = 25
    aggregation_total_timeout: int = 28
    webhook_request_timeout: int = 10

    # 管理员
    default_admin_password: str = "Admin@123"

    # 时区
    tz: str = "Asia/Shanghai"

    # 调试
    debug: bool = False

    # JWT 有效期
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # 数据库路径
    db_path: str = "zabbixscreen.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
