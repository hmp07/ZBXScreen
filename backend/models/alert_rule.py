"""告警规则模型"""
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from models import Base, utcnow, utcnow


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, default="zabbix_trigger")  # zabbix_trigger / custom_threshold
    datasource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hostgroup_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 空=全部
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="WARNING")  # INFO/WARNING/AVERAGE/HIGH/DISASTER
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # 规则详细配置（JSON）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
