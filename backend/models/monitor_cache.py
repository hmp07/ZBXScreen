"""监控数据缓存模型 — 调度器写入，API worker 读取"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from models import Base, utcnow, utcnow


class MonitorCache(Base):
    __tablename__ = "monitor_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    cache_type: Mapped[str] = mapped_column(String(50), nullable=False)  # summary / hosts / top_cpu / top_memory / top_disk / top_network / alerts
    datasource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL=聚合全部
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
