"""告警记录模型"""
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from models import Base, utcnow, utcnow


class AlertRecord(Base):
    __tablename__ = "alert_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="Zabbix eventid，去重用")
    host_id: Mapped[str] = mapped_column(String(50), nullable=False)
    host_name: Mapped[str] = mapped_column(String(200), nullable=False)
    trigger_name: Mapped[str] = mapped_column(String(500), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # INFO/WARNING/AVERAGE/HIGH/DISASTER
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active / recovered
    value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_occurred: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    datasource_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="数据源ID，追溯告警来源")
    webhook_pushed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
