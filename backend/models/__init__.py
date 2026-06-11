from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    """返回 naive UTC datetime（兼容 SQLAlchemy DateTime 列）"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass
