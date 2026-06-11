"""Webhook 端点配置模型"""
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from models import Base, utcnow, utcnow


class WebhookConfig(Base):
    __tablename__ = "webhook_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="POST")  # POST / PUT
    headers_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # 自定义请求头 JSON
    trigger_levels: Mapped[str | None] = mapped_column(Text, nullable=True)  # 触发级别列表（逗号分隔）
    hostgroup_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # 绑定主机组 ID（逗号分隔，空=全部）
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=3)
    retry_interval: Mapped[int] = mapped_column(Integer, default=10)  # 秒
    timeout: Mapped[int] = mapped_column(Integer, default=10)  # 秒
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
