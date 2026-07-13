"""
ZabbixScreen 配置管理
从环境变量读取配置，提供默认值
"""
import os
import sys
from pydantic_settings import BaseSettings
from pydantic import field_validator


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

    @field_validator("app_secret_key")
    @classmethod
    def check_secret_key_not_default(cls, v: str) -> str:
        if v == "change-this-in-production" or v == "change-this-to-a-random-64-char-string":
            print("=" * 60)
            print("  SECURITY ERROR: APP_SECRET_KEY is set to the default value!")
            print("  Set APP_SECRET_KEY environment variable to a random 64-char string.")
            print("  Generate one with: openssl rand -base64 32")
            print("  The application will now exit.")
            print("=" * 60)
            sys.exit(1)
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
